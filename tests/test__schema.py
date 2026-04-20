# mypy: disable-error-code="no-untyped-def, no-untyped-call"
# pylint: disable=duplicate-code
from __future__ import annotations

import filecmp
import logging
import tempfile
from functools import partial
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

import pyproject2conda
from pyproject2conda import _schema as mod
from pyproject2conda.cli import app

if TYPE_CHECKING:
    from typing import Any

ROOT = Path(__file__).resolve().parent / "data"


def do_run(runner, command, *opts, filename=None, must_exist=False):
    if filename is None:
        filename = ROOT / "test-pyproject.toml"
    filename = Path(filename)
    if must_exist and not filename.exists():
        msg = f"filename {filename} does not exist"
        raise ValueError(msg)

    return runner.invoke(app, [command, "-f", str(filename), *opts])


@pytest.fixture
def simple_toml() -> str:
    return """\
    [project.optional-dependencies]
    test = [
        "pandas",
        "pytest", # p2c: -c conda-forge

    ]

    [dependency-groups]
    thing = ["a-thing"]

    [tool.pyproject2conda]
    channels = ['conda-forge']
    # these are the same as the default values of `p2c project`
    template-python = "py{py}-{env}"
    template = "hello-{env}"
    style = "yaml"
    # options
    python = "3.10"
    default-envs = ["test", "dev", "dist-pypi"]

    [tool.pyproject2conda.envs.base]
    extras = []
    style = "yaml"
    python = []

    [tool.pyproject2conda.envs.base2]
    style = "yaml"
    extras = []


    [tool.pyproject2conda.envs.base-pip-only]
    style = "yaml"
    extras = []
    pip-only = true

    [tool.pyproject2conda.envs.base-custom-command]
    style = "yaml"
    extras = []
    custom-command = "make hello"

    [tool.pyproject2conda.envs.base3]
    style = "yaml"
    python = "default"

    [tool.pyproject2conda.envs.base4]
    style = "yaml"
    python = ["3.9", "3.10", "3.11", "3.12", "3.13"]
    template-python = "py{py}-hello"

    [tool.pyproject2conda.envs.base5]
    style = "yaml"
    python = "all"
    template-python = "py{py}-hello"

    [tool.pyproject2conda.envs.base_lowest]
    style = "yaml"
    python = "lowest"
    template-python = "py{py}-hello"

    [tool.pyproject2conda.envs.base_highest]
    style = "yaml"
    python = "highest"
    template-python = "py{py}-hello"


    [tool.pyproject2conda.envs.base_name]
    name = "py{py}-{env}"

    [tool.pyproject2conda.envs.extension_yaml]
    style = "yaml"
    yaml-ext = ".yml"

    [tool.pyproject2conda.envs.extension_txt]
    style = "requirements"
    reqs-ext = ".in"

    [tool.pyproject2conda.envs.both]
    groups = "thing"

    [[tool.pyproject2conda.overrides]]
    envs = ["both"]
    extras = ["test"]


    [tool.pyproject2conda.envs.header0]
    extras = []
    style = "yaml"
    python = []
    header = false


    [tool.pyproject2conda.envs.header1]
    extras = []
    style = "yaml"
    python = []
    header = true

    [project]
    name = "hello"
    requires-python = ">=3.8,<3.11"


    """


@pytest.fixture
def classifiers() -> str:
    return """
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Science/Research",
        "License :: Public Domain",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering",
    ]
    """


@pytest.fixture
def simple_config(simple_toml: str) -> mod.Config:
    return mod.Config.from_string(dedent(simple_toml))


@pytest.fixture
def simple_config_classifiers(simple_toml: str, classifiers: str) -> mod.Config:
    return mod.Config.from_string(dedent(simple_toml + classifiers))


@pytest.fixture
def simple_env() -> mod.Env:
    return mod.Env(
        channels=["conda-forge"],
        template_python="py{py}-{env}",
        template="hello-{env}",
        style="yaml",
        python="3.10",
    )


@pytest.mark.parametrize(
    ("env_name", "update_params", "kws"),
    [
        pytest.param(
            "base",
            {"python": [], "output": "hello-base.yaml"},
            {},
        ),
        pytest.param(
            "base2",
            {"output": "py310-base2.yaml"},
            {},
        ),
        pytest.param(
            "header0",
            {"python": [], "header": False, "output": "hello-header0.yaml"},
            {},
        ),
        pytest.param(
            "header1",
            {"python": [], "header": True, "output": "hello-header1.yaml"},
            {},
        ),
        pytest.param(
            "base-pip-only",
            {"pip_only": True, "output": "py310-base-pip-only.yaml"},
            {},
        ),
        pytest.param(
            "base_name",
            {"name": "py310-base-name", "output": "py310-base-name.yaml"},
            {},
        ),
        pytest.param(
            "base_custom_command",
            {
                "custom_command": "make hello",
                "output": "py310-base-custom-command.yaml",
            },
            {},
        ),
        pytest.param(
            "both",
            {"extras": ["test"], "groups": ["thing"], "output": "py310-both.yaml"},
            {},
        ),
        pytest.param(
            "extension_yaml",
            {"yaml_ext": ".yml", "output": "py310-extension-yaml.yml"},
            {},
        ),
        # kws
        pytest.param(
            "base",
            {"python": [], "reqs": ["-e ."], "output": "hello-base.yaml"},
            {"reqs": ["-e ."]},
        ),
        pytest.param(
            "base",
            {"python": [], "template": "there-{env}", "output": "there-base.yaml"},
            {"template": "there-{env}"},
        ),
        pytest.param(
            "base",
            {
                "python": [],
                "allow_empty": True,
                "template": "there-{env}",
                "output": "there-base.yaml",
            },
            {"allow-empty": True, "template": "there-{env}"},
        ),
        # requirements
        pytest.param(
            "extension_txt",
            {
                "style": ["requirements"],
                "reqs_ext": ".in",
                "output": "hello-extension-txt.in",
            },
            {},
        ),
    ],
)
def test_option_override_base(
    simple_config: mod.Config,
    simple_env: mod.Env,
    env_name: str,
    update_params: dict[str, Any],
    kws: dict[str, Any],
) -> None:

    config = simple_config.update_options(kws) if kws else simple_config
    output = list(config.iter_envs(envs=[env_name]))
    env = simple_env.model_copy(update=update_params)

    assert output[0] == (
        env.style[0],
        env,
    )


def test_option_override_base3_default_python_error(
    example_path: Path,  # noqa: ARG001
    simple_config: mod.Config,
) -> None:
    # using default python without a version
    with pytest.raises(
        ValueError,
        match=r"Must include `.python-version-default` or `.python-version`.*",
    ):
        list(simple_config.iter_envs(envs=["base3"]))


def test_option_override_base3_default_python(
    example_path, simple_toml: str, simple_env: mod.Env
) -> None:
    with (example_path / ".python-version-default").open("w") as f:
        f.write("3.10\n")

    from pyproject2conda.utils import get_default_pythons_with_fallback

    assert get_default_pythons_with_fallback() == ["3.10"]

    config = mod.Config.from_string(dedent(simple_toml))
    output = list(config.iter_envs(envs=["base3"]))

    assert output[0] == (
        "yaml",
        simple_env.model_copy(update={"python": "3.10", "output": "py310-base3.yaml"}),
    )


def test_option_override_all_pythons_error(simple_config: mod.Config) -> None:
    with pytest.raises(ValueError, match=r"Must specify python versions .*"):
        list(simple_config.iter_envs(envs=["base5"]))


def test_option_override_all_pythons(
    simple_config_classifiers: mod.Config, simple_env: mod.Env
) -> None:
    a = list(simple_config_classifiers.iter_envs(envs=["base4"]))
    b = list(simple_config_classifiers.iter_envs(envs=["base5"]))

    assert len(a) == len(b) == 5

    assert a[0] == (
        "yaml",
        simple_env.model_copy(
            update={
                "python": "3.9",
                "template_python": "py{py}-hello",
                "output": "py39-hello.yaml",
            }
        ),
    )

    assert a == b


def test_option_override_lowest_highest(
    simple_config_classifiers: mod.Config, simple_env: mod.Env
) -> None:

    a = list(simple_config_classifiers.iter_envs(envs=["base_lowest"]))
    b = list(simple_config_classifiers.iter_envs(envs=["base_highest"]))

    assert a[0] == (
        "yaml",
        simple_env.model_copy(
            update={
                "python": "3.9",
                "template_python": "py{py}-hello",
                "output": "py39-hello.yaml",
            }
        ),
    )

    assert b[0] == (
        "yaml",
        simple_env.model_copy(
            update={
                "python": "3.13",
                "template_python": "py{py}-hello",
                "output": "py313-hello.yaml",
            }
        ),
    )


@pytest.mark.parametrize("fname", ["test-pyproject.toml", "test-pyproject-groups.toml"])
def test_dry(fname, runner) -> None:
    filename = ROOT / fname

    expected = """\
# --------------------
# Creating yaml py310-test-extras.yaml
channels:
  - conda-forge
dependencies:
  - python=3.10
  - conda-forge::pytest
  - pandas
# --------------------
# Creating yaml py311-test-extras.yaml
channels:
  - conda-forge
dependencies:
  - python=3.11
  - conda-forge::pytest
  - pandas
# --------------------
# Creating requirements test-extras.txt
pandas
pytest
    """

    result = do_run(
        runner, "project", "--dry", "--envs", "test-extras", filename=filename
    )

    assert result.output == dedent(expected)


def test_config_only_default() -> None:
    d0 = {
        "extras": [],
        "groups": [],
        "extras_or_groups": ["test"],
        "sort": True,
        "skip_package": False,
        "pip_only": False,
        "header": None,
        "custom_command": None,
        "overwrite": "check",
        "verbose": 0,
        "name": None,
        "channels": None,
        "python": "3.8",
        "output": "py38-test.yaml",
        "deps": None,
        "reqs": None,
        "allow_empty": False,
    }

    d1 = d0.copy()
    d1.update(extras=["test"], extras_or_groups=[])

    s0 = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default-envs = ["test"]
    """
    s1 = """
    [tool.pyproject2conda.envs.test]
    python = ["3.8"]
    extras = "test"
    """

    for s, d in zip([s0, s1], (d0, d1), strict=False):
        c = mod.Config.from_string(s)
        assert list(c.iter_envs()) == [("yaml", mod.Env.model_validate(d))]


def test_config_errors() -> None:
    s = """
    [tool.pyproject2conda]
    python = ["3.8"]

    [tool.pyproject2conda.envs.test]
    extras = "test"
    """

    # raise error for bad env
    c = mod.Config.from_string(s)
    with pytest.raises(ValueError):
        c.config.env_config("hello")

    s1 = """
    [tool.pyproject2conda]
    python = ["3.8"]

    [tool.pyproject2conda.envs.test]
    style = "thing"
    """

    # raise error for bad env
    with pytest.raises(ValidationError):
        c = mod.Config.from_string(s1)


@pytest.mark.parametrize(
    "s",
    [
        pytest.param(
            dedent("""
            [tool.pyproject2conda]
            python = ["3.8"]
            default-envs = ["test"]

            [[tool.pyproject2conda.overrides]]
            envs = ["test"]
            skip-package = true
            pip-only = true
            """),
        ),
        pytest.param(
            dedent("""
            [tool.pyproject2conda]
            python = ["3.8"]
            default-envs = ["test"]
            pip-only = true
            skip-package = true
            """),
        ),
    ],
)
def test_config_overrides2(s: str) -> None:
    c = mod.Config.from_string(s)

    expected = (
        "yaml",
        mod.Env(
            python="3.8",
            skip_package=True,
            pip_only=True,
            output="py38-test.yaml",
            extras_or_groups=["test"],
        ),
    )

    assert next(iter(c.iter_envs())) == expected


def test_config_overrides_no_envs() -> None:
    # test overrides env
    s = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default-envs = ["test"]

    [[tool.pyproject2conda.overrides]]
    skip-package = true
    """

    with pytest.raises(ValidationError):
        mod.Config.from_string(s)


def test_config_python_include_version() -> None:
    s = """
    [tool.pyproject2conda.envs.test-1]
    extras = ["test"]
    output = "py38-test.yaml"
    python-include = "3.8"
    python-version = "3.8"

    [tool.pyproject2conda.envs."py38-test"]
    extras = ["test"]
    python-include = "3.8"
    python-version = "3.8"
    """

    c = mod.Config.from_string(s)

    expected = [
        (
            "yaml",
            mod.Env(
                extras=["test"],
                python_include="3.8",
                python_version="3.8",
                output="py38-test.yaml",
            ),
        ),
    ] * 2

    assert list(c.iter_envs()) == expected


def test_version(runner) -> None:
    result = runner.invoke(app, ["--version"])

    assert (
        result.stdout.strip()
        == f"pyproject2conda, version {pyproject2conda.__version__}"
    )


def get_times(path: Path) -> dict[Path, float]:
    return {
        p: p.stat().st_mtime for ext in ("txt", "yaml") for p in path.glob(f"*.{ext}")
    }


@pytest.mark.parametrize(
    ("fname", "opt"),
    [
        ("test-pyproject.toml", "-e"),
        ("test-pyproject-groups.toml", "-g"),
    ],
)
def test_multiple(fname, opt, runner, caplog) -> None:
    filename = ROOT / fname
    do_run_ = partial(do_run, filename=filename)

    caplog.set_level(logging.INFO)

    t1 = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    path1 = Path(t1.name)

    do_run_(
        runner,
        "project",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    assert "Creating" in caplog.text

    orig_times = get_times(path1)

    # running this again?
    do_run_(
        runner,
        "project",
        "-v",
        "--overwrite=check",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    assert "Skipping requirements" in caplog.text

    assert orig_times == get_times(path1)

    # and again (without verbose)
    do_run_(
        runner,
        "project",
        "--overwrite=check",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    assert orig_times == get_times(path1)

    t2 = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
    path2 = t2.name

    do_run_(
        runner, "yaml", opt, "dev", "-p", "3.10", "-o", f"{path2}/py310-dev.yaml", "-v"
    )

    do_run_(
        runner,
        "yaml",
        opt,
        "dist-pypi",
        "--skip-package",
        "-p",
        "3.10",
        "-o",
        f"{path2}/py310-dist-pypi.yaml",
    )

    do_run_(runner, "yaml", opt, "test", "-p", "3.10", "-o", f"{path2}/py310-test.yaml")
    do_run_(runner, "yaml", opt, "test", "-p", "3.11", "-o", f"{path2}/py311-test.yaml")

    do_run_(
        runner,
        "yaml",
        opt,
        "test",
        "--skip-package",
        "-p",
        "3.10",
        "-o",
        f"{path2}/py310-test-extras.yaml",
    )
    do_run_(
        runner,
        "yaml",
        opt,
        "test",
        "--skip-package",
        "-p",
        "3.11",
        "-o",
        f"{path2}/py311-test-extras.yaml",
    )

    do_run_(
        runner, "r", opt, "test", "--skip-package", "-o", f"{path2}/test-extras.txt"
    )

    do_run_(runner, "req", "-o", f"{path2}/base.txt")

    paths1 = Path(path1).glob("*")
    names1 = {x.name for x in paths1}

    expected = {
        "base.txt",
        "py310-dev.yaml",
        "py310-dist-pypi.yaml",
        "py310-test-extras.yaml",
        "py310-test.yaml",
        "py311-test-extras.yaml",
        "py311-test.yaml",
        "test-extras.txt",
    }

    assert names1 == expected

    paths2 = Path(path2).glob("*")
    names2 = {x.name for x in paths2}

    assert expected == names2

    for x in expected:
        assert filecmp.cmp(f"{path1}/{x}", f"{path2}/{x}")

    t1.cleanup()
    t2.cleanup()
