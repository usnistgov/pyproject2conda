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
[repo-link]: https://github.com/usnistgov/pyproject2conda
[conda-badge]: https://img.shields.io/conda/v/conda-forge/pyproject2conda
[conda-link]: https://anaconda.org/conda-forge/pyproject2conda
[license-badge]: https://img.shields.io/pypi/l/cmomy?color=informational
[license-link]: https://github.com/usnistgov/pyproject2conda/blob/main/LICENSE

<!-- other links -->

[poetry2conda]: https://github.com/dojeda/poetry2conda

# `pyproject2conda`

A script to convert `pyproject.toml` dependencies to `environemnt.yaml` files.

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
conda install -c conda-forge pyproject2conda
```

## Example usage

### Basic usage

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog
import subprocess
import shlex
from functools import lru_cache

import textwrap
def wrap_command(cmd):

    cmd = textwrap.wrap(cmd.strip(), 80)

    if len(cmd) > 1:
        cmd[:-1] = [c + " \\" for c in cmd[:-1]]
        cmd[1:]  = [" "*4 + c for c in cmd[1:]]

    return "\n".join(cmd)

@lru_cache
def get_pyproject(path):
    with open(path, 'r') as f:
        lines = [_.strip() for _ in f]
    return lines

def run_command(cmd, wrapper="bash", include_cmd=True, bounds=None):
    args = shlex.split(cmd)
    output = subprocess.check_output(args)

    total = output.decode()

    if bounds is not None:
        total = total.split("\n")[bounds[0]:bounds[1]]
        if bounds[0] is not None:
            total = ["...\n"] + total
        if bounds[1] is not None:
            total = total + ["\n ...\n"]

        total = "\n".join(total)

    if include_cmd:
        cmd = wrap_command(cmd)

        total = f"$ {cmd}\n{total}"

    if wrapper:
        total = f"```{wrapper}\n"  + total + "```\n"

    print(total)

def cat_lines(
        path="tests/data/test-pyproject.toml",
        begin=None, end=None, begin_dot=None, end_dot=None,
    ):
    lines = get_pyproject(path)

    begin_dot = begin_dot or begin is not None
    end_dot = end_dot or end is not None

    if isinstance(begin, str):
        begin = lines.index(begin)
    if isinstance(end, str):
        end = lines.index(end)

    output = '\n'.join(lines[slice(begin, end)])

    if begin_dot:
        output = "# ...\n" +  output

    if end_dot:
        output = output + "\n# ..."

    output = "\n```toml\n" + output + "\n```\n"
    print(output)

]]] -->
<!-- [[[end]]] -->

Consider the `toml` file
[test-pyproject.toml](./tests/data/test-pyproject.toml).

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin=None, end="[project.optional-dependencies]", begin_dot=False)]]] -->

```toml
[project]
name = "hello"
requires-python = ">=3.8,<3.11"
dependencies = [
"athing", # p2c: -p # a comment
"bthing", # p2c: -s "bthing-conda"
"cthing; python_version < '3.10'", # p2c: -c conda-forge

]

# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note the comment lines `# p2c:...`. These are special tokens that
`pyproject2conda` will analyze. The basic options are:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("""python -c "from pyproject2conda.parser import _default_parser; _default_parser().parse_args(['--help'])" """, include_cmd=False, wrapper="bash")]]] -->
```bash
usage: -c [-h] [-c CHANNEL] [-p] [-s] [package ...]

Parser searches for comments '# p2c: [OPTIONS] CONDA-PACKAGES

positional arguments:
  package

options:
  -h, --help            show this help message and exit
  -c CHANNEL, --channel CHANNEL
                        Channel to add to the pyproject requirement
  -p, --pip             If specified, install pyproject dependency with pip
  -s, --skip            If specified skip pyproject dependency on this line
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

So, if we run the following, we get:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml
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
include the specification from `pyproject.toml`, use `--python-include` option:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml --python-include")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml --python-include
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

### Specify python version

To specify a specific value of python in the output, pass a value with:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml --python-include python=3.9")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml --python-include \
    python=3.9
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
`pyproject.toml` syntax `"...; python_version < 'some-version-number'"`. For is
parsed for both the pip packages and conda packages:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml --python-version 3.10")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml --python-version 3.10
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - pip
  - pip:
      - athing
```

<!-- [[[end]]] -->

It is common to want to specify the python version and include it in the
resulting environment file. You could, for example use:

<!-- markdownlint-disable MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml --python-version 3.10 --python-include python=3.10")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml --python-version 3.10 \
    --python-include python=3.10
channels:
  - conda-forge
dependencies:
  - python=3.10
  - bthing-conda
  - pip
  - pip:
      - athing
```

<!-- [[[end]]] -->
<!-- markdownlint-enable MD013 -->

Because this is common, you can also just pass the option `-p/--python`:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml --python 3.10")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml --python 3.10
channels:
  - conda-forge
dependencies:
  - python=3.10
  - bthing-conda
  - pip
  - pip:
      - athing
```

<!-- [[[end]]] -->

### Adding extra conda dependencies and pip requirements

You can also add additional conda and pip dependencies with the flags
`-d/--deps` and `-r/--reqs`, respectively. Adding the last example:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml -d dep -r req")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml -d dep -r req
channels:
  - conda-forge
dependencies:
  - bthing-conda
  - conda-forge::cthing
  - dep
  - pip
  - pip:
      - athing
      - req
```

<!-- [[[end]]] -->

These will also obey dependencies like `dep:python_version<={version}`. Pass the
flags multiple times to pass multiple dependencies.

### Command "aliases"

The name `pyproject2conda` can be a bit long to type. For this reason, the
package also ships with the alias `p2c`, which has the exact same functionality.
Additionally, the subcommands can be shortened to a unique match:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("p2c y -f tests/data/test-pyproject.toml --python 3.10")]]] -->

```bash
$ p2c y -f tests/data/test-pyproject.toml --python 3.10
channels:
  - conda-forge
dependencies:
  - python=3.10
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
<!-- [[[cog cat_lines(begin="[project.optional-dependencies]", end="[tool.pyproject2conda]")]]] -->

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
dev = ["hello[test]", "hello[dev-extras]"]
dist-pypi = [
# this is intended to be parsed with --no-base option
"setuptools",
"build", # p2c: -p

]

# ...
```

<!-- [[[end]]] -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

and running the following gives:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml -e test")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml -e test
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
```

<!-- [[[end]]] -->

`pyproject2conda` also works with self referenced dependencies:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml -e dev")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml -e dev
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
```

<!-- [[[end]]] -->

This also shows that `p2c` comments without dependencies are also parsed. To
comment out such lines, make sure `p2c` is preceded by `##`.

### Header in output

By default, `pyproject2conda` includes a header in most output files to note
that the files are auto generated. No header is included by default when writing
to standard output. To override this behavior, pass `--header/--noheader`:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml --header")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml --header
#
# This file is autogenerated by pyproject2conda
# with the following command:
#
#     $ pyproject2conda yaml -f tests/data/test-pyproject.toml --header
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
```

<!-- [[[end]]] -->

### Usage within python

`pyproject2conda` can also be used within python:

```pycon
>>> from pyproject2conda import PyProject2Conda
>>> p = PyProject2Conda.from_path("./tests/data/test-pyproject.toml")

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
  - conda-forge::pytest
  - pandas
  - pip
  - pip:
      - athing

```

### Configuration

`pyproject2conda` can be configured with a `[tool.pyproject2conda]` section in
`pyproject.toml`. To specify conda channels use:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin="[tool.pyproject2conda]", end=None)]]] -->

```toml
# ...
[tool.pyproject2conda]
channels = ['conda-forge']
# these are the same as the default values of `p2c project`
template_python = "py{py}-{env}"
template = "{env}"
style = "yaml"
# options
python = ["3.10"]
# Note that this is relative to the location of pyproject.toml
user_config = "config/userconfig.toml"
default_envs = ["test", "dev", "dist-pypi"]

[tool.pyproject2conda.envs."test-extras"]
extras = ["test"]
style = ["yaml", "requirements"]

[[tool.pyproject2conda.overrides]]
envs = ['test-extras', "dist-pypi"]
base = false

[[tool.pyproject2conda.overrides]]
envs = ["test", "test-extras"]
python = ["3.10", "3.11"]
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note that specifying channels at the command line overrides
`tool.pyproject2conda.channels`.

You can also specify environments without the base dependencies (those under
`project.dependencies`) by passing the `--no-base` flag. This is useful for
defining environments for build, etc, that do not require the package be
installed. For example:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin="dist-pypi = [", end="[tool.pyproject2conda]")]]] -->

```toml
# ...
dist-pypi = [
# this is intended to be parsed with --no-base option
"setuptools",
"build", # p2c: -p

]

# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

These can be accessed using either of the following:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml -e dist-pypi --no-base")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml -e dist-pypi --no-base
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
>>> p = PyProject2Conda.from_path("./tests/data/test-pyproject.toml")

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

### Creating multiple environments from `pyproject.toml`

`pyproject2conda` provides a means to create all needed environment/requirement
files in one go. We configure the environments using the `pyproject.toml` files
in the `[tool.pyproject2conda]` section. For example, example the configuration:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin="[tool.pyproject2conda]", end=None)]]] -->

```toml
# ...
[tool.pyproject2conda]
channels = ['conda-forge']
# these are the same as the default values of `p2c project`
template_python = "py{py}-{env}"
template = "{env}"
style = "yaml"
# options
python = ["3.10"]
# Note that this is relative to the location of pyproject.toml
user_config = "config/userconfig.toml"
default_envs = ["test", "dev", "dist-pypi"]

[tool.pyproject2conda.envs."test-extras"]
extras = ["test"]
style = ["yaml", "requirements"]

[[tool.pyproject2conda.overrides]]
envs = ['test-extras', "dist-pypi"]
base = false

[[tool.pyproject2conda.overrides]]
envs = ["test", "test-extras"]
python = ["3.10", "3.11"]
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

run through the command `pyproject2conda project` (or `p2c project`):

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("p2c project -f tests/data/test-pyproject.toml --dry", wrapper="bash", bounds=(None, 45))]]] -->

```bash
$ p2c project -f tests/data/test-pyproject.toml --dry
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
# Creating yaml py310-test.yaml
channels:
  - conda-forge
dependencies:
  - python=3.10
  - bthing-conda
  - conda-forge::pytest
  - pandas
  - pip
  - pip:
      - athing
# Creating yaml py311-test.yaml
channels:
  - conda-forge
dependencies:
  - python=3.11
  - bthing-conda
  - conda-forge::pytest
  - pandas
  - pip
  - pip:
      - athing
# Creating yaml py310-dev.yaml
channels:
  - conda-forge
dependencies:
  - python=3.10
  - bthing-conda

 ...
```

<!-- [[[end]]] -->

Note that here, we have used the `--dry` option to just print the output. In
production, you'd omit this flag, and files according to `--template` and
`--template-python` would be used.

The options under `[tool.pyproject2conda]` follow the command line options
(replace `-` with `_`). To specify an environment, you can either use the
`[tool.pyproject.envs."environment-name"]` method, or, if the environment is the
same as the "extras" name, you can just specify it under
`tool.pyproject2conda.default_envs`:

```toml
[tool.pyproject2conda]
# ...
default_envs = ["test"]

```

is equivalent to

```toml
[tool.pyproject2conda.envs.test]
extras = ["tests"]

```

To specify a conda environment (`yaml`) file, pass `style = "yaml"` (the
default). To specify a requirements file, pass `style = "requirements"`. You can
specify both to make both.

Options in a given `tool.pyproject2conda.envs."environemnt-name"` section
override those at the `tool.pyproject2conda` level. So, for example:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin='[tool.pyproject2conda.envs."test-extras"]', end='[[tool.pyproject2conda.overrides]]', begin_dot=False)]]] -->

```toml
# ...
[tool.pyproject2conda.envs."test-extras"]
extras = ["test"]
style = ["yaml", "requirements"]

# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

will override use the two styles instead of the default of `yaml`.

You can also override options for multiple environments using the
`[[tools.pyproject2conda.overrides]]` list. Just specify the override option(s)
and the environments to apply them to. For example, above we specify that the
base option is `False` for envs `test-extras` and `dist-pypi`, and that the
python version should be `3.10` and `3.11` for envs `test` and `test-extras`.

So in all, options are picked up, in order, from the environment definition,
then the overrides list, and finally, from the default options.

You can also define "user defined" configurations. This can be done through the
option `--user-config`. This allows you to define your own environments outside
of the (most likely source controlled) `pyproject.toml` file. For example, we
have the option `user_config=config/userconfig.toml`.

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(path="./tests/data/config/userconfig.toml", begin=None, end=None)]]] -->

```toml
[tool.pyproject2conda.envs."user-dev"]
extras = ["dev", "dist-pypi"]
deps = ["extra-dep"]
reqs = ["extra-req"]
name = "hello"
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note that the full path of this file is note that the path of the `user_conifg`
file is relative to them`pyproject.toml` file. So, if the `pyproject.toml` file
is at `a/path/pyproject.toml`, the path of user configuration files will be
`a/path/config/userconfig.toml`. We then can run the following:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("p2c project -f tests/data/test-pyproject.toml --dry --envs user-dev", wrapper="bash")]]] -->
```bash
$ p2c project -f tests/data/test-pyproject.toml --dry --envs user-dev
# Creating yaml py310-user-dev.yaml
name: hello
channels:
  - conda-forge
dependencies:
  - python=3.10
  - bthing-conda
  - conda-forge::pytest
  - conda-matplotlib
  - extra-dep
  - pandas
  - setuptools
  - pip
  - pip:
      - athing
      - build
      - extra-req
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

### CLI options

<!-- markdownlint-disable MD013 -->
<!-- prettier-ignore-start -->
<!-- [[[cog
  import os
  os.environ["P2C_RICH_CLICK_MAX_WIDTH"] = "90"

  run_command("pyproject2conda --help", wrapper="bash")

  cmds = [
    "list",
    "yaml",
    "requirements",
    "project",
    "conda-requirements",
    "json"
  ]

  for cmd in cmds:
    print(f"#### {cmd}\n")
    run_command(f"pyproject2conda {cmd} --help", wrapper="bash")

]]] -->
```bash
$ pyproject2conda --help

 Usage: pyproject2conda [OPTIONS] COMMAND [ARGS]...

╭─ Options ──────────────────────────────────────────────────────────────────────────────╮
│ --version      Show the version and exit.                                              │
│ --help         Show this message and exit.                                             │
╰────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────╮
│ conda-requirements  Create requirement files for conda and pip.                        │
│ json                Create json representation.                                        │
│ list                List available extras                                              │
│ project             Create multiple environment files from `pyproject.toml`            │
│                     specification.                                                     │
│ requirements        Create requirements.txt for pip dependencies.                      │
│ yaml                Create yaml file from dependencies and optional-dependencies.      │
╰────────────────────────────────────────────────────────────────────────────────────────╯

```

#### list

```bash
$ pyproject2conda list --help

 Usage: pyproject2conda list [OPTIONS]

 List available extras

╭─ Options ──────────────────────────────────────────────────────────────────────────────╮
│ --file     -f  PATH  input pyproject.toml file                                         │
│ --verbose  -v                                                                          │
│ --help               Show this message and exit.                                       │
╰────────────────────────────────────────────────────────────────────────────────────────╯

```

#### yaml

```bash
$ pyproject2conda yaml --help

 Usage: pyproject2conda yaml [OPTIONS]

 Create yaml file from dependencies and optional-dependencies.

╭─ Options ──────────────────────────────────────────────────────────────────────────────╮
│ --file                -f  PATH                input pyproject.toml file                │
│ --extra               -e  TEXT                Extra depenedencies. Can specify         │
│                                               multiple times for multiple extras.      │
│ --channel             -c  TEXT                conda channel.  Can specify. Overrides   │
│                                               [tool.pyproject2conda.channels]          │
│ --output              -o  PATH                File to output results                   │
│ --name                -n  TEXT                Name of conda env                        │
│ --python-include          TEXT                If flag passed without options, include  │
│                                               python spec from pyproject.toml in yaml  │
│                                               output. If value passed, use this value  │
│                                               (exactly) in the output. So, for         │
│                                               example, pass `--python-include          │
│                                               "python=3.8"`                            │
│ --python-version          TEXT                Python version to check `python_verion   │
│                                               <=> {python_version}` lines against.     │
│                                               That is, this version is used to limit   │
│                                               packages in resulting output. For        │
│                                               example, if have a line like `a-package; │
│                                               python_version < '3.9'`, Using           │
│                                               `--python-version 3.10` will not include │
│                                               `a-package`, while `--python-version     │
│                                               3.8` will include `a-package`.           │
│ --python              -p  TEXT                Python version. Passing `--python        │
│                                               {version}` is equivalent to passing      │
│                                               `--python-version={version}              │
│                                               --python-include=python{version}`. If    │
│                                               passed, this overrides values of passed  │
│                                               via `--python-version` and               │
│                                               `--python-include`.                      │
│ --base/--no-base                              Default is to include base               │
│                                               (project.dependencies) with extras.      │
│                                               However, passing `--no-base` will        │
│                                               exclude base dependencies. This is       │
│                                               useful to define environments that       │
│                                               should exclude base dependencies (like   │
│                                               build, etc) in pyproject.toml.           │
│ --sort/--no-sort                              Default is to sort the dependencies      │
│                                               (excluding `--python-include`). Pass     │
│                                               `--no-sort` to instead place             │
│                                               dependencies in order they are gathered. │
│ --header/--no-header                          If True (--header) include header line   │
│                                               in output. Default is to include the     │
│                                               header for output to a file, and not to  │
│                                               include header when writing to stdout.   │
│ --overwrite           -w  [check|force|skip]  What to do if output file exists.        │
│                                               (check): Create if missing. If output    │
│                                               exists and passed `--filename` is newer, │
│                                               recreate output, else skip. (skip): If   │
│                                               output exists, skip. (force): force:     │
│                                               force recreate output.                   │
│ --verbose             -v                                                               │
│ --deps                -d  TEXT                Additional conda dependencies.           │
│ --reqs                -r  TEXT                Additional pip requirements.             │
│ --help                                        Show this message and exit.              │
╰────────────────────────────────────────────────────────────────────────────────────────╯

```

#### requirements

```bash
$ pyproject2conda requirements --help

 Usage: pyproject2conda requirements [OPTIONS]

 Create requirements.txt for pip dependencies.

╭─ Options ──────────────────────────────────────────────────────────────────────────────╮
│ --extra               -e  TEXT                Extra depenedencies. Can specify         │
│                                               multiple times for multiple extras.      │
│ --file                -f  PATH                input pyproject.toml file                │
│ --output              -o  PATH                File to output results                   │
│ --base/--no-base                              Default is to include base               │
│                                               (project.dependencies) with extras.      │
│                                               However, passing `--no-base` will        │
│                                               exclude base dependencies. This is       │
│                                               useful to define environments that       │
│                                               should exclude base dependencies (like   │
│                                               build, etc) in pyproject.toml.           │
│ --sort/--no-sort                              Default is to sort the dependencies      │
│                                               (excluding `--python-include`). Pass     │
│                                               `--no-sort` to instead place             │
│                                               dependencies in order they are gathered. │
│ --header/--no-header                          If True (--header) include header line   │
│                                               in output. Default is to include the     │
│                                               header for output to a file, and not to  │
│                                               include header when writing to stdout.   │
│ --overwrite           -w  [check|force|skip]  What to do if output file exists.        │
│                                               (check): Create if missing. If output    │
│                                               exists and passed `--filename` is newer, │
│                                               recreate output, else skip. (skip): If   │
│                                               output exists, skip. (force): force:     │
│                                               force recreate output.                   │
│ --verbose             -v                                                               │
│ --reqs                -r  TEXT                Additional pip requirements.             │
│ --help                                        Show this message and exit.              │
╰────────────────────────────────────────────────────────────────────────────────────────╯

```

#### project

```bash
$ pyproject2conda project --help

 Usage: pyproject2conda project [OPTIONS]

 Create multiple environment files from `pyproject.toml` specification.

╭─ Options ──────────────────────────────────────────────────────────────────────────────╮
│ --file                -f  PATH                input pyproject.toml file                │
│ --envs                    TEXT                List of environments to build files for. │
│                                               Default to building all environments     │
│ --template                TEXT                Template for environments that do not    │
│                                               have a python version. Defaults to       │
│                                               `{env}`.                                 │
│ --template-python         TEXT                Template for environments that do have a │
│                                               python version. Defaults to              │
│                                               "py{py}-{env}". For example, with        │
│                                               `--template-python="py{py}-{env}"` and   │
│                                               `--python=3.8` and environment "dev",    │
│                                               output would be "py38-dev"               │
│                                               * {py} -> "38"                           │
│                                               * {py_version} -> "3.8"                  │
│                                               * {env} -> "dev"                         │
│ --sort/--no-sort                              Default is to sort the dependencies      │
│                                               (excluding `--python-include`). Pass     │
│                                               `--no-sort` to instead place             │
│                                               dependencies in order they are gathered. │
│ --header/--no-header                          If True (--header) include header line   │
│                                               in output. Default is to include the     │
│                                               header for output to a file, and not to  │
│                                               include header when writing to stdout.   │
│ --overwrite           -w  [check|force|skip]  What to do if output file exists.        │
│                                               (check): Create if missing. If output    │
│                                               exists and passed `--filename` is newer, │
│                                               recreate output, else skip. (skip): If   │
│                                               output exists, skip. (force): force:     │
│                                               force recreate output.                   │
│ --verbose             -v                                                               │
│ --dry/--no-dry                                If true, do a dry run                    │
│ --user-config             TEXT                Additional toml file to supply           │
│                                               configuration. This can be used to       │
│                                               override/add environment files for your  │
│                                               own use (apart from project env files).  │
│                                               The (default) value `infer` means to     │
│                                               infer the configuration from             │
│                                               `--filename`.                            │
│ --help                                        Show this message and exit.              │
╰────────────────────────────────────────────────────────────────────────────────────────╯

```

#### conda-requirements

```bash
$ pyproject2conda conda-requirements --help

 Usage: pyproject2conda conda-requirements [OPTIONS] [PATH_CONDA] [PATH_PIP]

 Create requirement files for conda and pip.
 These can be install with, for example,
 conda install --file {path_conda} pip install -r {path_pip}

╭─ Options ──────────────────────────────────────────────────────────────────────────────╮
│ --extra               -e  TEXT  Extra depenedencies. Can specify multiple times for    │
│                                 multiple extras.                                       │
│ --python-include          TEXT  If flag passed without options, include python spec    │
│                                 from pyproject.toml in yaml output. If value passed,   │
│                                 use this value (exactly) in the output. So, for        │
│                                 example, pass `--python-include "python=3.8"`          │
│ --python-version          TEXT  Python version to check `python_verion <=>             │
│                                 {python_version}` lines against. That is, this version │
│                                 is used to limit packages in resulting output. For     │
│                                 example, if have a line like `a-package;               │
│                                 python_version < '3.9'`, Using `--python-version 3.10` │
│                                 will not include `a-package`, while `--python-version  │
│                                 3.8` will include `a-package`.                         │
│ --python              -p  TEXT  Python version. Passing `--python {version}` is        │
│                                 equivalent to passing `--python-version={version}      │
│                                 --python-include=python{version}`. If passed, this     │
│                                 overrides values of passed via `--python-version` and  │
│                                 `--python-include`.                                    │
│ --channel             -c  TEXT  conda channel.  Can specify. Overrides                 │
│                                 [tool.pyproject2conda.channels]                        │
│ --file                -f  PATH  input pyproject.toml file                              │
│ --base/--no-base                Default is to include base (project.dependencies) with │
│                                 extras. However, passing `--no-base` will exclude base │
│                                 dependencies. This is useful to define environments    │
│                                 that should exclude base dependencies (like build,     │
│                                 etc) in pyproject.toml.                                │
│ --sort/--no-sort                Default is to sort the dependencies (excluding         │
│                                 `--python-include`). Pass `--no-sort` to instead place │
│                                 dependencies in order they are gathered.               │
│ --header/--no-header            If True (--header) include header line in output.      │
│                                 Default is to include the header for output to a file, │
│                                 and not to include header when writing to stdout.      │
│ --prefix                  TEXT  set conda-output=prefix + 'conda.txt',                 │
│                                 pip-output=prefix + 'pip.txt'                          │
│ --prepend-channel                                                                      │
│ --deps                -d  TEXT  Additional conda dependencies.                         │
│ --reqs                -r  TEXT  Additional pip requirements.                           │
│ --help                          Show this message and exit.                            │
╰────────────────────────────────────────────────────────────────────────────────────────╯

```

#### json

```bash
$ pyproject2conda json --help

 Usage: pyproject2conda json [OPTIONS]

 Create json representation.
 Keys are: "dependencies": conda dependencies. "pip": pip dependencies. "channels": conda
 channels.

╭─ Options ──────────────────────────────────────────────────────────────────────────────╮
│ --extra           -e  TEXT  Extra depenedencies. Can specify multiple times for        │
│                             multiple extras.                                           │
│ --python-include      TEXT  If flag passed without options, include python spec from   │
│                             pyproject.toml in yaml output. If value passed, use this   │
│                             value (exactly) in the output. So, for example, pass       │
│                             `--python-include "python=3.8"`                            │
│ --python-version      TEXT  Python version to check `python_verion <=>                 │
│                             {python_version}` lines against. That is, this version is  │
│                             used to limit packages in resulting output. For example,   │
│                             if have a line like `a-package; python_version < '3.9'`,   │
│                             Using `--python-version 3.10` will not include             │
│                             `a-package`, while `--python-version 3.8` will include     │
│                             `a-package`.                                               │
│ --channel         -c  TEXT  conda channel.  Can specify. Overrides                     │
│                             [tool.pyproject2conda.channels]                            │
│ --file            -f  PATH  input pyproject.toml file                                  │
│ --sort/--no-sort            Default is to sort the dependencies (excluding             │
│                             `--python-include`). Pass `--no-sort` to instead place     │
│                             dependencies in order they are gathered.                   │
│ --output          -o  PATH  File to output results                                     │
│ --base/--no-base            Default is to include base (project.dependencies) with     │
│                             extras. However, passing `--no-base` will exclude base     │
│                             dependencies. This is useful to define environments that   │
│                             should exclude base dependencies (like build, etc) in      │
│                             pyproject.toml.                                            │
│ --deps            -d  TEXT  Additional conda dependencies.                             │
│ --reqs            -r  TEXT  Additional pip requirements.                               │
│ --help                      Show this message and exit.                                │
╰────────────────────────────────────────────────────────────────────────────────────────╯

```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

<!-- markdownlint-enable MD013 -->
<!-- end-docs -->

## Documentation

See the [documentation][docs-link] for a look at `pyproject2conda` in action.

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

<!--  LocalWords:  conda subcommands
 -->
