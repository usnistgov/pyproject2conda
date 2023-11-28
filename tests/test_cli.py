# mypy: disable-error-code="no-untyped-def, no-untyped-call, assignment"
from pyproject2conda.cli import app

from click.testing import CliRunner

# from typer.testing import CliRunner

from textwrap import dedent

from pathlib import Path
import tempfile
import json

import sys

import pytest


ROOT = Path(__file__).resolve().parent / "data"


def do_run(runner, command, *opts, filename=None, must_exist=False, **kwargs):
    if filename is None:
        raise ValueError
    # if filename is None:
    #     filename = str(ROOT / "test-pyproject.toml")
    filename = Path(filename)
    if must_exist and not filename.exists():
        raise ValueError(f"filename {filename} does not exist")

    result = runner.invoke(app, [command, "-f", str(filename), *opts], **kwargs)

    return result


def check_result(result, expected):
    assert result.output == dedent(expected)


@pytest.fixture(params=["test-pyproject.toml", "test-pyproject-alt.toml"])
def filename(request):
    return ROOT / request.param


def test_list(filename):
    runner = CliRunner()

    for cmd in ["l", "list"]:
        result = do_run(runner, cmd, filename=filename)
        expected = """\
        Extras:
        =======
        * test
        * dev-extras
        * dev
        * dist-pypi
        * build-system.requires
        """
        check_result(result, expected)

    result = do_run(runner, "list", "-v", filename=filename)
    # TODO: the logger writes to output
    # assert result.output == f"filename: {ROOT / 'test-pyproject.toml'} [pyproject2conda - INFO]"
    check_result(result, expected)


def test_create(filename):
    runner = CliRunner()

    # test unknown file

    result = do_run(runner, "yaml", filename="hello/there.toml")

    assert isinstance(result.exception, FileNotFoundError)

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

    result = do_run(runner, "yaml", filename=filename)

    check_result(result, expected)

    cmd = " ".join([Path(sys.argv[0]).name] + sys.argv[1:])

    expected = f"""\
#
# This file is autogenerated by pyproject2conda
# with the following command:
#
#     $ {cmd}
#
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

    result = do_run(runner, "yaml", "--header", filename=filename)

    check_result(result, expected)

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

    for opt in [("--python-include", "infer")]:
        for cmd in ["y", "yaml"]:
            result = do_run(runner, cmd, *opt, filename=filename)
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
    for opts in [
        ("--python-include", "python=3.8"),
        ("--python", "3.8"),
        ("-p", "3.8"),
    ]:
        result = do_run(runner, "yaml", *opts, filename=filename)
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
        result = do_run(runner, "yaml", opt, "dev", "--no-sort", filename=filename)
        check_result(result, expected)

    # test if add in "test" gives same answer
    result = do_run(
        runner, "yaml", "-e", "dev", "-e", "test", "--no-sort", filename=filename
    )
    check_result(result, expected)

    expected = """\
channels:
  - conda-forge
dependencies:
  - additional-thing
  - bthing-conda
  - conda-forge::cthing
  - conda-forge::pytest
  - conda-matplotlib
  - pandas
  - pip
  - pip:
      - athing
    """

    for opt in ["-e", "--extra"]:
        result = do_run(runner, "yaml", opt, "dev", filename=filename)
        check_result(result, expected)

    # test if add in "test" gives same answer
    result = do_run(runner, "yaml", "-e", "dev", "-e", "test", filename=filename)
    check_result(result, expected)

    # different ordering
    expected = """\
channels:
  - conda-forge
dependencies:
  - conda-forge::cthing
  - bthing-conda
  - conda-forge::pytest
  - pandas
  - conda-matplotlib
  - additional-thing
  - pip
  - pip:
      - athing
    """

    for opt in ["-e", "--extra"]:
        result = do_run(
            runner,
            "yaml",
            opt,
            "dev",
            "--no-sort",
            filename=ROOT / "test-pyproject-reorder.toml",
            must_exist=True,
        )
        check_result(result, expected)

    # test if add in "test" gives same answer
    result = do_run(
        runner,
        "yaml",
        "-e",
        "dev",
        "-e",
        "test",
        "--no-sort",
        filename=ROOT / "test-pyproject-reorder.toml",
        must_exist=True,
    )
    check_result(result, expected)

    expected = """\
channels:
  - conda-forge
dependencies:
  - additional-thing
  - bthing-conda
  - conda-forge::cthing
  - conda-forge::pytest
  - conda-matplotlib
  - pandas
  - pip
  - pip:
      - athing
    """

    for opt in ["-e", "--extra"]:
        result = do_run(
            runner,
            "yaml",
            opt,
            "dev",
            filename=ROOT / "test-pyproject-reorder.toml",
            must_exist=True,
        )
        check_result(result, expected)

    # test if add in "test" gives same answer
    result = do_run(
        runner,
        "yaml",
        "-e",
        "dev",
        "-e",
        "test",
        filename=ROOT / "test-pyproject-reorder.toml",
        must_exist=True,
    )
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
        result = do_run(runner, "yaml", opt, "hello", filename=filename)
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
        result = do_run(runner, "yaml", opt, "hello", opt, "there", filename=filename)
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
    result = do_run(runner, "yaml", "-e", "test", "--no-sort", filename=filename)
    check_result(result, expected)

    expected = """\
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - conda-forge::pytest
  - pandas
  - pip
  - pip:
      - athing
    """
    result = do_run(runner, "yaml", "-e", "test", filename=filename)
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
        result = do_run(
            runner, "yaml", opt, "dist-pypi", "--no-base", filename=filename
        )
        check_result(result, expected)


def test_requirements(filename):
    runner = CliRunner()

    expected = """\
athing
bthing
cthing;python_version<"3.10"
    """

    for cmd in ["r", "requirements"]:
        result = do_run(runner, cmd, filename=filename)
        check_result(result, expected)

    expected = """\
athing
bthing
cthing;python_version<"3.10"
pandas
pytest
matplotlib
    """

    result = do_run(runner, "requirements", "-e", "dev", "--no-sort", filename=filename)
    check_result(result, expected)

    result = do_run(
        runner,
        "requirements",
        "-e",
        "dev",
        "-e",
        "test",
        "--no-sort",
        filename=filename,
    )
    check_result(result, expected)

    expected = """\
athing
bthing
cthing;python_version<"3.10"
pandas
pytest
matplotlib
thing;python_version<"3.10"
other
    """

    result = do_run(
        runner,
        "requirements",
        "-e",
        "dev",
        "--no-sort",
        "-r",
        "thing;python_version<'3.10'",
        "-r",
        "other",
        filename=filename,
    )

    check_result(result, expected)

    expected = """\
athing
bthing
cthing;python_version<"3.10"
matplotlib
pandas
pytest
    """

    result = do_run(runner, "requirements", "-e", "dev", filename=filename)
    check_result(result, expected)

    result = do_run(
        runner, "requirements", "-e", "dev", "-e", "test", filename=filename
    )
    check_result(result, expected)

    expected = """\
athing
bthing
cthing;python_version<"3.10"
matplotlib
other
pandas
pytest
thing;python_version<"3.10"
    """

    result = do_run(
        runner,
        "requirements",
        "-e",
        "dev",
        "-r",
        "thing;python_version<'3.10'",
        "-r",
        "other",
        filename=filename,
    )

    check_result(result, expected)

    # allow whitespace:
    expected = """\
athing
bthing
cthing; python_version < "3.10"
matplotlib
other
pandas
pytest
thing; python_version < "3.10"
    """

    result = do_run(
        runner,
        "requirements",
        "-e",
        "dev",
        "-r",
        "thing; python_version < '3.10'",
        "-r",
        "other",
        "--no-remove-whitespace",
        filename=filename,
    )

    check_result(result, expected)

    expected = """\
setuptools
build
    """

    result = do_run(
        runner,
        "requirements",
        "-e",
        "dist-pypi",
        "--no-base",
        "--no-sort",
        filename=filename,
    )
    check_result(result, expected)

    expected = """\
build
setuptools
    """

    result = do_run(
        runner, "requirements", "-e", "dist-pypi", "--no-base", filename=filename
    )
    check_result(result, expected)


def check_results_conda_req(path, expected):
    with open(path, "r") as f:
        result = f.read()

    assert result == dedent(expected)


def test_conda_requirements(filename):
    runner = CliRunner()

    result = do_run(runner, "c", "hello.txt", filename=filename)

    assert isinstance(result.exception, ValueError)

    result = do_run(runner, "c", "--prefix", "hello", "a", "b", filename=filename)

    assert isinstance(result.exception, ValueError)

    # stdout
    result = do_run(runner, "c", filename=filename)

    expected = """\
#conda requirements
bthing-conda
conda-forge::cthing
pip

#pip requirements
athing
    """

    assert result.output == dedent(expected)

    with tempfile.TemporaryDirectory() as d_tmp:
        d = Path(d_tmp)

        expected_conda = """\
bthing-conda
conda-forge::cthing
pip
        """
        expected_pip = """\
athing
        """

        for cmd in ["c", "conda-requirements"]:
            do_run(
                runner,
                cmd,
                "--prefix",
                str(d / "hello-"),
                "--no-header",
                filename=filename,
            )

            check_results_conda_req(d / "hello-conda.txt", expected_conda)
            check_results_conda_req(d / "hello-pip.txt", expected_pip)

        do_run(
            runner,
            "conda-requirements",
            str(d / "conda-output.txt"),
            str(d / "pip-output.txt"),
            "--no-header",
            filename=filename,
        )

        check_results_conda_req(d / "conda-output.txt", expected_conda)
        check_results_conda_req(d / "pip-output.txt", expected_pip)

        do_run(
            runner,
            "c",
            "--prefix",
            str(d / "hello-"),
            "--prepend-channel",
            "-c",
            "achannel",
            "--no-header",
            filename=filename,
        )

        expected_conda = """\
achannel::bthing-conda
conda-forge::cthing
achannel::pip
        """

        check_results_conda_req(d / "hello-conda.txt", expected_conda)
        check_results_conda_req(d / "hello-pip.txt", expected_pip)


def test_json(filename):
    runner = CliRunner()

    # stdout
    result = do_run(runner, "j", filename=filename)

    expected = """\
{"dependencies": ["bthing-conda", "conda-forge::cthing", "pip"], "pip": ["athing"], "channels": ["conda-forge"]}
    """

    assert result.output == dedent(expected)

    def check_results(path, expected):
        with open(path, "r") as f:
            result = json.load(f)

        assert result == expected

    with tempfile.TemporaryDirectory() as d_tmp:
        d = Path(d_tmp)

        expected = {  # type: ignore
            "dependencies": ["bthing-conda", "conda-forge::cthing", "pip"],
            "pip": ["athing"],
            "channels": ["conda-forge"],
        }

        do_run(runner, "json", "-o", str(d / "hello.json"), filename=filename)

        check_results(d / "hello.json", expected)

        expected = {  # type: ignore
            "dependencies": [
                "bthing-conda",
                "conda-forge::cthing",
                "pandas",
                "conda-forge::pytest",
                "additional-thing",
                "conda-matplotlib",
                "pip",
            ],
            "pip": ["athing"],
            "channels": ["conda-forge"],
        }

        do_run(
            runner,
            "json",
            "-o",
            str(d / "there.json"),
            "-e",
            "dev",
            "--no-sort",
            filename=filename,
        )

        check_results(d / "there.json", expected)

        expected = {  # type: ignore
            "dependencies": [
                "additional-thing",
                "bthing-conda",
                "conda-forge::cthing",
                "conda-forge::pytest",
                "conda-matplotlib",
                "pandas",
                "pip",
            ],
            "pip": ["athing"],
            "channels": ["conda-forge"],
        }

        do_run(
            runner, "json", "-o", str(d / "there.json"), "-e", "dev", filename=filename
        )

        check_results(d / "there.json", expected)


def test_alias(filename):
    runner = CliRunner()

    result = do_run(runner, "q", filename=filename)

    assert isinstance(result.exception, BaseException)


#     expected = """\
# Usage: app [OPTIONS] COMMAND [ARGS]...
# Try 'app --help' for help.

# Error: No such command 'q'.
#     """

#     check_result(result, expected)


def test_overwrite(filename):
    runner = CliRunner(mix_stderr=True)

    with tempfile.TemporaryDirectory() as d_tmp:
        d = Path(d_tmp)

        path = d / "out.yaml"

        assert not path.exists()

        result = do_run(
            runner,
            "yaml",
            "-o",
            str(path),
            "-v",
            "-w",
            "force",
            catch_exceptions=False,
            filename=filename,
        )
        # assert result.output.strip() == f"# Creating yaml {d_tmp}/out.yaml"

        orig_time = path.stat().st_mtime

        for cmd in ["check", "skip", "force"]:
            result = do_run(
                runner,
                "yaml",
                "-o",
                str(d / "out.yaml"),
                "-v",
                "-w",
                cmd,
                catch_exceptions=False,
                filename=filename,
            )

            if cmd == "force":
                assert path.stat().st_mtime > orig_time
            else:
                assert path.stat().st_mtime == orig_time

            # assert (
            #     result.output.strip()
            #     == f"# Skipping yaml {d_tmp}/out.yaml. Pass `-w force` to force recreate output"
            # )

        path = d / "out.txt"
        assert not path.exists()

        result = do_run(
            runner,
            "r",
            "-o",
            str(d / "out.txt"),
            "-v",
            "-w",
            "force",
            catch_exceptions=False,
            filename=filename,
        )
        orig_time = path.stat().st_mtime

        # assert result.output.strip() == f"# Creating requirements {d_tmp}/out.txt"

        for cmd in ["check", "skip", "force"]:
            result = do_run(
                runner,
                "r",
                "-o",
                str(path),
                "-v",
                "-w",
                cmd,
                catch_exceptions=False,
                filename=filename,
            )

            if cmd == "force":
                assert path.stat().st_mtime > orig_time
            else:
                assert path.stat().st_mtime == orig_time
            # assert (
            #     result.output.strip()
            #     == f"# Skipping requirements {d_tmp}/out.txt. Pass `-w force` to force recreate output"
            # )
