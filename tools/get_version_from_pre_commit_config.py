# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyyaml>=6.0.3",
# ]
# ///
"""Get repo version for repo from .pre-commit-config.yaml"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def _get_version(path: Path, url: str) -> str:
    import yaml  # type: ignore[import-untyped] # pyright: ignore[reportMissingModuleSource] # pyrefly: ignore[missing-import] # ty: ignore[unresolved-import] # pylint: disable=import-error

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for repo in data.get("repos", []):
        if repo.get("repo") == url and "rev" in repo:
            out = repo["rev"]
            if isinstance(out, str):
                return out.lstrip("v")

    msg = f"Failed to find {url}"
    raise ValueError(msg)


def _get_args(argv: Sequence[str] | None = None) -> tuple[Path, str]:
    from argparse import ArgumentParser

    parser = ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--config",
        type=Path,
        default=".pre-commit-config.yaml",
        help="pre-commit config file",
    )
    _ = parser.add_argument("repo", type=str, help="repo name to extract version for")

    opts = parser.parse_args(argv)

    return opts.config, opts.repo


def main(argv: Sequence[str] | None = None) -> bool:
    """Main function."""
    config, url = _get_args(argv)

    version = _get_version(config, url)

    print(version)  # ruff: ignore[print]

    return False


if __name__ == "__main__":
    raise SystemExit(main())
