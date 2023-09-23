# mypy: disable-error-code="no-untyped-def, no-untyped-call"
"""
Console script for pyproject2conda (:mod:`pyproject2conda.cli`)
===============================================================
"""
# * Imports
import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import typer
from noxopt import Annotated

from pyproject2conda import __version__
from pyproject2conda.parser import PyProject2Conda
from pyproject2conda.utils import (
    parse_pythons,
    update_target,
)

if "P2C_RICH_MAX_WIDTH" in os.environ:
    context_settings = {"max_content_width": os.environ["P2C_RICH_MAX_WIDTH"]}
else:
    context_settings = {}

context_settings = {"max_content_width": 40}

app = typer.Typer(context_settings=context_settings)


def version_callback(value: bool):
    if value:
        typer.echo(f"{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    # Do other global stuff, handle other global options here
    return


def hello(there: Annotated[str, typer.Option("--there", help="a thing")] = "there"):
    print("hello", there)


# if os.environ.get("P2C_USE_CLICK", "True").lower() not in ("0", "f", "false"):
#     # use rich
#     import rich_click as click
#     from rich_click.rich_group import RichGroup

#     if "P2C_RICH_CLICK_MAX_WIDTH" in os.environ:
#         click.rich_click.MAX_WIDTH = int(
#             os.environ["P2C_RICH_CLICK_MAX_WIDTH"]
#         )  # pragma: no cover

# else:  # pragma: no cover
#     # Special case for generating README.pdf
#     import click  # type: ignore[no-redef]
#     from click import Group as RichGroup  # type: ignore[assignment]


# * Options

DEFAULT_TOML_PATH = Path("./pyproject.toml")

PYPROJECT_CLI = Annotated[
    Path,
    typer.Option(
        "--file",
        "-f",
        help="input pyproject.toml file",
    ),
]
EXTRAS_CLI = Annotated[
    Optional[List[str]],
    typer.Option(
        "--extra",
        "-e",
        help="Extra depenedencies. Can specify multiple times for multiple extras.",
    ),
]
CHANNEL_CLI = Annotated[
    Optional[List[str]],
    typer.Option(
        "--channel",
        "-c",
        help="conda channel.  Can specify. Overrides [tool.pyproject2conda.channels]",
    ),
]
NAME_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--name",
        "-n",
        help="Name of conda env",
    ),
]
OUTPUT_CLI = Annotated[
    Optional[Path],
    typer.Option(
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
    bool, typer.Option("--verbose", "-v", help="Pass `-v/--verbose` for verbose output")
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
PYTHON_FROM_CONFIG_CLI = Annotated[
    bool,
    typer.Option(
        help="""
        If specified, get python spec from pyproject.toml.
        This only applies if `--python-include` and `--python` are
        not set.
        """
    ),
]
PYTHON_INCLUDE_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--python-include",
        help="""
        If value passed, use this value (exactly) in the output. So, for example,
        pass `--python-include "python=3.8"`
        """,
    ),
]
PYTHON_VERSION_CLI = Annotated[
    Optional[str],
    typer.Option(
        "--python-version",
        help="""
         Python version to check `python_verion <=> {python_version}` lines against. That is,
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


# * Utils
def _get_header_cmd(header: bool | None, output: str | Path | None) -> str | None:
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
# class AliasedGroup(RichGroup):
#     """Provide aliasing for commands"""

#     def get_command(self, ctx, cmd_name):  # type: ignore
#         rv = click.Group.get_command(self, ctx, cmd_name)
#         if rv is not None:
#             return rv
#         matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
#         if not matches:
#             return None
#         elif len(matches) == 1:
#             return click.Group.get_command(self, ctx, matches[0])
#         ctx.fail(
#             "Too many matches: %s" % ", ".join(sorted(matches))
#         )  # pragma: no cover


# @click.group(cls=AliasedGroup)
# @click.version_option(version=__version__)
# def app() -> None:
#     pass


# ** List
@app.command("l", hidden=True)
@app.command()
def list(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    verbose: VERBOSE_CLI = False,
) -> None:
    """List available extras. (Alias `l`)"""

    if verbose:
        print(f"filename: {filename}")

    d = _get_pyproject2conda(filename)
    print(f"extras  : {d.list_extras()}")


# ** Yaml
@app.command("y", hidden=True)
@app.command()
def yaml(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    extras: EXTRAS_CLI = None,
    channels: CHANNEL_CLI = None,
    output: OUTPUT_CLI = None,
    name: NAME_CLI = None,
    python_from_config: PYTHON_FROM_CONFIG_CLI = False,
    python_include: PYTHON_INCLUDE_CLI = None,
    python_version: PYTHON_VERSION_CLI = None,
    python: PYTHON_CLI = None,
    base: BASE_DEPENDENCIES_CLI = True,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.check,
    verbose: VERBOSE_CLI = False,
    deps: DEPS_CLI = None,
    reqs: REQS_CLI = None,
):
    """Create yaml file from dependencies and optional-dependencies. (Alias `y`)"""

    if not update_target(output, filename, overwrite=overwrite.value):
        if verbose:
            print(f"# Skipping yaml {output}. Pass `-w force` to force recreate output")
        return

    if not channels:
        channels = None

    python_include, python_version = parse_pythons(
        python_from_config=python_from_config,
        python_include=python_include,
        python_version=python_version,
        python=python,
    )

    d = _get_pyproject2conda(filename)

    if verbose and output:
        print(f"# Creating yaml {output}")

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
        print(s, end="")


# ** Requirements
@app.command("r", hidden=True)
@app.command()
def requirements(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    extras: EXTRAS_CLI = None,
    output: OUTPUT_CLI = None,
    base: BASE_DEPENDENCIES_CLI = True,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.check,
    verbose: VERBOSE_CLI = False,
    reqs: REQS_CLI = None,
):
    """Create requirements.txt for pip dependencies. (Alias "r")"""

    if not update_target(output, filename, overwrite=overwrite.value):
        if verbose:
            print(
                f"# Skipping requirements {output}. Pass `-w force` to force recreate output"
            )
        return

    d = _get_pyproject2conda(filename)

    if verbose and output:
        print(f"# Creating requirements {output}")

    s = d.to_requirements(
        extras=extras,
        stream=output,
        include_base_dependencies=base,
        header_cmd=_get_header_cmd(header, output),
        sort=sort,
        reqs=reqs,
    )
    if not output:
        print(s, end="")


# # ** From project
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
        Additional toml file to supply configuration. This can be used to override/add
        environment files for your own use (apart from project env files).
        The (default) value `infer` means to infer the configuration from `--filename`.
        """,
    ),
]


@app.command("p", hidden=True)
@app.command()
def project(
    filename: PYPROJECT_CLI = DEFAULT_TOML_PATH,
    envs: ENVS_CLI = None,
    template: TEMPLATE_CLI = None,
    template_python: TEMPLATE_PYTHON_CLI = None,
    sort: SORT_DEPENDENCIES_CLI = True,
    header: HEADER_CLI = None,
    overwrite: OVERWRITE_CLI = Overwrite.check,
    verbose: VERBOSE_CLI = False,
    dry: DRY_CLI = False,
    user_config: USER_CONFIG_CLI = "infer",
):
    """Create multiple environment files from `pyproject.toml` specification. (Alias "p")"""
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
        overwrite=overwrite.value,
        verbose=verbose,
    ):
        if dry:
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
                print(
                    f"# Skipping {style} {d['output']}.  Pass `-w force to force recreate output`"
                )
        else:
            d["overwrite"] = Overwrite("force")
            if style == "yaml":
                yaml(filename=filename, **d)

            elif style == "requirements":
                requirements(filename=filename, **d)
            else:
                raise ValueError(f"unknown style {style}")


# ** Conda requirements
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


@app.command("cr", hidden=True)
@app.command()
def conda_requirements(
    path_conda: Annotated[Optional[str], typer.Argument()] = None,
    path_pip: Annotated[Optional[str], typer.Argument()] = None,
    extras: EXTRAS_CLI = None,
    python_from_config: PYTHON_FROM_CONFIG_CLI = False,
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
):
    """
    Create requirement files for conda and pip. (Alias "cr")

    These can be install with, for example,

    conda install --file {path_conda}
    pip install -r {path_pip}
    """

    python_include, python_version = parse_pythons(
        python_from_config=python_from_config,
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
        print(s, end="")


# ** json
@app.command("j", hidden=True)
@app.command("json")
def to_json(
    extras: EXTRAS_CLI = None,
    python_from_config: PYTHON_FROM_CONFIG_CLI = False,
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
):
    """
    Create json representation. (Alias "j")

    Keys are:
    "dependencies": conda dependencies.
    "pip": pip dependencies.
    "channels": conda channels.
    """

    import json

    d = _get_pyproject2conda(filename)

    python_include, python_version = parse_pythons(
        python_from_config=python_from_config,
        python_include=python_include,
        python_version=python_version,
        python=python,
    )

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
        print(json.dumps(result))  # , indent=2))


# ** Main
if __name__ == "__main__":
    app()  # pragma: no cover
