# pylint: disable=consider-using-tuple

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from packaging.version import InvalidVersion

import pyproject2conda._utils as utils

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from typing import Any


def test_list_to_string() -> None:
    assert utils.list_to_str(["a", "b"], eol=True) == "a\nb\n"
    assert utils.list_to_str(["a", "b"], eol=False) == "a\nb"
    assert utils.list_to_str(None) == ""  # noqa: PLC1901  # pylint: disable=use-implicit-booleaness-not-comparison-to-string


def test_template() -> None:
    assert utils.path_from_template(None) is None

    expected = Path("py38-test.yaml")

    t = utils.path_from_template(
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
    example_path: Path,
    python_version_default: str,
    python_version: str,
    expected: list[str],
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
    ("pythons", "default_pythons", "all_pythons", "expected"),
    [
        pytest.param(
            ("3.10", "3.11"),
            [],
            [],
            nullcontext(["3.10", "3.11"]),
        ),
        pytest.param(
            ("3.9", "3.10"),
            ["3.11"],
            ["3.12", "3.13"],
            nullcontext(["3.9", "3.10"]),
        ),
        pytest.param(
            ("default",),
            ["3.11"],
            ["3.12", "3.13"],
            nullcontext(["3.11"]),
        ),
        pytest.param(
            ("default",),
            [],
            ["3.12", "3.13"],
            pytest.raises(ValueError, match=r"Must include .*"),
        ),
        pytest.param(
            ("low",),
            ["3.11"],
            ["3.12", "3.13"],
            nullcontext(["3.12"]),
        ),
        pytest.param(
            ("lowest",),
            ["3.11"],
            ["3.12", "3.13"],
            nullcontext(["3.12"]),
        ),
        pytest.param(
            ("high",),
            ["3.11"],
            ["3.12", "3.13"],
            nullcontext(["3.13"]),
        ),
        pytest.param(
            ("highest",),
            ["3.11"],
            ["3.12", "3.13"],
            nullcontext(["3.13"]),
        ),
        pytest.param(
            ("all",),
            ["3.11"],
            ["3.12", "3.13"],
            nullcontext(["3.12", "3.13"]),
        ),
        pytest.param(
            ("all",),
            ["3.11"],
            [],
            pytest.raises(ValueError, match=r"Must specify .*"),
        ),
        pytest.param(
            ("thing",),
            ["3.11"],
            [],
            pytest.raises(InvalidVersion, match=r"Invalid version.*"),
        ),
    ],
)
def test_select_python(
    pythons: Sequence[str],
    default_pythons: list[str],
    all_pythons: list[str],
    expected: Any,
) -> None:

    with expected as e:
        assert utils.select_pythons(pythons, default_pythons, all_pythons) == e


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
        utils._get_standard_format_dict(  # noqa: SLF001  # pylint: disable=protected-access
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
            nullcontext("thing-there.txt"),  # pyrefly: ignore
        ),
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
        assert utils.path_from_template(
            template=template,
            python_version=python_version,
            env_name=env_name,
            ext=ext,
        ) == Path(e)


@pytest.mark.parametrize(
    ("name", "python_version", "env_name", "expected"),
    [
        ("my-env", "3.8", "thing", nullcontext("my-env")),  # pyrefly: ignore
        ("my-env-{py}", None, "thing", pytest.raises(KeyError)),
        (
            "my-{env}-{py}",
            "3.8",
            "thing",
            nullcontext("my-thing-38"),  # pyrefly: ignore
        ),
        (None, "3.8", "thing", nullcontext(None)),
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


@pytest.mark.parametrize(
    ("func", "x", "expected", "same"),
    [
        (utils.validate_iterable_str, "hello", ["hello"], False),
        (
            utils.validate_iterable_str,
            (_ for _ in ["hello"]),
            (_ for _ in ["hello"]),
            True,
        ),
        (utils.validate_iterable_str, ["hello"], ["hello"], True),
        # validate_list_of_str
        (utils.validate_list_of_str, None, [], False),
        (utils.validate_list_of_str, ["hello"], ["hello"], True),
        (utils.validate_list_of_str, "hello", ["hello"], False),
        (utils.validate_list_of_str, (_ for _ in ["hello"]), ["hello"], False),
        # validate list of normalizedname
        (utils.validate_list_of_normalizedname, None, [], False),
        (utils.validate_list_of_normalizedname, "hello_there", ["hello-there"], False),
        (
            utils.validate_list_of_normalizedname,
            ["hello_there"],
            ["hello-there"],
            False,
        ),
        # validate dict of normalizedname
        (utils.validate_dict_normalizedname, {}, {}, False),
        (
            utils.validate_dict_normalizedname,
            {"hello_there": "thing"},
            {"hello-there": "thing"},
            False,
        ),
    ],
)
def test_validation(
    func: Callable[..., Any], x: Any, expected: Any, same: bool
) -> None:

    out = func(x)

    if same:
        assert out is x
    else:
        assert out is not x

    assert type(out) is type(expected)
    assert list(out) == list(expected)


def test_update_target(tmp_path: Path) -> None:
    import os

    a_file = tmp_path / "a.txt"
    b_file = tmp_path / "b.txt"

    a_file.write_text("hello", encoding="utf-8")
    b_file.write_text("there", encoding="utf-8")

    os.utime(a_file, (10, 10))
    os.utime(b_file, (100, 100))

    assert utils.update_target(None, overwrite="skip")
    assert utils.update_target(a_file, b_file, overwrite="force")
    assert utils.update_target(tmp_path / "hello", overwrite="skip")
    assert utils.update_target(tmp_path / "hello", overwrite="check")
    assert not utils.update_target(a_file, a_file, overwrite="check")
    assert not utils.update_target(b_file, a_file, overwrite="check")
    assert utils.update_target(a_file, b_file, overwrite="check")

    with pytest.raises(ValueError, match=r"unknown option .*"):
        utils.update_target(a_file, b_file, overwrite="thing")
