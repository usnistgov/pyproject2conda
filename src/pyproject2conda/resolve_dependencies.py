"""Resolve ``optional-dependencies`` and ``dependency-groups``"""
# pylint: disable=bad-builtin

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NewType, cast

from dependency_groups import DependencyGroupResolver
from packaging.requirements import Requirement
from packaging.utils import NormalizedName, canonicalize_name

from ._typing_compat import override

if TYPE_CHECKING:
    from collections.abc import (
        Iterable,
        Mapping,
        Sequence,
    )
    from typing import Any


NormalizedRequirement = NewType("NormalizedRequirement", Requirement)
"""NewType to signal normalized requirement"""


def canonicalize_requirement(dep: Requirement) -> NormalizedRequirement:
    """Normalized ``Requirement``"""
    dep.name = canonicalize_name(dep.name)
    dep.extras = {canonicalize_name(e) for e in dep.extras}
    return cast("NormalizedRequirement", dep)


@dataclass
class _Resolve(ABC):
    """Base resolver"""

    package_name: NormalizedName
    unresolved: Mapping[str, Any]
    resolved: dict[NormalizedName, set[NormalizedRequirement]] = field(
        init=False, default_factory=dict[NormalizedName, set[NormalizedRequirement]]
    )

    @abstractmethod
    def _get_unresolved_deps(
        self, key: NormalizedName
    ) -> Iterable[NormalizedRequirement]: ...

    @abstractmethod
    def _get_resolved_package_extras(
        self, extras: Iterable[NormalizedName]
    ) -> Iterable[NormalizedRequirement]: ...

    def _resolve(self, key: NormalizedName) -> set[NormalizedRequirement]:
        """Do underlying resolve of normalized group/extra"""
        if key in self.resolved:
            return self.resolved[key]

        resolved: set[NormalizedRequirement] = set()
        for dep in self._get_unresolved_deps(key):
            if dep in resolved:
                continue
            if dep.name == self.package_name:
                resolved.update(
                    self._get_resolved_package_extras(
                        map(canonicalize_name, dep.extras)
                    )
                )
            else:
                resolved.add(dep)

        self.resolved[key] = resolved
        return resolved

    def __getitem__(self, key: str | Iterable[str]) -> set[NormalizedRequirement]:
        if isinstance(key, str):
            key = [key]

        out: set[NormalizedRequirement] = set()
        for k in map(canonicalize_name, key):
            out.update(self._resolve(k))
        return out


@dataclass
class ResolveOptionalDependencies(_Resolve):
    """Resolve ``optional-dependencies``."""

    # pyrefly: ignore [bad-override]
    unresolved: Mapping[NormalizedName, Sequence[NormalizedRequirement]]  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]

    @override
    def _get_unresolved_deps(
        self, key: NormalizedName
    ) -> Iterable[NormalizedRequirement]:
        yield from self.unresolved[key]

    @override
    def _get_resolved_package_extras(
        self, extras: Iterable[NormalizedName]
    ) -> Iterable[NormalizedRequirement]:
        for e in extras:
            yield from self._resolve(e)


@dataclass
class ResolveDependencyGroups(_Resolve):
    """Resolve ``dependency-groups``."""

    optional_dependencies: ResolveOptionalDependencies
    _resolver: DependencyGroupResolver = field(init=False)

    def __post_init__(self) -> None:
        self._resolver = DependencyGroupResolver(self.unresolved)

    @override
    def _get_unresolved_deps(
        self, key: NormalizedName
    ) -> Iterable[NormalizedRequirement]:
        return map(canonicalize_requirement, self._resolver.resolve(key))
