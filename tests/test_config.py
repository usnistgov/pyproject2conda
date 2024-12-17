# mypy: disable-error-code="no-untyped-def, no-untyped-call"
import filecmp
import logging
import tempfile
from functools import partial
from pathlib import Path
from textwrap import dedent

import pytest

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
        "py{py}-{env}", env_name="test", python="3.8", ext=".yaml"
    )

    assert t == expected

    t = utils.filename_from_template(
        "py{py}-{env}", env_name="test", python_version="3.8", ext=".yaml"
    )

    assert t == expected


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
    template_python = "py{py}-{env}"
    template = "hello-{env}"
    style = "yaml"
    # options
    python = "3.10"
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


    [tool.pyproject2conda.envs.base3]
    style = "yaml"
    python = "default"

    [tool.pyproject2conda.envs.base4]
    style = "yaml"
    python = ["3.9", "3.10", "3.11", "3.12", "3.13"]
    template_python = "py{py}-hello"

    [tool.pyproject2conda.envs.base5]
    style = "yaml"
    python = "all"
    template_python = "py{py}-hello"

    [tool.pyproject2conda.envs.base_lowest]
    style = "yaml"
    python = "lowest"
    template_python = "py{py}-hello"

    [tool.pyproject2conda.envs.base_highest]
    style = "yaml"
    python = "highest"
    template_python = "py{py}-hello"


    [tool.pyproject2conda.envs.extension_yaml]
    style = "yaml"
    yaml_ext = ".yml"

    [tool.pyproject2conda.envs.extension_txt]
    style = "requirements"
    reqs_ext = ".in"

    [tool.pyproject2conda.envs.both]
    groups = "thing"


    [[tool.pyproject2conda.overrides]]
    envs = ["both"]
    extras = ["test"]

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
def simple_config(simple_toml: str) -> Config:
    return Config.from_string(dedent(simple_toml))


def test_option_override_base(simple_config: Config) -> None:
    output = list(simple_config.iter_envs(envs=["base"]))

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


def test_option_override_base_reqs(simple_config: Config) -> None:
    output = list(simple_config.iter_envs(envs=["base"], reqs=["-e ."]))

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
            "reqs": ["-e ."],
            "deps": None,
            "name": None,
            "channels": ["conda-forge"],
            "allow_empty": False,
            "remove_whitespace": True,
            "output": "hello-base.yaml",
        },
    )


def test_option_override_base2(simple_config: Config) -> None:
    output = list(simple_config.iter_envs(envs=["base2"]))

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


def test_option_override_both(simple_config: Config) -> None:
    output = list(simple_config.iter_envs(envs=["both"]))

    assert output[0] == (
        "yaml",
        {
            "extras": ["test"],
            "groups": ["thing"],
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
            "output": "py310-both.yaml",
            "python": "3.10",
        },
    )


def test_option_override_base_template(simple_config: Config) -> None:
    output = list(simple_config.iter_envs(envs=["base"], template="there-{env}"))

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


def test_option_override_base_allow_empty(simple_config: Config) -> None:
    output = list(
        simple_config.iter_envs(envs=["base"], allow_empty=True, template="there-{env}")
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
            "remove_whitespace": True,
            "output": "there-base.yaml",
        },
    )


def test_option_override_base_allow_empty_other(simple_config: Config) -> None:
    output = list(
        simple_config.iter_envs(
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


def test_option_override_base3_default_python_error(
    example_path: Path,  # noqa: ARG001
    simple_config: Config,
) -> None:
    # using default python without a version
    with pytest.raises(ValueError, match="Must include `.python-version` .*"):
        list(simple_config.iter_envs(envs=["base3"]))


def test_option_override_base3_default_python(example_path, simple_toml: str) -> None:
    with (example_path / ".python-version").open("w") as f:
        f.write("3.10\n")

    from pyproject2conda.utils import get_default_pythons

    assert get_default_pythons() == ["3.10"]

    config = Config.from_string(dedent(simple_toml))
    output = list(config.iter_envs(envs=["base3"]))

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
            "output": "py310-base3.yaml",
            "python": "3.10",
        },
    )


def test_option_override_all_pythons_error(simple_config: Config) -> None:
    with pytest.raises(ValueError, match="Must specify python versions .*"):
        list(simple_config.iter_envs(envs=["base5"]))


def test_option_override_all_pythons(simple_toml: str, classifiers: str) -> None:
    simple_config = Config.from_string(dedent(simple_toml + classifiers))

    a = list(simple_config.iter_envs(envs=["base4"]))
    b = list(simple_config.iter_envs(envs=["base5"]))

    assert len(a) == len(b) == 5

    assert a[0] == (
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
            "output": "py39-hello.yaml",
            "python": "3.9",
        },
    )

    assert a == b


def test_option_override_lowest_highest(simple_toml: str, classifiers: str) -> None:
    simple_config = Config.from_string(dedent(simple_toml + classifiers))

    a = list(simple_config.iter_envs(envs=["base_lowest"]))
    b = list(simple_config.iter_envs(envs=["base_highest"]))

    assert a[0] == (
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
            "output": "py39-hello.yaml",
            "python": "3.9",
        },
    )

    assert b[0] == (
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
            "output": "py313-hello.yaml",
            "python": "3.13",
        },
    )


def test_option_override_extension_yaml(simple_config: Config) -> None:
    output = list(simple_config.iter_envs(envs=["extension_yaml"]))

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
            "output": "py310-extension_yaml.yml",
            "python": "3.10",
        },
    )


def test_option_override_extension_txt(simple_config: Config) -> None:
    output = list(simple_config.iter_envs(envs=["extension_txt"]))

    assert output[0] == (
        "requirements",
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
            "allow_empty": False,
            "remove_whitespace": False,
            "output": "hello-extension_txt.in",
        },
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


def test_version(runner) -> None:
    result = runner.invoke(app, ["--version"])

    assert (
        result.stdout.strip()
        == f"pyproject2conda, version {pyproject2conda.__version__}"
    )


@pytest.mark.parametrize(
    ("fname", "opt"),
    [
        ("test-pyproject.toml", "-e"),
        ("test-pyproject-groups.toml", "-g"),
    ],
)
def test_multiple(fname, opt, runner, caplog) -> None:
    filename = ROOT / fname
    _do_run = partial(do_run, filename=filename)

    caplog.set_level(logging.INFO)

    t1 = tempfile.TemporaryDirectory()
    path1 = t1.name

    _do_run(
        runner,
        "project",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    assert "Creating" in caplog.text

    # running this again?
    _do_run(
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
    _do_run(
        runner,
        "project",
        "--template-python",
        f"{path1}/" + "py{py}-{env}",
        "--template",
        f"{path1}/" + "{env}",
    )

    t2 = tempfile.TemporaryDirectory()
    path2 = t2.name

    _do_run(
        runner, "yaml", opt, "dev", "-p", "3.10", "-o", f"{path2}/py310-dev.yaml", "-v"
    )

    _do_run(
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

    _do_run(runner, "yaml", opt, "test", "-p", "3.10", "-o", f"{path2}/py310-test.yaml")
    _do_run(runner, "yaml", opt, "test", "-p", "3.11", "-o", f"{path2}/py311-test.yaml")

    _do_run(
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
    _do_run(
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

    _do_run(
        runner, "r", opt, "test", "--skip-package", "-o", f"{path2}/test-extras.txt"
    )

    _do_run(
        runner,
        "yaml",
        opt,
        "dev",
        opt,
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

    _do_run(runner, "req", "-o", f"{path2}/base.txt")

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
