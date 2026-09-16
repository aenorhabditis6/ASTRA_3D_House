"""Deterministic manifests for immutable reconstruction inputs."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import ValidationError

SCHEMA_VERSION = "1.0"
HASH_BLOCK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Return the lower-case SHA-256 digest of *path* without loading it whole."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(HASH_BLOCK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative_path(raw_path: object) -> PurePosixPath:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValidationError("manifest asset path must be a non-empty string")
    path = PurePosixPath(raw_path)
    if path.is_absolute():
        raise ValidationError(f"manifest asset path must be relative: {raw_path}")
    if ".." in path.parts:
        raise ValidationError(f"manifest asset path contains parent traversal: {raw_path}")
    if path.as_posix() != raw_path or "\\" in raw_path:
        raise ValidationError(f"manifest asset path must use normalized POSIX form: {raw_path}")
    return path


def _resolve_under_root(root: Path, relative: PurePosixPath) -> Path:
    root = Path(root).resolve()
    candidate = root.joinpath(*relative.parts).resolve()
    if not candidate.is_relative_to(root):
        raise ValidationError(f"manifest asset escapes root: {relative.as_posix()}")
    return candidate


def build_manifest(root: Path, paths: tuple[Path, ...]) -> dict[str, Any]:
    """Build a stable manifest for files located below *root*.

    Paths may be root-relative or absolute paths below ``root``.  The result is
    sorted by normalized POSIX path so repeated runs are byte-stable once
    serialized with sorted keys.
    """
    root = Path(root).resolve()
    assets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for supplied in paths:
        supplied = Path(supplied)
        candidate = supplied if supplied.is_absolute() else root / supplied
        try:
            relative = candidate.resolve().relative_to(root)
        except ValueError as error:
            raise ValidationError(f"source is outside manifest root: {supplied}") from error
        normalized = PurePosixPath(relative.as_posix())
        key = normalized.as_posix()
        if key in seen:
            raise ValidationError(f"duplicate manifest asset path: {key}")
        seen.add(key)
        if not candidate.is_file():
            raise ValidationError(f"manifest asset is missing or not a file: {key}")
        assets.append(
            {
                "path": key,
                "bytes": candidate.stat().st_size,
                "sha256": sha256_file(candidate),
            }
        )
    assets.sort(key=lambda asset: asset["path"])
    return {"schema_version": SCHEMA_VERSION, "assets": assets}


def verify_manifest(root: Path, manifest: Mapping[str, Any]) -> None:
    """Raise :class:`ValidationError` unless every manifest asset is intact."""
    if not isinstance(manifest, Mapping):
        raise ValidationError("manifest must be a JSON object")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(
            f"unsupported manifest schema_version: {manifest.get('schema_version')!r}"
        )
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValidationError("manifest assets must be a list")

    seen: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            raise ValidationError(f"manifest asset {index} must be an object")
        relative = _safe_relative_path(asset.get("path"))
        key = relative.as_posix()
        if key in seen:
            raise ValidationError(f"duplicate manifest asset path: {key}")
        seen.add(key)

        path = _resolve_under_root(Path(root), relative)
        if not path.is_file():
            raise ValidationError(f"{key}: source file is missing")

        expected_bytes = asset.get("bytes")
        if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool):
            raise ValidationError(f"{key}: bytes must be an integer")
        actual_bytes = path.stat().st_size
        if actual_bytes != expected_bytes:
            raise ValidationError(
                f"{key}: byte-size mismatch (expected {expected_bytes}, got {actual_bytes})"
            )

        expected_digest = asset.get("sha256")
        if (
            not isinstance(expected_digest, str)
            or len(expected_digest) != 64
            or any(character not in "0123456789abcdef" for character in expected_digest)
        ):
            raise ValidationError(f"{key}: SHA-256 must be 64 lower-case hex digits")
        actual_digest = sha256_file(path)
        if actual_digest != expected_digest:
            raise ValidationError(
                f"{key}: SHA-256 mismatch (expected {expected_digest}, got {actual_digest})"
            )
