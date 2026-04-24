"""Resolve ``optional-dependencies`` and ``dependency-groups``"""
# pylint: disable=bad-builtin

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from packaging.dependency_groups import DependencyGroupResolver
from packaging.utils import NormalizedName, canonicalize_name

from ._normalized_requirements import NormalizedRequirement, canonicalize_requirement
from ._typing_compat import override

if TYPE_CHECKING:
    from collections.abc import (
        Iterable,
        Sequence,
    )
    from typing import Any


@dataclass
class _Resolve(ABC):
    """Base resolver"""

    package_name: NormalizedName
    unresolved: dict[NormalizedName, Any]
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

    def get(self, keys: Iterable[NormalizedName]) -> set[NormalizedRequirement]:
        out: set[NormalizedRequirement] = set()
        for k in keys:
            out.update(self._resolve(k))
        return out

    def __getitem__(self, key: str | Iterable[str]) -> set[NormalizedRequirement]:
        if isinstance(key, str):
            key = [key]
        return self.get(map(canonicalize_name, key))


@dataclass
class ResolveOptionalDependencies(_Resolve):
    """Resolve ``optional-dependencies``."""

    unresolved: dict[NormalizedName, Sequence[NormalizedRequirement]]

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
        self._resolver = DependencyGroupResolver(
            cast("dict[str, Any]", self.unresolved)
        )

    @override
    def _get_unresolved_deps(
        self, key: NormalizedName
    ) -> Iterable[NormalizedRequirement]:
        return map(canonicalize_requirement, self._resolver.resolve(key))

    @override
    def _get_resolved_package_extras(
        self, extras: Iterable[NormalizedName]
    ) -> Iterable[NormalizedRequirement]:
        yield from self.optional_dependencies[extras]
