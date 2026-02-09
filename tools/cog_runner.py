"""Script to run cog on files with optional linters/formatters."""

from __future__ import annotations

import logging
import shlex
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence


FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("cog_runner")


def _run_cog(
    *,
    files: Iterable[str],
    extras: Iterable[str],
    use_uvx: bool = False,
    env: Mapping[str, str] | None = None,
    constraints: str,
    constraints_locked: str,
) -> None:
    import os

    env = dict(os.environ, **({} if env is None else env))

    # unset PRE_COMMIT
    _ = env.pop("PRE_COMMIT")

    command: list[str]
    if use_uvx:
        command = ["uvx", "--from=cogapp"]
        if constraints_locked:
            constraints = constraints_locked
        if constraints:
            command.append(f"--constraints={constraints}")
    else:
        command = ["uv", "run"]

    command = [
        *command,
        *extras,
        "cog",
        "-rP",
        *files,
    ]

    logger.info(shlex.join(command))

    from subprocess import check_call

    _ = check_call(command, env=env)


def _run_linters(
    files: Sequence[str],
    linters: Iterable[str],
    check: bool,
    constraints: str,
) -> None:
    from subprocess import run

    for linter in linters:
        command = [
            "uvx",
            *([f"--constraints={constraints}"] if constraints else []),
            "prek",
            "run",
            linter,
            "--files",
            *files,
        ]

        logger.info(shlex.join(command))
        _ = run(command, check=check)


def main(args: Sequence[str] | None = None) -> int:
    """Main script."""
    parser = ArgumentParser(description="run cog and linters")
    _ = parser.add_argument(
        "--use-uvx",
        action="store_true",
        help="use uvx instead of uv run",
    )
    _ = parser.add_argument(
        "--lint",
        dest="linters",
        action="append",
        default=[],
        help="linters (if fail, command fails)",
    )
    _ = parser.add_argument(
        "--format",
        dest="formatters",
        action="append",
        default=[],
        help="formatters (if fail, command does not fail)",
    )
    _ = parser.add_argument(
        "--constraints",
        default="requirements/uvx-tools.txt",
        help="Constraints used with ``uv run``. Pass '' for no constraints",
    )
    _ = parser.add_argument(
        "--constraints-locked",
        default="requirements/lock/uvx-tools.txt",
        help="Constraints used with ``uvx cog``. Pass '' for no constraints",
    )
    _ = parser.add_argument(
        "files",
        nargs="+",
    )

    opts, extras = parser.parse_known_args(args)

    for path in opts.files:
        if not Path(path).exists():
            msg = f"{path} does not exist.  Remember that options should passed with --name=value and not --name value"
            raise ValueError(msg)

    logger.debug("opts: %s", opts)
    logger.debug("extras: %s", extras)

    _run_cog(
        files=opts.files,
        extras=extras,
        use_uvx=opts.use_uvx,
        env={"COLUMNS": "90", "NO_COLOR": "1"},
        constraints=opts.constraints,
        constraints_locked=opts.constraints_locked,
    )

    _run_linters(
        opts.files,
        opts.formatters,
        check=False,
        constraints=opts.constraints,
    )

    _run_linters(
        opts.files,
        opts.linters,
        check=True,
        constraints=opts.constraints,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
