from pyproject2conda.cli import app
from click.testing import CliRunner

from textwrap import dedent

from pathlib import Path
import tempfile
import json

ROOT = Path(__file__).resolve().parent


def do_run(runner, command, *opts, filename=None):
    if filename is None:
        filename = str(ROOT / "test-pyproject.toml")
    result = runner.invoke(app, [command, "-f", filename, *opts])
    return result


def check_result(result, expected):
    assert result.output == dedent(expected)


def test_list():
    runner = CliRunner()

    for cmd in ["l", "list"]:
        result = do_run(runner, cmd)
        expected = """\
        extras  : ['test', 'dev-extras', 'dev', 'dist-pypi']
        """
        check_result(result, expected)

    result = do_run(runner, "list", "-v")
    expected = f"""\
filename: {ROOT / "test-pyproject.toml"}
extras  : ['test', 'dev-extras', 'dev', 'dist-pypi']
    """
    check_result(result, expected)


def test_create():
    runner = CliRunner()

    # test unknown file

    result = do_run(runner, "yaml", filename="hello/there.toml")

    assert isinstance(result.exception, ValueError)

    expected = """\
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
    """

    result = do_run(runner, "yaml")

    expected = """\
#
# This file is autogenerated by pyrpoject2conda.
# You should not manually edit this file.
# Instead edit the corresponding pyproject.toml file.
#
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
    """

    result = do_run(runner, "yaml", "--header")

    # -p flag
    expected = """\
channels:
  - conda-forge
dependencies:
  - python>=3.8,<3.11
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
    """

    for opt in ["--python-include"]:
        for cmd in ["y", "yaml"]:
            result = do_run(runner, cmd, opt)
            check_result(result, expected)

    # -p python=3.8
    expected = """\
channels:
  - conda-forge
dependencies:
  - python=3.8
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
    """
    for opt in ["--python-include"]:
        result = do_run(runner, "yaml", opt, "python=3.8")
        check_result(result, expected)

    # dev
    expected = """\
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pandas
  - conda-forge::pytest
  - additional-thing
  - conda-matplotlib
  - pip
  - pip:
      - athing
    """

    for opt in ["-e", "--extra"]:
        result = do_run(runner, "yaml", opt, "dev")
        check_result(result, expected)

    # test if add in "test" gives same answer
    result = do_run(runner, "yaml", "-e", "dev", "-e", "test")
    check_result(result, expected)

    # override channel
    expected = """\
channels:
  - hello
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
    """

    for opt in ["-c", "--channel"]:
        result = do_run(runner, "yaml", opt, "hello")
        check_result(result, expected)

    expected = """\
channels:
  - hello
  - there
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
    """

    for opt in ["-c", "--channel"]:
        result = do_run(runner, "yaml", opt, "hello", opt, "there")
        check_result(result, expected)

    # test
    expected = """\
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pandas
  - conda-forge::pytest
  - pip
  - pip:
      - athing
    """
    result = do_run(runner, "yaml", "-e", "test")
    check_result(result, expected)

    # isolated
    expected = """\
channels:
  - conda-forge
dependencies:
  - setuptools
  - pip
  - pip:
      - build
    """
    for opt in ["-e", "--extra"]:
        result = do_run(runner, "yaml", opt, "dist-pypi", "--no-base")
        check_result(result, expected)


def test_requirements():
    runner = CliRunner()

    expected = """\
athing
bthing
cthing; python_version < '3.10'
    """

    for cmd in ["r", "req", "requirements"]:
        result = do_run(runner, cmd)
        check_result(result, expected)

    expected = """\
athing
bthing
cthing; python_version < '3.10'
pandas
pytest
matplotlib
    """

    result = do_run(runner, "requirements", "-e", "dev")
    check_result(result, expected)

    result = do_run(runner, "requirements", "-e", "dev", "-e", "test")
    check_result(result, expected)

    expected = """\
setuptools
build
    """

    result = do_run(runner, "requirements", "-e", "dist-pypi", "--no-base")
    check_result(result, expected)


def check_results_conda_req(path, expected):
    with open(path, "r") as f:
        result = f.read()

    assert result == dedent(expected)


def test_conda_requirements():
    runner = CliRunner()

    result = do_run(runner, "conda-req", "hello.txt")

    assert isinstance(result.exception, ValueError)

    result = do_run(runner, "conda-req", "--prefix", "hello", "a", "b")

    assert isinstance(result.exception, ValueError)

    # stdout
    result = do_run(runner, "conda-req")

    expected = """\
#conda requirements
bthing-conda
conda-forge::cthing

#pip requirements
athing
    """

    assert result.output == dedent(expected)

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)

        expected_conda = """\
bthing-conda
conda-forge::cthing
        """
        expected_pip = """\
athing
        """

        for cmd in ["c", "conda-requirements"]:
            do_run(runner, cmd, "--prefix", str(d / "hello-"), "--no-header")

            check_results_conda_req(d / "hello-conda.txt", expected_conda)
            check_results_conda_req(d / "hello-pip.txt", expected_pip)

        do_run(
            runner,
            "conda-requirements",
            str(d / "conda-output.txt"),
            str(d / "pip-output.txt"),
            "--no-header",
        )

        check_results_conda_req(d / "conda-output.txt", expected_conda)
        check_results_conda_req(d / "pip-output.txt", expected_pip)

        do_run(
            runner,
            "conda-req",
            "--prefix",
            str(d / "hello-"),
            "--prepend-channel",
            "-c",
            "achannel",
            "--no-header",
        )

        expected_conda = """\
achannel::bthing-conda
conda-forge::cthing
        """

        check_results_conda_req(d / "hello-conda.txt", expected_conda)
        check_results_conda_req(d / "hello-pip.txt", expected_pip)


def test_json():
    runner = CliRunner()

    # stdout
    result = do_run(runner, "j")

    expected = """\
{"dependencies": ["bthing-conda", "conda-forge::cthing"], "pip": ["athing"], "channels": ["conda-forge"]}
    """

    assert result.output == dedent(expected)

    def check_results(path, expected):
        with open(path, "r") as f:
            result = json.load(f)

        assert result == expected

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)

        expected = {
            "dependencies": ["bthing-conda", "conda-forge::cthing"],
            "pip": ["athing"],
            "channels": ["conda-forge"],
        }

        do_run(runner, "json", "-o", str(d / "hello.json"))

        check_results(d / "hello.json", expected)

        expected = {
            "dependencies": [
                "bthing-conda",
                "conda-forge::cthing",
                "pandas",
                "conda-forge::pytest",
                "additional-thing",
                "conda-matplotlib",
            ],
            "pip": ["athing"],
            "channels": ["conda-forge"],
        }

        do_run(runner, "json", "-o", str(d / "there.json"), "-e", "dev")

        check_results(d / "there.json", expected)


def test_alias():
    runner = CliRunner()

    result = do_run(runner, "q")

    expected = """\
Usage: app [OPTIONS] COMMAND [ARGS]...
Try 'app --help' for help.

Error: No such command 'q'.
    """

    check_result(result, expected)
