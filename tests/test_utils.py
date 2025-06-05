from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from pyproject2conda import utils

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


def test_template() -> None:
    assert utils.filename_from_template(None) is None

    expected = "py38-test.yaml"

    t = utils.filename_from_template(
        "py{py}-{env}", env_name="test", python_version="3.8", ext=".yaml"
    )

    assert t == expected


@pytest.mark.parametrize(
    ("python_version_default", "python_version", "expected"),
    [
        (None, None, []),
        (None, "3.10", ["3.10"]),
        ("3.12", "3.11", ["3.12"]),
        ("3.11", None, ["3.11"]),
    ],
)
def test_default_pythons(
    example_path, python_version_default, python_version, expected
) -> None:
    for name, version in zip(
        [".python-version-default", ".python-version"],
        [python_version_default, python_version],
        strict=False,
    ):
        if version is not None:
            with (example_path / name).open("w") as f:
                f.write(f"{version}\n")

    assert utils.get_default_pythons_with_fallback() == expected


@pytest.mark.parametrize(
    ("versions", "lowest", "highest"),
    [
        (["3.8", "3.10", "3.6"], "3.6", "3.10"),
    ],
)
def test_get_lowest_highest_version(
    versions: Iterable[str], lowest: str, highest: str
) -> None:
    assert utils.get_highest_version(versions) == highest
    assert utils.get_lowest_version(versions) == lowest


@pytest.mark.parametrize(
    ("env_name", "python_version", "expected"),
    [
        (None, None, {}),
        (None, "3.8", {"py": "38", "py_version": "3.8"}),
        ("thing", None, {"env": "thing"}),
        ("thing", "3.8", {"py": "38", "py_version": "3.8", "env": "thing"}),
    ],
)
def test__get_standard_format_dict(
    env_name: str | None, python_version: str | None, expected: dict[str, str]
) -> None:
    assert (
        utils._get_standard_format_dict(  # noqa: SLF001
            env_name=env_name, python_version=python_version
        )
        == expected
    )


@pytest.mark.parametrize(
    ("template", "python_version", "env_name", "ext", "expected"),
    [
        (
            "thing-{env}",
            "3.8",
            "there",
            ".txt",
            nullcontext("thing-there.txt"),
        ),  # pyrefly: ignore
        ("thing-{py}", None, "there", ".yaml", pytest.raises(KeyError)),
    ],
)
def test_filename_from_template(
    template: str,
    python_version: str,
    env_name: str,
    ext: str,
    expected: Any,
) -> None:
    with expected as e:
        assert (
            utils.filename_from_template(
                template=template,
                python_version=python_version,
                env_name=env_name,
                ext=ext,
            )
            == e
        )


@pytest.mark.parametrize(
    ("name", "python_version", "env_name", "expected"),
    [
        ("my-env", "3.8", "thing", nullcontext("my-env")),  # pyrefly: ignore
        ("my-env-{py}", None, "thing", pytest.raises(KeyError)),
        (
            "my-{env}-{py}",
            "3.8",
            "thing",
            nullcontext("my-thing-38"),
        ),  # pyrefly: ignore
    ],
)
def test_conda_env_name_from_template(
    name: str,
    python_version: str,
    env_name: str,
    expected: Any,
) -> None:
    with expected as e:
        assert (
            utils.conda_env_name_from_template(
                name=name, python_version=python_version, env_name=env_name
            )
            == e
        )
