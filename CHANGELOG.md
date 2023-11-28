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
