"""Simple cli script to execute notebooks using only `nbclient`."""

from __future__ import annotations

import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

import nbformat  # type: ignore[import-not-found,unused-ignore]
from nbclient.client import (  # type: ignore[import-not-found,unused-ignore]
    NotebookClient,  # type: ignore[import-not-found,unused-ignore]
)

if TYPE_CHECKING:
    from typing import Sequence

# * Logging
FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger("execute_notebook")


def get_parser() -> ArgumentParser:
    """Get parser."""
    parser = ArgumentParser(
        description="Application to execute and optionally save a notebook."
    )

    parser.add_argument("notebooks", help="notebook files to execute", nargs="+")
    parser.add_argument(
        "--timeout", type=int, default=None, help="Time to wait for output."
    )
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=60,
        help="Time to wait for kernel to start.",
    )
    parser.add_argument(
        "-e",
        "--allow-errors",
        action="store_true",
        help="If passed, allow errors in notebook.",
    )
    parser.add_argument(
        "-k", "--kernel-name", type=str, default="python3", help="kernel name."
    )
    parser.add_argument(
        "--skip-cells-with-tag",
        type=str,
        default="skip-execution",
        help="name of cell tag to use to denote a cell that should be skipped.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Set verbosity level.  Pass multiple times to up level.",
    )
    parser.add_argument(
        "-i",
        "--inplace",
        action="store_true",
        help="If passed, overwrite input with executed notebooks.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output name.  Supports replace {notebook_name}.",
    )

    return parser


def set_verbosity_level(logger: logging.Logger, verbosity: int | None) -> None:
    """Set verbosity level."""
    if verbosity is None:
        return

    if verbosity < 0:
        level = logging.WARNING
    elif verbosity == 0:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logger.setLevel(level)


def run_notebook(
    notebook_path: str,
    timeout: int | None = None,
    startup_timeout: int = 60,
    allow_errors: bool = False,
    skip_cells_with_tag: str = "str-execution",
    kernel_name: str = "",
    inplace: bool = False,
    output_base: str | None = None,
) -> None:
    """Run a notebook by path."""
    # Log it
    logger.info("Executing %s", notebook_path)

    input_path = Path(notebook_path).with_suffix(".ipynb")

    # Get its parent directory so we can add it to the $PATH
    path = input_path.parent.absolute()

    # Optional output of executed notebook
    if inplace:
        output_path = input_path
    elif output_base:
        output_path = input_path.parent.joinpath(
            output_base.format(notebook_name=input_path.with_suffix("").name)
        ).with_suffix(".ipynb")
    else:
        output_path = None

    if output_path and not output_path.parent.is_dir():
        msg = f"Cannot write to directory={output_path.parent} that does not exist"
        raise ValueError(msg)

    # Open up the notebook we're going to run
    with input_path.open() as f:
        nb: nbformat.NotebookNode = nbformat.read(f, as_version=4)  # type: ignore[no-untyped-call,unused-ignore]

    # Configure nbclient to run the notebook
    client = NotebookClient(  # pyright: ignore[reportUnknownVariableType]
        nb,  # pyright: ignore[reportUnknownArgumentType]
        timeout=timeout,
        startup_timeout=startup_timeout,
        skip_cells_with_tag=skip_cells_with_tag,
        allow_errors=allow_errors,
        kernel_name=kernel_name,
        resources={"metadata": {"path": path}},
    )

    # Run it
    client.execute()  # pyright: ignore[reportUnknownMemberType]

    # Save it
    if output_path:
        logger.info("Save executed results to %s", output_path)
        nbformat.write(nb, output_path)  # type: ignore[no-untyped-call, unused-ignore]


def verify_notebooks(
    notebooks: Sequence[str],
    output_base: str | None,
) -> None:
    """Make sure notebooks/output make sense"""
    if (
        len(notebooks) > 1
        and output_base is not None
        and "{notebook_name}" not in output_base
    ):
        msg = (
            "If passing multiple notebooks with `--output=output` option, "
            "output string must contain {notebook_name}"
        )
        raise ValueError(msg)


if __name__ == "__main__":
    parser = get_parser()
    options = parser.parse_args()

    set_verbosity_level(logger, options.verbose)
    verify_notebooks(notebooks=options.notebooks, output_base=options.output)

    for notebook in options.notebooks:
        run_notebook(
            notebook,
            timeout=options.timeout,
            startup_timeout=options.startup_timeout,
            allow_errors=options.allow_errors,
            skip_cells_with_tag=options.skip_cells_with_tag,
            kernel_name=options.kernel_name,
            inplace=options.inplace,
            output_base=options.output,
        )
