from pyproject2conda.cli import app
from click.testing import CliRunner

from textwrap import dedent

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_list():
    runner = CliRunner()
    result = runner.invoke(app, ["list", "-f", str(ROOT / "test-pyproject.toml")])
    expected = """\
    extras  : ['test', 'dev-extras', 'dev']
    isolated: ['dist-pypi']
    """

    assert result.output == dedent(expected)


def test_create():
    runner = CliRunner()
    result = runner.invoke(app, ["create", "-f", str(ROOT / "test-pyproject.toml")])

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

    assert (result.output) == dedent(expected)

    result = runner.invoke(
        app, ["create", "-f", str(ROOT / "test-pyproject.toml"), "dev"]
    )

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

    assert result.output == dedent(expected)

    result = runner.invoke(
        app, ["create", "-f", str(ROOT / "test-pyproject.toml"), "-c", "hello"]
    )

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

    assert dedent(expected) == result.output

    result = runner.invoke(
        app, ["create", "-f", str(ROOT / "test-pyproject.toml"), "test"]
    )

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

    assert dedent(expected) == result.output

    result = runner.invoke(
        app, ["isolated", "-f", str(ROOT / "test-pyproject.toml"), "dist-pypi"]
    )

    expected = """\
channels:
  - conda-forge
dependencies:
  - setuptools
  - pip
  - pip:
      - build
    """

    assert result.output == dedent(expected)
