"""Console script for pyproject2conda."""


import rich_click as click

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
ISOLATED_CLI = click.option(
    "-i",
    "--isolated",
    "isolated",
    type=str,
    multiple=True,
    help="Isolated dependencies (under [tool.pyproject2conda.isolated-dependencies]).  Can specify multiple times.",
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


PYTHON_CLI = click.option(
    "-p",
    "--python",
    "python",
    is_flag=False,
    flag_value="get",
    default=None,
    help="if flag passed without options, include python spec from pyproject.toml in output.  If value passed, use this value of python in the output",
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
        ctx.fail("Too many matches: %s" % ", ".join(sorted(matches)))


@click.group(cls=AliasedGroup)
def app():
    pass


@app.command()
@PYPROJECT_CLI
@VERBOSE_CLI
def list(
    filename,
    verbose,
):
    """List available extras/isolated"""

    if verbose:
        click.echo(f"filename: {filename}")

    d = PyProject2Conda.from_path(filename)
    click.echo(f"extras  : {d.list_extras()}")
    click.echo(f"isolated: {d.list_isolated()}")


@app.command()
@EXTRAS_CLI
@ISOLATED_CLI
@CHANNEL_CLI
@PYPROJECT_CLI
@NAME_CLI
@OUTPUT_CLI
@PYTHON_CLI
def yaml(
    extras,
    isolated,
    channels,
    filename,
    name,
    output,
    python,
):
    """Create yaml file from dependencies and optional-dependencies."""

    if not channels:
        channels = None

    d = PyProject2Conda.from_path(filename)
    s = d.to_conda_yaml(
        extras=extras,
        isolated=isolated,
        channels=channels,
        name=name,
        stream=output,
        python=python,
    )
    if not output:
        click.echo(s, nl=False)


@app.command()
@EXTRAS_CLI
@ISOLATED_CLI
@PYPROJECT_CLI
@OUTPUT_CLI
def requirements(
    extras,
    isolated,
    filename,
    output,
):
    """Create requirements.txt for pip depedencies."""

    d = PyProject2Conda.from_path(filename)
    s = d.to_requirements(
        extras=extras,
        isolated=isolated,
        stream=output,
    )
    if not output:
        click.echo(s, nl=False)


@app.command()
@EXTRAS_CLI
@ISOLATED_CLI
@PYTHON_CLI
@CHANNEL_CLI
@PYPROJECT_CLI
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
    isolated,
    python,
    channels,
    filename,
    prefix,
    prepend_channel,
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

    deps, reqs = d.to_conda_requirements(
        extras=extras,
        isolated=isolated,
        python=python,
        channels=channels,
        prepend_channel=prepend_channel,
        stream_conda=path_conda,
        stream_pip=path_pip,
    )

    if not path_conda:
        s = f"#conda requirements\n{deps}\n#pip requirements\n{reqs}"
        click.echo(s, nl=False)


@app.command("json")
@EXTRAS_CLI
@ISOLATED_CLI
@PYTHON_CLI
@CHANNEL_CLI
@PYPROJECT_CLI
@OUTPUT_CLI
def to_json(
    extras,
    isolated,
    python,
    channels,
    filename,
    output,
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
        extras=extras, isolated=isolated, channels=channels, python=python
    )

    if output:
        with open(output, "w") as f:
            json.dump(result, f)
    else:
        click.echo(json.dumps(result))  # , indent=2))


# @app.command("yaml-conda-req")
# @EXTRAS_CLI
# @PYTHON_CLI
# @PYPROJECT_CLI
# def conda_requirements(
#         extras,
#         python,
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
# @PYTHON_CLI
# def isolated(
#     isolated,
#     channel,
#     filename,
#     name,
#     output,
#     python,
# ):
#     """Create yaml file from [tool.pyproject2conda.isolated-dependencies]"""

#     if not channel:
#         channel = None
#     d = PyProject2Conda.from_path(filename)
#     s = d.to_conda_yaml(
#         isolated=isolated, channels=channel, name=name, python=python, stream=output
#     )
#     if not output:
#         click.echo(s, nl=False)


if __name__ == "__main__":
    app()
