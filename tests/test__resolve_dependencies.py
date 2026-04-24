# pylint: disable=bad-builtin
from __future__ import annotations

import pytest
from packaging.requirements import Requirement
from packaging.utils import NormalizedName, canonicalize_name

from pyproject2conda._normalized_requirements import canonicalize_requirement
from pyproject2conda._resolve_dependencies import (
    ResolveDependencyGroups,
    ResolveOptionalDependencies,
)


@pytest.mark.parametrize(
    ("dep", "expected"),
    [
        pytest.param("foo[a_thing, b]", "foo[a-thing,b]", id="norm extras"),
        pytest.param("a_thing", "a-thing", id="norm name"),
        pytest.param("a.thing[b.thing]", "a-thing[b-thing]", id="norm all"),
    ],
)
def test__canonicalize_requirement(dep: str, expected: str) -> None:
    assert str(canonicalize_requirement(Requirement(dep))) == expected


@pytest.fixture
def package_name() -> NormalizedName:
    return NormalizedName("package")


@pytest.fixture
def optional_dependencies(package_name: NormalizedName) -> ResolveOptionalDependencies:
    deps = {
        "a_option": ["a_thing", "b_thing", "package[b_option, c_option]"],
        "b.option": ["b_0", "b_1", "package[other]"],
        "c-option": ["b_0", "c_0"],
        "other": ["other_0", "other_1"],
        "all": ["package[a-option]", "package[other]"],
    }

    return ResolveOptionalDependencies(
        package_name=package_name,
        unresolved={
            canonicalize_name(k): list(
                map(canonicalize_requirement, map(Requirement, v))
            )
            for k, v in deps.items()
        },
    )


@pytest.fixture
def dependency_groups(
    package_name: NormalizedName, optional_dependencies: ResolveOptionalDependencies
) -> ResolveDependencyGroups:
    groups = {
        "dev": [
            "jupyter",
            {"include-group": "test"},
            {"include-group": "optional"},
            {"include-group": "type_check"},
        ],
        "test": [
            "pytest",
        ],
        "optional": ["package[all]"],
        "type.check": [
            "types-pyyaml",
            "pytest",
            "mypy",
        ],
    }

    return ResolveDependencyGroups(
        package_name=package_name,
        unresolved=groups,
        optional_dependencies=optional_dependencies,
    )


@pytest.mark.parametrize(
    ("extras", "expected"),
    [
        pytest.param("c.option", ["b-0", "c-0"], id="single group"),
        pytest.param(
            "a_option",
            ["a-thing", "b-0", "b-1", "b-thing", "c-0", "other-0", "other-1"],
            id="package expand",
        ),
        pytest.param(
            ["other", "c-option"],
            ["b-0", "c-0", "other-0", "other-1"],
            id="multiple groups",
        ),
        pytest.param(
            ["all"],
            ["a-thing", "b-0", "b-1", "b-thing", "c-0", "other-0", "other-1"],
            id="package and group expand",
        ),
    ],
)
def test_optional_dependencies(
    optional_dependencies: ResolveOptionalDependencies,
    extras: str | list[str],
    expected: list[str],
) -> None:
    assert sorted(map(str, optional_dependencies[extras])) == expected


@pytest.mark.parametrize(
    ("groups", "expected"),
    [
        pytest.param("test", ["pytest"], id="simple group"),
        pytest.param(
            "dev",
            [
                "a-thing",
                "b-0",
                "b-1",
                "b-thing",
                "c-0",
                "jupyter",
                "mypy",
                "other-0",
                "other-1",
                "pytest",
                "types-pyyaml",
            ],
            id="recursive group",
        ),
        pytest.param(
            ["test", "type_check"],
            ["mypy", "pytest", "types-pyyaml"],
            id="multiple groups",
        ),
    ],
)
def test_parsedependencies_resolve_groups(
    dependency_groups: ResolveDependencyGroups,
    groups: str | list[str],
    expected: list[str],
) -> None:
    assert sorted(map(str, dependency_groups[groups])) == expected
