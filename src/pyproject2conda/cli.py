"""Console script for pyproject2conda."""


import rich_click as click

from pyproject2conda.parser import PyProject2Conda

FILE_CLI = click.option(
    "-f",
    "--file",
    "filename",
    type=click.Path(),
    default="pyproject.toml",
    help="input pyproject.toml file",
)
EXTRAS_CLI = click.argument(
    "extras", type=str, nargs=-1
)  # , help="extra depenedencies")
ISOLATED_CLI = click.argument(
    "isolated", type=str, nargs=-1, required=True
)  # , help="Isolated dependencies (under [tool.pyproject2conda.isolated-dependencies])")
CHANNEL_CLI = click.option(
    "-c",
    "--channel",
    "channel",
    type=str,
    default=None,
    multiple=True,
    help="conda channel.  Can be specified multiple times. Overrides [tool.pyproject2conda.channels]",
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


@click.group()
def app():
    pass


@app.command()
@FILE_CLI
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
@CHANNEL_CLI
@FILE_CLI
@NAME_CLI
@OUTPUT_CLI
def create(
    extras,
    channel,
    filename,
    name,
    output,
):
    """Create yaml file from dependencies and optional-dependencies."""

    if not channel:
        channel = None
    d = PyProject2Conda.from_path(filename)
    s = d.to_conda_yaml(extras=extras, channels=channel, name=name, stream=output)
    if not output:
        click.echo(s, nl=False)


@app.command()
@ISOLATED_CLI
@CHANNEL_CLI
@FILE_CLI
@NAME_CLI
@OUTPUT_CLI
def isolated(
    isolated,
    channel,
    filename,
    name,
    output,
):
    """Create yaml file from [tool.pyproject2conda.isolated-dependencies]"""

    if not channel:
        channel = None
    d = PyProject2Conda.from_path(filename)
    s = d.to_conda_yaml(isolated=isolated, channels=channel, name=name)
    if not output:
        click.echo(s, nl=False)


if __name__ == "__main__":
    app()
