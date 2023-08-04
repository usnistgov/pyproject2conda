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

<!-- [[[cog
import subprocess
import shlex

def run_command(cmd, wrapper="bash", include_cmd=True):
    args = shlex.split(cmd)
    output = subprocess.check_output(args)

    total = output.decode()
    if include_cmd:
        total = f"$ {cmd}\n{total}"

    if wrapper:
        total = f"\n```{wrapper}\n"  + total + "```\n"

    print(total)

def cat_lines(path="tests/test-pyproject.toml", begin=0, end=8, begin_dot=True, end_dot=True):
    with open(path, 'r') as f:
        lines = [line.rstrip() for line in f]

    output = '\n'.join(lines[slice(begin, end)])

    if begin_dot:
        output = "# ...\n" +  output

    if end_dot:
        output = output + "\n# ..."

    output = "\n```toml\n" + output + "\n```\n"
    print(output)
]]] -->
<!-- [[[end]]] -->

Consider the `toml` file [test-pyproject.toml](./tests/test-pyproject.toml).

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin=0, end=8, begin_dot=False)]]] -->

```toml
[project]
name = "hello"
requires-python = ">=3.8,<3.11"
dependencies = [
    "athing", # p2c: -p # a comment
    "bthing", # p2c: -s "bthing-conda"
    "cthing; python_version < '3.10'", # p2c: -c conda-forge

# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note the comment lines `# p2c:...`. These are special tokens that
`pyproject2conda` will analyze. The basic options are:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("""python -c "from pyproject2conda.parser import _default_parser; _default_parser().parse_args(['--help'])" """, include_cmd=False, wrapper="text")]]] -->

```text
usage: -c [-h] [-c CHANNEL] [-p] [-s] [package ...]

Parser searches for comments '# p2c: [OPTIONS]

positional arguments:
  package

options:
  -h, --help            show this help message and exit
  -c CHANNEL, --channel CHANNEL
                        Channel to add to the pyproject requirement
  -p, --pip             If specified, install dependency on pyproject
                        dependency (on this line) with pip
  -s, --skip            If specified skip pyproject dependency on this line
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

So, if we run the following, we get:

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

Note that other comments can be mixed in.

By default, the python version is not included in the resulting conda output. To
include the specification from pyproject.toml, use `-p/--python` option:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml --python-include")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml --python-include
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

To specify a specific value of python in the output, pass a value with:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml --python-include python=3.9")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml --python-include python=3.9
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

Note that this is for including python in the resulting environment file.

You can also constrain packages by the python version using the standard
pyproject.toml syntax `"...; python_version < 'some-version-number'"`. For is
parsed for for both the pip packages and conda packages:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml --python-version 3.10")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml --python-version 3.10
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - pip
  - pip:
      - athing
```

<!-- [[[end]]] -->

### Installing extras

Given the extra dependency:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable MD013 -->
<!-- [[[cog cat_lines(begin=9, end=22)]]] -->

```toml
# ...

[project.optional-dependencies]
test = [
    "pandas",
    "pytest", # p2c: -c conda-forge

]
dev-extras = [
    # p2c: -s "additional-thing; python_version < '3.9'" # this is an additional conda package
    ## p2c: -s "another-thing" # this will be skipped because of ## before p2c.
    "matplotlib", # p2c: -s conda-matplotlib

]
# ...
```

<!-- [[[end]]] -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

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

This also shows that `p2c` comments without dependencies are also parsed. To
comment out such lines, make sure `p2c` is preceded by `##`.

### Header in output

By default, `pyproject2conda` includes a header in most output files to note
that the files are auto generated. No header is included by default when writing
to standard output. To override this behavior, pass `--header/--noheader`:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml --header")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml --header
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
```

<!-- [[[end]]] -->

### Usage within python

`pyproject2conda` can also be used within python:

```pycon
>>> from pyproject2conda import PyProject2Conda
>>> p = PyProject2Conda.from_path("./tests/test-pyproject.toml")

# Basic environment
>>> print(p.to_conda_yaml(python_include="get").strip())
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

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin=30, end=None)]]] -->

```toml
# ...
[tool.pyproject2conda]
channels = ['conda-forge']
# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note that specifying channels at the comand line overrides
`tool.pyproject2conda.channels`.

You can also specify environments without the base dependencies (those under
`project.dependencies`) by passing the `--no-base` flag. This is useful for
defining environments for build, etc, that do not require the package be
installed. For example:

<!-- prettier-ignore-start -->
!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin=22, end=26)]]] -->

```toml
# ...
dev = ["hello[test]", "hello[dev-extras]"]
dist-pypi = [
    # this is intended to be parsed with --no-base option
    "setuptools",
# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

These can be accessed using either of the following:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/test-pyproject.toml -e dist-pypi --no-base")]]] -->

```bash
$ pyproject2conda yaml -f tests/test-pyproject.toml -e dist-pypi --no-base
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
>>> print(p.to_conda_yaml(extras='dist-pypi', include_base_dependencies=False).strip())
channels:
  - conda-forge
dependencies:
  - setuptools
  - pip
  - pip:
      - build

```

### CLI options

<!-- prettier-ignore-start -->
<!-- [[[cog run_command("pyproject2conda --help", wrapper="text")]]] -->

```text
$ pyproject2conda --help
Usage: pyproject2conda [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  conda-requirements  Create requirement files for conda and pip.
  json                Create json representation.
  list                List available extras
  requirements        Create requirements.txt for pip depedencies.
  yaml                Create yaml file from dependencies and...
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda list --help", wrapper="text")]]] -->

```text
$ pyproject2conda list --help
Usage: pyproject2conda list [OPTIONS]

  List available extras

Options:
  -f, --file PATH  input pyproject.toml file
  -v, --verbose
  --help           Show this message and exit.
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda yaml --help", wrapper="text")]]] -->

```text
$ pyproject2conda yaml --help
Usage: pyproject2conda yaml [OPTIONS]

  Create yaml file from dependencies and optional-dependencies.

Options:
  -e, --extra TEXT        Extra depenedencies. Can specify multiple times for
                          multiple extras.
  -c, --channel TEXT      conda channel.  Can specify. Overrides
                          [tool.pyproject2conda.channels]
  -f, --file PATH         input pyproject.toml file
  -n, --name TEXT         Name of conda env
  -o, --output PATH       File to output results
  --python-include TEXT   If flag passed without options, include python spec
                          from pyproject.toml in yaml output.  If value
                          passed, use this value (exactly) in the output. So,
                          for example, pass `--python-include "python=3.8"`
  --python-version TEXT   Python version to check `python_verion <=>
                          {python_version}` lines against.  That is, this
                          version is used to limit packages in resulting
                          output. For example, if have a line like
                          `a-package; python_version < '3.9'`, Using
                          `--python-version 3.10` will not include
                          `a-package`, while `--python-version 3.8` will
                          include `a-package`.
  --base / --no-base      Default is to include base (project.dependencies)
                          with extras. However, passing `--no-base` will
                          exclude base dependencies. This is useful to define
                          environments that should exclude base dependencies
                          (like build, etc) in pyproject.toml.
  --header / --no-header  If True (--header) include header line in output.
                          Default is to include the header for output to a
                          file, and not to include header when writing to
                          stdout.
  --help                  Show this message and exit.
```

<!-- [[[end]]] -->

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda requirements --help", wrapper="text")]]] -->

```text
$ pyproject2conda requirements --help
Usage: pyproject2conda requirements [OPTIONS]

  Create requirements.txt for pip depedencies.

Options:
  -e, --extra TEXT        Extra depenedencies. Can specify multiple times for
                          multiple extras.
  -f, --file PATH         input pyproject.toml file
  -o, --output PATH       File to output results
  --base / --no-base      Default is to include base (project.dependencies)
                          with extras. However, passing `--no-base` will
                          exclude base dependencies. This is useful to define
                          environments that should exclude base dependencies
                          (like build, etc) in pyproject.toml.
  --header / --no-header  If True (--header) include header line in output.
                          Default is to include the header for output to a
                          file, and not to include header when writing to
                          stdout.
  --help                  Show this message and exit.
```

<!-- [[[end]]] -->

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda conda-requirements --help", wrapper="text")]]] -->

```text
$ pyproject2conda conda-requirements --help
Usage: pyproject2conda conda-requirements [OPTIONS] [PATH_CONDA] [PATH_PIP]

  Create requirement files for conda and pip.

  These can be install with, for example,

  conda install --file {path_conda} pip install -r {path_pip}

Options:
  -e, --extra TEXT        Extra depenedencies. Can specify multiple times for
                          multiple extras.
  --python-include TEXT   If flag passed without options, include python spec
                          from pyproject.toml in yaml output.  If value
                          passed, use this value (exactly) in the output. So,
                          for example, pass `--python-include "python=3.8"`
  --python-version TEXT   Python version to check `python_verion <=>
                          {python_version}` lines against.  That is, this
                          version is used to limit packages in resulting
                          output. For example, if have a line like
                          `a-package; python_version < '3.9'`, Using
                          `--python-version 3.10` will not include
                          `a-package`, while `--python-version 3.8` will
                          include `a-package`.
  -c, --channel TEXT      conda channel.  Can specify. Overrides
                          [tool.pyproject2conda.channels]
  -f, --file PATH         input pyproject.toml file
  --base / --no-base      Default is to include base (project.dependencies)
                          with extras. However, passing `--no-base` will
                          exclude base dependencies. This is useful to define
                          environments that should exclude base dependencies
                          (like build, etc) in pyproject.toml.
  --header / --no-header  If True (--header) include header line in output.
                          Default is to include the header for output to a
                          file, and not to include header when writing to
                          stdout.
  --prefix TEXT           set conda-output=prefix + 'conda.txt', pip-
                          output=prefix + 'pip.txt'
  --prepend-channel
  --help                  Show this message and exit.
```

<!-- [[[end]]] -->

<!-- [[[cog run_command("pyproject2conda json --help", wrapper="text")]]] -->

```text
$ pyproject2conda json --help
Usage: pyproject2conda json [OPTIONS]

  Create json representation.

  Keys are: "dependencies": conda dependencies. "pip": pip dependencies.
  "channels": conda channels.

Options:
  -e, --extra TEXT       Extra depenedencies. Can specify multiple times for
                         multiple extras.
  --python-include TEXT  If flag passed without options, include python spec
                         from pyproject.toml in yaml output.  If value passed,
                         use this value (exactly) in the output. So, for
                         example, pass `--python-include "python=3.8"`
  --python-version TEXT  Python version to check `python_verion <=>
                         {python_version}` lines against.  That is, this
                         version is used to limit packages in resulting
                         output. For example, if have a line like
                         `a-package; python_version < '3.9'`, Using `--python-
                         version 3.10` will not include `a-package`, while
                         `--python-version 3.8` will include `a-package`.
  -c, --channel TEXT     conda channel.  Can specify. Overrides
                         [tool.pyproject2conda.channels]
  -f, --file PATH        input pyproject.toml file
  -o, --output PATH      File to output results
  --base / --no-base     Default is to include base (project.dependencies)
                         with extras. However, passing `--no-base` will
                         exclude base dependencies. This is useful to define
                         environments that should exclude base dependencies
                         (like build, etc) in pyproject.toml.
  --help                 Show this message and exit.
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

<!-- end-docs -->

<!-- ## Documentation -->

<!-- See the [documentation][docs-link] for a look at -->
<!-- `pyproject2conda` in action. -->

## License

This is free software. See [LICENSE][license-link].

## Related work

TBD

## Contact

The author can be reached at <wpk@nist.gov>.

## Credits

This package was created with
[Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[wpk-nist-gov/cookiecutter-pypackage](https://github.com/wpk-nist-gov/cookiecutter-pypackage)
Project template forked from
[audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage).
