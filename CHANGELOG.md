<!-- markdownlint-disable MD024 -->

# Changelog

Changelog for `pyproject2conda`

## Unreleased

See the fragment files in
[changelog.d](https://github.com/usnistgov/pyproject2conda)

<!-- scriv-insert-here -->

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
