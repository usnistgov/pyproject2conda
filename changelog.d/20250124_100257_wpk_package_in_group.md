<!-- markdownlint-disable MD041 -->
<!--
A new scriv changelog fragment.

Uncomment the section that is right (remove the HTML comment wrapper).
-->

<!--
### Removed

- A bullet item for the Removed category.

-->

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

<!--
### Changed

- A bullet item for the Changed category.

-->
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
