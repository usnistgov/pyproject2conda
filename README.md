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
[conda-badge]: https://img.shields.io/conda/v/wpk-nist/pyproject2conda
[conda-link]: https://anaconda.org/wpk-nist/pyproject2conda
[license-badge]: https://img.shields.io/pypi/l/cmomy?color=informational
[license-link]:
  https://github.com/wpk-nist-gov/pyproject2conda/blob/main/LICENSE

<!-- other links -->

[poetry2conda]: https://github.com/dojeda/poetry2conda

# `pyproject2conda`

A script to convert `pyproject.toml` dependecies to `environemnt.yaml` files.

## Overview

The main goal of `pyproject2conda` is to provide a means to keep all basic
dependency information, for both `pip` based and `conda` based environments, in
`pyproject.toml`. I often use a mix of pip and conda when developing packages,
and in my everyday workflow. Some packages just aren't available on both. If you
use poetry, I'd highly recommend [poetry2conda].

## Features

- Simple comment based syntax to add information to dependencies when creating
  `environment.yaml`

## Status

This package is actively used by the author, but is still very much a work in
progress. Please feel free to create a pull request for wanted features and
suggestions!

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

### Basic usage

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

Note the comment lines `# p2c:...`. These are special tokens that
`pyproject2conda` will analyze. The basic options are:

```bash
Arguments:   Additional (conda) packages

-p --pip     Pip install pyproject package on this line.
-s --skip    Skip pyproject package on this line.
-c --channel Add channel to pyproject package on this line
```

So, if we run the following, we get:

<!-- [[[cog
import subprocess
import shlex

def run_command(cmd, wrapper="bash"):
    args = shlex.split(cmd)
    output = subprocess.check_output(args)
    total = f"$ {cmd}\n{output.decode()}"

    if wrapper:
        total = f"\n```{wrapper}\n"  + total + "```\n"

    print(total)
]]] -->
<!-- [[[end]]] -->

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
```

<!-- [[[end]]] -->

Note that other comments can be mixed in. This also works with extras. For
example, with the following:

Also, by default, the python version is not included in the resulting conda
output. To include the specification from pyproject.toml, use `-p/--python`
option:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml -p")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml -p
channels:
  - conda-forge
dependencies:
  - python>=3.8,<3.11
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
```

<!-- [[[end]]] -->

To specify a value of python, pass a value with:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml -p python=3.9")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml -p python=3.9
channels:
  - conda-forge
dependencies:
  - python=3.9
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing
```

<!-- [[[end]]] -->

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

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml -e test")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml -e test
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

<!-- [[[end]]] -->

`pyproject2conda` also works with self referenced dependencies:

```toml
# ...
[project.optional-dependencies]
# ...
dev-extras = [
  # p2c: -s additional-thing # this is an additional conda package
  "matplotlib", # p2c: -s conda-matplotlib

]
dev = ["hello[test]", "hello[dev-extras]"]
# ...

```

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml -e dev")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml -e dev
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
```

<!-- [[[end]]] -->

### Usage within python

`pyproject2conda` can also be used within python:

```pycon
>>> from pyproject2conda import PyProject2Conda
>>> p = PyProject2Conda.from_path("./tests/test-pyproject.toml")

# Basic environment
>>> print(p.to_conda_yaml(python="get").strip())
channels:
  - conda-forge
dependencies:
  - python>=3.8,<3.11
  - bthing-conda
  - conda-forge::cthing
  - pip
  - pip:
      - athing

# Environment with extras
>>> print(p.to_conda_yaml(extras="test").strip())
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

### Configuration

`pyproject2conda` can be configured with a `[tool.pyproject2conda]` section in
`pyproject.toml`. To specify conda channels use:

```toml
# Why channel conda-forge appeared above
[tool.pyproject2conda]
channels = ["conda-forge"]

```

Note that specifying channels at the comand line overrides

You can also specify `isolated-dependencies`. These are dependencies for things
that should not include package dependencies (things like build dependencies).
For example:

```toml
[tool.pyproject2conda.isolated-dependencies]
dist-pypi = [
  "setuptools",
  "build", # p2c: -p

]

```

These can be accessed using either of the following:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml -i dist-pypi")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml -i dist-pypi
channels:
  - conda-forge
dependencies:
  - setuptools
  - pip
  - pip:
      - build
```

<!-- [[[end]]] -->

or

```pycon
>>> from pyproject2conda import PyProject2Conda
>>> p = PyProject2Conda.from_path("./tests/test-pyproject.toml")

# Basic environment
>>> print(p.to_conda_yaml(isolated='dist-pypi').strip())
channels:
  - conda-forge
dependencies:
  - setuptools
  - pip
  - pip:
      - build

```

### CLI options

<!-- [[[cog run_command("pyproject2conda --help")]]] -->

```bash
$ pyproject2conda --help
Usage: pyproject2conda [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  conda-requirements  Create requirement files for conda and pip.
  json                Create json representation.
  list                List available extras/isolated
  requirements        Create requirements.txt for pip depedencies.
  yaml                Create yaml file from dependencies and...
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda list --help")]]] -->

```bash
$ pyproject2conda list --help
Usage: pyproject2conda list [OPTIONS]

  List available extras/isolated

Options:
  -f, --file PATH  input pyproject.toml file
  -v, --verbose
  --help           Show this message and exit.
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda yaml --help")]]] -->

```bash
$ pyproject2conda yaml --help
Usage: pyproject2conda yaml [OPTIONS]

  Create yaml file from dependencies and optional-dependencies.

Options:
  -e, --extra TEXT     Extra depenedencies. Can specify multiple times for
                       multiple extras.
  -i, --isolated TEXT  Isolated dependencies (under
                       [tool.pyproject2conda.isolated-dependencies]).  Can
                       specify multiple times.
  -c, --channel TEXT   conda channel.  Can specify. Overrides
                       [tool.pyproject2conda.channels]
  -f, --file PATH      input pyproject.toml file
  -n, --name TEXT      Name of conda env
  -o, --output PATH    File to output results
  -p, --python TEXT    if flag passed without options, include python spec
                       from pyproject.toml in output.  If value passed, use
                       this value of python in the output
  --help               Show this message and exit.
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda requirements --help")]]] -->

```bash
$ pyproject2conda requirements --help
Usage: pyproject2conda requirements [OPTIONS]

  Create requirements.txt for pip depedencies.

Options:
  -e, --extra TEXT     Extra depenedencies. Can specify multiple times for
                       multiple extras.
  -i, --isolated TEXT  Isolated dependencies (under
                       [tool.pyproject2conda.isolated-dependencies]).  Can
                       specify multiple times.
  -f, --file PATH      input pyproject.toml file
  -o, --output PATH    File to output results
  --help               Show this message and exit.
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda conda-requirements --help")]]] -->

```bash
$ pyproject2conda conda-requirements --help
Usage: pyproject2conda conda-requirements [OPTIONS] [PATH_CONDA] [PATH_PIP]

  Create requirement files for conda and pip.

  These can be install with, for example,

  conda install --file {path_conda} pip install -r {path_pip}

Options:
  -e, --extra TEXT     Extra depenedencies. Can specify multiple times for
                       multiple extras.
  -i, --isolated TEXT  Isolated dependencies (under
                       [tool.pyproject2conda.isolated-dependencies]).  Can
                       specify multiple times.
  -p, --python TEXT    if flag passed without options, include python spec
                       from pyproject.toml in output.  If value passed, use
                       this value of python in the output
  -c, --channel TEXT   conda channel.  Can specify. Overrides
                       [tool.pyproject2conda.channels]
  -f, --file PATH      input pyproject.toml file
  --prefix TEXT        set conda-output=prefix + 'conda.txt', pip-
                       output=prefix + 'pip.txt'
  --prepend-channel
  --help               Show this message and exit.
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda json --help")]]] -->

```bash
$ pyproject2conda json --help
Usage: pyproject2conda json [OPTIONS]

  Create json representation.

  Keys are: "dependencies": conda dependencies. "pip": pip dependencies.
  "channels": conda channels.

Options:
  -e, --extra TEXT     Extra depenedencies. Can specify multiple times for
                       multiple extras.
  -i, --isolated TEXT  Isolated dependencies (under
                       [tool.pyproject2conda.isolated-dependencies]).  Can
                       specify multiple times.
  -p, --python TEXT    if flag passed without options, include python spec
                       from pyproject.toml in output.  If value passed, use
                       this value of python in the output
  -c, --channel TEXT   conda channel.  Can specify. Overrides
                       [tool.pyproject2conda.channels]
  -f, --file PATH      input pyproject.toml file
  -o, --output PATH    File to output results
  --help               Show this message and exit.
```

<!-- [[[end]]] -->

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
