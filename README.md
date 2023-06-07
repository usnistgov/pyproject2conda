<!-- markdownlint-disable MD041 -->

[![Repo][repo-badge]][repo-link] [![Docs][docs-badge]][docs-link]
[![PyPI license][license-badge]][license-link]
[![PyPI version][pypi-badge]][pypi-link]
[![Conda (channel only)][conda-badge]][conda-link]
[![Code style: black][black-badge]][black-link]

<!--
  For more badges, see
  https://shields.io/category/other
  https://naereen.github.io/badges/
  [pypi-badge]: https://badge.fury.io/py/pyproject2conda
-->

[black-badge]: https://img.shields.io/badge/code%20style-black-000000.svg
[black-link]: https://github.com/psf/black
[pypi-badge]: https://img.shields.io/pypi/v/pyproject2conda
[pypi-link]: https://pypi.org/project/pyproject2conda
[docs-badge]: https://img.shields.io/badge/docs-sphinx-informational
[docs-link]: https://pages.nist.gov/pyproject2conda/
[repo-badge]: https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff
[repo-link]: https://github.com/wpk-nist-gov/pyproject2conda
[conda-badge]:https://img.shields.io/conda/v/wpk-nist/pyproject2conda
[conda-link]: https://anaconda.org/wpk-nist/pyproject2conda
[license-badge]: https://img.shields.io/pypi/l/cmomy?color=informational
[license-link]: https://github.com/wpk-nist-gov/pyproject2conda/blob/main/LICENSE

<!-- other links -->

[poetry2conda]: https://github.com/dojeda/poetry2conda

# `pyproject2conda`

A script to convert `pyproject.toml` dependecies to `environemnt.yaml` files.

## Overview

The main goal of `pyproject2conda` is to provide a means to keep all basic dependency information, for both `pip` based and `conda` based environments, in `pyproject.toml`. 
I often use a mix of pip and conda when developing packages, and in my everyday workflow.  Some packages just aren't available on both.
If you use poetry, I'd highly recommend [poetry2conda].

## Features

- Simple comment based syntax to add information to dependencies when creating `environment.yaml`

## Status

This package is actively used by the author, but is still very much a work in progress.
Please feel free to create a pull
request for wanted features and suggestions!

## Quick start

Use one of the following

```bash
pip install pyproject2conda
```

or

```bash
conda install -c wpk-nist pyproject2conda
```

## Example usage

Consider the `toml` file [test-pyproject.toml](./tests/test-pyproject.toml).

```toml
[project]
name = "hello"
requires-python = ">=3.8,<3.11"
dependencies = [
    "athing", # p2c: -p # a comment
    "bthing", # p2c: -s bthing-conda
    "cthing", # p2c: -c conda-forge

]
# ...
```

Note the comment lines `# p2c:...`.  These are special tokens that `pyproject2conda` will analyze.  The basic options are:

```
Arguments:   Additional (conda) packages

-p --pip     Pip install pyproject package on this line.
-s --skip    Skip pyproject package on this line.
-c --channel Add channel to pyproject package on this line
```

So, if we run the following, we get:

```bash
$ pyproject2conda create -f test/test-pyproject.toml
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
```
Note that other comments can be mixed in.  This also works with extras.  For example, with the following:

```toml
# ...
[project.optional-dependencies]
test = [
    "pandas",
    "pytest", # p2c: -c conda-forge

]
# ...
```

and running the the following gives:

```bash 
$ pyproject2conda create -f tests/test-pyproject.toml test
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
```

`pyproject2conda` can also be used within python:

```pycon
>>> from pyproject2conda import PyProject2Conda
>>> p = PyProject2Conda.from_path("./tests/test-pyproject.toml")

# Basic environment
>>> print(p.to_conda_yaml().strip())
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing

# Environment with extras
>>> print(p.to_conda_yaml(extras='test').strip())
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

```

<!-- end-docs -->

<!-- ## Documentation -->

<!-- See the [documentation][docs-link] for a look at -->
<!-- `pyproject2conda` in action. -->

## License

This is free software. See [LICENSE][license-link].

## Related work

TBD

## Contact

The author can be reached at wpk@nist.gov.

## Credits

This package was created with
[Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[wpk-nist-gov/cookiecutter-pypackage](https://github.com/wpk-nist-gov/cookiecutter-pypackage)
Project template forked from
[audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage).
