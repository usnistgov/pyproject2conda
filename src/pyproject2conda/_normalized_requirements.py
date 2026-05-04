from __future__ import annotations

from typing import TYPE_CHECKING, cast

from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import NormalizedName, canonicalize_name

from ._typing_compat import override
from ._utils import MISSING

if TYPE_CHECKING:
    from collections.abc import (
        Iterable,
        Iterator,
    )
    from typing import Any

    from ._typing import MISSING_TYPE
    from ._typing_compat import Self


class NormalizedRequirement(Requirement):
    def __init__(self, requirement_string: str) -> None:
        super().__init__(requirement_string)

        self.name: NormalizedName = canonicalize_name(self.name)  # pyright: ignore[reportIncompatibleVariableOverride]  # pyrefly: ignore[bad-override]
        self.extras = {canonicalize_name(e) for e in self.extras}


class FallbackRequirement(NormalizedRequirement):
    def __init__(self, requirement_string: str) -> None:
        super().__init__("none")
        self.name = cast("NormalizedName", requirement_string)


class CondaRequirement(NormalizedRequirement):
    def __init__(self, requirement_string: str) -> None:

        self.channel: str | None
        if "::" in requirement_string:
            self.channel, _, requirement_string = requirement_string.partition("::")
        else:
            self.channel = None

        super().__init__(requirement_string)

    def evaluate(
        self,
        env: dict[str, Any] | None,
    ) -> bool:
        if self.marker and env:
            return self.marker.evaluate(env)
        return True

    def update(  # noqa: C901
        self,
        channel: str | None = None,
        name: str | MISSING_TYPE = MISSING,
        # pyrefly: ignore [bad-function-definition]
        url: str | MISSING_TYPE | None = MISSING,
        # pyrefly: ignore [bad-function-definition]
        extras: str | Iterable[str] | MISSING_TYPE | None = MISSING,
        # pyrefly: ignore [bad-function-definition]
        specifier: str | SpecifierSet | MISSING_TYPE | None = MISSING,
        # pyrefly: ignore [bad-function-definition]
        marker: str | Marker | MISSING_TYPE | None = MISSING,
        inplace: bool = False,
    ) -> Self:
        """Remove unused components"""
        req = self if inplace else type(self)(str(self))

        if channel is not None:
            req.channel = channel

        if name is not MISSING:
            # pyrefly: ignore [bad-assignment]
            req.name = canonicalize_name(name)

        if url is not MISSING:
            # pyrefly: ignore [bad-assignment]
            req.url = url

        if extras is not MISSING:
            extras_: set[str]
            if extras is None:
                extras_ = set()
            elif isinstance(extras, str):
                extras_ = {canonicalize_name(extras)}
            else:
                extras_ = {canonicalize_name(e) for e in extras}
            req.extras = extras_

        if specifier is not MISSING:
            if specifier is None:
                specifier = SpecifierSet()
            elif isinstance(specifier, str):
                specifier = SpecifierSet(specifier)
            # pyrefly: ignore [bad-assignment]
            req.specifier = specifier

        if marker is not MISSING:
            if isinstance(marker, str):
                marker = Marker(marker)

            # pyrefly: ignore [bad-assignment]
            req.marker = marker

        return req

    @override
    def _iter_parts(self, name: str) -> Iterator[str]:
        if self.channel:
            yield f"{self.channel}::"

        yield from super()._iter_parts(name)


def canonicalize_requirement(dep: str | Requirement) -> NormalizedRequirement:
    """Normalized Requirement from :class:`~packaging.requirements.Requirement`"""
    return NormalizedRequirement(str(dep))


def canonicalize_pip_requirement(
    dep: str,
) -> NormalizedRequirement | FallbackRequirement:
    try:
        return NormalizedRequirement(dep)
    except InvalidRequirement:
        return FallbackRequirement(dep)
