<!-- markdownlint-disable MD024 -->
<!-- markdownlint-disable MD013 -->
<!-- prettier-ignore-start -->

# Changelog

Changelog for `pyproject2conda`

## Unreleased

[changelog.d]: https://github.com/usnistgov/pyproject2conda/tree/main/changelog.d

See the fragment files in [changelog.d]

<!-- prettier-ignore-end -->

<!-- markdownlint-enable MD013 -->

<!-- scriv-insert-here -->

## v0.19.0 — 2025-01-29

### Added

- Added pre-commit hooks `pyproject2conda-project`, `pyproject2conda-yaml`, and
  `pyproject2conda-requirements`.

### Changed

- Changed default of `--overwrite` to `force`. This simplifies using with
  `pre-commit`.
- `--commit-command` defaults to `pre-commit` when run under pre-commit

## v0.18.0 — 2025-01-24

### Added

- Can now specify current package in dependency-groups like with extras. For
  example, with:

```toml
[project]
name = "mypackage"
...

optional-dependencies.opt = [ "opt1" ]

[dependency-groups]
dev = [
  "pytest",
  "mypackage[opt]"
]
```

Will render optional dependencies from `opt` extra when using group `dev`

- Added flag `--pip-only` to treat all requirements as pip requirements in
  `environment.yaml` files. Closes #8

## v0.16.0 — 2024-12-31

### Changed

- Read default version from first found file, in order,
  `.python-version-default` and `.python-version`. This allows for "default"
  version being different from pinned version specifier, as the latter can be a
  range of python values.

## v0.15.0 — 2024-12-17

### Added

- Can now pass requirements for package with `--req/-r "-e ."` for example.

## v0.14.0 — 2024-12-16

### Added

- `--python` flag now accepts options `default`, `all`, `lowest`, and `highest`.
  `default` sets python to value found in `.python-version` file in current
  directory. Other options extract values entries of form
  `"Programming Language :: Python :: 3.10"'`, etc,from
  `pyproject.toml:project.classifiers` table.

  - `all`: All specified python version
  - `lowest`: Lowest python version
  - `highest`: Highest python version

- Added `--reqs-ext` and `--yaml-ext` options.

## v0.13.0 — 2024-11-04

### Changed

- Allow `overrides` for all options.
- `overrides` override environment options.

## v0.12.0 — 2024-11-04

### Removed

- Removed comments based (`# p2c: ...`) support. Specify changes with
  `tool.pyproject2conda.dependencies` table only. This greatly simplifies the
  code, and has become the primary way to use the `pyproject2conda`.

### Added

- Added [PEP 735](https://peps.python.org/pep-0735/) support. This includes
  adding option `--group` to the cli, and `groups` key to
  `tools.pyproject2conda.envs....` tables. There is also an option
  `--extra-or-group` (or `extras_or_groups` in pyproject.toml) that will first
  try to find dependencies from "extras" and then from "groups".

### Changed

- Passing no extras to an environment now defaults to no added extras or groups.
  Old behavior (to default to the extra with the same name as the environment)
  was lead to complications with support of `dependency-groups`. Explicitly pass
  the extra or group if to get the old behavior.
- `default_envs` now passed the environment name as `extras_or_groups`.
  Therefore, if the name of the environment is an extra, it will be used.
  Otherwise, it will be from a group of that name.

- Removed option `--base/--no-base`. Replaced with `--skip-package`. Default is
  to include package dependencies. Pass `--skip-package` (or
  `skip_package = true` in `pyproject.toml`) to skip package dependencies.

## v0.11.0 — 2023-11-28

### Added

- Can now access "build-system.requires" as an extra. This can be useful for
  creating isolated environments to build a package.

### Changed

- Can now specify `pip` as a conda dependency. This is needed for cases that
  there are no pip dependencies in the environment, but you want it there for
  installing local packages. This may be the case if using `conda-lock` on an
  environment. Note that, much like python is always first in the dependency
  list, pip is always last.

## v0.10.0 — 2023-11-17

### Added

- Can now specify conda changes using `tool.pyproject2conda.dependencies` table.
  This is an alternative to using `# p2c:` comments.
- Refactored code. Split `parser` to `requirements` and `overrides`. Also
  cleaned up the parsing logic to hopefully make future changes simpler.

## v0.9.0 — 2023-11-14

### Added

- Default is now to remove whitespace from dependencies. For example, the
  dependency `module > 0.1` will become `module>0.1`. To override this
  behaviour, pass the option `--no-remove-whitespace`.
- Now supports python version `>3.8,<=3.12`
- Can now specify `extras = false` in pyprojec.toml to skip any extras. The
  default (`extras = true`) is the same as `extras = [env_name]` where
  `env_name` is the name of the environment (e.g.,
  `tool.pyproject2conda.envs.env_name`).

## v0.8.0 — 2023-10-02

### Added

- Added option to either raise error, or print message for environments with no
  dependencies.

### Changed

- pyproject2conda now works with `pyproject.toml` files with no dependencies.

## v0.7.0 — 2023-09-26

### Added

- Now use `logging` to print info output.

### Changed

- cli now uses `typer`. Since the program was already typed, this simplifies the
  interface.
- Program can now be called with any of `pyproject2conda`, `p2c`, or
  `python -m pyproject2conda`.
- Added cli options to web documentation.
- Fixed small typos and typing issues.
- The cli option `--python-include` now requires an argument. This is due to
  `typer` not liking options with zero or one arguments. Instead of the bare
  flag `--python-include` including the python spec from `pyproject.toml`, you
  have to pass `--python-include infer` to get that behavior.
- Added extra `all` to pip install options. The default is to not include `rich`
  or `shellingham`. Using `pip install pyproject2conda[all]` includes these
  optional packages. Note that the conda-forge recipe is based on the plain
  install (i.e., no `rich` or `shellingham`). However, the conda-froge recipe
  for `typer` does include these. That means, if you want to install
  `pyproject2conda` without the optional extras, you'll have to use pip.

## v0.6.1 — 2023-09-22

### Changed

- Fixed edge case where `--overwrite=check` and have a `user_config`. Now when
  using `p2c project` with a `user_config` and `overwrite=check`, the timestamp
  of the output file will be compared to both the `filename=pyproject.toml` and
  `user_config`.

## v0.6.0 — 2023-09-19

### Added

- Added `project` subcommand. This uses a configuration in `pyproject.toml` to
  build multiple enivonments in one go.
- Added `--deps` and `--reqs` flags to include extra conda and pip requirements.
- Added `--overwrite` to check if output file exists.
- Now (correctly) using rich_click.
- Added tests for all new cases, and some edge cases.

## v0.5.1 — 2023-09-09

### Added

- Added `--sort/--no-sort` flag to cli. Default is to sort dependencies. This
  fixes issues with changing order in `pyproject.toml` leading to different yaml
  files.

### Changed

- Changed structure of the repo to better support some third party tools.
- Moved nox environments from `.nox` to `.nox/{project-name}/envs`. This fixes
  issues with ipykernel giving odd names for locally installed environments.
- Moved repo specific dot files to the `config` directory (e.g.,
  `.noxconfig.toml` to `config/userconfig.toml`). This cleans up the top level
  of the repo.
- added some support for using `nbqa` to run mypy/pyright on notebooks.
- Added ability to bootstrap development environment using pipx. This should
  simplify initial setup. See Contributing for more info.

- Main repo now on usnistgov.
