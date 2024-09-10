# pyright: reportUnknownMemberType=false
"""
Console script for pyproject2conda (:mod:`~pyproject2conda.cli`)
================================================================
"""
# * Imports -------------------------------------------------------------------

import locale
import logging
import os
from enum import Enum
from functools import lru_cache, wraps
from inspect import signature
from pathlib import Path
from typing import Any, Callable, List, Optional, Union, cast

# from click import click.Context
import click
import typer
from typer.core import TyperGroup

from pyproject2conda import __version__
from pyproject2conda.requirements import ParseDepends
from pyproject2conda.utils import (
    parse_pythons,
    update_target,
)

from ._typing import R
from ._typing_compat import Annotated

# * Logger -----------------------------------------------------------------------------

FORMAT = "%(message)s [%(name)s - %(levelname)s]"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger("pyproject2conda")


# * Settings ---------------------------------------------------------------------------
if "P2C_COLUMNS" in os.environ:
    os.environ["COLUMNS"] = os.environ["P2C_COLUMNS"]  # pragma: no cover


# * Typer App --------------------------------------------------------------------------


class AliasedGroup(TyperGroup):
    """Provide aliasing for commands"""

    def get_command(
        self, ctx: click.Context, cmd_name: str
    ) -> Optional[click.core.Command]:
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if not matches:
            return None
        if len(matches) == 1:
            return super().get_command(ctx, matches[0])
        ctx.fail(
            "Too many matches: {}".format(", ".join(sorted(matches)))
        )  # pragma: no cover
        return None  # pragma: no cover

    def list_commands(self, ctx: click.Context) -> List[str]:  # noqa: ARG002
        return list(self.commands)


app_typer = typer.Typer(cls=AliasedGroup, no_args_is_help=True)


def version_callback(value: bool) -> None:
    """Versioning call back."""
    if value:
        typer.echo(f"pyproject2conda, version {__version__}")
        raise typer.Exit


@app_typer.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
) -> None:
    """
    Extract conda `environment.yaml` and pip `requirement.txt` files from `pyproject.toml`

    Note that all subcommands can be called with shortest possible match. Also, you can
    call with any of `pyproject2conda`, `p2c`, `python -m pyproject2conda`.
    For example,

    .. code-block:: console

            # these are equivalent
            $ pyproject2conda yaml ...
            $ p2c y ...
            $ python -m pyproject2conda ...
    """
    return


# * Options ----------------------------------------------------------------------------

DEFAULT_TOML_PATH = Path("./pyproject.toml")

PYPROJECT_CLI = Annotated[
    Path,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--file",
        "-f",
        help="input pyproject.toml file",
    ),
]
EXTRAS_CLI = Annotated[
    Optional[List[str]],
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--extra",
        "-e",
        help="""
        Extra dependencies. Can specify multiple times for multiple extras.
        Use name `extras` for specifying in `pyproject.toml`
        Note thate for `project` application, this parameter defaults to the
        name of the environment.  If you want no extras, you must pass
        `extras = false`.
        """,
    ),
]
CHANNEL_CLI = Annotated[
    Optional[List[str]],
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--channel",
        "-c",
        help="Conda channel.  Can specify. Overrides [tool.pyproject2conda.channels]",
    ),
]
NAME_CLI = Annotated[
    Optional[str],
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--name",
        "-n",
        help="Name of conda env",
    ),
]
OUTPUT_CLI = Annotated[
    Optional[Path],
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--output",
        "-o",
        help="File to output results",
    ),
]


class Overwrite(str, Enum):
    """Options for `--overwrite`"""

    check = "check"
    skip = "skip"
    foce = "force"


OVERWRITE_CLI = Annotated[
    Overwrite,
    typer.Option(
        "--overwrite",
        "-w",
        case_sensitive=False,
        help="""
    What to do if output file exists.
    (check): Create if missing. If output exists and passed `--filename` is newer, recreate output, else skip.
    (skip): If output exists, skip.
    (force): force: force recreate output.
    """,
    ),
]

VERBOSE_CLI = Annotated[
    Optional[int],
    typer.Option(
        "--verbose",
        "-v",
        help="Pass `-v/--verbose` for verbose output.  Pass multiple times to set verbosity level.",
        count=True,
    ),
]
BASE_DEPENDENCIES_CLI = Annotated[
    bool,
    typer.Option(
        "--base/--no-base",
        help="""
        Default is to include base (project.dependencies) with extras. However, passing
        `--no-base` will exclude base dependencies. This is useful to define environments
        that should exclude base dependencies (like build, etc) in pyproject.toml.
        """,
    ),
]
SORT_DEPENDENCIES_CLI = Annotated[
    bool,
    typer.Option(
        "--sort/--no-sort",
        help="""
        Default is to sort the dependencies (excluding `--python-include`). Pass `--no-sort`
        to instead place dependencies in order they are gathered.
        """,
    ),
]
PYTHON_INCLUDE_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--python-include",
        help="""
        If value passed, use this value (exactly) in the output. So, for example,
        pass `--python-include "python=3.8"`. Special case is the value `"infer"`.  This
        infers the value of python from `pyproject.toml`
        """,
    ),
]
PYTHON_VERSION_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--python-version",
        help="""
         Python version to check `python_version <=> {python_version}` lines against. That is,
         this version is used to limit packages in resulting output. For example, if have a
         line like `a-package; python_version < '3.9'`, Using `--python-version 3.10` will
         not include `a-package`, while `--python-version 3.8` will include `a-package`.
         """,
    ),
]
PYTHON_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--python",
        "-p",
        help="""
        Python version. Passing `--python {version}` is equivalent to passing
        `--python-version={version} --python-include=python{version}`. If passed, this
        overrides values of passed via `--python-version` and `--python-include`.
        """,
    ),
]
HEADER_CLI = Annotated[
    Optional[bool],
    typer.Option(
        "--header/--no-header",
        help="""
        If True (--header) include header line in output. Default is to include the header
        for output to a file, and not to include header when writing to stdout.
        """,
    ),
]
DEPS_CLI = Annotated[
    Optional[List[str]],
    typer.Option(
        "--deps",
        "-d",
        help="Additional conda dependencies.",
    ),
]
REQS_CLI = Annotated[
    Optional[List[str]],
    typer.Option(
        "--reqs",
        "-r",
        help="Additional pip requirements.",
    ),
]
ENVS_CLI = Annotated[
    Optional[List[str]],
    typer.Option(
        help="List of environments to build files for.  Default to building all environments",
    ),
]
TEMPLATE_CLI = Annotated[
    Optional[str],
    typer.Option(
        help="Template for environments that do not have a python version. Defaults to `{env}`."
    ),
]
TEMPLATE_PYTHON_CLI = Annotated[
    Optional[str],
    typer.Option(
        help="""
        Template for environments that do have a python version. Defaults to
        "py{py}-{env}". For example, with `--template-python="py{py}-{env}"` and
        `--python=3.8` and environment "dev", output would be "py38-dev"
        \b
        * {py} -> "38"
        * {py_version} -> "3.8"
        * {env} -> "dev"
        """,
    ),
]
DRY_CLI = Annotated[
    bool,
    typer.Option(
        "--dry",
        help="If passed, do a dry run",
    ),
]
USER_CONFIG_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--user-config",
        help="""
        Additional toml file to supply configuration. This can be used to
        override/add environment files for your own use (apart from project env
        files). The (default) value `infer` means to infer the configuration
        from `--filename`.
        """,
    ),
]
# For conda-requirements
PREFIX_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--prefix",
        help="set conda-output=prefix + 'conda.txt', pip-output=prefix + 'pip.txt'",
    ),
]
PREPEND_CHANNEL_CLI = Annotated[
    bool,
    typer.Option(
        "--prepend-channel",
    ),
]


ALLOW_EMPTY_OPTION = typer.Option(
    "--allow-empty/--no-allow-empty",
    help="""
    What to do if there are no package requirements for an environment. The
    default (`--no-allow-empty`) is to raise an error if the specification
    leads to no requirements. Passing `--allow-empty` will lead to a message
    being printed, but no environment file being created.
    """,
)


REMOVE_WHITESPACE_OPTION = typer.Option(
    "--remove-whitespace/--no-remove-whitespace",
    help="""
    What to do with whitespace in a dependency. The default (`--remove-whitespace`) is
    to remove whitespace in a given dependency. For example, the dependency
    `package >= 1.0` will be converted to `package>=1.0`. Pass `--no-remove-whitespace`
    to keep the the whitespace in the output.
    """,
)


# * Utils ------------------------------------------------------------------------------
def _get_header_cmd(
    header: Optional[bool], output: Union[str, Path, None]
) -> Optional[str]:
    if header is None:
        header = output is not None

    if header:
        import sys
        from pathlib import Path

        return " ".join([Path(sys.argv[0]).name] + sys.argv[1:])

    return None


@lru_cache
def _get_requirement_parser(filename: Union[str, Path]) -> ParseDepends:
    return ParseDepends.from_path(filename)


def _log_skipping(
    logger: logging.Logger, style: str, output: Union[str, Path, None]
) -> None:
    logger.info(
        "Skipping %s %s. Pass `-w force` to force recreate output", style, output
    )


def _log_creating(
    logger: logging.Logger,
    style: str,
    output: Union[str, Path, None],
    prefix: Optional[str] = None,
) -> None:
    if prefix is None:  # pragma: no cover
        prefix = "# " if prefix is None and output is None else ""

    s = f"{prefix}Creating {style}"

    if output:
        s = f"{s} {output}"

    logger.info(s)


def add_verbose_logger(
    logger: logging.Logger, verbose_arg: str = "verbose"
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorator factory to add logger and set logger level based on verbosity argument value."""

    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        bind = signature(func).bind

        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> R:
            params = bind(*args, **kwargs)
            params.apply_defaults()

            verbosity = cast("Optional[int]", params.arguments[verbose_arg])

            if verbosity is None:
                # leave where it is:
                pass
            else:
                if verbosity < 0:  # pragma: no cover
                    level = logging.ERROR
                elif verbosity == 0:  # pragma: no cover
                    level = logging.WARNING
                elif verbosity == 1:
                    level = logging.INFO
                else:  # pragma: no cover
                    level = logging.DEBUG

                logger.setLevel(level)

            # add error logger to function call
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.exception("found error")
                raise

        return wrapped

    return decorator


# * Commands ---------------------------------------------------------------------------
# ** List
# @app_typer.command("l", hidden=True)
@app_typer.command("list")
@add_verbose_logger(logger)
def create_list(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    verbose: VERBOSE_CLI = None,
) -> None:
    """List available extras."""
    logger.info("filename: %s", filename)

    d = _get_requirement_parser(filename)

    print("Extras:")
    print("=======")

    for extra in d.extras:
        print("*", extra)


# ** Yaml
# @app_typer.command("y", hidden=True)
@app_typer.command()
@add_verbose_logger(logger)
def yaml(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    extras: EXTRAS_CLI = None,
    channels: CHANNEL_CLI = None,
    output: OUTPUT_CLI = None,
    name: NAME_CLI = None,
    python_include: PYTHON_INCLUDE_CLI = None,
    python_version: PYTHON_VERSION_CLI = None,
    python: PYTHON_CLI = None,
    base: BASE_DEPENDENCIES_CLI = True,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.check,
    verbose: VERBOSE_CLI = None,
    deps: DEPS_CLI = None,
    reqs: REQS_CLI = None,
    allow_empty: Annotated[bool, ALLOW_EMPTY_OPTION] = False,
    remove_whitespace: Annotated[bool, REMOVE_WHITESPACE_OPTION] = True,
) -> None:
    """Create yaml file from dependencies and optional-dependencies."""
    if not update_target(output, filename, overwrite=overwrite.value):
        _log_skipping(logger, "yaml", output)
        return

    if not channels:
        channels = None

    python_include, python_version = parse_pythons(
        python_include=python_include,
        python_version=python_version,
        python=python,
    )

    d = _get_requirement_parser(filename)

    _log_creating(logger, "yaml", output)

    s = d.to_conda_yaml(
        extras=extras,
        channels=channels,
        name=name,
        output=output,
        python_include=python_include,
        python_version=python_version,
        include_base=base,
        header_cmd=_get_header_cmd(header, output),
        sort=sort,
        conda_deps=deps,
        pip_deps=reqs,
        allow_empty=allow_empty,
        remove_whitespace=remove_whitespace,
    )
    if not output:
        print(s, end="")


# ** Requirements
# @app_typer.command("r", hidden=True)
@app_typer.command()
@add_verbose_logger(logger)
def requirements(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    extras: EXTRAS_CLI = None,
    output: OUTPUT_CLI = None,
    base: BASE_DEPENDENCIES_CLI = True,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.check,
    verbose: VERBOSE_CLI = None,
    reqs: REQS_CLI = None,
    allow_empty: Annotated[bool, ALLOW_EMPTY_OPTION] = False,
    remove_whitespace: Annotated[bool, REMOVE_WHITESPACE_OPTION] = True,
) -> None:
    """Create requirements.txt for pip dependencies."""
    if not update_target(output, filename, overwrite=overwrite.value):
        _log_skipping(logger, "requirements", output)
        return

    d = _get_requirement_parser(filename)

    _log_creating(logger, "requirements", output)

    s = d.to_requirements(
        extras=extras,
        output=output,
        include_base=base,
        header_cmd=_get_header_cmd(header, output),
        sort=sort,
        pip_deps=reqs,
        allow_empty=allow_empty,
        remove_whitespace=remove_whitespace,
    )
    if not output:
        print(s, end="")


# ** From project


# @app_typer.command("p", hidden=True)
@app_typer.command()
@add_verbose_logger(logger)
def project(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    envs: ENVS_CLI = None,
    template: TEMPLATE_CLI = None,
    template_python: TEMPLATE_PYTHON_CLI = None,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.check,
    verbose: VERBOSE_CLI = None,
    dry: DRY_CLI = False,
    user_config: USER_CONFIG_CLI = "infer",
    allow_empty: Annotated[Optional[bool], ALLOW_EMPTY_OPTION] = None,
    remove_whitespace: Annotated[Optional[bool], REMOVE_WHITESPACE_OPTION] = None,
) -> None:
    """Create multiple environment files from `pyproject.toml` specification."""
    from pyproject2conda.config import Config

    c = Config.from_file(filename, user_config=user_config)

    if user_config == "infer" or user_config is None:
        user_config = c.user_config()

    for style, d in c.iter_envs(
        envs=envs,
        template=template,
        template_python=template_python,
        sort=sort,
        header=header,
        overwrite=overwrite.value,
        verbose=verbose,
        allow_empty=allow_empty,
        remove_whitespace=remove_whitespace,
    ):
        if dry:
            # small header
            print("# " + "-" * 20)
            print("# Creating {style} {output}".format(style=style, output=d["output"]))
            d["output"] = None

        # Special case: have output and userconfig.  Check update
        if not update_target(
            d["output"],
            filename,
            *([user_config] if user_config else []),
            overwrite=d["overwrite"],
        ):
            if verbose:
                _log_skipping(logger, style, d["output"])
        else:
            d["overwrite"] = Overwrite("force")
            if style == "yaml":
                yaml(filename=filename, **d)

            elif style == "requirements":
                requirements(filename=filename, **d)
            else:  # pragma: no cover
                msg = f"unknown style {style}"
                raise ValueError(msg)


# ** Conda requirements


# @app_typer.command("cr", hidden=True)
@app_typer.command()
@add_verbose_logger(logger)
def conda_requirements(
    path_conda: Annotated[Optional[str], typer.Argument()] = None,
    path_pip: Annotated[Optional[str], typer.Argument()] = None,
    extras: EXTRAS_CLI = None,
    python_include: PYTHON_INCLUDE_CLI = None,
    python_version: PYTHON_VERSION_CLI = None,
    python: PYTHON_CLI = None,
    channels: CHANNEL_CLI = None,
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    base: BASE_DEPENDENCIES_CLI = True,
    prefix: PREFIX_CLI = None,
    prepend_channel: PREPEND_CHANNEL_CLI = False,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    # paths,
    deps: DEPS_CLI = None,
    reqs: REQS_CLI = None,
    verbose: VERBOSE_CLI = None,
) -> None:
    """
    Create requirement files for conda and pip.

    These can be install with, for example,

    conda install --file {path_conda}
    pip install -r {path_pip}
    """
    python_include, python_version = parse_pythons(
        python_include=python_include,
        python_version=python_version,
        python=python,
    )

    if path_conda and not path_pip:
        msg = "can only specify neither or both path_conda and path_pip"
        raise ValueError(msg)

    if path_conda and path_pip and prefix is not None:
        msg = "specify path_conda and path_pip or prefix, not all"
        raise ValueError(msg)

    if prefix is not None:
        path_conda = prefix + "conda.txt"
        path_pip = prefix + "pip.txt"

    d = _get_requirement_parser(filename)

    _get_header_cmd(header, path_conda)

    deps_str, reqs_str = d.to_conda_requirements(
        extras=extras,
        python_include=python_include,
        python_version=python_version,
        channels=channels,
        prepend_channel=prepend_channel,
        output_conda=path_conda,
        output_pip=path_pip,
        include_base=base,
        header_cmd=_get_header_cmd(header, path_conda),
        sort=sort,
        conda_deps=deps,
        pip_deps=reqs,
    )

    if not path_conda:
        s = f"#conda requirements\n{deps_str}\n#pip requirements\n{reqs_str}"
        print(s, end="")


# ** json
# @app_typer.command("j", hidden=True)
@app_typer.command("json")
@add_verbose_logger(logger)
def to_json(
    extras: EXTRAS_CLI = None,
    python_include: PYTHON_INCLUDE_CLI = None,
    python_version: PYTHON_VERSION_CLI = None,
    python: PYTHON_CLI = None,
    channels: CHANNEL_CLI = None,
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    sort: SORT_DEPENDENCIES_CLI = True,
    output: OUTPUT_CLI = None,
    base: BASE_DEPENDENCIES_CLI = True,
    deps: DEPS_CLI = None,
    reqs: REQS_CLI = None,
    verbose: VERBOSE_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.check,
) -> None:
    """
    Create json representation.

    Keys are:
    "dependencies": conda dependencies.
    "pip": pip dependencies.
    "channels": conda channels.
    """
    if not update_target(output, filename, overwrite=overwrite.value):
        _log_skipping(logger, "yaml", output)
        return

    import json

    d = _get_requirement_parser(filename)

    python_include, python_version = parse_pythons(
        python_include=python_include,
        python_version=python_version,
        python=python,
    )

    conda_deps, pip_deps = d.conda_and_pip_requirements(
        extras=extras,
        python_include=python_include,
        python_version=python_version,
        include_base=base,
        sort=sort,
        conda_deps=deps,
        pip_deps=reqs,
    )

    result = {
        "dependencies": conda_deps,
        "pip": pip_deps,
    }

    channels = channels or d.channels
    if channels:
        result["channels"] = channels

    if output:
        with Path(output).open("w", encoding=locale.getpreferredencoding(False)) as f:
            json.dump(result, f)
    else:
        print(json.dumps(result))  # , indent=2))


# * Click app
# # If need be, can work directly with click
# @click.group(cls=AliasedGroup)
# @click.version_option(version=__version__)
# def app_click() -> None:
#     pass
# typer_click_object = typer.main.get_command(app_typer)  # noqa: ERA001
# app = click.CommandCollection(sources=[app_click, typer_click_object], cls=AliasedGroup)  # noqa: ERA001

# Just use the click app....
app = typer.main.get_command(app_typer)


# ** Main
if __name__ == "__main__":
    app()  # pragma: no cover
