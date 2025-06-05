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

- The config file version of command line options now accept either dashes or
  underscores. For example, the command line option `--template-python` now
  respects either `template-python` or `template_python` in the
  `tool.pyproject2conda` table of `pyproject.toml`. Note that you have to use
  either all dashes or all underscores, not a mix. The parser first looks for
  options with dashes, then falls back to underscores, so if they are both
  present, the dashed version will win.

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
