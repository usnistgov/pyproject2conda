from pyproject2conda.cli import app
from click.testing import CliRunner

from textwrap import dedent

from pathlib import Path
import tempfile
import pytest
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

    result = do_run(runner, "list")
    expected = """\
    extras  : ['test', 'dev-extras', 'dev']
    isolated: ['dist-pypi']
    """
    check_result(result, expected)


def test_create():
    runner = CliRunner()

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

    for opt in ["-p", "--python"]:
        result = do_run(runner, "yaml", opt)
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
    for opt in ["-p", "--python"]:
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
    for opt in ["-i", "--isolated"]:
        result = do_run(runner, "yaml", opt, "dist-pypi")
        check_result(result, expected)


def test_requirements():
    runner = CliRunner()

    expected = """\
athing
bthing
cthing
    """

    result = do_run(runner, "requirements")
    check_result(result, expected)

    expected = """\
athing
bthing
cthing
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

    result = do_run(runner, "requirements", "-i", "dist-pypi")
    check_result(result, expected)


def check_results_conda_req(path, expected):
    with open(path, "r") as f:
        result = f.read()

    assert result == dedent(expected)


def test_conda_requirements():
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)

        expected_conda = """\
bthing-conda
conda-forge::cthing
        """
        expected_pip = """\
athing
        """

        do_run(runner, "conda-requirements", "--prefix", str(d / "hello-"))

        check_results_conda_req(d / "hello-conda.txt", expected_conda)
        check_results_conda_req(d / "hello-pip.txt", expected_pip)

        do_run(
            runner,
            "conda-requirements",
            str(d / "conda-output.txt"),
            str(d / "pip-output.txt"),
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
        )

        expected_conda = """\
achannel::bthing-conda
conda-forge::cthing
        """

        check_results_conda_req(d / "hello-conda.txt", expected_conda)
        check_results_conda_req(d / "hello-pip.txt", expected_pip)


def test_json():
    runner = CliRunner()

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
