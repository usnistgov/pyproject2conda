# pyright: reportUnknownMemberType=false
"""
Console script for pyproject2conda (:mod:`~pyproject2conda.cli`)
================================================================
"""

from __future__ import annotations

import locale
import logging
import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from typer.core import TyperGroup

from pyproject2conda import __version__
from pyproject2conda.requirements import ParseDepends
from pyproject2conda.utils import (
    parse_pythons,
    update_target,
)

if TYPE_CHECKING:
    import click

# * Logger -----------------------------------------------------------------------------

FORMAT = "%(message)s [%(name)s - %(levelname)s]"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger("pyproject2conda")


# * Callbacks -----------------------------------------------------------------
def _callback_verbose(
    verbose: int | None,
) -> int | None:
    if verbose is None:
        return None

    if verbose < 0:  # pragma: no cover
        level = logging.ERROR
    elif not verbose:  # pragma: no cover
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:  # pragma: no cover
        level = logging.DEBUG

    for _logger in map(logging.getLogger, logging.root.manager.loggerDict):  # pylint: disable=no-member,bad-builtin
        _logger.setLevel(level)
    return verbose


def _callback_columns(
    columns: int | None,
) -> int | None:
    if columns is not None:
        os.environ["COLUMNS"] = str(columns)
    return columns


def _callback_version(value: bool) -> None:
    """Versioning call back."""
    if value:
        typer.echo(f"pyproject2conda, version {__version__}")
        raise typer.Exit


# * Typer App --------------------------------------------------------------------------
class AliasedGroup(TyperGroup):
    """Provide aliasing for commands"""

    def get_command(  # noqa: D102
        self, ctx: click.Context, cmd_name: str
    ) -> click.Command | None:
        if (rv := super().get_command(ctx, cmd_name)) is not None:
            return rv
        if not (
            matches := [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        ):
            return None
        if len(matches) == 1:
            return super().get_command(ctx, matches[0])
        ctx.fail(
            "Too many matches: {}".format(", ".join(sorted(matches)))
        )  # pragma: no cover
        return None  # type: ignore[unreachable]  # pragma: no cover

    def list_commands(self, ctx: click.Context) -> list[str]:  # noqa: ARG002, D102
        return list(self.commands)


app_typer = typer.Typer(cls=AliasedGroup, no_args_is_help=True)


@app_typer.callback()
def main(
    version: Annotated[  # noqa: ARG001
        bool,
        typer.Option("--version", "-v", callback=_callback_version, is_eager=True),
    ] = False,
    columns: Annotated[  # noqa: ARG001
        int | None,
        typer.Option(
            "--columns",
            envvar="P2C_COLUMNS",
            help="Column width in terminal.  Set ``COLUMNS`` environment variable to this value",
            callback=_callback_columns,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """
    Extract conda ``environment.yaml`` and pip ``requirement.txt`` files from ``pyproject.toml``

    Note that all subcommands can be called with shortest possible match. Also, you can
    call with any of ``pyproject2conda``, ``p2c``, ``python -m pyproject2conda``.
    For example,

    .. code-block:: console

            # these are equivalent
            $ pyproject2conda yaml ...
            $ p2c y ...
            $ python -m pyproject2conda yaml ...
    """
    return


# * Options ----------------------------------------------------------------------------

PYPROJECT_CLI = Annotated[
    Path,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--pyproject-file",
        "--file",
        "-f",
        help="input pyproject.toml file",
        default_factory=lambda: Path("./pyproject.toml"),
        show_default="pyproject.toml",
    ),
]
EXTRAS_CLI = Annotated[
    list[str] | None,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--extra",
        "-e",
        help="""
        Include dependencies from extra <extra> from ``project.optional-dependencies`` table of ``pyproject.toml``.
        Can specify multiple times for multiple extras.
        Use name ``extras`` for specifying in ``pyproject.toml``
        """,
    ),
]
GROUPS_CLI = Annotated[
    list[str] | None,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--group",
        "-g",
        help="""
        Include dependencies from group <group> from ``dependency-groups`` table of ``pyproject.toml``.
        Can specify multiple times for multiple groups.
        Use name ``groups`` for specifying in ``pyproject.toml``
        """,
    ),
]
EXTRAS_OR_GROUPS_CLI = Annotated[
    list[str] | None,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--extra-or-group",
        help="""
        Include dependencies from extra or group of ``pyproject.toml``.
        Extras are checked first, followed by groups.  The first instance of ``extra-or-group`` found is used.
        That is, if both ``extras`` and ``groups`` contain ``extra-or-group``, the extra will be used.
        Use name ``extras-or-groups`` for specifying in ``pyproject.toml``
        """,
    ),
]
CHANNEL_CLI = Annotated[
    list[str] | None,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--channel",
        "-c",
        help="Conda channel.  Can specify. Overrides [tool.pyproject2conda.channels]",
    ),
]
NAME_CLI = Annotated[
    str | None,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--name",
        "-n",
        help="Name of conda env",
    ),
]
OUTPUT_CLI = Annotated[
    Path | None,
    typer.Option(  # pyright: ignore[reportUnknownMemberType]
        "--output",
        "-o",
        help="File to output results",
    ),
]


class Overwrite(str, Enum):
    """Options for ``--overwrite``"""

    check = "check"
    skip = "skip"
    force = "force"


OVERWRITE_CLI = Annotated[
    Overwrite,
    typer.Option(
        "--overwrite",
        "-w",
        case_sensitive=False,
        help="""
    What to do if output file exists.
    (check): Create if missing. If output exists and passed ``--filename`` is newer, recreate output, else skip.
    (skip): If output exists, skip.
    (force): force: force recreate output.
    """,
    ),
]
VERBOSE_CLI = Annotated[
    int | None,
    typer.Option(
        "--verbose",
        "-v",
        help="Pass ``-v/--verbose`` for verbose output.  Pass multiple times to set verbosity level.",
        count=True,
        callback=_callback_verbose,
    ),
]
SKIP_PACKAGE_CLI = Annotated[
    bool,
    typer.Option(
        "--skip-package",
        help="""
        Default is to include package dependencies from ``project.dependencies``
        table of ``pyproject.toml``. Passing ``--skip-package`` (or ``skip_package =
        true`` in ``tool.pyproject2conda.envs...`` table of ``pyproject.toml``) will
        exclude the package dependencies. This is useful to define environments
        that should exclude base dependencies (like build, etc) in
        pyproject.toml.
        """,
    ),
]
PIP_ONLY_CLI = Annotated[
    bool,
    typer.Option(
        "--pip-only",
        help="""Treat all requirements as pip requirements. Use option ``pip_only`` in pyproject.toml""",
    ),
]
SORT_DEPENDENCIES_CLI = Annotated[
    bool,
    typer.Option(
        "--sort/--no-sort",
        help="""
        Default is to sort the dependencies (excluding ``--python-include``).
        Pass ``--no-sort`` to instead place dependencies in order they are
        gathered.  Use option ``sort = true/false`` in pyproject.toml
        """,
    ),
]
PYTHON_INCLUDE_CLI = Annotated[
    str | None,
    typer.Option(
        "--python-include",
        help="""
        If value passed, use this value (exactly) in the output. So, for
        example, pass ``--python-include "python=3.8"``. Special case is the
        value ``"infer"``. This infers the value of python from ``pyproject.toml``
        """,
    ),
]
PYTHON_VERSION_CLI = Annotated[
    str | None,
    typer.Option(
        "--python-version",
        help="""
         Python version to check ``python_version <=> {python_version}`` lines
         against. That is, this version is used to limit packages in resulting
         output. For example, if have a line like ``a-package; python_version <
         '3.9'``, Using ``--python-version 3.10`` will not include ``a-package``,
         while ``--python-version 3.8`` will include ``a-package``.
         """,
    ),
]
PYTHON_CLI = Annotated[
    str | None,
    typer.Option(
        "--python",
        "-p",
        help="""
        python version. passing ``--python {version}`` is equivalent to passing
        ``--python-version={version} --python-include=python{version}``. if
        passed, this overrides values of passed via ``--python-version`` and
        ``--python-include``. pass ``--python="default"`` to include the python
        version (major.minor only) from, in order, ``.python-version-default`` or
        ``.python-version``file in the current directory. pass ``"lowest"`` or
        ``"highest"`` to include the lowest or highest python version,
        respectively, from ``pyproject.toml:project.classifiers`` table. in
        project mode, you can pass multiple python version in ``pyproject.toml``
        with, e.g., ``python = ["3.8", "3.9", ....]``, or using ``python = "all"``,
        to include all python versions extracted from
        ``pyproject.toml:project.classifiers`` table.
        """,
    ),
]
HEADER_CLI = Annotated[
    bool | None,
    typer.Option(
        "--header/--no-header",
        help="""
        If True (--header) include header line in output. Default is to include
        the header for output to a file, and not to include header when writing
        to stdout.
        """,
    ),
]
CUSTOM_COMMAND_CLI = Annotated[
    str | None,
    typer.Option(
        "--custom-command",
        help="""
        Custom command to place in header.  Implies ``--header``.
        """,
    ),
]
DEPS_CLI = Annotated[
    list[str] | None,
    typer.Option(
        "--deps",
        "-d",
        help="Additional conda dependencies.",
    ),
]
REQS_CLI = Annotated[
    list[str] | None,
    typer.Option(
        "--reqs",
        "-r",
        help="""
        Additional pip requirements. For example, pass ``-r '-e .'`` to included
        editable version of current package in requirements file.
        """,
    ),
]
ENVS_CLI = Annotated[
    list[str] | None,
    typer.Option(
        help="List of environments to build files for.  Default to building all environments",
    ),
]
TEMPLATE_CLI = Annotated[
    str | None,
    typer.Option(
        help="Template for environments that do not have a python version. Defaults to ``{env}``."
    ),
]
TEMPLATE_PYTHON_CLI = Annotated[
    str | None,
    typer.Option(
        help="""
        Template for environments that do have a python version. Defaults to
        "py{py}-{env}". For example, with ``--template-python="py{py}-{env}"`` and
        ``--python=3.8`` and environment "dev", output would be "py38-dev"
        \b
        * {py} -> "38"
        * {py_version} -> "3.8"
        * {env} -> "dev"
        """,
    ),
]
REQS_EXT_CLI = Annotated[
    str | None,
    typer.Option(
        "--reqs-ext",
        help="""
        Extension to use with requirements file output created from template.  Defaults to ``".txt"``.
        """,
    ),
]
YAML_EXT_CLI = Annotated[
    str | None,
    typer.Option(
        "--yaml-ext",
        help="""
        Extension to use with conda environment.yaml file output created from template.  Defaults to ``".yaml"``
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
    str | None,
    typer.Option(
        "--user-config",
        help="""
        Additional toml file to supply configuration. This can be used to
        override/add environment files for your own use (apart from project env
        files). The (default) value ``infer`` means to infer the configuration
        from ``--filename``.
        """,
    ),
]
# For conda-requirements
PREFIX_CLI = Annotated[
    str | None,
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
    default (``--no-allow-empty``) is to raise an error if the specification
    leads to no requirements. Passing ``--allow-empty`` will lead to a message
    being printed, but no environment file being created.
    """,
)
REMOVE_WHITESPACE_OPTION = typer.Option(
    "--remove-whitespace/--no-remove-whitespace",
    help="""
    What to do with whitespace in a dependency. Passing ``--remove-whitespace``
    will remove whitespace in a given dependency. For example, the dependency
    ``package >= 1.0`` will be converted to ``package>=1.0``. Pass
    ``--no-remove-whitespace`` to keep the the whitespace in the output.
    """,
)


# * Utils ------------------------------------------------------------------------------
def _get_header_cmd(
    custom_command: str | None,
    header: bool | None,
    output: str | Path | None,
) -> str | None:
    if custom_command is not None:
        return custom_command

    if (header is None or header) and ("PRE_COMMIT" in os.environ):
        return "pre-commit"

    if header is None:
        header = output is not None

    if header:
        import sys

        return " ".join([Path(sys.argv[0]).name, *sys.argv[1:]])

    return None


@lru_cache
def _get_requirement_parser(filename: str | Path) -> ParseDepends:
    return ParseDepends.from_path(filename)


def _log_skipping(
    logger: logging.Logger, style: str, output: str | Path | None
) -> None:
    logger.info(
        "Skipping %s %s. Pass `-w force` to force recreate output", style, output
    )


def _log_creating(
    logger: logging.Logger,
    style: str,
    output: str | Path | None,
    prefix: str | None = None,
) -> None:
    if prefix is None:  # pragma: no cover
        prefix = "# " if output is None else ""

    s = f"{prefix}Creating {style}"

    if output:
        s = f"{s} {output}"

    logger.info(s)


# * Commands ---------------------------------------------------------------------------
# ** List
# @app_typer.command("l", hidden=True)
@app_typer.command("list")
def create_list(
    pyproject_filename: PYPROJECT_CLI,
    verbose: VERBOSE_CLI = None,  # noqa: ARG001
) -> None:
    """List available extras."""
    logger.info("pyproject_filename: %s", pyproject_filename)

    d = _get_requirement_parser(pyproject_filename)

    for name, vals in [("Extras", d.extras), ("Groups", d.groups)]:  # pylint: disable=consider-using-tuple
        print(name)
        print("======")
        for val in sorted(vals):
            print("*", val)


# ** Yaml
# @app_typer.command("y", hidden=True)
@app_typer.command()
def yaml(
    pyproject_filename: PYPROJECT_CLI,
    extras: EXTRAS_CLI = None,
    groups: GROUPS_CLI = None,
    extras_or_groups: EXTRAS_OR_GROUPS_CLI = None,
    channels: CHANNEL_CLI = None,
    output: OUTPUT_CLI = None,
    name: NAME_CLI = None,
    python_include: PYTHON_INCLUDE_CLI = None,
    python_version: PYTHON_VERSION_CLI = None,
    python: PYTHON_CLI = None,
    skip_package: SKIP_PACKAGE_CLI = False,
    pip_only: PIP_ONLY_CLI = False,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    custom_command: CUSTOM_COMMAND_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.force,
    verbose: VERBOSE_CLI = None,  # noqa: ARG001
    deps: DEPS_CLI = None,
    reqs: REQS_CLI = None,
    allow_empty: Annotated[bool, ALLOW_EMPTY_OPTION] = False,
    remove_whitespace: Annotated[bool, REMOVE_WHITESPACE_OPTION] = True,
) -> None:
    """Create yaml file from dependencies and optional-dependencies."""
    if not update_target(output, pyproject_filename, overwrite=overwrite.value):
        _log_skipping(logger, "yaml", output)
        return

    if not channels:
        channels = None

    python_include, python_version = parse_pythons(
        python_include=python_include,
        python_version=python_version,
        python=python,
        toml_path=pyproject_filename,
    )

    d = _get_requirement_parser(pyproject_filename)

    _log_creating(logger, "yaml", output)

    s = d.to_conda_yaml(
        extras=extras,
        groups=groups,
        extras_or_groups=extras_or_groups,
        channels=channels,
        name=name,
        output=output,
        python_include=python_include,
        python_version=python_version,
        skip_package=skip_package,
        pip_only=pip_only,
        header_cmd=_get_header_cmd(custom_command, header, output),
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
def requirements(
    pyproject_filename: PYPROJECT_CLI,
    extras: EXTRAS_CLI = None,
    groups: GROUPS_CLI = None,
    extras_or_groups: EXTRAS_OR_GROUPS_CLI = None,
    output: OUTPUT_CLI = None,
    skip_package: SKIP_PACKAGE_CLI = False,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    custom_command: CUSTOM_COMMAND_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.force,
    verbose: VERBOSE_CLI = None,  # noqa: ARG001
    reqs: REQS_CLI = None,
    allow_empty: Annotated[bool, ALLOW_EMPTY_OPTION] = False,
    remove_whitespace: Annotated[bool, REMOVE_WHITESPACE_OPTION] = False,
) -> None:
    """Create requirements.txt for pip dependencies.  Note that all requirements are normalized using ``packaging.requirements.Requirement``"""
    if not update_target(output, pyproject_filename, overwrite=overwrite.value):
        _log_skipping(logger, "requirements", output)
        return

    d = _get_requirement_parser(pyproject_filename)

    _log_creating(logger, "requirements", output)

    s = d.to_requirements(
        extras=extras,
        groups=groups,
        extras_or_groups=extras_or_groups,
        output=output,
        skip_package=skip_package,
        header_cmd=_get_header_cmd(custom_command, header, output),
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
def project(
    pyproject_filename: PYPROJECT_CLI,
    envs: ENVS_CLI = None,
    template: TEMPLATE_CLI = None,
    template_python: TEMPLATE_PYTHON_CLI = None,
    reqs: REQS_CLI = None,
    deps: DEPS_CLI = None,
    reqs_ext: REQS_EXT_CLI = ".txt",
    yaml_ext: YAML_EXT_CLI = ".yaml",
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    custom_command: CUSTOM_COMMAND_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.force,
    verbose: VERBOSE_CLI = None,
    dry: DRY_CLI = False,
    pip_only: PIP_ONLY_CLI = False,
    user_config: USER_CONFIG_CLI = "infer",
    allow_empty: Annotated[bool | None, ALLOW_EMPTY_OPTION] = None,
    remove_whitespace: Annotated[bool | None, REMOVE_WHITESPACE_OPTION] = None,
) -> None:
    """
    Create multiple environment files from ``pyproject.toml`` specification.

    Note that if you specify options in ``pyproject.toml``, the name is usually
    the same as the command line option. You can replace dashes with
    underscores if you wish, but if you do so, replace all dashes with
    underscores. For cases where the option can take multiple values, the
    config file option will be plural. For example, the command line option
    ``--group`` becomes the config file option ``groups = ...``.  Boolean options
    like ``--sort/--no-sort`` become ``sort = true/false`` in the config file.
    """
    from pyproject2conda.config import Config

    c = Config.from_file(pyproject_filename, user_config=user_config)

    if user_config == "infer" or user_config is None:
        user_config = c.user_config()

    for style, d in c.iter_envs(
        envs=envs,
        reqs_ext=reqs_ext,
        yaml_ext=yaml_ext,
        template=template,
        template_python=template_python,
        reqs=reqs,
        deps=deps,
        sort=sort,
        header=header,
        custom_command=custom_command,
        overwrite=overwrite.value,
        verbose=verbose,
        allow_empty=allow_empty,
        remove_whitespace=remove_whitespace,
        pip_only=pip_only or None,
    ):
        if dry:
            # small header
            print("# " + "-" * 20)
            print("# Creating {style} {output}".format(style=style, output=d["output"]))
            d["output"] = None

        # Special case: have output and userconfig.  Check update
        if not update_target(
            d["output"],
            pyproject_filename,
            *([user_config] if user_config else []),
            overwrite=d["overwrite"],
        ):
            if verbose:
                _log_skipping(logger, style, d["output"])
        else:
            d["overwrite"] = Overwrite("force")
            if style == "yaml":
                yaml(pyproject_filename=pyproject_filename, **d)

            elif style == "requirements":
                requirements(pyproject_filename=pyproject_filename, **d)
            else:  # pragma: no cover
                msg = f"unknown style {style}"
                raise ValueError(msg)


# ** Conda requirements


# @app_typer.command("cr", hidden=True)
@app_typer.command()
def conda_requirements(
    pyproject_filename: PYPROJECT_CLI,
    path_conda: Annotated[str | None, typer.Argument()] = None,
    path_pip: Annotated[str | None, typer.Argument()] = None,
    extras: EXTRAS_CLI = None,
    groups: GROUPS_CLI = None,
    extras_or_groups: EXTRAS_OR_GROUPS_CLI = None,
    python_include: PYTHON_INCLUDE_CLI = None,
    python_version: PYTHON_VERSION_CLI = None,
    python: PYTHON_CLI = None,
    channels: CHANNEL_CLI = None,
    skip_package: SKIP_PACKAGE_CLI = False,
    prefix: PREFIX_CLI = None,
    prepend_channel: PREPEND_CHANNEL_CLI = False,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    custom_command: CUSTOM_COMMAND_CLI = None,
    # paths,
    deps: DEPS_CLI = None,
    reqs: REQS_CLI = None,
    verbose: VERBOSE_CLI = None,  # noqa: ARG001
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
        toml_path=pyproject_filename,
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

    d = _get_requirement_parser(pyproject_filename)

    deps_str, reqs_str = d.to_conda_requirements(
        extras=extras,
        groups=groups,
        extras_or_groups=extras_or_groups,
        python_include=python_include,
        python_version=python_version,
        channels=channels,
        prepend_channel=prepend_channel,
        output_conda=path_conda,
        output_pip=path_pip,
        skip_package=skip_package,
        header_cmd=_get_header_cmd(custom_command, header, path_conda),
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
def to_json(
    pyproject_filename: PYPROJECT_CLI,
    extras: EXTRAS_CLI = None,
    groups: GROUPS_CLI = None,
    extras_or_groups: EXTRAS_OR_GROUPS_CLI = None,
    python_include: PYTHON_INCLUDE_CLI = None,
    python_version: PYTHON_VERSION_CLI = None,
    python: PYTHON_CLI = None,
    channels: CHANNEL_CLI = None,
    sort: SORT_DEPENDENCIES_CLI = True,
    output: OUTPUT_CLI = None,
    skip_package: SKIP_PACKAGE_CLI = False,
    deps: DEPS_CLI = None,
    reqs: REQS_CLI = None,
    verbose: VERBOSE_CLI = None,  # noqa: ARG001
    overwrite: OVERWRITE_CLI = Overwrite.force,
) -> None:
    """
    Create json representation.

    Keys are:
    "dependencies": conda dependencies.
    "pip": pip dependencies.
    "channels": conda channels.
    """
    if not update_target(output, pyproject_filename, overwrite=overwrite.value):
        _log_skipping(logger, "yaml", output)
        return

    import json

    d = _get_requirement_parser(pyproject_filename)

    python_include, python_version = parse_pythons(
        python_include=python_include,
        python_version=python_version,
        python=python,
        toml_path=pyproject_filename,
    )

    conda_deps, pip_deps = d.conda_and_pip_requirements(
        extras=extras,
        groups=groups,
        extras_or_groups=extras_or_groups,
        python_include=python_include,
        python_version=python_version,
        skip_package=skip_package,
        sort=sort,
        conda_deps=deps,
        pip_deps=reqs,
    )

    result = {
        "dependencies": conda_deps,
        "pip": pip_deps,
    }

    if channels := channels or d.channels:
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
app = typer.main.get_command(app_typer)  # ty: ignore[unresolved-attribute]


# ** Main
if __name__ == "__main__":
    app()  # pragma: no cover
