"""Check distribution versions."""
# pyright: reportUnknownMemberType=false,reportUnknownVariableType=false
# ruff: noqa: T201

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pkginfo",
# ]
# ///
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

import pkginfo  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]  # pylint: disable=import-error

if TYPE_CHECKING:
    from collections.abc import Sequence


def _get_parser() -> ArgumentParser:
    parser = ArgumentParser()
    _ = parser.add_argument(
        "--version",
        default="0.1.0",
    )
    _ = parser.add_argument("paths", nargs="+", type=Path)
    return parser


def _get_version(path: Path) -> str:
    if path.suffix == ".whl":
        return pkginfo.Wheel(path).version  # type: ignore[no-any-return]
    return pkginfo.SDist(path).version  # type: ignore[no-any-return]


def main(args: Sequence[str] | None = None) -> int:
    """Main script"""
    parser = _get_parser()
    options = parser.parse_args(args)

    target_version: str = options.version.lstrip("v")

    print("target_version:", target_version)
    code = 0
    for path in options.paths:
        if (version := _get_version(path)) != target_version:
            code += 1
        print(f"{path} {version=}")

    print("Success: versions match" if not code else "Error: version mismatch")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
