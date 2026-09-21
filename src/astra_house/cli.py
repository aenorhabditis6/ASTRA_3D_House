"""Command-line entry point for ASTRA room reconstruction."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from .errors import ValidationError
from .io import save_room
from .logical_room import build_logical_room
from .manifest import verify_manifest
from .measurements import MeasurementSet
from .plan import PlanAnnotation
from .review import write_plan_overlay, write_quality_report

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
Runner = Callable[[list[str]], object]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="astra-house",
        description="Build verifiable room reconstruction artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command")
    build_parser = subparsers.add_parser(
        "build-logical",
        help="Build the logical room model and review artifacts.",
    )
    build_parser.add_argument(
        "--project",
        required=True,
        type=Path,
        help="Project directory containing manifest.json and plan-annotation.json.",
    )
    build_parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: build/<project-name>).",
    )
    build_parser.add_argument(
        "--blender",
        required=True,
        type=Path,
        help="Path to the Blender executable.",
    )
    return parser


def _subprocess_runner(command: list[str]) -> None:
    subprocess.run(command, check=True)


def build_logical_project(
    *,
    project_dir: Path,
    output_dir: Path,
    blender: Path,
    runner: Runner = _subprocess_runner,
) -> Path:
    """Build every logical-room artifact and return the master Blend path."""
    project_dir = _resolve_from_repository(project_dir)
    output_dir = _resolve_from_repository(output_dir)
    blender = Path(blender).expanduser()

    manifest_path = project_dir / "manifest.json"
    annotation_path = project_dir / "plan-annotation.json"
    measurements_path = project_dir / "measurements.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot load manifest {manifest_path}: {error}") from error
    verify_manifest(REPOSITORY_ROOT, manifest)

    try:
        annotation_data = json.loads(annotation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(
            f"cannot load plan annotation {annotation_path}: {error}"
        ) from error
    annotation = PlanAnnotation.from_dict(annotation_data)
    try:
        measurements_data = json.loads(measurements_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(
            f"cannot load measurements {measurements_path}: {error}"
        ) from error
    measurements = MeasurementSet.from_dict(measurements_data)
    room = build_logical_room(annotation, measurements)
    room_path = project_dir / "room.json"
    save_room(room, room_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = output_dir / "plan-review.svg"
    report_path = output_dir / "quality-report.json"
    blend_path = output_dir / "house_master.blend"
    glb_path = output_dir / "house.glb"
    write_plan_overlay(annotation, room, overlay_path)
    write_quality_report(annotation, room, report_path)

    builder_path = REPOSITORY_ROOT / "blender" / "build_scene.py"
    command = [
        str(blender),
        "--background",
        "--factory-startup",
        "--python-exit-code",
        "1",
        "--python",
        str(builder_path),
        "--",
        str(room_path),
        str(blend_path),
        str(glb_path),
    ]
    runner(command)

    missing = [path.name for path in (blend_path, glb_path) if not path.is_file()]
    if missing:
        raise ValidationError(
            "Blender completed without required outputs: " + ", ".join(missing)
        )
    return blend_path


def _resolve_from_repository(path: Path) -> Path:
    path = Path(path).expanduser()
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command is None:
        parser.print_help(file=sys.stderr)
        return 2
    if args.command == "build-logical":
        output = args.output or Path("build") / args.project.name
        try:
            blend_path = build_logical_project(
                project_dir=args.project,
                output_dir=output,
                blender=args.blender,
            )
        except ValidationError as error:
            print(f"astra-house: validation failed: {error}", file=sys.stderr)
            return 2
        except subprocess.CalledProcessError as error:
            print(
                f"astra-house: Blender failed with exit code {error.returncode}",
                file=sys.stderr,
            )
            return 3
        except OSError as error:
            print(f"astra-house: could not start Blender: {error}", file=sys.stderr)
            return 3
        print(blend_path)
        return 0
    raise AssertionError(f"unhandled command {args.command!r}")


def console_main() -> None:
    """Installed console-script wrapper."""
    raise SystemExit(main())


if __name__ == "__main__":
    console_main()
