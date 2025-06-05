"""
Utility methods (:mod:`pyproject2conda.utils`)
==============================================
"""

from __future__ import annotations

import enum
import re
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence
    from typing import Any

    from ._typing import T


# taken from https://github.com/python-attrs/attrs/blob/main/src/attr/_make.py
class _Missing(enum.Enum):
    """
    Sentinel to indicate the lack of a value when ``None`` is ambiguous.

    If extending attrs, you can use ``typing.Literal[MISSING]`` to show
    that a value may be ``MISSING``.

    .. versionchanged:: 21.1.0 ``bool(MISSING)`` is now False.
    .. versionchanged:: 22.2.0 ``MISSING`` is now an ``enum.Enum`` variant.
    """

    MISSING = enum.auto()

    def __repr__(self) -> str:
        return "MISSING"  # pragma: no cover

    def __bool__(self) -> bool:
        return False  # pragma: no cover


MISSING = _Missing.MISSING
"""
Sentinel to indicate the lack of a value when ``None`` is ambiguous.
"""


# taken from https://github.com/conda/conda-lock/blob/main/conda_lock/common.py
def get_in(
    keys: Sequence[Any],
    nested_dict: Mapping[Any, Any],
    default: Any = None,
    factory: Callable[[], Any] | None = None,
) -> Any:
    """
    >>> foo = {"a": {"b": {"c": 1}}}
    >>> get_in(["a", "b"], foo)
    {'c': 1}

    """
    import operator
    from functools import reduce

    try:
        return reduce(  # pyre-ignore[no-matching-overload] # ty: ignore[no-matching-overload]
            operator.getitem,  # pyre-ignore[bad-argument-type]
            keys,
            nested_dict,
        )
    except (KeyError, IndexError, TypeError):
        if factory is not None:
            return factory()
        return default


def get_default_pythons(path: str | Path = ".python-version") -> list[str]:
    """Get default python value from .python-version file"""
    path = Path(path)
    if path.exists():
        out = path.read_text().split()
        # only keep major.minor
        out[0] = ".".join(out[0].split(".")[:2])
        return out
    return []


def get_default_pythons_with_fallback(
    paths: Iterable[str | Path] = (".python-version-default", ".python-version"),
) -> list[str]:
    """Get default pythons from possibly multiple sources"""
    for path in paths:
        out = get_default_pythons(path)
        if len(out) > 0:
            return out

    return []


def get_all_pythons(
    data: dict[str, Any] | None, path: str | Path | None = None
) -> list[str]:
    """Get python versions from pyproject:project.classifiers"""
    if data is None:
        assert path is not None  # noqa: S101

        from ._compat import tomllib

        with Path(path).open("rb") as f:
            data = tomllib.load(f)

    return [
        c.split()[-1]
        for c in get_in(["project", "classifiers"], data, factory=list)
        if c.startswith("Programming Language :: Python :: 3.")
    ]


def get_lowest_version(versions: Iterable[str]) -> str:
    """Get lowest version"""
    return min(versions, key=Version)  # ty: ignore[no-matching-overload]


def get_highest_version(versions: Iterable[str]) -> str:
    """Get highest version"""
    return max(versions, key=Version)  # ty: ignore[no-matching-overload]


def select_pythons(
    pythons: Sequence[str],
    default_pythons: list[str],
    all_pythons: list[str],
) -> list[str]:
    """Select pythons from string values."""
    if len(pythons) == 1:
        python = pythons[0]

        if python == "default":
            if not default_pythons:
                msg = "Must include `.python-version-default` or `.python-version` to use `python = 'default'`."
                raise ValueError(msg)
            return default_pythons

        if python in {"all", "lowest", "highest"}:
            if not all_pythons:
                msg = "Must specify python versions in project.classifiers table to use `python` in `{'all', 'lowest', 'highest'}`"
                raise ValueError(msg)
            return (
                all_pythons
                if python == "all"
                else [get_lowest_version(all_pythons)]
                if python == "lowest"
                else [get_highest_version(all_pythons)]
            )

    return list(pythons)


def parse_pythons(
    python_include: str | None,
    python_version: str | None,
    python: str | None,
    toml_path: str | Path,
) -> tuple[str | None, str | None]:
    """Create python_include/python_version."""
    if python:
        python = select_pythons(
            [python],
            get_default_pythons(),
            get_all_pythons(data=None, path=toml_path),
        )[0]
        return f"python={python}", python

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
            deps_filtered: list[Path] = [d for d in map(Path, deps) if d.exists()]  # pylint: disable=bad-builtin

            target_time = target.stat().st_mtime

            update = any(target_time < dep.stat().st_mtime for dep in deps_filtered)
    else:  # pragma: no cover
        msg = f"unknown option overwrite={overwrite}"
        raise ValueError(msg)

    return update


# * filename from template
def filename_from_template(
    template: str | None,
    python: str | None = None,
    python_version: str | None = None,
    env_name: str | None = None,
    ext: str | None = ".yaml",
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

    kws: dict[str, str] = {}
    if python:
        py_version = python
    elif python_version:
        py_version = python_version
    else:
        py_version = None

    if py_version:
        kws["py_version"] = py_version
        kws["py"] = py_version.replace(".", "")

    if env_name:  # pragma: no cover
        kws["env"] = env_name

    if ext:  # pragma: no cover
        template += f"{ext}"

    return template.format(**kws)


_WHITE_SPACE_REGEX = re.compile(r"\s+")


def remove_whitespace(s: str) -> str:
    """Cleanup whitespace from string."""
    return re.sub(_WHITE_SPACE_REGEX, "", s)


def remove_whitespace_list(s: Iterable[str]) -> list[str]:
    """Cleanup whitespace from list of strings."""
    return [remove_whitespace(x) for x in s]


def unique_list(values: Iterable[T]) -> list[T]:
    """
    Return only unique values in list.
    Unlike using set(values), this preserves order.
    """
    output: list[T] = []
    for v in values:
        if v not in output:
            output.append(v)
    return output


def list_to_str(values: Iterable[str] | None, eol: bool = True) -> str:
    """Join list of strings with newlines to single string."""
    if values:
        output = "\n".join(values)
        if eol:
            output += "\n"
    else:
        output = ""

    return output
