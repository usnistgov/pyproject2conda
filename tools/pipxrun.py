"""
A script to invoke utilities from either pipx or from local installs.

I got tired of installing mypy/pyright in a million venvs. I got around this
for pyright using a central install and running in an activated venv. You can
do likewise with mypy, by passing `--python-executable`. I got the bright idea
to use `pipx` to manage mypy and pyright. But when working from my own machine,
I'd already have the type checkers installed centrally. This script automates
running these tools. It does the following:

* Optionally can set the `specification` (i.e., "mypy==1.2.3...", etc)
* Will check if the specification is installed. If it is, use it (unless pass
 `-x`). Otherwise, run the command via `pipx` (something like `pipx run
 mypy==1.2.3...`)
* You can set the specifications from a `requirements.txt` file. So you can use
  tools like `pip-compile` to manage the versions.
* Makes the `--python-executable` and `--pythonpath` flags to mypy and pyright
  the same. Defaults to using `sys.executable` from the python running this
* Also sets `--python-version` and `--pythonversion` in mypy and pyright
* For other tools, just run them from pipx or installed.
"""

from __future__ import annotations

import locale
import logging
import os
import re
import shlex
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from packaging.requirements import Requirement
from packaging.version import Version

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterable, Iterator, Mapping, Sequence
    from types import ModuleType

# Optional imports
colorlog: ModuleType | None
try:
    import colorlog
except ImportError:
    colorlog = None


# * Logger --------------------------------------------------------------------
# Taken from nox.logger (https://github.com/wntrblm/nox/tree/main/nox/logger.py)

SUCCESS = 25
OUTPUT = logging.DEBUG - 1


def _get_format(color: bool, add_timestamp: bool) -> str:
    if color and colorlog:
        if add_timestamp:
            return "%(cyan)s%(name)s > [%(asctime)s] %(log_color)s%(message)s"
        return "%(cyan)s%(name)s > %(log_color)s%(message)s"

    if add_timestamp:
        return "%(name)s > [%(asctime)s] %(message)s"

    return "%(name)s > %(message)s"


class PipxRunFormatter(logging.Formatter):
    """Custom formatter."""

    def __init__(self, add_timestamp: bool = False) -> None:
        super().__init__(fmt=_get_format(color=False, add_timestamp=add_timestamp))
        self._simple_fmt = logging.Formatter("%(message)s")

    def format(self, record: Any) -> str:
        if record.levelname == "OUTPUT":
            return self._simple_fmt.format(record)
        return super().format(record)


if colorlog:

    class PipxRunColoredFormatter(colorlog.ColoredFormatter):  # type: ignore[misc,name-defined]
        """Colored formatter."""

        def __init__(
            self,
            datefmt: Any = None,
            style: Any = None,
            log_colors: Any = None,
            reset: bool = True,
            secondary_log_colors: Any = None,
            add_timestamp: bool = False,
        ) -> None:
            super().__init__(  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
                fmt=_get_format(color=True, add_timestamp=add_timestamp),
                datefmt=datefmt,
                style=style,
                log_colors=log_colors,
                reset=reset,
                secondary_log_colors=secondary_log_colors,
            )
            self._simple_fmt = logging.Formatter("%(message)s")

        def format(self, record: Any) -> str:
            if record.levelname == "OUTPUT":
                return self._simple_fmt.format(record)
            return super().format(record)  # type: ignore[no-any-return]


class LoggerWithSuccessAndOutput(logging.getLoggerClass()):  # type: ignore[misc]
    """Custom Logger."""

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        logging.addLevelName(SUCCESS, "SUCCESS")
        logging.addLevelName(OUTPUT, "OUTPUT")

    def success(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(SUCCESS):  # pragma: no cover
            self._log(SUCCESS, msg, args, **kwargs)

    def output(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(OUTPUT):  # pragma: no cover
            self._log(OUTPUT, msg, args, **kwargs)


logging.setLoggerClass(LoggerWithSuccessAndOutput)
logger = cast(LoggerWithSuccessAndOutput, logging.getLogger("pipxrun"))


def _get_formatter(color: bool, add_timestamp: bool) -> logging.Formatter:
    if color and colorlog:
        return PipxRunColoredFormatter(
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
                "SUCCESS": "green",
            },
            style="%",
            secondary_log_colors=None,
            add_timestamp=add_timestamp,
        )
    return PipxRunFormatter(add_timestamp=add_timestamp)


def setup_logging(
    color: bool, verbosity: int = 0, add_timestamp: bool = False
) -> None:  # pragma: no cover
    """Setup logging.

    Args:
        color (bool): If true, the output will be colored using
            colorlog. Otherwise, it will be plaintext.
    """
    root_logger = logging.getLogger()

    level_number = max(0, logging.WARNING - 10 * verbosity)
    root_logger.setLevel(level_number)

    # if verbose:
    #     root_logger.setLevel(OUTPUT)
    # else:
    #     root_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()

    handler.setFormatter(_get_formatter(color, add_timestamp))
    root_logger.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger("sh").setLevel(logging.WARNING)


# Original
# class CustomFormatter(logging.Formatter):
#     """Custom formatter."""

#     def format(self, record: logging.LogRecord) -> str:
#         """Custom format."""
#         msg = textwrap.fill(
#             super().format(record),
#             width=_max_output_width(),
#             subsequent_indent=" " * 4,
#             break_long_words=False,
#             replace_whitespace=False,
#             drop_whitespace=False,
#             break_on_hyphens=False,
#         ).replace("\n", "\\\n")
#         if msg.endswith("\\\n"):
#             msg = msg.rstrip("\\\n") + "\n"

#         return msg


# handler = logging.StreamHandler(sys.stdout)
# handler.setFormatter(
#     CustomFormatter(
#         "{name}({levelname}): {message}",
#         style="{",
#     )
# )

# logging.basicConfig(
#     level=logging.WARNING,
#     handlers=[
#         handler,
#     ],
# )
# logger = logging.getLogger("pipxrun")

# def _set_verbosity_level(logger: logging.Logger, verbosity: int) -> None:
#     """Set verbosity level."""
#     level_number = max(0, logging.WARNING - 10 * verbosity)
#     logger.setLevel(level_number)


# * Utilities -----------------------------------------------------------------
@lru_cache
def _comment_re() -> re.Pattern[str]:
    return re.compile(r"(^|\s+)#.*$")


# @lru_cache
# def _max_output_width() -> int:
#     import shutil

#     width = shutil.get_terminal_size((80, 20)).columns

#     min_width, max_width = 20, 150
#     if width > max_width:
#         width = max_width
#     if width < min_width:
#         width = min_width
#     return width


# def _print_header(name: str = "") -> None:
#     if logger.isEnabledFor(logging.WARNING):
#         fmt = f"{{:=<{_max_output_width()}}}"
#         if name:
#             name = f"= {name} "
#         print(fmt.format(name))


@lru_cache
def _get_command_version(name: str, path: str) -> Version:
    # Note that this version is faster than
    # Calling subprocess to get --version (see bottom of file).
    # But it might break on windows...

    with Path(path).open(encoding=locale.getpreferredencoding(False)) as f:
        python_executable = f.readline().strip().replace("#!", "")

    return Version(
        subprocess.check_output(
            [
                python_executable,
                "-c",
                f"from importlib.metadata import version; print(version('{name}'))",
            ]
        )
        .decode()
        .strip()
    )


def _parse_requirements(requirements: Path) -> Iterator[Requirement]:
    comment_re = _comment_re()

    def ignore_comments(lines: Iterable[str]) -> Iterator[str]:
        """Strips comments and filter empty lines."""
        for line in lines:
            if line_formatted := comment_re.sub("", line).strip():
                yield line_formatted

    with requirements.open() as f:
        yield from map(Requirement, ignore_comments(f))


@lru_cache
def _get_python_version(python_version: str | None) -> str:
    if python_version is None:
        return "{}.{}".format(*sys.version_info[:2])
    return python_version


@lru_cache
def _get_python_executable(python_executable: str | None) -> str:
    if python_executable is None:
        return sys.executable
    return python_executable


def _iter_specs(specs: Iterable[str | Requirement]) -> Iterator[Requirement]:
    for spec in specs:
        if isinstance(spec, str):
            yield Requirement(spec)
        else:
            yield spec


# * Specs ---------------------------------------------------------------------
class Specifications:
    """Working with specifications."""

    def __init__(self, specs: dict[str, Requirement]) -> None:
        self.specs = specs

    def assign(
        self, specs: str | Requirement | Iterable[str | Requirement]
    ) -> Specifications:
        if isinstance(specs, (str, Requirement)):
            specs = [specs]

        return type(self)(
            specs=dict(self.specs, **{spec.name: spec for spec in _iter_specs(specs)})
        )

    def get(self, index: str, default: Requirement | None = None) -> Requirement | None:
        return self.specs.get(index, default)

    @classmethod
    def combine(cls, *specs: Specifications) -> Specifications:
        new_specs: dict[str, Requirement] = {}
        for spec in specs:
            new_specs.update(spec.specs)
        return cls(new_specs)

    @classmethod
    def from_requirements(
        cls,
        *specs: Requirement,
        requirements: str | Path | Iterable[str | Path] | None = None,
    ) -> Specifications:
        if requirements is None:
            requirements = []
        elif isinstance(requirements, (str, Path)):
            requirements = [requirements]

        specs_dict: dict[str, Requirement] = {
            req.name: req
            for requirement in requirements
            for req in _parse_requirements(Path(requirement))
        }

        # update specs
        specs_dict.update({spec.name: spec for spec in _iter_specs(specs)})

        return cls(specs_dict)


# * Dummy session -------------------------------------------------------------


class SessionInterfaceTemplate(Protocol):
    """Generic session."""

    def run(
        self,
        *args: str | os.PathLike[str],
        env: Mapping[str, str | None] | None = None,
        include_outer_env: bool = True,
        # **kwargs: Any,
        # silent: bool = False,
        # success_codes: Iterable[int] | None = None,
        # log: bool = True,
        # external: Literal["error", True, False] | None = None,
        # stdout: int | IO[str] | None = None,
        # stderr: int | IO[str] = subprocess.STDOUT,
        # interrupt_timeout: float | None = 0.3,
        # terminate_timeout: float | None = 0.2,
    ) -> Any | None: ...

    def log(self, *args: Any, **kwargs: Any) -> None: ...

    def warn(self, *args: Any, **kwargs: Any) -> None: ...

    def debug(self, *args: Any, **kwargs: Any) -> None: ...


def _clean_env(env: Mapping[str, str | None] | None = None) -> dict[str, str] | None:
    if env is None:
        return None
    return {k: v for k, v in env.items() if v is not None}


class Session:
    """Basic session"""

    def log(self, *args: Any, **kwargs: Any) -> None:
        """Alias to self.info"""
        self.info(*args, **kwargs)

    @staticmethod
    def info(*args: Any, **kwargs: Any) -> None:
        """Output log info."""
        logger.info(*args, **kwargs)

    @staticmethod
    def warn(*args: Any, **kwargs: Any) -> None:
        """Output log.warning"""
        logger.warning(*args, **kwargs)

    @staticmethod
    def debug(*args: Any, **kwargs: Any) -> None:
        """Debug."""
        logger.debug(*args, **kwargs)

    def run(
        self,
        *args: str | os.PathLike[str],
        env: Mapping[str, str | None] | None = None,
        include_outer_env: bool = True,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Actually do the run."""
        cleaned_args = [os.fsdecode(arg) for arg in args]

        full_cmd = shlex.join(cleaned_args)

        self.info("Running %s", full_cmd)
        r = subprocess.run(cleaned_args, check=False, env=_clean_env(env))  # pyright: ignore[reportUnknownVariableType]

        returncode: int = r.returncode  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        if returncode != 0:
            logger.error("Command %s failed with exit code %s", full_cmd, returncode)  # pyright: ignore[reportUnknownArgumentType]
            msg = f"Returned code {returncode}"
            raise RuntimeError(msg)


# * Command -------------------------------------------------------------------
class Command:
    """Class to handle commands."""

    def __init__(
        self, name: str, args: Iterable[str], spec: Requirement | None = None
    ) -> None:
        self.name = name
        self.args = list(args)
        self.spec = spec

    @classmethod
    def from_command(cls, *commands: str | os.PathLike[str]) -> Command:
        """Create from command iterable"""
        name, *args = map(os.fsdecode, commands)
        spec = Requirement(name)
        return cls(
            name=spec.name,
            args=args,
            spec=spec if spec.specifier else None,
        )

    def assign_spec(self, spec: Requirement | None, override: bool = False) -> Command:
        """Update spec from specs dict."""
        if spec and (override or not self.spec):
            return type(self)(name=self.name, args=self.args, spec=spec)
        return self

    def _get_python_flags(
        self,
        python_executable: str | None,
        python_version: str | None,
    ) -> list[str]:
        if self.name == "mypy":
            return [
                f"--python-executable={_get_python_executable(python_executable)}",
                f"--python-version={_get_python_version(python_version)}",
            ]
        if self.name == "pyright":
            return [
                f"--pythonpath={_get_python_executable(python_executable)}",
                f"--pythonversion={_get_python_version(python_version)}",
            ]

        return []

    @staticmethod
    def _get_pipx_flags(verbosity: int) -> list[str]:
        if verbosity > 0:
            return [f"-{'v' * verbosity}"]
        if verbosity < 0:
            return [f"-{'q' * -verbosity}"]
        return []

    def command(
        self,
        session: SessionInterfaceTemplate,
        python_executable: str | None,
        python_version: str | None,
        files: str | Iterable[str] | None,
        pipx_only: bool = False,
        verbosity: int = 0,
    ) -> list[str]:
        """Create command list."""
        from shutil import which

        if files is None:
            files = []
        elif isinstance(files, str):
            files = [files]

        commands: list[str] = []
        if not pipx_only and (exe_path := which(self.name)):
            if self.spec is None:
                session.log("Using local %s at %s", self.name, exe_path)
                commands = [exe_path]
            elif (
                exe_version := _get_command_version(name=self.name, path=exe_path)
            ) and exe_version in self.spec.specifier:
                session.log(
                    "Using local %s with version %s at %s",
                    self.spec,
                    exe_version,
                    exe_path,
                )
                commands = [exe_path]

        if not commands:
            session.warn("Using pipx run %s", self.spec or self.name)
            commands = [
                "pipx",
                "run",
                *self._get_pipx_flags(verbosity=verbosity),
                *([f"--spec={self.spec}"] if self.spec else []),
                self.name,
            ]

        return [
            *commands,
            *self._get_python_flags(
                python_executable=python_executable,
                python_version=python_version,
            ),
            *self.args,
            *files,
        ]

    def run(
        self,
        session: SessionInterfaceTemplate,
        python_executable: str | None,
        python_version: str | None,
        files: Iterable[str] | None = None,
        dry: bool = False,
        verbosity: int = 0,
        pipx_only: bool = False,
        env: Mapping[str, str] | None = None,
        include_outer_env: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Run the command"""
        # _print_header(self.name)

        command = self.command(
            session=session,
            python_executable=python_executable,
            python_version=python_version,
            files=files,
            pipx_only=pipx_only,
            verbosity=verbosity,
        )

        if dry:
            session.log("Would run with commands: %s", command)
            return 0

        return session.run(
            *command, env=env, include_outer_env=include_outer_env, **kwargs
        )


def run(
    *args: str | os.PathLike[str],
    session: SessionInterfaceTemplate | None = None,
    specs: Specifications | None = None,
    extra_specs: str | Requirement | Iterable[str | Requirement] | None = None,
    python_version: str | None = None,
    python_executable: str | None = None,
    verbosity: int = -2,
    pipx_only: bool = False,
    env: Mapping[str, str] | None = None,
    files: Iterable[str] | None = None,
    include_outer_env: bool = True,
    **kwargs: Any,
) -> Any:
    """Run command"""
    command = Command.from_command(*args)

    if specs is None:
        specs = Specifications({})

    if extra_specs is not None:
        specs = specs.assign(extra_specs)

    command = command.assign_spec(specs.get(command.name))

    session = session or Session()

    return command.run(
        session=session,
        python_executable=python_executable,
        python_version=python_version,
        files=files,
        verbosity=verbosity,
        pipx_only=pipx_only,
        env=env,
        include_outer_env=include_outer_env,
        **kwargs,
    )


# * CLI -----------------------------------------------------------------------
def _parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    """Get parser."""
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Run executable using pipx or from installed if matches specification."
    )
    parser.add_argument(
        "--python-executable",
        dest="python_executable",
        default=None,  # Path(sys.executable),
        type=Path,
        help="""
        Path to python executable. Defaults to ``sys.executable``. This is
        passed to `--python-executable` in mypy and `--pythonpath` in pyright.
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
        to ``--python-version`` and ``--pythonversion`` in mypy and pyright.
        """,
    )
    parser.add_argument(
        "-c",
        "--command",
        dest="commands",
        default=[],
        action="append",
        type=str,
        help="""
        Checkers command. This can include extra flags to the checker. This can
        also be passed multiple times for multiple checkers. This can also
        include a Requirement specification, which overrides any specification
        from ``--requirement`` or ``--spec``. For example,
        ``--command='mypy==1.8.0 --no-incremental' -c pyright``
        """,
    )
    parser.add_argument(
        "-r",
        "--requirement",
        dest="requirements",
        default=[],
        action="append",
        type=Path,
        help="Requirements (requirements.txt) specs for checker.  Can specify multiple times.",
    )
    parser.add_argument(
        "-s",
        "--spec",
        dest="specs",
        default=[],
        action="append",
        type=Requirement,
        help="""
        Package specification. Can pass multiple times. Overrides specs read
        from ``--requirements``. For example, ``--spec 'mypy==1.2.3'``.
        """,
    )
    parser.add_argument("--dry", action="store_true", help="Do dry run")
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        default=0,
        help="Set verbosity level.  Pass multiple times to up level.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="Lower verbosity level.  Pass multiple times to up level.",
    )
    parser.add_argument(
        "-x",
        "--pipx",
        dest="pipx_only",
        action="store_true",
        help="Always use pipx to run the commands (No local fallback)",
    )
    parser.add_argument(
        "--fail-fast",
        dest="fail_fast",
        action="store_true",
        help="If passed, exit at first error.",
    )
    parser.add_argument(
        "files", type=str, default=[], nargs="*", help="Optional files to check."
    )

    options = parser.parse_args() if args is None else parser.parse_args(args)

    if not options.commands:
        parser.print_usage()

    return options


def main(args: Sequence[str] | None = None) -> int:
    """Main script."""
    if not (options := _parse_args(args)).commands:
        return 0

    # setup logging:
    setup_logging(
        color=True, verbosity=options.verbosity - options.quiet, add_timestamp=False
    )

    logger.info(
        "Running with python %s at %s",
        _get_python_version(None),
        _get_python_executable(None),
    )

    commands = [
        Command.from_command(*shlex.split(command)) for command in options.commands
    ]

    # specs from requirements
    specs = Specifications.from_requirements(
        *options.specs, requirements=options.requirements
    )

    # update command specs
    commands = [command.assign_spec(specs.get(command.name)) for command in commands]

    session = Session()

    s = 0

    for command in commands:
        try:
            command.run(
                session=session,
                python_executable=options.python_executable,
                python_version=options.python_version,
                dry=options.dry,
                verbosity=options.verbosity - options.quiet - 2,
                pipx_only=options.pipx_only,
                files=options.files,
            )
        except RuntimeError:  # noqa: PERF203
            s += 1
            if options.fail_fast:
                return s
    return s


if __name__ == "__main__":
    sys.exit(main())


# Alternative method to get command version...
# @lru_cache
# def _version_re() -> re.Pattern[str]:
#     return re.compile(
#         r"\b([1-9][0-9]*!)?(0|[1-9][0-9]*)"
#         r"(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))"
#         r"?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?\b"
#     )
#
#
# @lru_cache
# def _get_command_version(command: str, flag: str = "--version") -> Version | None:
#     version_search = _version_re().search(
#         subprocess.check_output([command, flag])
#         .decode()
#         .strip()
#     )
#     if version_search:
#         return Version(version_search.group(0))
#     return None
#
#
# def _get_site(python_executable: str | Path) -> str:
#     """Getesite-packages for python path (trying to make pytype work)"""
#     return (
#         subprocess.check_output(
#             [
#                 python_executable,
#                 "-c",
#                 "import sysconfig; print(sysconfig.get_paths()['purelib'])",
#             ]
#         )
#         .decode()
#         .strip()
#     )
