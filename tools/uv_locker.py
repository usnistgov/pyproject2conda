"""
Automate creation of locked requirements.txt and scripts.py

This uses a [tool.uv-locker] section of `pyproject.toml`
"""
# /// script
# requires-python = ">=3.11"
# ///
# pylint: disable=missing-class-docstring

from __future__ import annotations

import logging
import shlex
import subprocess
from argparse import ArgumentParser
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import tomllib

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any

FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("uv-locker")


@lru_cache
def _get_min_python_version() -> str:
    data: list[str] = (
        tomllib
        .loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        .get("project", {})
        .get("classifiers", [])
    )
    version: str | None = next(
        (
            c.split()[-1]
            for c in data
            if c.startswith("Programming Language :: Python :: 3.")
        ),
        None,
    )
    if version is None:
        msg = (
            "Could not determine minimum Python version: no "
            "'Programming Language :: Python :: 3.x' classifier found in pyproject.toml."
        )
        raise RuntimeError(msg)
    return version


@lru_cache
def _get_default_version() -> str:
    return Path(".python-version").read_text(encoding="utf-8").strip()


def _check_call(args: Sequence[str], **kwargs: Any) -> None:
    logger.info("Run %s", shlex.join(args))
    _ = subprocess.check_call(args, **kwargs)


@dataclass
class _Script:
    path: Path
    options: list[str]

    @classmethod
    def from_data(cls, data: str | dict[str, Any]) -> _Script:
        if isinstance(data, str):
            return cls(path=Path(data), options=[])
        return cls(path=Path(data["path"]), options=data.get("options", []))

    def lock(
        self,
        extra_options: Sequence[str],
    ) -> None:

        options = [
            "uv",
            "lock",
            *self.options,
            *extra_options,
            f"--script={self.path}",
        ]
        _check_call(options)


@dataclass
class _Requirement:
    path: Path
    options: list[str]
    python: str | None  # `--python-version`.  {"min", "default", python_version}
    output_file: Path

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> _Requirement:
        python = data.get("python")
        if python == "min":
            python = _get_min_python_version()
        elif python == "default":
            python = _get_default_version()

        options = data.get("options", [])
        if python is not None:
            options.append(f"--python-version={python}")

        return cls(
            path=Path(data["path"]),
            options=options,
            python=python,
            output_file=Path(data["output-file"]),
        )

    def lock(
        self,
        extra_options: Sequence[str],
    ) -> None:
        options = [
            "uv",
            "pip",
            "compile",
            *self.options,
            *extra_options,
            f"--output-file={self.output_file}",
            str(self.path),
        ]
        _check_call(options)


@dataclass
class _Config:
    scripts: list[_Script]
    requirements: list[_Requirement]
    pip_compile_config_file: Path | None
    quiet: bool = True  # If true, include `--quiet` in uv pip compile

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> _Config:
        return cls(
            scripts=[_Script.from_data(d) for d in data.get("scripts", [])],
            requirements=[
                _Requirement.from_data(d) for d in data.get("requirements", [])
            ],
            pip_compile_config_file=_path_or_none(data.get("pip-compile-config-file")),
            quiet=data.get("quiet", True),
        )

    @classmethod
    def from_pyproject_path(cls, path: Path) -> _Config:
        data = (
            tomllib
            .loads(path.read_text(encoding="utf-8"))
            .get("tool", {})
            .get("uv-locker", {})
        )
        return cls.from_data(data)

    def get_extra_options(self, upgrade: bool, options: Iterable[str]) -> list[str]:
        return [
            *(
                [f"--config-file={self.pip_compile_config_file}"]
                if self.pip_compile_config_file
                else []
            ),
            *(["--quiet"] if self.quiet else []),
            *(["--upgrade"] if upgrade else []),
            *options,
        ]


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

    if not (lock or sync):
        return

    # Execute uv lock or sync command.
    command = [
        "uv",
        ("sync" if sync else "lock"),
        *(["--no-active"] if sync else []),
        *(["--upgrade"] if upgrade else []),
        *uv_options,
    ]
    _check_call(command)


def _path_or_none(x: str | None) -> Path | None:
    if x is None:
        return x
    path = Path(x)
    return path if path.exists() else None


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
        "--all-files",
        dest="all_files",
        action="store_true",
        help="Run lock all requirements and scripts in config.",
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
        help="""
        Which paths to consider.  Only paths found in ``pyproject.toml:tool.uv-locker.scripts/requirements`` will be processed.
        """,
    )

    opts = parser.parse_args(args)

    uv_options: list[str] = opts.uv_options
    _maybe_lock_or_sync(
        lock=opts.lock,
        sync=opts.sync,
        sync_or_lock=opts.sync_or_lock,
        upgrade=opts.upgrade,
        uv_options=uv_options,
    )

    config = _Config.from_pyproject_path(Path("pyproject.toml"))
    paths = set(opts.paths)

    extra_options = config.get_extra_options(upgrade=opts.upgrade, options=uv_options)
    # NOTE: do this so can could have same path for multiple outputs
    for script in config.scripts:
        if opts.all_files or script.path in paths:
            script.lock(extra_options)

    for requirement in config.requirements:
        if opts.all_files or requirement.path in paths:
            requirement.lock(extra_options)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
