"""Command-line entry point for ASTRA room reconstruction."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="astra-house",
        description="Build verifiable room reconstruction artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "build-logical",
        help="Build the logical room model and review artifacts.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command is None:
        parser.print_help(file=sys.stderr)
        return 2
    return 0


def console_main() -> None:
    """Installed console-script wrapper."""
    raise SystemExit(main())


if __name__ == "__main__":
    console_main()
