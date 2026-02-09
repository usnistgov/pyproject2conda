<!-- markdownlint-disable MD041 -->

<!-- prettier-ignore-start -->
[![Repo][repo-badge]][repo-link]
[![Docs][docs-badge]][docs-link]
[![PyPI license][license-badge]][license-link]
[![PyPI version][pypi-badge]][pypi-link]
[![Conda (channel only)][conda-badge]][conda-link]
[![Code style: ruff][ruff-badge]][ruff-link]
[![uv][uv-badge]][uv-link]

<!--
  For more badges, see
  https://shields.io/category/other
  https://naereen.github.io/badges/
  [pypi-badge]: https://badge.fury.io/py/pyproject2conda
-->

[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff-link]: https://github.com/astral-sh/ruff
[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
[uv-link]: https://github.com/astral-sh/uv
[pypi-badge]: https://img.shields.io/pypi/v/pyproject2conda
[pypi-link]: https://pypi.org/project/pyproject2conda
[docs-badge]: https://img.shields.io/badge/docs-sphinx-informational
[docs-link]: https://pages.nist.gov/pyproject2conda/
[repo-badge]: https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff
[repo-link]: https://github.com/usnistgov/pyproject2conda
[conda-badge]: https://img.shields.io/conda/v/conda-forge/pyproject2conda
[conda-link]: https://anaconda.org/conda-forge/pyproject2conda
[license-badge]: https://img.shields.io/pypi/l/pyproject2conda?color=informational
[license-link]: https://github.com/usnistgov/pyproject2conda/blob/main/LICENSE
[changelog-link]: https://github.com/usnistgov/pyproject2conda/blob/main/CHANGELOG.md
[pre-commit]: https://pre-commit.com/

<!-- other links -->

[poetry2conda]: https://github.com/dojeda/poetry2conda

<!-- prettier-ignore-end -->

# `pyproject2conda`

A script to convert `pyproject.toml` dependencies to `environment.yaml` files.

## Overview

The main goal of `pyproject2conda` is to provide a means to keep all basic
dependency information, for both `pip` based and `conda` based environments, in
`pyproject.toml`. I often use a mix of pip and conda when developing packages,
and in my everyday workflow. Some packages just aren't available on both. If you
use poetry, I'd highly recommend [poetry2conda].

## Features

- Automatic creation of `environment.yaml`and `requirements.txt` files from
  `pyproject.toml`.
- Simple remapping of `pypi` package name to `conda` package name when creating
  `environment.yaml` files.
- [pre-commit] hooks to automatically keep dependency files up to data.

## Status

This package is actively used by the author, but is still very much a work in
progress. Please feel free to create a pull request for wanted features and
suggestions!

## Pre-commit hooks

`pyproject2conda` works with [pre-commit]. Hooks are available for the
`project`, `yaml`, and `requirements` subcommands described below:

```yaml
- repo: https://github.com/usnistgov/pyproject2conda
  rev: { version } # replace with current version
  hooks:
    - id: pyproject2conda-project
    - id: pyproject2conda-yaml
    - id: pyproject2conda-requirements
```

For `yaml` and `requirements`, you can override the default behavior (of
creating environment/requirement files from the `dependency-group` `dev`) by
passing in `args`. For example, you could use the following to create an
environment file with the extra `dev-complete`

```yaml
- repo: https://github.com/usnistgov/pyproject2conda
  rev: { version } # replace with current version
  hooks:
    - id: pyproject2conda-yaml
      args: ["-e", "dev-complete", "-o", "environment-dev.yaml", "-w", "force"]
```

Note that if called from pre-commit (detected by the presence of `PRE_COMMIT`
environment variable), the default is to set `--custom-command="pre-commit"`.
You can explicitly pass in `--custom-command` to override this.

## Installation

<!-- start-installation -->

Use one of the following to install `pyproject2conda`:

<!-- markdownlint-disable MD014 -->

```bash
$ pip/pipx/uvx install pyproject2conda
```

or

```bash
$ conda/condax install -c conda-forge pyproject2conda
```

[rich]: https://github.com/Textualize/rich
[shellingham]: https://github.com/sarugaku/shellingham
[typer]: https://github.com/fastapi/typer

If using pip, to install with [rich] and [shellingham] support, either install
them your self, or use:

```bash
$ pip/pipx/uvx install pyproject2conda[all]
```

<!-- markdownlint-enable MD014 -->

The conda-forge distribution of [typer] (which `pyproject2conda` uses) installs
[rich] and [shellingham] by default.

<!-- end-installation -->

## Example usage

### Basic usage

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog
import sys

sys.path.insert(0, ".")
from tools.cog_utils import wrap_command, get_pyproject, run_command, cat_lines
sys.path.pop(0)
]]] -->
<!-- [[[end]]] -->

Consider the `toml` file
[test-pyproject.toml](https://github.com/usnistgov/pyproject2conda/blob/main/tests/data/test-pyproject.toml).

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin=None, end="[tool.pyproject2conda]", begin_dot=False)]]] -->

```toml
[project]
name = "hello"
requires-python = ">=3.8,<3.11"
dependencies = [
"athing",                          #
"bthing",
"cthing; python_version < '3.10'",
]

[project.optional-dependencies]
test = [
"pandas", #
"pytest",
]
dev-extras = [ "matplotlib" ]
dev = [ "hello[dev-extras]", "hello[test]" ]
dist-pypi = [
# this is intended to be parsed with --skip-package option
"build",
"setuptools",
]

[tool.pyproject2conda.dependencies]
athing = { pip = true }
bthing = { skip = true, packages = "bthing-conda" }
cthing = { channel = "conda-forge" }
pytest = { channel = "conda-forge" }
matplotlib = { skip = true, packages = [
"additional-thing; python_version < '3.9'",
"conda-matplotlib",
] }
build = { channel = "pip" }

# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note the table `[tool.pyproject2conda.dependencies]`. This table takes as keys
the dependency names from `project.dependencies` or
`project.optional-dependencies`, and as values a mapping with keys:

- `pip`: if `true`, specify install via pip in `environment.yaml` file
- `skip`: if `true`, skip the dependency
- `channel`: conda-channel to use for this dependency
- `packages`: Additional packages to include in `environment.yaml` file

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

By default, the python version is not included in the resulting conda output. To
include the specification from `pyproject.toml`, use `--python-include infer`
option:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml --python-include infer")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml --python-include infer
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

Passing `--python="default"` will extract the python version from
`.python-version` file. Passing `--python` value `"lowest"` or `"highest"` will
extract the lowest or highest python version, respectively, from the
`project.classifiers` table of the `pyproject.toml` file. Using the option
`python="all"` in `pyproject.toml` will include all python versions in the
`project.classifiers` table.

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

You can also call with `python -m pyproject2conda`.

### Installing extras

Given the extra dependency:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable MD013 -->
<!-- [[[cog cat_lines(begin="[project.optional-dependencies]", end="[tool.pyproject2conda.dependencies]")]]] -->

```toml
# ...
[project.optional-dependencies]
test = [
"pandas", #
"pytest",
]
dev-extras = [ "matplotlib" ]
dev = [ "hello[dev-extras]", "hello[test]" ]
dist-pypi = [
# this is intended to be parsed with --skip-package option
"build",
"setuptools",
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

### Installing from `dependency-groups`

`pyproject2conda` also support the [PEP 735](https://peps.python.org/pep-0735/)
`dependency-groups` table. For example, if we have the follinging

<!-- prettier-ignore-start -->
<!-- markdownlint-disable MD013 -->
<!-- [[[cog cat_lines(begin="[dependency-groups]", end="[tool.pyproject2conda.dependencies]", path="tests/data/test-pyproject-groups.toml")]]] -->

```toml
# ...
[dependency-groups]
test = [ "pandas", "pytest" ]
dev-extras = [ "matplotlib" ]
dev = [ { include-group = "dev-extras" }, { include-group = "test" } ]
dist-pypi = [
# this is intended to be parsed with --skip-package option
"build",
"setuptools",
]
optional-opt1 = [ "hello[opt1]" ]
optional-opt2 = [ "hello[opt2]" ]
optional-all = [ "hello[all]" ]

# ...
```

<!-- [[[end]]] -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

Then, we can build a requirement file, specifying groups with `-g/--group` flag.

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject-groups.toml --group dev")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject-groups.toml --group dev
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

The advantage of using `dependency-groups` as opposed to
`package.optional-dependencies` is that they work for non-package projects, and
are not included in the metadata of distributed packages.

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

You can customize the command in the header with the `--custom-command` option.

### Usage within python

`pyproject2conda` can also be used within python:

```pycon
>>> from pyproject2conda.requirements import ParseDepends
>>> p = ParseDepends.from_path("./tests/data/test-pyproject.toml")

# Basic environment
>>> print(p.to_conda_yaml(python_include="infer").strip())
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
channels = [ 'conda-forge' ]
# these are the same as the default values of `p2c project`
template-python = "py{py}-{env}"
template = "{env}"
style = "yaml"
# options
python = [ "3.10" ]
# Note that this is relative to the location of pyproject.toml
user-config = "config/userconfig.toml"
# These environments will be created with the package, package dependencies, and
# dependencies from groups or extras with environment name so the below is the
# same as
#
# [tool.pyproject2conda.envs.test]
# extras-or-groups = "test"
#
default-envs = [ "dev", "dist-pypi", "test" ]

[tool.pyproject2conda.envs.base]
style = [ "requirements" ]

# This will have no extras or groups
#
# A value of `extras = true` will would be equivalent to
# passing extras-or-groups = <env-name>
[tool.pyproject2conda.envs."test-extras"]
extras = [ "test" ]
style = [ "requirements", "yaml" ]

[[tool.pyproject2conda.overrides]]
envs = [ "dist-pypi", 'test-extras' ]
skip-package = true

[[tool.pyproject2conda.overrides]]
envs = [ "test", "test-extras" ]
python = [ "3.10", "3.11" ]
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note that specifying channels at the command line overrides
`tool.pyproject2conda.channels`.

You can also specify environments without the package dependences (those under
`project.dependencies`) by passing the `--skip-package` flag. This is useful for
defining environments for build, etc, that do not require the package be
installed. For example:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin="dist-pypi = [", end="[tool.pyproject2conda]")]]] -->

```toml
# ...
dist-pypi = [
# this is intended to be parsed with --skip-package option
"build",
"setuptools",
]

[tool.pyproject2conda.dependencies]
athing = { pip = true }
bthing = { skip = true, packages = "bthing-conda" }
cthing = { channel = "conda-forge" }
pytest = { channel = "conda-forge" }
matplotlib = { skip = true, packages = [
"additional-thing; python_version < '3.9'",
"conda-matplotlib",
] }
build = { channel = "pip" }

# ...
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

These can be accessed using either of the following:

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("pyproject2conda yaml -f tests/data/test-pyproject.toml -e dist-pypi --skip-package")]]] -->

```bash
$ pyproject2conda yaml -f tests/data/test-pyproject.toml -e dist-pypi --skip- \
    package
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
>>> from pyproject2conda.requirements import ParseDepends
>>> p = ParseDepends.from_path("./tests/data/test-pyproject.toml")

# Basic environment
>>> print(p.to_conda_yaml(extras="dist-pypi", skip_package=True).strip())
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
channels = [ 'conda-forge' ]
# these are the same as the default values of `p2c project`
template-python = "py{py}-{env}"
template = "{env}"
style = "yaml"
# options
python = [ "3.10" ]
# Note that this is relative to the location of pyproject.toml
user-config = "config/userconfig.toml"
# These environments will be created with the package, package dependencies, and
# dependencies from groups or extras with environment name so the below is the
# same as
#
# [tool.pyproject2conda.envs.test]
# extras-or-groups = "test"
#
default-envs = [ "dev", "dist-pypi", "test" ]

[tool.pyproject2conda.envs.base]
style = [ "requirements" ]

# This will have no extras or groups
#
# A value of `extras = true` will would be equivalent to
# passing extras-or-groups = <env-name>
[tool.pyproject2conda.envs."test-extras"]
extras = [ "test" ]
style = [ "requirements", "yaml" ]

[[tool.pyproject2conda.overrides]]
envs = [ "dist-pypi", 'test-extras' ]
skip-package = true

[[tool.pyproject2conda.overrides]]
envs = [ "test", "test-extras" ]
python = [ "3.10", "3.11" ]
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

run through the command `pyproject2conda project` (or `p2c project`):

<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("p2c project -f tests/data/test-pyproject.toml --dry ", wrapper="bash", bounds=(None, 45))]]] -->

```bash
$ p2c project -f tests/data/test-pyproject.toml --dry
# --------------------
# Creating requirements base.txt
athing
bthing
cthing; python_version < "3.10"
# --------------------
# Creating requirements test-extras.txt
pandas
pytest
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
# Creating yaml py310-dev.yaml
channels:
  - conda-forge
dependencies:
  - python=3.10
  - bthing-conda
  - conda-forge::pytest
  - conda-matplotlib
  - pandas
  - pip
  - pip:
      - athing
# --------------------
# Creating yaml py310-dist-pypi.yaml
channels:
  - conda-forge
dependencies:
  - python=3.10
  - setuptools

 ...
```

<!-- [[[end]]] -->

Note that here, we have used the `--dry` option to just print the output. In
production, you'd omit this flag, and files according to `--template` and
`--template-python` would be used.

The options under `[tool.pyproject2conda]` follow the command line options. For
example, specify `template-python = ...` in the config file instead of passing
`--template-python`. You can optionally replace all dashes with underscores in
config file option names, but this will be deprecated in future versions. To
specify an environment, you can either use the
`[tool.pyproject.envs."environment-name"]` method, or, if the environment is the
same as an `project.optional-dependencies` or `dependency-groups`, you can just
specify it under `tool.pyproject2conda.default-envs`:

```toml
[tool.pyproject2conda]
# ...
default-envs = ["test"]

```

is equivalent to

```toml
[tool.pyproject2conda.envs.test]
extras = ["tests"]

```

To specify a conda environment (`yaml`) file, pass `style = "yaml"` (the
default). To specify a requirements file, pass `style = "requirements"`. You can
specify both to make both.

Options in a given `tool.pyproject2conda.envs."environment-name"` section
override those at the `tool.pyproject2conda` level. So, for example:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(begin='[tool.pyproject2conda.envs."test-extras"]', end='[[tool.pyproject2conda.overrides]]', begin_dot=False)]]] -->

```toml
# ...
[tool.pyproject2conda.envs."test-extras"]
extras = [ "test" ]
style = [ "requirements", "yaml" ]

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
Note that each "overrides" table must specify the options to be overridden, and
the environments that these overrides apply to. Also, note that subsequent
overrides override previous overrides/options (last option wins).

So in all, options are picked up, in order, from the overrides list, then the
environment definition, and finally, from the default options.

You can also define "user defined" configurations. This can be done through the
option `--user-config`. This allows you to define your own environments outside
of the (most likely source controlled) `pyproject.toml` file. For example, we
have the option `user-config=config/userconfig.toml`.

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog cat_lines(path="./tests/data/config/userconfig.toml", begin=None, end=None)]]] -->

```toml
[tool.pyproject2conda.envs."user-dev"]
extras-or-groups = [ "dev", "dist-pypi" ]
deps = [ "extra-dep" ]
reqs = [ "extra-req" ]
name = "hello"
```

<!-- [[[end]]] -->
<!-- prettier-ignore-end -->

Note that the full path of this file is note that the path of the `user-config`
file is relative to them`pyproject.toml` file. So, if the `pyproject.toml` file
is at `a/path/pyproject.toml`, the path of user configuration files will be
`a/path/config/userconfig.toml`. We then can run the following:

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD013 -->
<!-- [[[cog run_command("p2c project -f tests/data/test-pyproject.toml --dry --envs user-dev", wrapper="bash")]]] -->

```bash
$ p2c project -f tests/data/test-pyproject.toml --dry --envs user-dev
# --------------------
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

See
[command line interface documentation](https://pages.nist.gov/pyproject2conda/reference/cli.html#)
for details on the commands and options.

<!-- markdownlint-disable MD013 -->
<!-- prettier-ignore-start -->
<!-- [cog
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

] -->

<!-- [end] -->
<!-- prettier-ignore-end -->

<!-- markdownlint-enable MD013 -->

## Related work

The application `pyproject2conda` is used in the development of the following
packages:

- [`cmomy`](https://github.com/usnistgov/cmomy)
- [`thermoextrap`](https://github.com/usnistgov/thermoextrap)
- [`tmmc-lnpy`](https://github.com/usnistgov/tmmc-lnpy)
- [`module-utilities`](https://github.com/usnistgov/module-utilities)
- [`analphipy`](https://github.com/conda-forge/analphipy-feedstock)
- `pyproject2conda` itself!

<!-- end-docs -->

## Documentation

See the [documentation][docs-link] for a look at `pyproject2conda` in action.

## What's new?

See [changelog][changelog-link].

## License

This is free software. See [LICENSE][license-link].

## Contact

The author can be reached at <wpk@nist.gov>.

## Credits

This package was created using
[Cookiecutter](https://github.com/audreyr/cookiecutter) with the
[usnistgov/cookiecutter-nist-python](https://github.com/usnistgov/cookiecutter-nist-python)
template.

<!--  LocalWords:  conda subcommands
 -->
