"""
Utility methods (:mod:`pyproject2conda.utils`)
==============================================
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Mapping, Sequence

    from ._typing import Dec, F


# taken from https://github.com/conda/conda-lock/blob/main/conda_lock/common.py
def get_in(
    keys: Sequence[Any], nested_dict: Mapping[Any, Any], default: Any = None
) -> Any:
    """
    >>> foo = {'a': {'b': {'c': 1}}}
    >>> get_in(['a', 'b'], foo)
    {'c': 1}

    """
    import operator
    from functools import reduce

    try:
        return reduce(operator.getitem, keys, nested_dict)
    except (KeyError, IndexError, TypeError):
        return default


# def compose_decorators(*decs: Dec[F]) -> Dec[F]:
#     from functools import reduce
#     def wrapper(func: F) -> F:
#         return reduce(lambda x, f: f(x), reversed(decs), func)
#     return wrapper


def compose_decorators(*decs: Dec[F]) -> Dec[F]:
    def wrapper(func: F) -> F:
        for d in reversed(decs):
            func = d(func)
        return func

    return wrapper


def parse_pythons(
    python_include: str | None, python_version: str | None, python: str | None
) -> tuple[str | None, str | None]:
    if python:
        return f"python={python}", python
    else:
        return python_include, python_version


def update_target(
    target: str | Path | None,
    *deps: str | Path,
    overwrite: str = "check",
) -> bool:
    """Check if target is older than deps:"""

    if target is None:
        # No output file. always run.
        return True

    overwrite = overwrite.lower()
    target = Path(target)

    if overwrite == "force":
        update = True
    elif overwrite == "skip":
        update = not target.exists()

    elif overwrite == "check":
        if not target.exists():
            update = True
        else:
            # check times
            deps_filtered = []
            for d in map(Path, deps):
                if d.exists():
                    deps_filtered.append(d)

            target_time = target.stat().st_mtime

            update = any(target_time < dep.stat().st_mtime for dep in deps_filtered)

    return update


# * filename from template
def filename_from_template(
    template: str | None,
    python: str | None = None,
    python_version: str | None = None,
    env_name: str | None = None,
    ext: str | None = "yaml",
) -> str | None:
    """
    Create a filename from

    --python-include python=3.8 or --python-version 3.8 or --python 3.8
    py_version: 3.8
    py: 38

    env : name of environment
    """

    if template is None:
        return None

    kws = {}
    if python:
        py_version = python
    elif python_version:
        py_version = python_version
    # elif python_include is not None:
    #     import re

    #     m = re.match(".*?([0-9.]+)", python_include)
    #     py_version = m.group(1)  # type: ignore
    else:
        py_version = None

    if py_version:
        kws["py_version"] = py_version
        kws["py"] = py_version.replace(".", "")

    if env_name:
        kws["env"] = env_name

    if ext:
        template = template + f".{ext}"

    return template.format(**kws)
