# mypy: disable-error-code="no-untyped-def, no-untyped-call"
import filecmp
import logging
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

import pyproject2conda
from pyproject2conda import utils
from pyproject2conda.cli import app
from pyproject2conda.config import Config

ROOT = Path(__file__).resolve().parent / "data"


def do_run(runner, command, *opts, filename=None, must_exist=False):
    if filename is None:
        filename = str(ROOT / "test-pyproject.toml")
    filename = Path(filename)
    if must_exist and not filename.exists():
        msg = f"filename {filename} does not exist"
        raise ValueError(msg)

    return runner.invoke(app, [command, "-f", str(filename), *opts])


def test_template() -> None:
    assert utils.filename_from_template(None) is None

    expected = "py38-test.yaml"

    t = utils.filename_from_template(
        "py{py}-{env}", env_name="test", python="3.8", ext="yaml"
    )

    assert t == expected

    t = utils.filename_from_template(
        "py{py}-{env}", env_name="test", python_version="3.8", ext="yaml"
    )

    assert t == expected


def test_option_override() -> None:
    toml = """\
    [project]
    name = "hello"
    requires-python = ">=3.8,<3.11"


    [project.optional-dependencies]
    test = [
        "pandas",
        "pytest", # p2c: -c conda-forge

    ]

    [tool.pyproject2conda]
    channels = ['conda-forge']
    # these are the same as the default values of `p2c project`
    template_python = "py{py}-{env}"
    template = "hello-{env}"
    style = "yaml"
    # options
    python = ["3.10"]
    # Note that this is relative to the location of pyproject.toml
    user_config = "config/userconfig.toml"
    default_envs = ["test", "dev", "dist-pypi"]

    [tool.pyproject2conda.envs.base]
    extras = []
    style = "yaml"
    python = []

    [tool.pyproject2conda.envs.base2]
    style = "yaml"
    extras = []
    """

    d = Config.from_string(dedent(toml))

    output = list(d.iter_envs(envs=["base"]))

    assert output[0] == (
        "yaml",
        {
            "extras": [],
            "groups": [],
            "extras_or_groups": [],
            "sort": True,
            "skip_package": False,
            "header": None,
            "overwrite": "check",
            "verbose": None,
            "reqs": None,
            "deps": None,
            "name": None,
            "channels": ["conda-forge"],
            "allow_empty": False,
            "remove_whitespace": True,
            "output": "hello-base.yaml",
        },
    )

    output = list(d.iter_envs(envs=["base2"]))

    assert output[0] == (
        "yaml",
        {
            "extras": [],
            "groups": [],
            "extras_or_groups": [],
            "sort": True,
            "skip_package": False,
            "header": None,
            "overwrite": "check",
            "verbose": None,
            "reqs": None,
            "deps": None,
            "name": None,
            "channels": ["conda-forge"],
            "allow_empty": False,
            "remove_whitespace": True,
            "output": "py310-base2.yaml",
            "python": "3.10",
        },
    )

    output = list(d.iter_envs(envs=["base"], template="there-{env}"))

    assert output[0] == (
        "yaml",
        {
            "extras": [],
            "groups": [],
            "extras_or_groups": [],
            "sort": True,
            "skip_package": False,
            "header": None,
            "overwrite": "check",
            "verbose": None,
            "reqs": None,
            "deps": None,
            "name": None,
            "channels": ["conda-forge"],
            "allow_empty": False,
            "remove_whitespace": True,
            "output": "there-base.yaml",
        },
    )

    output = list(d.iter_envs(envs=["base"], allow_empty=True, template="there-{env}"))

    assert output[0] == (
        "yaml",
        {
            "extras": [],
            "groups": [],
            "extras_or_groups": [],
            "sort": True,
            "skip_package": False,
            "header": None,
            "overwrite": "check",
            "verbose": None,
            "reqs": None,
            "deps": None,
            "name": None,
            "channels": ["conda-forge"],
            "allow_empty": True,
            "remove_whitespace": True,
            "output": "there-base.yaml",
        },
    )

    output = list(
        d.iter_envs(
            envs=["base"],
            allow_empty=True,
            remove_whitespace=False,
            template="there-{env}",
        )
    )

    assert output[0] == (
        "yaml",
        {
            "extras": [],
            "groups": [],
            "extras_or_groups": [],
            "sort": True,
            "skip_package": False,
            "header": None,
            "overwrite": "check",
            "verbose": None,
            "reqs": None,
            "deps": None,
            "name": None,
            "channels": ["conda-forge"],
            "allow_empty": True,
            "remove_whitespace": False,
            "output": "there-base.yaml",
        },
    )


def test_dry() -> None:
    runner = CliRunner()

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

    result = do_run(runner, "project", "--dry", "--envs", "test-extras")

    assert result.output == dedent(expected)


def test_config_only_default() -> None:
    d0 = {
        "extras": [],
        "groups": [],
        "extras_or_groups": ["test"],
        "sort": True,
        "skip_package": False,
        "header": None,
        "overwrite": "check",
        "verbose": None,
        "name": None,
        "channels": None,
        "python": "3.8",
        "output": "py38-test.yaml",
        "deps": None,
        "reqs": None,
        "allow_empty": False,
        "remove_whitespace": True,
    }

    d1 = d0.copy()
    d1.update(extras=["test"], extras_or_groups=[])

    s0 = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default_envs = ["test"]
    """
    s1 = """
    [tool.pyproject2conda.envs.test]
    python = ["3.8"]
    extras = true
    """

    for s, d in zip([s0, s1], (d0, d1)):
        c = Config.from_string(s)
        assert list(c.iter_envs()) == [("yaml", d)]


def test_config_errors() -> None:
    s = """
    [tool.pyproject2conda]
    python = ["3.8"]

    [tool.pyproject2conda.envs.test]
    extras = true
    """

    # raise error for bad env
    c = Config.from_string(s)
    with pytest.raises(ValueError):
        c.channels(env_name="hello")

    s1 = """
    [tool.pyproject2conda]
    python = ["3.8"]

    [tool.pyproject2conda.envs.test]
    style = "thing"
    """

    # raise error for bad env
    c = Config.from_string(s1)
    with pytest.raises(ValueError):
        c.style(env_name="test")

    with pytest.raises(ValueError):
        list(c.iter_envs())


def test_config_overrides() -> None:
    # test overrides env
    s = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default_envs = ["test"]

    [[tool.pyproject2conda.overrides]]
    envs = ["test"]
    skip_package = true
    """

    c = Config.from_string(s)

    expected = (
        "yaml",
        {
            "extras": [],
            "groups": [],
            "extras_or_groups": ["test"],
            "sort": True,
            "skip_package": True,
            "header": None,
            "overwrite": "check",
            "verbose": None,
            "name": None,
            "channels": None,
            "python": "3.8",
            "output": "py38-test.yaml",
            "deps": None,
            "reqs": None,
            "allow_empty": False,
            "remove_whitespace": True,
        },
    )

    assert next(iter(c.iter_envs())) == expected


def test_conifg_overrides_no_envs() -> None:
    # test overrides env
    s = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default_envs = ["test"]

    [[tool.pyproject2conda.overrides]]
    skip_package = true
    """

    c = Config.from_string(s)

    with pytest.raises(ValueError):
        c.overrides  # noqa: B018


def test_config_python_include_version() -> None:
    s = """
    [tool.pyproject2conda.envs.test-1]
    extras = ["test"]
    output = "py38-test.yaml"
    python_include = "3.8"
    python_version = "3.8"

    [tool.pyproject2conda.envs."py38-test"]
    extras = ["test"]
    python_include = "3.8"
    python_version = "3.8"
    """

    c = Config.from_string(s)

    expected = [
        (
            "yaml",
            {
                "extras": ["test"],
                "groups": [],
                "extras_or_groups": [],
                "sort": True,
                "skip_package": False,
                "header": None,
                "overwrite": "check",
                "verbose": None,
                "name": None,
                "channels": None,
                "python_include": "3.8",
                "python_version": "3.8",
                "output": "py38-test.yaml",
                "deps": None,
                "reqs": None,
                "allow_empty": False,
                "remove_whitespace": True,
            },
        ),
        (
            "yaml",
            {
                "extras": ["test"],
                "groups": [],
                "extras_or_groups": [],
                "sort": True,
                "skip_package": False,
                "header": None,
                "overwrite": "check",
                "verbose": None,
                "name": None,
                "channels": None,
                "python_include": "3.8",
                "python_version": "3.8",
                "output": "py38-test.yaml",
                "deps": None,
                "reqs": None,
                "allow_empty": False,
                "remove_whitespace": True,
            },
        ),
    ]

    assert list(c.iter_envs()) == expected

    # no output:


def test_config_user_config() -> None:
    # test overrides env
    s = """
    [tool.pyproject2conda.envs.test]
    python = "3.8"
    extras = "test"


    """

    s_user = """
    [tool.pyproject2conda.envs.user]
    extras = ["a", "b"]
    python = "3.9"

    [[tool.pyproject2conda.overrides]]
    envs = ["test"]
    skip_package = true
    """

    c = Config.from_string(s, s_user)

    expected = [
        (
            "yaml",
            {
                "extras": ["test"],
                "groups": [],
                "extras_or_groups": [],
                "sort": True,
                "skip_package": True,
                "header": None,
                "overwrite": "check",
                "verbose": None,
                "name": None,
                "channels": None,
                "python": "3.8",
                "output": "py38-test.yaml",
                "deps": None,
                "reqs": None,
                "allow_empty": False,
                "remove_whitespace": True,
            },
        ),
        (
            "yaml",
            {
                "extras": ["a", "b"],
                "groups": [],
                "extras_or_groups": [],
                "sort": True,
                "skip_package": False,
                "header": None,
                "overwrite": "check",
                "verbose": None,
                "name": None,
                "channels": None,
                "python": "3.9",
                "output": "py39-user.yaml",
                "deps": None,
                "reqs": None,
                "allow_empty": False,
                "remove_whitespace": True,
            },
        ),
    ]

    assert list(c.iter_envs()) == expected

    # bad user
    s_user2 = """
    [[tool.pyproject2conda.envs]]
    extras = ["a", "b"]
    python = "3.9"

    [[tool.pyproject2conda.overrides]]
    envs = ["test"]
    skip_package = true
    """

    with pytest.raises(TypeError):
        c = Config.from_string(s, s_user2)

    s_user2 = """
    [tool.pyproject2conda.envs]
    extras = ["a", "b"]
    python = "3.9"

    [tool.pyproject2conda.overrides]
    envs = ["test"]
    skip_package = true
    """

    with pytest.raises(TypeError):
        c = Config.from_string(s, s_user2)

    # blank config, only user
    s2 = """
    [tool.pyproject2conda]
    """

    c = Config.from_string(s2, s_user)

    assert c.data == {
        "envs": {"user": {"extras": ["a", "b"], "python": "3.9"}},
        "overrides": [{"envs": ["test"], "skip_package": True}],
    }


def test_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert (
        result.stdout.strip()
        == f"pyproject2conda, version {pyproject2conda.__version__}"
    )


def test_multiple(caplog) -> None:
    runner = CliRunner()

    caplog.set_level(logging.INFO)

    t1 = tempfile.TemporaryDirectory()
    path1 = t1.name

    do_run(
        runner,
        "project",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    assert "Creating" in caplog.text

    # running this again?
    do_run(
        runner,
        "project",
        "-v",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    assert "Skipping requirements" in caplog.text

    # run again no verbose:
    do_run(
        runner,
        "project",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    t2 = tempfile.TemporaryDirectory()
    path2 = t2.name

    do_run(
        runner, "yaml", "-e", "dev", "-p", "3.10", "-o", f"{path2}/py310-dev.yaml", "-v"
    )

    do_run(
        runner,
        "yaml",
        "-e",
        "dist-pypi",
        "--skip-package",
        "-p",
        "3.10",
        "-o",
        f"{path2}/py310-dist-pypi.yaml",
    )

    do_run(runner, "yaml", "-e", "test", "-p", "3.10", "-o", f"{path2}/py310-test.yaml")
    do_run(runner, "yaml", "-e", "test", "-p", "3.11", "-o", f"{path2}/py311-test.yaml")

    do_run(
        runner,
        "yaml",
        "-e",
        "test",
        "--skip-package",
        "-p",
        "3.10",
        "-o",
        f"{path2}/py310-test-extras.yaml",
    )
    do_run(
        runner,
        "yaml",
        "-e",
        "test",
        "--skip-package",
        "-p",
        "3.11",
        "-o",
        f"{path2}/py311-test-extras.yaml",
    )

    do_run(
        runner, "r", "-e", "test", "--skip-package", "-o", f"{path2}/test-extras.txt"
    )

    do_run(
        runner,
        "yaml",
        "-e",
        "dev",
        "-e",
        "dist-pypi",
        "--name",
        "hello",
        "-p",
        "3.10",
        "-d",
        "extra-dep",
        "-r",
        "extra-req",
        "-o",
        f"{path2}/py310-user-dev.yaml",
    )

    do_run(runner, "req", "-o", f"{path2}/base.txt")

    paths1 = Path(path1).glob("*")
    names1 = {x.name for x in paths1}

    expected = set(
        "base.txt py310-dev.yaml py310-dist-pypi.yaml py310-test-extras.yaml py310-test.yaml py310-user-dev.yaml py311-test-extras.yaml py311-test.yaml test-extras.txt".split()
    )

    assert names1 == expected

    paths2 = Path(path2).glob("*")
    names2 = {x.name for x in paths2}

    assert expected == names2

    for x in expected:
        assert filecmp.cmp(f"{path1}/{x}", f"{path2}/{x}")

    t1.cleanup()
    t2.cleanup()
