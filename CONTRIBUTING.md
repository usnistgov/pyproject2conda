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

- Optionally install [pre-commit] hooks with

  ```bash
  just pre-commit install
  ```

  You can instead use [prek].

- Create a branch for local development:

  ```bash
  git checkout -b name-of-your-bugfix-or-feature
  ```

- When you're done making changes, check that your changes pass the pre-commit
  checks: tests.

  ```bash
  just pre-commit run [--all-files]
  ```

  To run tests, use:

  ```bash
  just test
  ```

  To test against multiple python versions, use [nox]:

  ```bash
  just test-all
  ```

- Create changelog fragment. See [scriv] for more info.

  ```bash
  just scriv-create --edit
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

## Using [just] as task runner

The project includes a `justfile` to be invoked using [just] to simplify common
tasks. Run `just` with no options to see available commands. Just can be
installed using:

```bash
uv tool install rust-just
```

## Using nox

This project makes extensive use of [nox] to automate testing, type checking,
documentation creation, etc. To see all nox session, run:

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

### Update/lock/sync requirements

The project is setup to create `environment.yaml` and `requirement.txt` files
from `pyproject.toml`. This can be done using:

```bash
just lock/sync
```

This runs `uv lock` and update requirements files. Pass `-upgrade/-U` to upgrade
requirements.

## ipykernel

The environments created by nox `dev`, or running `just install-kernel`, will
try to add meaningful display names for ipykernel. These are installed at the
user level. To cleanup the kernels (meaning, removing installed kernels that
point to a removed environment), You can use the script
`tools/clean_kernelspec.py`:

```bash
python tools/clean_kernelspec.py
```

### Development tools

The only required tool is [uv], but it highly recommended to also install
[just].

## Package version

Versioning is handled by the `project.version` variable in `pyproject.toml`. Use
`uv version --bump` to update the package version.

[commitizen]: https://github.com/commitizen-tools/commitizen
[conventional-style]: https://www.conventionalcommits.org/en/v1.0.0/
[just]: https://github.com/casey/just
[nox]: https://github.com/wntrblm/nox
[pre-commit]: https://pre-commit.com/
[prek]: https://github.com/j178/prek
[scriv]: https://github.com/nedbat/scriv
[uv]: https://github.com/astral-sh/uv
