from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

from pyproject2conda import _normalized_requirements as mod
from pyproject2conda.utils import MISSING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@pytest.mark.parametrize(
    ("cls", "dep", "expected"),
    [
        (mod.NormalizedRequirement, "a_thing", "a-thing"),
        (mod.NormalizedRequirement, "a_thing[other_thing]", "a-thing[other-thing]"),
        (mod.canonicalize_requirement, "a_thing[other_thing]", "a-thing[other-thing]"),
        (
            mod.canonicalize_requirement,
            Requirement("a_thing[other_thing]"),
            "a-thing[other-thing]",
        ),
        (
            mod.canonicalize_pip_requirement,
            "a_thing[other_thing]",
            "a-thing[other-thing]",
        ),
        (mod.canonicalize_pip_requirement, "thing=hello_there", "thing=hello_there"),
        (mod.FallbackRequirement, "-e .", "-e ."),
        (mod.FallbackRequirement, "thing=hello", "thing=hello"),
        (mod.CondaRequirement, "a_thing", "a-thing"),
        (mod.CondaRequirement, "channel::a_thing", "channel::a-thing"),
    ],
)
def test_requirements_classes(
    cls: Callable[[str], mod.NormalizedRequirement], dep: str, expected: str
) -> None:
    assert str(cls(dep)) == expected


@pytest.mark.parametrize(
    ("dep", "env", "expected"),
    [
        ("thing; python_version <'3.10'", None, True),
        ("thing; python_version <'3.10'", {}, True),
        ("thing; python_version <'3.10'", {"python": "3.14"}, False),
    ],
)
def test_condarequirement_evaluate(
    dep: str, env: dict[str, Any], expected: bool
) -> None:
    assert mod.CondaRequirement(dep).evaluate(env) is expected


@pytest.mark.parametrize(
    ("dep", "kws", "expected"),
    [
        ("thing[a,b,c]", {}, "thing"),
        ("thing[a]; python_version < '3.10'", {}, "thing"),
        ("thing[a]; python_version < '3.10'", {"channel": "hello"}, "hello::thing"),
        ("thing[a]", {"name": "hello"}, "hello"),
        ("thing[a]", {"extras": "hello"}, "thing[hello]"),
        ("thing[a]", {"extras": MISSING}, "thing[a]"),
        ("thing[a]", {"extras": ["hello", "there"]}, "thing[hello,there]"),
        ("thing[a]", {"url": "url"}, "thing @ url"),
        ("thing<2.0", {}, "thing<2.0"),
        ("thing<2.0", {"specifier": ">2.0"}, "thing>2.0"),
        ("thing<2.0", {"specifier": SpecifierSet(">3.0")}, "thing>3.0"),
        ("thing<2.0", {"specifier": None}, "thing"),
        (
            "thing",
            {"marker": "python_version<'3.10'"},
            'thing; python_version < "3.10"',
        ),
        (
            "thing",
            {"marker": Marker("python_version<'3.10'")},
            'thing; python_version < "3.10"',
        ),
        (
            "thing; python_version < '3.10'",
            {"marker": MISSING},
            'thing; python_version < "3.10"',
        ),
    ],
)
def test_condarequirement_update(dep: str, kws: dict[str, Any], expected: str) -> None:
    assert (
        str(mod.CondaRequirement(dep).update(**{"extras": None, "marker": None, **kws}))  # ty: ignore[invalid-argument-type]  # pyrefly: ignore[bad-argument-type]
        == expected
    )
