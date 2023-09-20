# mypy: disable-error-code="no-untyped-def, no-untyped-call"
import pytest
from pyproject2conda.cli import app
from pyproject2conda.config import Config
from pyproject2conda import utils
from click.testing import CliRunner


from pathlib import Path
import tempfile

import filecmp
from textwrap import dedent

ROOT = Path(__file__).resolve().parent / "data"


def do_run(runner, command, *opts, filename=None, must_exist=False):
    if filename is None:
        filename = str(ROOT / "test-pyproject.toml")
    filename = Path(filename)
    if must_exist and not filename.exists():
        raise ValueError(f"filename {filename} does not exist")

    result = runner.invoke(app, [command, "-f", str(filename), *opts])
    return result


def test_template():
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


def test_dry():
    runner = CliRunner()

    expected = """\
# Creating yaml py310-test-extras.yaml
channels:
  - conda-forge
dependencies:
  - python=3.10
  - conda-forge::pytest
  - pandas
# Creating yaml py311-test-extras.yaml
channels:
  - conda-forge
dependencies:
  - python=3.11
  - conda-forge::pytest
  - pandas
# Creating requirements test-extras.txt
pandas
pytest
    """

    result = do_run(runner, "proj", "--dry", "--envs", "test-extras")

    assert result.output == dedent(expected)


def test_config_only_default():
    expected = [
        (
            "yaml",
            {
                "extras": ["test"],
                "sort": True,
                "base": True,
                "header": None,
                "overwrite": "check",
                "verbose": True,
                "name": None,
                "channels": None,
                "python": "3.8",
                "output": "py38-test.yaml",
                "deps": None,
                "reqs": None,
            },
        )
    ]

    s0 = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default_envs = ["test"]
    """
    s1 = """
    [tool.pyproject2conda]
    python = ["3.8"]

    [tool.pyproject2conda.envs.test]
    """

    s2 = """
    [tool.pyproject2conda.envs.test]
    python = "3.8"


    """

    for s in [s0, s1, s2]:
        c = Config.from_string(s)

        assert list(c.iter()) == expected


def test_config_overrides():
    # test overrides env
    s = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default_envs = ["test"]

    [[tool.pyproject2conda.overrides]]
    envs = ["test"]
    base = false
    """

    c = Config.from_string(s)

    expected = (
        "yaml",
        {
            "extras": ["test"],
            "sort": True,
            "base": False,
            "header": None,
            "overwrite": "check",
            "verbose": True,
            "name": None,
            "channels": None,
            "python": "3.8",
            "output": "py38-test.yaml",
            "deps": None,
            "reqs": None,
        },
    )

    assert list(c.iter())[0] == expected


def test_conifg_overrides_no_envs():
    # test overrides env
    s = """
    [tool.pyproject2conda]
    python = ["3.8"]
    default_envs = ["test"]

    [[tool.pyproject2conda.overrides]]
    base = false
    """

    c = Config.from_string(s)

    with pytest.raises(ValueError):
        c.overrides


def test_config_python_include_version():
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
                "sort": True,
                "base": True,
                "header": None,
                "overwrite": "check",
                "verbose": True,
                "name": None,
                "channels": None,
                "python_include": "3.8",
                "python_version": "3.8",
                "output": "py38-test.yaml",
                "deps": None,
                "reqs": None,
            },
        ),
        (
            "yaml",
            {
                "extras": ["test"],
                "sort": True,
                "base": True,
                "header": None,
                "overwrite": "check",
                "verbose": True,
                "name": None,
                "channels": None,
                "python_include": "3.8",
                "python_version": "3.8",
                "output": "py38-test.yaml",
                "deps": None,
                "reqs": None,
            },
        ),
    ]

    assert list(c.iter()) == expected

    # no output:


def test_config_user_config():
    # test overrides env
    s = """
    [tool.pyproject2conda.envs.test]
    python = "3.8"


    """

    s_user = """
    [tool.pyproject2conda.envs.user]
    extras = ["a", "b"]
    python = "3.9"

    [[tool.pyproject2conda.overrides]]
    envs = ["test"]
    base = false
    """

    c = Config.from_string(s, s_user)

    expected = [
        (
            "yaml",
            {
                "extras": ["test"],
                "sort": True,
                "base": False,
                "header": None,
                "overwrite": "check",
                "verbose": True,
                "name": None,
                "channels": None,
                "python": "3.8",
                "output": "py38-test.yaml",
                "deps": None,
                "reqs": None,
            },
        ),
        (
            "yaml",
            {
                "extras": ["a", "b"],
                "sort": True,
                "base": True,
                "header": None,
                "overwrite": "check",
                "verbose": True,
                "name": None,
                "channels": None,
                "python": "3.9",
                "output": "py39-user.yaml",
                "deps": None,
                "reqs": None,
            },
        ),
    ]

    assert list(c.iter()) == expected

    # blank config, only user
    s = """
    [tool.pyproject2conda]
    """

    c = Config.from_string(s, s_user)

    assert c.data == {
        "envs": {"user": {"extras": ["a", "b"], "python": "3.9"}},
        "overrides": [{"envs": ["test"], "base": False}],
    }


def test_multiple():
    runner = CliRunner()

    t1 = tempfile.TemporaryDirectory()
    path1 = t1.name
    # path1 = ROOT / ".." / ".." / "tmp" / "output1"

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
    # path2 = ROOT / ".." / ".." / "tmp" / "output2"

    do_run(runner, "yaml", "-e", "dev", "-p", "3.10", "-o", f"{path2}/py310-dev.yaml")

    do_run(
        runner,
        "yaml",
        "-e",
        "dist-pypi",
        "--no-base",
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
        "--no-base",
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
        "--no-base",
        "-p",
        "3.11",
        "-o",
        f"{path2}/py311-test-extras.yaml",
    )

    do_run(runner, "req", "-e", "test", "--no-base", "-o", f"{path2}/test-extras.txt")

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

    paths1 = Path(path1).glob("*")
    names1 = set(x.name for x in paths1)

    expected = set(
        "py310-dev.yaml py310-dist-pypi.yaml py310-test-extras.yaml py310-test.yaml py310-user-dev.yaml py311-test-extras.yaml py311-test.yaml test-extras.txt".split()
    )

    assert names1 == expected

    paths2 = Path(path2).glob("*")
    names2 = set(x.name for x in paths2)

    assert expected == names2

    for x in expected:
        assert filecmp.cmp(f"{path1}/{x}", f"{path2}/{x}")

    t1.cleanup()
    t2.cleanup()
