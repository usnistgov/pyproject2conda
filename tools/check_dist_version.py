"""Check distribution versions."""
# pyright: reportUnknownMemberType=false,reportUnknownVariableType=false

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pkginfo",
# ]
# ///
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

import pkginfo  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]  # pylint: disable=import-error

if TYPE_CHECKING:
    from collections.abc import Sequence


def _get_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "--version",
        default="0.1.0",
    )
    parser.add_argument("paths", nargs="+", type=Path)
    return parser


def _get_version(path: Path) -> str:
    if path.suffix == ".whl":
        return pkginfo.Wheel(path).version  # type: ignore[no-any-return]
    return pkginfo.SDist(path).version  # type: ignore[no-any-return]


def main(args: Sequence[str] | None = None) -> int:
    """Main script"""
    parser = _get_parser()
    options = parser.parse_args(args)

    for path in options.paths:
        if (version := _get_version(path)) != options.version:
            msg = f"{version=} not equal to specified version={options.version}"
            raise ValueError(msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
