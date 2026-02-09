"""
Override dependencies (:mod:`~pyproject2conda.overrides`)
=========================================================
"""

from __future__ import annotations

from typing import TypedDict

from ._typing_compat import override


class OverrideDict(TypedDict, total=False):
    """Dict for storing override options."""

    pip: bool
    skip: bool
    channel: str | None
    packages: str | list[str]


class OverrideDeps:
    """Class to work with overrides from comment or table"""

    def __init__(
        self,
        pip: bool = False,
        skip: bool = False,
        packages: str | list[str] | None = None,
        channel: str | None = None,
    ) -> None:
        if channel is not None and channel.strip() in {"pip", "pypi"}:
            channel = None
            pip = True

        self.pip = pip
        self.skip = skip
        self.channel = channel

        if packages is None:
            packages = []
        elif isinstance(packages, str):
            packages = [packages]
        self.packages = packages

    @override
    def __repr__(self) -> str:  # pragma: no cover
        return repr(self.__dict__)
