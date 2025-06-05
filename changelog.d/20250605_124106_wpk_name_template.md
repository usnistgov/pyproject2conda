<!-- markdownlint-disable MD041 -->
<!--
A new scriv changelog fragment.

Uncomment the section that is right (remove the HTML comment wrapper).
-->

<!--
### Removed

- A bullet item for the Removed category.

-->
<!--
### Added

- A bullet item for the Added category.

-->

### Changed

- `--name` option (i.e., the `name` field in an environment.yaml file) now
  accepts the follinging fields:
  - `{py_version}`: the full python version passed in with `--python-version`,
    or specified in `pyproject.toml`
  - `{py}`: the python version without `"."` (so, for example, if
    `--python-version=3.8`, `{py}` will expand to `"38"`).
  - `{env}`: the environment name. Only applicable with the `project`
    subcommand.

<!--
### Deprecated

- A bullet item for the Deprecated category.

-->
<!--
### Fixed

- A bullet item for the Fixed category.

-->
<!--
### Security

- A bullet item for the Security category.

-->
