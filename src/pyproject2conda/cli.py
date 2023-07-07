"""Console script for pyproject2conda."""


import rich_click as click

from pyproject2conda import __version__
from pyproject2conda.parser import PyProject2Conda

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
    default=None,
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
VERBOSE_CLI = click.option("-v", "--verbose", "verbose", is_flag=True, default=False)
BASE_DEPENDENCIES_CLI = click.option(
    "--base/--no-base",
    "base",
    is_flag=True,
    default=True,
    help="""
    Default is to include base (project.dependencies) with extras.
    However, passing `--no-base` will exclude base dependencies. This is useful to define
    environments that should exclude base dependencies (like build, etc) in pyproject.toml.
    """,
)
PYTHON_INCLUDE_CLI = click.option(
    "--python-include",
    "python_include",
    is_flag=False,
    flag_value="get",
    default=None,
    help="""
    If flag passed without options, include python spec from pyproject.toml in yaml output.  If value passed, use this value (exactly) in the output.
    So, for example, pass `--python-include "python=3.8"`
    """,
)
PYTHON_VERSION_CLI = click.option(
    "--python-version",
    "python_version",
    type=str,
    default=None,
    help="""
    Python version to check `python_verion <=> {python_version}` lines against.  That is, this version is used to limit packages in resulting output.
    For example, if have a line like   `a-package; python_version < '3.9'`,
    Using `--python-version 3.10` will not include `a-package`, while `--python-version 3.8` will include `a-package`.
    """,
)

HEADER_CLI = click.option(
    "--header/--no-header",
    "header",
    is_flag=True,
    default=None,
    help="""
    If True (--header) include header line in output.
    Default is to include the header for output to a file, and
    not to include header when writing to stdout.
    """,
)


class AliasedGroup(click.Group):
    """Provide aliasing for commands"""

    def get_command(self, ctx, cmd_name):
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
def app():
    pass


@app.command()
@PYPROJECT_CLI
@VERBOSE_CLI
def list(
    filename,
    verbose,
):
    """List available extras"""

    if verbose:
        click.echo(f"filename: {filename}")

    d = PyProject2Conda.from_path(filename)
    click.echo(f"extras  : {d.list_extras()}")


def _get_header_cmd(header, output):
    if header is None:
        header = output is not None

    if header:
        return ""
        # import sys
        # from pathlib import Path
        # return " ".join([Path(sys.argv[0]).name] + sys.argv[1:])
    else:
        return None


@app.command()
@EXTRAS_CLI
@CHANNEL_CLI
@PYPROJECT_CLI
@NAME_CLI
@OUTPUT_CLI
@PYTHON_INCLUDE_CLI
@PYTHON_VERSION_CLI
@BASE_DEPENDENCIES_CLI
@HEADER_CLI
def yaml(
    extras,
    channels,
    filename,
    name,
    output,
    python_include,
    python_version,
    base,
    header,
):
    """Create yaml file from dependencies and optional-dependencies."""

    if not channels:
        channels = None

    d = PyProject2Conda.from_path(filename)
    s = d.to_conda_yaml(
        extras=extras,
        channels=channels,
        name=name,
        stream=output,
        python_include=python_include,
        python_version=python_version,
        include_base_dependencies=base,
        header_cmd=_get_header_cmd(header, output),
    )
    if not output:
        click.echo(s, nl=False)


@app.command()
@EXTRAS_CLI
@PYPROJECT_CLI
@OUTPUT_CLI
@BASE_DEPENDENCIES_CLI
@HEADER_CLI
def requirements(
    extras,
    filename,
    output,
    base,
    header,
):
    """Create requirements.txt for pip depedencies."""

    d = PyProject2Conda.from_path(filename)
    s = d.to_requirements(
        extras=extras,
        stream=output,
        include_base_dependencies=base,
        header_cmd=_get_header_cmd(header, output),
    )
    if not output:
        click.echo(s, nl=False)


@app.command()
@EXTRAS_CLI
@PYTHON_INCLUDE_CLI
@PYTHON_VERSION_CLI
@CHANNEL_CLI
@PYPROJECT_CLI
@BASE_DEPENDENCIES_CLI
@HEADER_CLI
@click.option(
    "--prefix",
    "prefix",
    type=str,
    default=None,
    help="set conda-output=prefix + 'conda.txt', pip-output=prefix + 'pip.txt'",
)
@click.option(
    "--prepend-channel",
    is_flag=True,
    default=False,
)
@click.argument("path_conda", type=str, required=False)
@click.argument("path_pip", type=str, required=False)
def conda_requirements(
    extras,
    python_include,
    python_version,
    channels,
    filename,
    base,
    prefix,
    prepend_channel,
    header,
    # paths,
    path_conda,
    path_pip,
):
    """
    Create requirement files for conda and pip.

    These can be install with, for example,

    conda install --file {path_conda}
    pip install -r {path_pip}
    """

    if path_conda and not path_pip:
        raise ValueError("can only specify neither or both path_conda and path_pip")

    if path_conda and path_pip and prefix is not None:
        raise ValueError("specify path_conda and path_pip or prefix, not all")

    if prefix is not None:
        path_conda = prefix + "conda.txt"
        path_pip = prefix + "pip.txt"

    d = PyProject2Conda.from_path(filename)

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
    )

    if not path_conda:
        s = f"#conda requirements\n{deps}\n#pip requirements\n{reqs}"
        click.echo(s, nl=False)


@app.command("json")
@EXTRAS_CLI
@PYTHON_INCLUDE_CLI
@PYTHON_VERSION_CLI
@CHANNEL_CLI
@PYPROJECT_CLI
@OUTPUT_CLI
@BASE_DEPENDENCIES_CLI
def to_json(
    extras,
    python_include,
    python_version,
    channels,
    filename,
    output,
    base,
):
    """
    Create json representation.

    Keys are:
    "dependencies": conda dependencies.
    "pip": pip dependencies.
    "channels": conda channels.
    """

    import json

    d = PyProject2Conda.from_path(filename)

    result = d.to_conda_lists(
        extras=extras,
        channels=channels,
        python_include=python_include,
        python_version=python_version,
        include_base_dependencies=base,
    )

    if output:
        with open(output, "w") as f:
            json.dump(result, f)
    else:
        click.echo(json.dumps(result))  # , indent=2))


# @app.command("yaml-conda-req")
# @EXTRAS_CLI
# @PYTHON_INCLUDE_CLI
# @PYPROJECT_CLI
# def conda_requirements(
#         extras,
#         python_include,
#         filename,

# ):
#     d = PyProject2Conda.from_path(filename)

#     output = d.to_conda_lists(extras=extras)
#     click.echo(f"{output}")


# @app.command()
# @ISOLATED_CLI
# @CHANNEL_CLI
# @PYPROJECT_CLI
# @NAME_CLI
# @OUTPUT_CLI
# @PYTHON_INCLUDE_CLI
# def isolated(
#     isolated,
#     channel,
#     filename,
#     name,
#     output,
#     python_include,
# ):
#     """Create yaml file from [tool.pyproject2conda.isolated-dependencies]"""

#     if not channel:
#         channel = None
#     d = PyProject2Conda.from_path(filename)
#     s = d.to_conda_yaml(
#         isolated=isolated, channels=channel, name=name, python_include=python_include, stream=output
#     )
#     if not output:
#         click.echo(s, nl=False)


if __name__ == "__main__":
    app()  # pragma: no cover
