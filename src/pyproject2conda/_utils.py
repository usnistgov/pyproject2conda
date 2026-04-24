"""
Utility methods (:mod:`pyproject2conda.utils`)
==============================================
"""

from __future__ import annotations

import enum
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.version import Version

from ._typing_compat import override

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import TypeVar

    T = TypeVar("T")


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

    @override
    def __repr__(self) -> str:
        return "MISSING"  # pragma: no cover

    def __bool__(self) -> bool:
        return False  # pragma: no cover


MISSING = _Missing.MISSING
"""
Sentinel to indicate the lack of a value when ``None`` is ambiguous.
"""


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


def get_lowest_version(versions: Iterable[str]) -> str:
    """Get lowest version"""
    return min(versions, key=Version)


def get_highest_version(versions: Iterable[str]) -> str:
    """Get highest version"""
    return max(versions, key=Version)


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
def _get_standard_format_dict(
    env_name: str | None = None,
    python_version: str | None = None,
) -> dict[str, str]:
    kws: dict[str, str] = {}
    if env_name:
        kws["env"] = env_name

    if python_version:
        kws["py_version"] = python_version
        kws["py"] = python_version.replace(".", "")

    return kws


def path_from_template(
    template: str | None,
    python_version: str | None = None,
    env_name: str | None = None,
    ext: str | None = ".yaml",
) -> Path | None:
    """
    Create a filename from

    --python-include python=3.8 or --python-version 3.8 or --python 3.8
    py_version: 3.8
    py: 38

    env : name of environment
    """
    if template is None:
        return None

    kws = _get_standard_format_dict(env_name=env_name, python_version=python_version)

    if ext:  # pragma: no cover
        template += f"{ext}"

    return Path(template.format(**kws))


def conda_env_name_from_template(
    name: str | None,
    python_version: str | None = None,
    env_name: str | None = None,
) -> str | None:
    """Create environment name from name or template"""
    if name is None:
        return name

    kws = _get_standard_format_dict(env_name=env_name, python_version=python_version)

    return name.format(**kws)


def list_to_str(values: Iterable[str] | None, eol: bool = True) -> str:
    """Join list of strings with newlines to single string."""
    if values:
        output = "\n".join(values)
        if eol:
            output += "\n"
    else:
        output = ""

    return output
