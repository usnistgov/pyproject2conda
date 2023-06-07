"""Console script for pyproject2conda."""


import rich_click as click

from pyproject2conda.parser import PyProject2Conda

FILE_CLI = click.option("-f","--file","filename", type=click.Path(), default="pyproject.toml", help="input pyproject.toml file")
EXTRAS_CLI = click.argument("extras", type=str, nargs=-1)#, help="extra depenedencies")
ISOLATED_CLI = click.argument("isolated", type=str, nargs=-1, required=True)#, help="Isolated dependencies (under [tool.pyproject2conda.isolated-dependencies])")
CHANNEL_CLI = click.option("-c","--channel", "channel", type=str, default=None, multiple=True, help="conda channel.  Can be specified multiple times. Overrides [tool.pyproject2conda.channels]")
NAME_CLI = click.option("-n","--name", "name", type=str, default=None, help="Name of conda env")
OUTPUT_CLI = click.option("-o","--output", "output", type=click.Path(), default=None, help="File to output results")

VERBOSE_CLI = click.option("-v", "--verbose", "verbose", is_flag=True, default=False)


@click.group()
def app(
):
    pass


@app.command()
@FILE_CLI
@VERBOSE_CLI
def list(
        filename,
        verbose,
):

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
    """
    Create yaml file from dependencies and optional-dependencies.
    """

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
    """
    Create yaml file from [tool.pyproject2conda.isolated-dependencies]
    """

    if not channel:
        channel = None
    d = PyProject2Conda.from_path(filename)
    s = d.to_conda_yaml(isolated=isolated, channels=channel, name=name)
    if not output:
        click.echo(s, nl=False)

if __name__ == "__main__":
    app()
# from __future__ import annotations
# import typer

# from typing import Optional

# from typing_extensions import Annotated

# from pyproject2conda.parser import PyProject2Conda

# app = typer.Typer(help="pyproject2conda CLI manager.")

# FILE_OPT = typer.Option('-f','--file')
# FILE_CLI = Annotated[str | None, FILE_OPT]
# FILE_CLI = Annotated[str | None, typer.Argument()]

# EXTRAS_OPT = typer.Option('-e','--extras')
# EXTRAS_CLI = Annotated[list[str] | None, EXTRAS_OPT]

# ISOLATED_OPT = typer.Option('-i','--isolated')
# ISOLATED_CLI = Annotated[list[str] | None, ISOLATED_OPT]

# @app.command()
# def main():
#     """Console script for pyproject2conda."""
#     print("hello")
#     print("Replace this message by putting your code into "
#                "pyproject2conda.cli.main")
#     print("See click documentation at https://click.palletsprojects.com/")
#     return 0


# @app.command()
# def list(
#         # file: FILE_CLI = "pyproject.toml",
#         file: Annotated[str, typer.Option('-f')] = "pyproject.toml",
# ):

#     d = PyProject2Conda.from_path(file)

#     print('extras', d.list_extras())
#     print('isolated', d.list_isolated())


# @app.command()
# def create(
#         file: FILE_CLI = "pyproject.toml",
#         extras: EXTRAS_CLI = None,
#         isolated: ISOLATED_CLI = None,
# ):
#     print(files)
#     print(extras)
#     print(isolated)



# @app.command()
# def other(name: Annotated[Optional[str], typer.Argument()] = None):
#     if name is None:
#         print("Hello World!")
#     else:
#         print(f"Hello {name}")
