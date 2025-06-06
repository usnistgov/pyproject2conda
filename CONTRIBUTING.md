# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

<!-- prettier-ignore-start -->
[issues]: https://github.com/usnistgov/pyproject2conda/issues
<!-- prettier-ignore-end -->

### Report Bugs

[Report bugs at here][issues]

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

This project could always use more documentation, whether as part of the
official docs, in docstrings, or even on the web in blog posts, articles, and
such.

### Submit Feedback

The best way to send feedback is to [file an issue][issues].

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are
  welcome!

## Making a contribution

Ready to contribute? Here's how to make a contribution.

- Fork the repo on GitHub.

- Clone your fork locally:

  ```bash
  git clone git@github.com:your_name_here/pyproject2conda.git
  ```

  If the repo includes submodules, you can add them either with the initial
  close using:

  ```bash
  git clone --recursive-submodules git@github.com:your_name_here/pyproject2conda.git
  ```

  or after the clone using

  ```bash
  cd pyproject2conda
  git submodule update --init --recursive
  ```

- Create development environment. See [](#setup-development-environment) for
  details.

- Initiate [pre-commit] with:

  ```bash
  pre-commit install
  ```

  To update the recipe, periodically run:

  ```bash
  pre-commit autoupdate
  ```

  If recipes change over time, you can clean up old installs with:

  ```bash
  pre-commit gc
  ```

- Create a branch for local development:

  ```bash
  git checkout -b name-of-your-bugfix-or-feature
  ```

  Now you can make your changes locally. Alternatively, we recommend using
  [git-flow].

- When you're done making changes, check that your changes pass the pre-commit
  checks: tests.

  ```bash
  pre-commit run [--all-files]
  ```

  To run tests, use:

  ```bash
  pytest
  ```

  To test against multiple python versions, use [nox]:

  ```bash
  nox -s test
  ```

- Create changelog fragment. See [scriv] for more info.

  ```bash
  scriv create --edit
  ```

- Commit your changes and push your branch to GitHub:

  ```bash
  git add .
  git commit -m "Your detailed description of your changes."
  git push origin name-of-your-bugfix-or-feature
  ```

  Note that the pre-commit hooks will force the commit message to be in the
  [conventional style][conventional-style]. To assist this, you may want to
  commit using [commitizen].

  ```bash
  cz commit
  ```

- Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

- The pull request should include tests.
- If the pull request adds functionality, the docs should be updated. Put your
  new functionality into a function with a docstring, and add the feature to the
  list in `CHANGELOG.md`. You should use [scriv] for this.
- The pull request should work for all supported python versions.

<!-- start-tutorial -->

## Using [pre-commit]

It is highly recommended to enable [pre-commit]. See
[](#setup-development-environment) for installation instructions. To install the
pre-commit hooks, run:

```bash
pre-commit install
```

This will enable a variety of code-checkers (linters) when you add a file to
commit. Alternatively, you can run the hooks over all files using:

```bash
pre-commit run --all-files
```

You can also run [pre-commit] on all files via nox using:

```bash
nox -s lint
```

## Using nox

This project makes extensive use of [nox] to automate testing, type checking,
documentation creation, etc. One downside of using [tox] with this particular
workflow is the need for multiple scripts, while with [nox], most everything is
self contained in the file `noxfile.py`. [nox] also allows for a mix of [conda]
and [virtualenv] environments.

### Installing interpreters for virtualenv creation

If using virtualenvs across multiple python versions (e.g., `test`, `typecheck`,
etc), you'll need to install python interpreters for each version. If using
[pyenv], you should be good to go.

Instead of using [pyenv], I use [uv] to manage python versions. For example:

```bash
uv python install python3.12
```

I also set the global [uv] config file (`~/.config/uv/uv.toml` on mac and linux)
to use only managed python:

```toml
python-preference = "only-managed"

```

[nox] is setup to automatically work with [uv]. Note that the python interpreter
may need to be installed before it can be used with [nox]

### Nox session options

To see all nox session, run:

```bash
nox --list
```

To simplify passing options to underlying commands, the options to a particular
nox session use `+` instead of `-` for options. For example, pass options to
pytest, use:

```bash
nox -s test -- ++test-opts -x -v
```

Using `+` for the session option `++test-opts` means we don't have to escape
`-x` or `-v`. To see all options:

```bash
nox -- ++help/+h
```

Note that these options should be passed _after_ `--`. For example, to build and
open the documentation, run:

```bash
nox -s docs -- +d build open
```

### Creating environment.yaml/requirement.txt files

The project is setup to create `environment.yaml` and `requirement.txt` files
from `pyproject.toml`. This can be done using:

```bash
just requirements
```

This uses [pyproject2conda] to create the requirement files. Note that all
requirement files are under something like
`requirements/py{version}-{env-name}.yaml` (conda environment) or
`requirements/{env-name}.txt` (virtual environment).

Additionally, requirement files for virtualenvs (e.g., `requirements.txt` like
files) will be "locked" using `uv pip compile` from [uv]. These files are placed
under `requirements/lock`. This uses the script `tools/requirements_lock.py`.
The `uv.lock` file will also be updated. To upgrade locked requirements pass
option `--upgrade/-U`.

## Using [just] as task runner

The project includes a `justfile` to be invoked using [just] to simplify common
tasks. Run `just` with no options to see available commands.

## ipykernel

The environments created by nox `dev`, or running `just install-kernel`, will
try to add meaningful display names for ipykernel. These are installed at the
user level. To cleanup the kernels (meaning, removing installed kernels that
point to a removed environment), You can use the script
`tools/clean_kernelspec.py`:

```bash
python tools/clean_kernelspec.py
```

## Building the docs

We use [nox] to isolate the documentation build. Specific tasks can be run with

```bash
nox -s docs -- +d [commands]
```

where commands can be one of:

- clean : remove old doc build
- build/html : build html documentation
- spelling : check spelling
- linkcheck : check the links
- release : make pages branch for documentation hosting (using
  [ghp-import](https://github.com/c-w/ghp-import))
- livehtml : Live documentation updates
- open : open the documentation in a web browser
- serve : Serve the created documentation webpage (Need this to view javascript
  in created pages).

## Testing with nox

The basic command is:

```bash
nox -s test -- [++test-opts] [++no-cov]
```

where you can pass in additional pytest options via `++test-opts`. For example:

```bash
nox -s test -- ++test-opts -x -v
```

Use session `test-conda` to test under a conda environment.

Note that by default, these will install an isolated copy of the package, as
apposed to installing with `pip install -e . --no-deps`. This is similar to how
[tox] works. This uses the nox session `build` behind the scenes. This should
therefore be a fast operation.

## Building distribution for conda

[grayskull]: https://github.com/conda/grayskull

For the most part, we use [grayskull] to create the conda recipe. However, I've
had issues getting it to play nice with `pyproject.toml` for some of the 'extra'
variables. So, we use grayskull to build the majority of the recipe, and append
the file `config/recipe-append.yaml`. For some edge cases (install name
different from package name, etc), you'll need to manually edit this file to
create the final recipe.

To build the conda recipe using [grayskull]:

```bash
nox -s conda-recipe -- ++conda-recipe [recipe, recipe-full]
```

To build the conda distribution:

```bash
nox -s conda-build -- ++conda-build [build,clean]
```

To upload the recipe, you'll need to run an external command like:

```bash
nox -s conda-build -- ++conda-build-run "anaconda upload PATH-TO-TARBALL"
```

## Building distribution for pypi

The basic command is:

```bash
nox -s build
```

To upload the pypi distribution:

```bash
nox -s publish -- +p [release, test]
```

- test : upload to testpypi
- release : upload to pypi

## Testing pypi or conda installs

Run:

```bash
nox -s testdist-pypi -- ++version [version]
```

to test a specific version from pypi and

```bash
nox -s testdist-conda -- ++version [version]
```

to do likewise from conda.

## Testing notebooks with [nbval]

To test notebooks expected output using [nbval], run

```bash
nox -s test-notebook
```

## Type checking

Run:

```bash
nox -s typecheck -- +m [commands] [options]
```

Note that the repo is setup to use a single install of [mypy] and [pyright]. The
script `tools/typecheck.py` will run the checkers via [uvx] and point the
checker to the appropriate python executable.

## Setup development environment

This project uses a host of tools to (hopefully) make development easier. We
recommend installing some of these tools system wide. For this, we recommend
using [uv] (or [pipx] or [condax]). We mostly use [uv], but the choice is yours.
For conda, we recommend actually using [mamba]. Alternatively, you can setup
`conda` to use the faster `mamba` solver. [See here][conda-fast-setup] for
details.

### Create development environment with conda

To install a development environment using [conda]/[mamba] run:

```bash
conda env create -n {env-name} -f requirements/py{version}-dev.yaml
conda activate {env-name}
pip install -e . --no-deps
```

### Create development environment with uv/pip

The easiest way to create an development environment, if using `uv.lock`
mechanism is:

```bash
uv sync
```

If the project does not use `uv.lock`, or you don't want to use uv to manage
your environment, then use one of the following:

```bash
# using venv
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/lock/py{version}-dev.txt
python -m pip install -e . --no-deps
# using uv
uv venv --python 3.11 .venv
uv pip sync requirements/lock/py{version}-dev.txt
```

Note that if the project is setup to use `uv.lock` but you'd like to use one of
the above, you may have to run something like:

```bash
uv export --dev > requirements.txt
```

and use this requirement file in the commands above.

If the project includes an ipython kernel, you can install it with:

```bash
just install-kernel
```

Alternatively, you can simply use:

```bash
nox -s dev
```

which will create a virtual environment under `.venv`. If you go this route, you
may want to use something like
[zsh-autoenv](https://github.com/Tarrasch/zsh-autoenv) (if using zsh shell) or
[autoenv](https://github.com/hyperupcall/autoenv) (if using bash) to auto
activate the development environment when in the parent directory.

### Development tools

The only required tool is [uv], but it highly recommended to also install
[just]. Other tools used are:

- [pre-commit]
- [just]
- [scriv]
- [pyright]
- [cruft]
- [commitizen]

which can be installed using:

```bash
uv tool install pre-commit
```

Note that the repo is setup to automatically use [uvx] for many of these tools.
Behind the scenes, the `justfile` and `noxfile.py` will invoke [uvx] with
constraints from `requirements/lock/uvx-tools.txt`. This will run the tool with
with the proper version. Note that if the tool is already installed with the
proper version, [uvx] will use it. This prevents having to install a bunch of
tooling in the "dev" environment, and also avoid creating a bunch of throw away
[nox] environments.

## Package version

[hatch-vcs]: https://github.com/ofek/hatch-vcs

Versioning is handled with [hatch-vcs]. The package version is set by the git
tag. For convenience, you can override the version with nox setting
`++version ...`. This is useful for updating the docs, etc.

Note that the version in a given environment/session can become stale. The
easiest way to update the installed package version version is to reinstall the
package. This can be done using the following:

```bash
# using pip
pip install -e . --no-deps
# using uv
uv pip install -e . --no-deps
```

To do this in a given session, use:

```bash
nox -s {session} -- +P/++update-package
```

[commitizen]: https://github.com/commitizen-tools/commitizen
[conda-fast-setup]:
  https://www.anaconda.com/blog/a-faster-conda-for-a-growing-community
[conda]: https://docs.conda.io/en/latest/
[condax]: https://github.com/mariusvniekerk/condax
[conventional-style]: https://www.conventionalcommits.org/en/v1.0.0/
[cruft]: https://github.com/cruft/cruft
[git-flow]: https://github.com/nvie/gitflow
[just]: https://github.com/casey/just
[mamba]: https://github.com/mamba-org/mamba
[mypy]: https://github.com/python/mypy
[nbval]: https://github.com/computationalmodelling/nbval
[nox]: https://github.com/wntrblm/nox
[pipx]: https://github.com/pypa/pipx
[pre-commit]: https://pre-commit.com/
[pyenv]: https://github.com/pyenv/pyenv
[pyproject2conda]: https://github.com/wpk-nist-gov/pyproject2conda
[pyright]: https://github.com/microsoft/pyright
[scriv]: https://github.com/nedbat/scriv
[tox]: https://tox.wiki/en/latest/
[uv]: https://github.com/astral-sh/uv
[uvx]: https://docs.astral.sh/uv/guides/tools/
[virtualenv]: https://virtualenv.pypa.io/en/latest/
