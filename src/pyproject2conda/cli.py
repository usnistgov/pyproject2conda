# mypy: disable-error-code="no-untyped-def, no-untyped-call"
"""
Console script for pyproject2conda (:mod:`pyproject2conda.cli`)
===============================================================
"""
# * Imports
from __future__ import annotations

import os
from functools import lru_cache

from pyproject2conda import __version__
from pyproject2conda.parser import PyProject2Conda
from pyproject2conda.utils import (
    compose_decorators,
    parse_pythons,
    update_target,
)

if os.environ.get("P2C_USE_CLICK", "True").lower() not in ("0", "f", "false"):
    # use rich
    import rich_click as click
    from rich_click.rich_group import RichGroup

    if "P2C_RICH_CLICK_MAX_WIDTH" in os.environ:
        click.rich_click.MAX_WIDTH = int(
            os.environ["P2C_RICH_CLICK_MAX_WIDTH"]
        )  # pragma: no cover

else:  # pragma: no cover
    # Special case for generating README.pdf
    import click  # type: ignore[no-redef]
    from click import Group as RichGroup  # type: ignore[assignment]


# * Click options
PYPROJECT_CLI = click.option(
    "-f",
    "--file",
    "filename",
    type=click.Path(),
    default="pyproject.toml",
    help="input pyproject.toml file",
)
EXTRAS_CLI = click.option(
    "-e",
    "--extra",
    "extras",
    type=str,
    multiple=True,
    help="Extra depenedencies. Can specify multiple times for multiple extras.",
)
CHANNEL_CLI = click.option(
    "-c",
    "--channel",
    "channels",
    type=str,
    multiple=True,
    help="conda channel.  Can specify. Overrides [tool.pyproject2conda.channels]",
)
NAME_CLI = click.option(
    "-n", "--name", "name", type=str, default=None, help="Name of conda env"
)
OUTPUT_CLI = click.option(
    "-o",
    "--output",
    "output",
    type=click.Path(),
    default=None,
    help="File to output results",
)
OVERWRITE_CLI = click.option(
    "-w",
    "--overwrite",
    "overwrite",
    type=click.Choice(["check", "force", "skip"], case_sensitive=False),
    default="check",
    help="""
    What to do if output file exists.
    (check): Create if missing. If output exists and passed `--filename` is newer, recreate output, else skip.
    (skip): If output exists, skip.
    (force): force: force recreate output.
    """,
)
VERBOSE_CLI = click.option("-v", "--verbose", "verbose", is_flag=True, default=False)
BASE_DEPENDENCIES_CLI = click.option(
    "--base/--no-base",
    "base",
    is_flag=True,
    default=True,
    help="""
    Default is to include base (project.dependencies) with extras. However, passing
    `--no-base` will exclude base dependencies. This is useful to define environments
    that should exclude base dependencies (like build, etc) in pyproject.toml.
    """,
)
SORT_DEPENDENCIES_CLI = click.option(
    "--sort/--no-sort",
    "sort",
    is_flag=True,
    default=True,
    help="""
    Default is to sort the dependencies (excluding `--python-include`). Pass `--no-sort`
    to instead place dependencies in order they are gathered.
    """,
)
PYTHON_INCLUDE_CLI = click.option(
    "--python-include",
    "python_include",
    is_flag=False,
    flag_value="get",
    default=None,
    help="""
    If flag passed without options, include python spec from pyproject.toml in yaml
    output. If value passed, use this value (exactly) in the output. So, for example,
    pass `--python-include "python=3.8"`
    """,
)
PYTHON_VERSION_CLI = click.option(
    "--python-version",
    "python_version",
    type=str,
    default=None,
    help="""
    Python version to check `python_verion <=> {python_version}` lines against. That is,
    this version is used to limit packages in resulting output. For example, if have a
    line like `a-package; python_version < '3.9'`, Using `--python-version 3.10` will
    not include `a-package`, while `--python-version 3.8` will include `a-package`.
    """,
)

PYTHON_CLI = click.option(
    "-p",
    "--python",
    "python",
    type=str,
    default=None,
    help="""
    Python version. Passing `--python {version}` is equivalent to passing
    `--python-version={version} --python-include=python{version}`. If passed, this
    overrides values of passed via `--python-version` and `--python-include`.
    """,
)
HEADER_CLI = click.option(
    "--header/--no-header",
    "header",
    is_flag=True,
    default=None,
    help="""
    If True (--header) include header line in output. Default is to include the header
    for output to a file, and not to include header when writing to stdout.
    """,
)
DEPS_CLI = click.option(
    "-d",
    "--deps",
    "deps",
    multiple=True,
    help="""
    Additional conda dependencies.
    """,
)
REQS_CLI = click.option(
    "-r",
    "--reqs",
    "reqs",
    multiple=True,
    help="""
    Additional pip requirements.
    """,
)


# * Utils
def _get_header_cmd(header: bool | None, output: click.Path | None) -> str | None:
    if header is None:
        header = output is not None

    if header:
        # return ""
        import sys
        from pathlib import Path

        return " ".join([Path(sys.argv[0]).name] + sys.argv[1:])
    else:
        return None


@lru_cache
def _get_pyproject2conda(filename) -> PyProject2Conda:
    return PyProject2Conda.from_path(filename)


# * App
class AliasedGroup(RichGroup):
    """Provide aliasing for commands"""

    def get_command(self, ctx, cmd_name):  # type: ignore
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail(
            "Too many matches: %s" % ", ".join(sorted(matches))
        )  # pragma: no cover


@click.group(cls=AliasedGroup)
@click.version_option(version=__version__)
def app() -> None:
    pass


# ** List
@app.command()
@PYPROJECT_CLI
@VERBOSE_CLI
def list(
    filename: str,
    verbose: bool,
) -> None:
    """List available extras"""

    if verbose:
        click.echo(f"filename: {filename}")

    d = _get_pyproject2conda(filename)
    click.echo(f"extras  : {d.list_extras()}")


# ** Yaml
def yaml(
    filename,
    extras,
    channels=None,
    output=None,
    name=None,
    python_include=None,
    python_version=None,
    python=None,
    base=True,
    sort=True,
    header=None,
    overwrite="check",
    verbose=False,
    deps=None,
    reqs=None,
):
    """Create yaml file from dependencies and optional-dependencies."""

    if not update_target(output, filename, overwrite=overwrite):
        if verbose:
            click.echo(
                f"# Skipping yaml {output}. Pass `-w force` to force recreate output"
            )
        return

    if not channels:
        channels = None

    python_include, python_version = parse_pythons(
        python_include=python_include,
        python_version=python_version,
        python=python,
    )

    d = _get_pyproject2conda(filename)

    if verbose and output:
        click.echo(f"# Creating yaml {output}")

    s = d.to_conda_yaml(
        extras=extras,
        channels=channels,
        name=name,
        stream=output,
        python_include=python_include,
        python_version=python_version,
        include_base_dependencies=base,
        header_cmd=_get_header_cmd(header, output),
        sort=sort,
        deps=deps,
        reqs=reqs,
    )
    if not output:
        click.echo(s, nl=False)


yaml_app = compose_decorators(  # type: ignore
    app.command(name="yaml"),
    PYPROJECT_CLI,
    EXTRAS_CLI,
    CHANNEL_CLI,
    OUTPUT_CLI,
    NAME_CLI,
    PYTHON_INCLUDE_CLI,
    PYTHON_VERSION_CLI,
    PYTHON_CLI,
    BASE_DEPENDENCIES_CLI,
    SORT_DEPENDENCIES_CLI,
    HEADER_CLI,
    OVERWRITE_CLI,
    VERBOSE_CLI,
    DEPS_CLI,
    REQS_CLI,
)(yaml)


# ** Requirements
def requirements(
    filename,
    extras,
    output=None,
    base=True,
    sort=True,
    header=None,
    overwrite="check",
    verbose=False,
    reqs=None,
):
    """Create requirements.txt for pip dependencies."""

    if not update_target(output, filename, overwrite=overwrite):
        if verbose:
            print(
                f"# Skipping requirements {output}. Pass `-w force` to force recreate output"
            )
        return

    d = _get_pyproject2conda(filename)

    if verbose and output:
        click.echo(f"# Creating requirements {output}")

    s = d.to_requirements(
        extras=extras,
        stream=output,
        include_base_dependencies=base,
        header_cmd=_get_header_cmd(header, output),
        sort=sort,
        reqs=reqs,
    )
    if not output:
        click.echo(s, nl=False)


requirements_app = compose_decorators(  # type: ignore
    app.command(name="requirements"),
    EXTRAS_CLI,
    PYPROJECT_CLI,
    OUTPUT_CLI,
    BASE_DEPENDENCIES_CLI,
    SORT_DEPENDENCIES_CLI,
    HEADER_CLI,
    OVERWRITE_CLI,
    VERBOSE_CLI,
    REQS_CLI,
)(requirements)


# # ** From project
def project(
    filename,
    envs,
    template,
    template_python,
    sort,
    header,
    overwrite,
    verbose,
    dry,
    user_config,
):
    """Create multiple environment files from `pyproject.toml` specification."""
    from .config import Config

    if dry:
        verbose = True

    c = Config.from_file(filename, user_config=user_config)

    if user_config == "infer" or user_config is None:
        user_config = c.user_config()

    for style, d in c.iter(
        envs=envs,
        template=template,
        template_python=template_python,
        sort=sort,
        header=header,
        overwrite=overwrite,
        verbose=verbose,
    ):
        if dry:
            click.echo(
                "# Creating {style} {output}".format(style=style, output=d["output"])
            )
            d["output"] = None

        # Special case: have output and userconfig.  Check update
        if not update_target(
            d["output"],
            filename,
            *([user_config] if user_config else []),
            overwrite=d["overwrite"],
        ):
            if verbose:
                click.echo(
                    f"# Skipping {style} {d['output']}.  Pass `-w force to force recreate output`"
                )
        else:
            d["overwrite"] = "force"
            if style == "yaml":
                yaml(filename=filename, **d)

            elif style == "requirements":
                requirements(filename=filename, **d)
            else:
                raise ValueError(f"unknown style {style}")


project_app = compose_decorators(  # type: ignore
    app.command(name="project"),
    PYPROJECT_CLI,
    click.option(
        "--envs",
        "envs",
        type=str,
        default=None,
        multiple=True,
        help="""
        List of environments to build files for.  Default to building all environments
        """,
    ),
    click.option(
        "--template",
        "template",
        type=str,
        default=None,
        help="""
        Template for environments that do not have a python version. Defaults to `{env}`.
        """,
    ),
    click.option(
        "--template-python",
        "template_python",
        default=None,
        type=str,
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
    SORT_DEPENDENCIES_CLI,
    HEADER_CLI,
    OVERWRITE_CLI,
    VERBOSE_CLI,
    click.option(
        "--dry/--no-dry",
        "dry",
        is_flag=True,
        default=False,
        help="If true, do a dry run",
    ),
    click.option(
        "--user-config",
        type=str,
        default="infer",
        help="""
        Additional toml file to supply configuration. This can be used to override/add
        environment files for your own use (apart from project env files).
        The (default) value `infer` means to infer the configuration from `--filename`.
        """,
    ),
)(project)


# ** Conda requirements
def conda_requirements(
    extras,
    python_include,
    python_version,
    python,
    channels,
    filename,
    base,
    prefix,
    prepend_channel,
    sort,
    header,
    # paths,
    path_conda,
    path_pip,
    deps,
    reqs,
):
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
        raise ValueError("can only specify neither or both path_conda and path_pip")

    if path_conda and path_pip and prefix is not None:
        raise ValueError("specify path_conda and path_pip or prefix, not all")

    if prefix is not None:
        path_conda = prefix + "conda.txt"
        path_pip = prefix + "pip.txt"

    d = _get_pyproject2conda(filename)

    _get_header_cmd(header, path_conda)

    deps, reqs = d.to_conda_requirements(
        extras=extras,
        python_include=python_include,
        python_version=python_version,
        channels=channels,
        prepend_channel=prepend_channel,
        stream_conda=path_conda,
        stream_pip=path_pip,
        include_base_dependencies=base,
        header_cmd=_get_header_cmd(header, path_conda),
        sort=sort,
        deps=deps,
        reqs=reqs,
    )

    if not path_conda:
        s = f"#conda requirements\n{deps}\n#pip requirements\n{reqs}"
        click.echo(s, nl=False)


conda_requirements_app = compose_decorators(  # type: ignore
    app.command(name="conda-requirements"),
    EXTRAS_CLI,
    PYTHON_INCLUDE_CLI,
    PYTHON_VERSION_CLI,
    PYTHON_CLI,
    CHANNEL_CLI,
    PYPROJECT_CLI,
    BASE_DEPENDENCIES_CLI,
    SORT_DEPENDENCIES_CLI,
    HEADER_CLI,
    click.option(
        "--prefix",
        "prefix",
        type=str,
        default=None,
        help="set conda-output=prefix + 'conda.txt', pip-output=prefix + 'pip.txt'",
    ),
    click.option(
        "--prepend-channel",
        is_flag=True,
        default=False,
    ),
    click.argument("path_conda", type=str, required=False),
    click.argument("path_pip", type=str, required=False),
    DEPS_CLI,
    REQS_CLI,
)(conda_requirements)


# ** json
def to_json(
    extras,
    python_include,
    python_version,
    channels,
    filename,
    sort,
    output,
    base,
    deps,
    reqs,
):
    """
    Create json representation.

    Keys are:
    "dependencies": conda dependencies.
    "pip": pip dependencies.
    "channels": conda channels.
    """

    import json

    d = _get_pyproject2conda(filename)

    result = d.to_conda_lists(
        extras=extras,
        channels=channels,
        python_include=python_include,
        python_version=python_version,
        include_base_dependencies=base,
        sort=sort,
        deps=deps,
        reqs=reqs,
    )

    if output:
        with open(output, "w") as f:
            json.dump(result, f)
    else:
        click.echo(json.dumps(result))  # , indent=2))


to_json_app = compose_decorators(  # type: ignore
    app.command(name="json"),
    EXTRAS_CLI,
    PYTHON_INCLUDE_CLI,
    PYTHON_VERSION_CLI,
    CHANNEL_CLI,
    PYPROJECT_CLI,
    SORT_DEPENDENCIES_CLI,
    OUTPUT_CLI,
    BASE_DEPENDENCIES_CLI,
    DEPS_CLI,
    REQS_CLI,
)(to_json)


# ** Main
if __name__ == "__main__":
    app()  # pragma: no cover
