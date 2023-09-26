"""Unitilities to use with cog"""
import shlex
import subprocess
import textwrap
from functools import lru_cache


def wrap_command(cmd):
    cmd = textwrap.wrap(cmd.strip(), 80)

    if len(cmd) > 1:
        cmd[:-1] = [c + " \\" for c in cmd[:-1]]
        cmd[1:] = [" " * 4 + c for c in cmd[1:]]

    return "\n".join(cmd)


@lru_cache
def get_pyproject(path):
    with open(path) as f:
        lines = [_.strip() for _ in f]
    return lines


def run_command(cmd, wrapper="bash", include_cmd=True, bounds=None):
    args = shlex.split(cmd)
    output = subprocess.check_output(args)

    total = output.decode()

    if bounds is not None:
        total = total.split("\n")[bounds[0] : bounds[1]]
        if bounds[0] is not None:
            total = ["...\n"] + total
        if bounds[1] is not None:
            total = total + ["\n ...\n"]

        total = "\n".join(total)

    if include_cmd:
        cmd = wrap_command(cmd)

        total = f"$ {cmd}\n{total}"

    if wrapper:
        total = f"```{wrapper}\n" + total + "```\n"

    print(total)


def cat_lines(
    path="tests/data/test-pyproject.toml",
    begin=None,
    end=None,
    begin_dot=None,
    end_dot=None,
):
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
    print(output)
