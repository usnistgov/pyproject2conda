"""Utilities to use with cog"""

from __future__ import annotations

import locale
import shlex
import subprocess
import textwrap
from functools import lru_cache
from pathlib import Path


def wrap_command(cmd: str) -> str:
    x = textwrap.wrap(cmd.strip(), 80)

    if len(cmd) > 1:
        x[:-1] = [c + " \\" for c in x[:-1]]
        x[1:] = [" " * 4 + c for c in x[1:]]

    return "\n".join(x)


@lru_cache
def get_pyproject(path: str) -> list[str]:
    with Path(path).open(encoding=locale.getpreferredencoding(False)) as f:
        return [_.strip() for _ in f]


def run_command(
    cmd: str,
    wrapper: str = "bash",
    include_cmd: bool = True,
    bounds: tuple[int | None, int | None] | None = None,
) -> None:
    args = shlex.split(cmd)
    output = subprocess.check_output(args)

    total = output.decode()

    if bounds is not None:
        x = total.split("\n")[bounds[0] : bounds[1]]
        if bounds[0] is not None:
            x = ["...\n", *x]
        if bounds[1] is not None:
            x = [*x, "\n ...\n"]

        total = "\n".join(x)

    if include_cmd:
        cmd = wrap_command(cmd)

        total = f"$ {cmd}\n{total}"

    if wrapper:
        total = f"```{wrapper}\n" + total + "```\n"

    print(total)  # noqa: T201


def cat_lines(
    path: str = "tests/data/test-pyproject.toml",
    begin: str | int | None = None,
    end: str | int | None = None,
    begin_dot: bool = False,
    end_dot: bool = False,
) -> None:
    lines = get_pyproject(path)

    begin_dot = begin_dot or begin is not None
    end_dot = end_dot or end is not None

    if isinstance(begin, str):
        begin = lines.index(begin)
    if isinstance(end, str):
        end = lines.index(end)

    output = "\n".join(lines[slice(begin, end)])

    if begin_dot:
        output = "# ...\n" + output

    if end_dot:
        output = output + "\n# ..."

    output = "\n```toml\n" + output + "\n```\n"
    print(output)  # noqa: T201
