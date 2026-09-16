"""Atomic JSON persistence for room models."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import ValidationError
from .model import RoomModel


def save_room(model: RoomModel, path: Path) -> None:
    """Validate and atomically save a room model as stable JSON."""
    model.validate()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(
                model.to_dict(),
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_room(path: Path) -> RoomModel:
    """Load and validate a room model from JSON."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot load room {path}: {error}") from error
    try:
        return RoomModel.from_dict(data)
    except ValidationError as error:
        raise ValidationError(f"invalid room {path}: {error}") from error
