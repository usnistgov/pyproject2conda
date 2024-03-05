"""Script to create pythons for use with virtualenvs"""

from __future__ import annotations

import sys
from functools import lru_cache

if sys.version_info < (3, 9):
    msg = "Requires python >= 3.9"
    raise RuntimeError(msg)

import logging

logging.basicConfig()
logger = logging.getLogger(__name__)


@lru_cache
def conda_cmd() -> str:
    """Get conda/mamba command."""
    import shutil

    if shutil.which("mamba"):
        out = "mamba"
    elif shutil.which("conda"):
        out = "conda"
    else:
        msg = "must have mamba or conda on path"
        raise ValueError(msg)
    return out


def create_env_from_spec(
    env_name: str,
    spec: str | list[str],
    flags: str | list[str] | None = None,
) -> None:
    """Create environment from spec."""
    import shlex
    import subprocess

    if not isinstance(spec, str):
        spec = " ".join(spec)

    if flags is not None and not isinstance(flags, str):
        flags = " ".join(flags)

    cmd = f"{conda_cmd()} create -n {env_name} {flags} {spec} "
    logging.info("running %s", cmd)

    out = subprocess.check_call(shlex.split(cmd))
    if out != 0:
        msg = f"failed {cmd}"
        raise RuntimeError(msg)


def create_environments(
    template: str = "test-{version}",
    versions: str | list[str] | None = None,
    flags: str | list[str] | None = None,
    env_map: dict[str, str] | None = None,
) -> None:
    """Create environment."""
    if versions is None:
        versions = ["3.8", "3.9", "3.10", "3.11"]

    if isinstance(versions, str):
        versions = [versions]

    for version in versions:
        env_name = template.format(version=version)

        if env_map and env_name in env_map:
            # environment exists
            logging.info(
                "Skipping environment %s.  Pass `--no-skip` to force recreation.",
                env_name,
            )
        else:
            logging.info("Creating environment %s.", env_name)

            spec = f"python={version}"
            create_env_from_spec(
                env_name=env_name,
                spec=spec,
                flags=flags,
            )


def main() -> None:
    """Main runner."""
    import argparse

    p = argparse.ArgumentParser(
        description="Create conda environments for creating virtualenvs",
    )

    p.add_argument(
        "-p",
        "--python-version",
        type=str,
        default=["3.8", "3.9", "3.10", "3.11"],
        nargs="+",
        help="""
        python versions to create environments for
        """,
    )
    p.add_argument(
        "-t",
        "--template",
        type=str,
        default="python-{version}",
        help="""
        Template for new environments. The available key is "{version}", which
        will expand to the python version being installed.
        """,
    )
    p.add_argument(
        "--yes",
        default=False,
        action="store_true",
        help="pass `--yes` to conda create",
    )
    p.add_argument("--dry", default=False, action="store_true", help="Do dry run.")
    p.add_argument(
        "-v",
        dest="verbose",
        default=False,
        action="store_true",
        help="verbose",
    )
    p.add_argument(
        "--skip",
        default=True,
        action=argparse.BooleanOptionalAction,
    )

    args = p.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    logging.info(f"{args=}")  # noqa: G004

    flags: list[str] = []
    if args.yes:
        flags.append("--yes")
    if args.dry:
        flags.append("--dry")

    if args.skip:
        from .common_utils import get_conda_environment_map

        env_map = get_conda_environment_map()
    else:
        env_map = None

    create_environments(
        versions=args.python_version,
        template=args.template,
        flags=flags,
        env_map=env_map,
    )


if __name__ == "__main__":
    if __package__ is None:  # pyright: ignore[reportUnnecessaryComparison]
        # Magic to be able to run script as either
        #   $ python -m tools.create_python
        # or
        #   $ python tools/create_python.py
        from pathlib import Path

        here = Path(__file__).absolute()
        __package__ = here.parent.name

    main()
