"""Create requirements/lock/*.txt files from requirements/*.txt files."""

from __future__ import annotations

import logging
import shlex
import sys
from argparse import ArgumentParser
from pathlib import Path
from subprocess import check_call
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("requirements_lock")

if sys.version_info < (3, 11):
    msg = "python>3.11 required"  # pyright: ignore[reportUnreachable]
    raise RuntimeError(msg)


USE_PYTHON_MIN_VERSION = [
    "test.txt",
    "test-extras.txt",
    "typecheck.txt",
    "uvx-tools.txt",
]
USE_NO_DEPS = ["uvx-tools.txt", "pre-commit-additional-dependencies.txt"]


def _get_min_python_version() -> str:
    with Path("pyproject.toml").open("rb") as f:
        import tomllib

        return next(  # type: ignore[no-any-return]
            c.split()[-1]
            for c in tomllib.load(f)["project"]["classifiers"]
            if c.startswith("Programming Language :: Python :: 3.")
        )


def _get_default_version() -> str:
    return Path(".python-version").read_text(encoding="utf-8").strip()


def _lock_files(
    paths: Iterable[Path],
    min_python_version: str,
    default_python_version: str,
    pip_compile_config_file: Path | None,
    upgrade: bool,
    uv_options: Sequence[str],
) -> None:
    for path in paths:
        python_version = (
            min_python_version
            if path.name in USE_PYTHON_MIN_VERSION
            else default_python_version
        )

        lockpath = path.parent / "lock" / path.name

        options = [
            "uv",
            "pip",
            "compile",
            "--universal",
            *(
                [f"--config-file={pip_compile_config_file}"]
                if pip_compile_config_file
                else []
            ),
            "-q",
            # don't include dependencies for uvx-tools
            *(["--no-deps", "--no-strip-extras"] if path.name in USE_NO_DEPS else []),
            "--python-version",
            python_version,
            *(["--upgrade"] if upgrade else []),
            *uv_options,
            str(path),
            "-o",
            str(lockpath),
        ]

        logger.info(shlex.join(options))
        _ = check_call(options)


def _maybe_lock_or_sync(
    lock: bool,
    sync: bool,
    sync_or_lock: bool,
    upgrade: bool,
    uv_options: Sequence[str],
) -> None:
    if sync_or_lock:
        if Path(".venv").exists():
            sync = True
        else:
            lock = True

    if lock or sync:
        command = [
            "uv",
            ("sync" if sync else "lock"),
            *(["--no-active"] if sync else []),
            *(["--upgrade"] if upgrade else []),
            *uv_options,
        ]

        logger.info(shlex.join(command))
        _ = check_call(command)


def main(args: Sequence[str] | None = None) -> int:
    """Main script."""
    # pylint: disable=duplicate-code
    parser = ArgumentParser()
    _ = parser.add_argument(
        "--upgrade",
        "-U",
        action="store_true",
        help="Upgrade requirements",
    )
    _ = parser.add_argument(
        "--pip-compile-config-file",
        default=None,
        type=Path,
        help="""
        Config file to use when invoking ``uv pip compile``.
        Useful if you want ``pip compile`` to have different settings from ``uv sync``.
        For example, you could use ``--pip-compile-config-file=requirements/uv.toml`` with
        pip-compile specific settings in ``requirements/uv.toml``.
        """,
    )
    _ = parser.add_argument(
        "--all-files",
        dest="all_files",
        action="store_true",
        help="Run ``uv pip compile`` on all files.",
    )
    _ = parser.add_argument(
        "--lock",
        action="store_true",
        help="Run ``uv lock``",
    )
    _ = parser.add_argument(
        "--sync",
        action="store_true",
        help="Run ``uv sync`` (overrides ``uv lock``)",
    )
    _ = parser.add_argument(
        "--sync-or-lock",
        action="store_true",
        help="""
        If directory ``.venv`` exists, run ``uv sync``.  Otherwise run ``uv lock``.
        Overridden by ``--sync``.
        """,
    )
    _ = parser.add_argument(
        "--uv-options",
        default="",
        type=shlex.split,
        help="""
        extra options to uv lock/sync/pip compile
        """,
    )
    _ = parser.add_argument(
        "paths",
        type=Path,
        nargs="*",
    )

    opts = parser.parse_args(args)

    _maybe_lock_or_sync(
        lock=opts.lock,
        sync=opts.sync,
        sync_or_lock=opts.sync_or_lock,
        upgrade=opts.upgrade,
        uv_options=opts.uv_options,
    )

    _lock_files(
        Path("./requirements").glob("*.txt") if opts.all_files else opts.paths,
        min_python_version=_get_min_python_version(),
        default_python_version=_get_default_version(),
        upgrade=opts.upgrade,
        pip_compile_config_file=opts.pip_compile_config_file,
        uv_options=opts.uv_options,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
