from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from .resolve_dependencies import (
    ResolveDependencyGroups,
    ResolveOptionalDependencies,
    canonicalize_requirement,
)
from .utils import get_in

if TYPE_CHECKING:
    from pathlib import Path

    from packaging.utils import NormalizedName

    from ._schema import DependencyMapping
    from ._typing_compat import Self
    from .resolve_dependencies import NormalizedRequirement


class ParseRequirements:
    def __init__(
        self,
        package_name: NormalizedName,
        optional_dependencies: ResolveOptionalDependencies,
        dependency_groups: ResolveDependencyGroups,
        build_system_requires: list[NormalizedRequirement],
        dependency_map: dict[NormalizedName, DependencyMapping] | None,
    ) -> None:
        self.package_name = package_name
        self.optional_dependencies = optional_dependencies
        self.dependency_groups = dependency_groups
        self.build_system_requires = build_system_requires

        if dependency_map is None:
            dependency_map = {}
        self.dependency_map = dependency_map

    @classmethod
    def from_string(
        cls,
        s: str,
        dependency_map: dict[NormalizedName, DependencyMapping] | None = None,
    ) -> Self:

        from ._compat import tomllib

        data = tomllib.loads(s)

        package_name = canonicalize_name(data["project"]["name"])

        optional_dependencies = ResolveOptionalDependencies(
            package_name=package_name,
            unresolved={
                canonicalize_name(k): list(
                    map(canonicalize_requirement, map(Requirement, v))
                )
                for k, v in get_in(
                    ("project", "optional-dependencies"),
                    data,
                    factory=dict,
                ).items()
            },
        )

        dependency_groups = ResolveDependencyGroups(
            package_name=package_name,
            unresolved=data.get("dependency-groups", {}),
            optional_dependencies=optional_dependencies,
        )

        build_system_requires = [
            canonicalize_requirement(x)
            for x in get_in(["build-system", "requires"], data, factory=list)
        ]

        return cls(
            package_name=package_name,
            optional_dependencies=optional_dependencies,
            dependency_groups=dependency_groups,
            build_system_requires=build_system_requires,
            dependency_map=dependency_map,
        )

    @classmethod
    def from_file(
        cls,
        p: Path,
        dependency_map: dict[NormalizedName, DependencyMapping] | None = None,
    ) -> Self:
        return cls.from_string(p.read_text(encoding="utf-8"), dependency_map)
