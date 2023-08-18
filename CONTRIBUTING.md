# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at <https://github.com/wpk-nist-gov/pyproject2conda/issues>.

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

`pyproject2conda` could always use more documentation, whether as part of the
official `pyproject2conda` docs, in docstrings, or even on the web in blog
posts, articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at
<https://github.com/wpk-nist-gov/pyproject2conda/issues>.

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- Remember that this is a volunteer-driven project, and that contributions are
  welcome!

## Get Started

### Environment setup

[pipx]: https://github.com/pypa/pipx
[condax]: https://github.com/mariusvniekerk/condax
[mamba]: https://github.com/mamba-org/mamba
[conda-fast-setup]:
  https://www.anaconda.com/blog/a-faster-conda-for-a-growing-community
[pre-commit]: https://pre-commit.com/
[nox]: https://github.com/wntrblm/nox
[noxopt]: https://github.com/rmorshea/noxopt
[tox]: https://tox.wiki/en/latest/
[cruft]: https://github.com/cruft/cruft
[cog]: https://github.com/nedbat/cog
[git-flow]: https://github.com/nvie/gitflow
[scriv]: https://github.com/nedbat/scriv
[conventional-style]: https://www.conventionalcommits.org/en/v1.0.0/
[commitizen]: https://github.com/commitizen-tools/commitizen
[nb_conda_kernels]: https://github.com/Anaconda-Platform/nb_conda_kernels
[pyproject2conda]: https://github.com/wpk-nist-gov/pyproject2conda

This project uses a host of tools to (hopefully) make development easier. We
recommend installing some of these tools system wide. For this, we recommend
using either [pipx] or [condax]. We mostly use conda/condax, but the choice is
yours. For conda, we recommend actually using [mamba]. Alternatively, you can
setup `conda` to use the faster `mamba` solver. See [here][conda-fast-setup] for
details.

Additional tools are:

- [pre-commit]
- [nox] with [noxopt]
- [cruft]
- [scriv]
- [commitizen] (optional)
- [pyproject2conda] (optional)
- [cog] (optional)

These are setup using the following:

```console
condax/pipx install pre-commit
condax/pipx install cruft
condax/pipx install commitizen # optional
pipx install scriv
pipx install pyproject2conda # optional
condax/pipx install cogapp # optional
```

if using pipx, nox can be installed with:

```bash
pipx install nox
pipx inject nox ruamel.yaml
pipx inject nox noxopt
```

If using condax, you'll need to use:

```bash
condax install nox
condax inject nox ruamel.yaml
conda activate ~/.condax/nox
pip install noxopt
```

### Getting the repo

Ready to contribute? Here's how to set up `pyproject2conda` for local
development.

- Fork the `pyproject2conda` repo on GitHub.

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

- Create development environment. There are two options to create the
  development environment.

  - The recommended method is to use nox. First you'll need to create the
    environment files using:

    ```bash
    nox -e pyproject2conda
    ```

    Then run:

    ```bash
    nox -e dev
    ```

    This create a development environment located at `.nox/dev`.

  - Alternatively, you can create centrally located conda environmentment using
    the command:

    ```bash
    conda/mamba env create -n {env-name} -f environment/dev.yaml
    ```

    ```bash
    pip install -e . --no-deps
    ```

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

  Additionally, you should run the following:

  ```bash
  make pre-commit-lint-markdown
  make pre-commit-codespell
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

### Dependency management

We use [pyproject2conda] to handle conda `environment.yaml` files. This extracts
the dependencies from `pyproject.toml`. See [pyproject2conda] for info. To make
the `environment.yaml` files, run:

```bash
nox -s pyproject2conda -- [--pyproject2conda-force]
```

Where the option in brackets is optional.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

- The pull request should include tests.
- If the pull request adds functionality, the docs should be updated. Put your
  new functionality into a function with a docstring, and add the feature to the
  list in CHANGELOG.md. You should use [scriv] for this.
- The pull request should work for Python 3.8, 3.9, 3.10.

## ipykernel

The environments created by nox `dev` and `docs` will try to add meaningful
display names for ipykernel (assuming you're using [nb_conda_kernels])

## Building the docs

We use [nox] to isolate the documentation build. Specific tasks can be run with

```bash
nox -s docs -- -d [commands]
```

where commands can be one of:

- clean : remove old doc build
- build/html : build html documentation
- spelling : check spelling
- linkcheck : check the links
- symlink : rebuild symlinks from `examples` to `docs/examples`
- release : make pages branch for documentation hosting (using
  [ghp-import](https://github.com/c-w/ghp-import))
- livehtml : Live documentation updates
- open : open the documentation in a web browser

## Testing with nox

The basic command is:

```bash
nox -s test -- [--test-opts] [--no-cov]
```

where you can pass in additional pytest options (properly escaped) via
`--test-opts`. For example:

```bash
nox -s test -- --test-opts "'-v'"
# or
nox -s test -- --test-opts "\-v"
```

## Building distribution for conda

[grayskull]: https://github.com/conda/grayskull

For the most part, we use [grayskull] to create the conda recipe. However, I've
had issues getting it to play nice with `pyproject.toml` for some of the 'extra'
variables. So, we use grayskull to build the majority of the recipe, and append
the file `.recipe-append.yaml`. For some edge cases (install name different from
package name, etc), you'll need to manually edit this file to create the final
recipe.

The basic command is:

```bash
nox -s dist-conda -- -c [command]
```

Where `command` is one of:

- clean
- recipe : create recipe via [grayskull]
- build : build the distribution

To upload the recipe, you'll need to run an external command like:

```bash
nox -s dist-conda -- --dist-conda-run "anaconda upload PATH-TO-TARBALL"
```

## Building distribution for pypi

The basic command is:

```bash
nox -s dist-pypi -- -p [command]
```

where `command` is one of:

- clean : clean out old distribution
- build : build distribution (if specify only this, clean will be called first)
- testrelease : upload to testpypi
- release : upload to pypi

## Testing pypi or conda installs

Run:

```bash
nox -s testdist-pypi -- --version [version]
```

to test a specific version from pypi and

```bash
nox -s testdist-conda -- --version [version]
```

to to likewise from conda.

## Type checking

Run:

```bash
nox -s typing -- -m [commands] [options]
```

## Package version

[setuptools_scm]: https://github.com/pypa/setuptools_scm

Versioning is handled with [setuptools_scm].The package version is set by the
git tag. For convenience, you can override the version with nox setting
`--version ...`. This is useful for updating the docs, etc.

We use the `write_to` option to [setuptools_scm]. This stores the current
version in `_version.py`. Note that if you build the package (or, build docs
with the `--version` flag), this will overwrite information in `_version.py` in
the `src` directory. To refresh the version, run:

```bash
make version-scm
```

This scheme avoids having to install `setuptools-scm` (and `setuptools`) in each
environment.

## Notes on [nox]

One downside of using [tox] with this particular workflow is the need for
multiple scripts/makefiles, while with [nox], most everything is self contained
in the file `noxfile.py`. [nox] also is allows for a mix of conda and virtualenv
environments.

We use a mix of conda environments and virtualenv with nox. For example, for
building the distribution, we use virtualenv, while for development, the default
is to create a conda environment. To facilitate this, we need to let virtualenv
know where different python interpreters are. I've had trouble mixing pyenv with
conda. Instead, I use conda to create multiple invironments to hold different
python version:

```bash
$ for version in 3.8 3.9 3.10 3.11; do
    conda create -n test-${version} python=${version}
  done
```

To tell nox where these environments live, create the file `.noxconfig.toml`
with the following:

```toml
[nox.python]
paths = ["~/.conda/envs/test-3.*/bin"]

```

where `~/.conda/envs` should be replaced by whatever prefix you have setup on
your machine. The `noxfile.py` will add this to the search path for python
versions when creating virtualenvs. The file `.noxconfig.toml` should not be
tracked by git. There is also an example file `.noxconfig.example.toml` to get
you started.

## Serving the documentation

To view to documentation with js headers/footers, you'll need to serve them:

```bash
python -m http.server -d docs/_build/html
```

Then open the address `localhost:8000` in a webbrowser.
