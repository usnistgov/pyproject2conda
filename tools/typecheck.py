"""
Interface to type checkers (mypy, (based)pyright, ty, pyrefly) to handle python-version and python-executable.

This allows for running centrally installed (or via uvx) type checkers against a given virtual environment.
"""
# pylint: disable=duplicate-code

from __future__ import annotations

import logging
import os
import shlex
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger("typecheck")


# * Utilities -----------------------------------------------------------------
def _setup_logging(
    verbosity: int = 0,
) -> None:  # pragma: no cover
    """Setup logging."""
    level_number = max(0, logging.WARNING - 10 * verbosity)
    logger.setLevel(level_number)

    # Silence noisy loggers
    logging.getLogger("sh").setLevel(logging.WARNING)


# * Runner --------------------------------------------------------------------
def _uvx_run(
    *args: str,
    env: Mapping[str, str] | None = None,
    dry_run: bool = False,
) -> int:
    import subprocess

    cleaned_args = ["uvx", *(os.fsdecode(arg) for arg in args)]
    full_cmd = shlex.join(cleaned_args)
    logger.info("Running %s", full_cmd)

    if dry_run:
        return 0

    r = subprocess.run(cleaned_args, check=False, env=env)

    if returncode := r.returncode:
        logger.error("Command %s failed with exit code %s", full_cmd, returncode)
        # msg = f"Returned code {returncode}"  # noqa: ERA001
        # raise RuntimeError(msg)  # noqa: ERA001
    return returncode


def _is_pyright_like(checker: str) -> bool:
    return checker in {"pyright", "basedpyright"}


def _run_checker(
    checker: str,
    *args: str,
    python_version: str,
    python_executable: str,
    constraints: list[Path],
    dry_run: bool = False,
) -> int:
    if _is_pyright_like(checker):
        python_flag = "pythonpath"
    elif checker == "ty":
        python_flag = "python"
    elif checker == "pyrefly":
        python_flag = "python-interpreter"
    else:
        # default to mypy
        python_flag = "python-executable"

    version_flag = "pythonversion" if _is_pyright_like(checker) else "python-version"

    check_subcommand = ["check"] if checker in {"ty", "pyrefly"} else []

    if checker == "ty":
        # ty prefers `--python` flag pointing to environonmentf
        python_executable = str(Path(python_executable).parent.parent)

    python_flags = (
        *check_subcommand,
        f"--{python_flag}={python_executable}",
        f"--{version_flag}={python_version}",
    )

    return _uvx_run(
        *(f"--constraints={c}" for c in constraints),
        *(["--with", "orjson"] if checker == "mypy" else []),
        checker,
        *python_flags,
        *args,
        dry_run=dry_run,
    )


# * Application ---------------------------------------------------------------
def get_parser() -> ArgumentParser:
    """Get argparser."""
    parser = ArgumentParser(description="Run executable using uvx.")
    parser.add_argument(
        "--python-executable",
        dest="python_executable",
        default=None,  # Path(sys.executable),
        type=Path,
        help="""
        Path to python executable. Defaults to ``sys.executable``. This is
        passed to `--python-executable` in mypy and `--pythonpath` in (based)pyright.
        """,
    )
    parser.add_argument(
        "--python-version",
        dest="python_version",
        default=None,
        type=str,
        help="""
        Python version (x.y) to typecheck against. Defaults to
        ``{sys.version_info.major}.{sys.version_info.minor}``. This is passed
        to ``--pythonversion`` in pyright and ``--python-version`` otherwise.
        """,
    )
    parser.add_argument(
        "-c",
        "--constraints",
        dest="constraints",
        default=[],
        action="append",
        type=Path,
        help="Requirements (requirements.txt) specs for checker.  Can specify multiple times.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        default=0,
        help="Set verbosity level.  Pass multiple times to up level.",
    )
    parser.add_argument(
        "-x",
        "--checker",
        dest="checkers",
        default=[],
        action="append",
        choices=["mypy", "pyright", "basedpyright", "ty", "pyrefly"],
        help="Type checker to use.",
    )
    parser.add_argument(
        "--allow-errors",
        action="store_true",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    parser.add_argument(
        "args",
        type=str,
        nargs="*",
        default=[],
        help="extra arguments to checker(s)",
    )

    return parser


def main(args: Sequence[str] | None = None) -> int:
    """Main script."""
    parser = get_parser()
    options = parser.parse_args(args)

    _setup_logging(options.verbosity)

    python_version = (
        options.python_version or f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    python_executable = options.python_executable or sys.executable

    logger.debug("checkers: %s", options.checkers)
    logger.debug("args: %s", options.args)

    code = 0
    for checker in options.checkers:
        code += _run_checker(
            checker,
            *options.args,
            python_version=python_version,
            python_executable=python_executable,
            constraints=options.constraints,
            dry_run=options.dry_run,
        )

    return 0 if options.allow_errors else code


if __name__ == "__main__":
    sys.exit(main())
