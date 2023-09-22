<!-- markdownlint-disable MD024 -->

# Changelog

Changelog for `pyproject2conda`

## Unreleased

See the fragment files in
[changelog.d](https://github.com/usnistgov/pyproject2conda)

<!-- scriv-insert-here -->

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
