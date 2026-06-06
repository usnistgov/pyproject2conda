"""Sync minimum versions of pyproject.toml dependencies to locked requirement file"""
# ruff: noqa: D101, D102, D103
# pylint: disable=missing-class-docstring
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "packaging>=26.2",
#     "requirements-parser>=0.13.0",
# ]
# ///

from __future__ import annotations

import logging
import re
import sys
from argparse import ArgumentParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any


FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("sync-pyproject-min-versions")


def get_versions_from_requirements(
    requirements_path: Path | None,
) -> dict[str, str]:
    if requirements_path is None:
        return {}

    from requirements import (  # type: ignore[attr-defined]  # pylint: disable=no-name-in-module
        parse,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]  # pyrefly: ignore[missing-module-attribute]  # ty: ignore[unresolved-import]
    )

    versions: dict[str, str] = {}
    with requirements_path.open(encoding="utf-8") as f:
        for requirement in parse(f):  # pyright: ignore[reportUnknownVariableType]
            name = cast("str", requirement.name)
            versions[name] = requirement.specs[0][-1]  # pyright: ignore[reportUnknownMemberType]
    return versions


# taken from https://github.com/pypa/packaging/blob/main/src/packaging/version.py
_version_pattern = r"""
    v?+                                                   # optional leading v
    (?a:
        (?:(?P<epoch>[0-9]+)!)?+                          # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*+)                 # release segment
        (?P<pre>                                          # pre-release
            [._-]?+
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [._-]?+
            (?P<pre_n>[0-9]+)?
        )?+
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [._-]?
                (?P<post_l>post|rev|r)
                [._-]?
                (?P<post_n2>[0-9]+)?
            )
        )?+
        (?P<dev>                                          # dev release
            [._-]?+
            (?P<dev_l>dev)
            [._-]?+
            (?P<dev_n>[0-9]+)?
        )?+
    )
    (?a:\+
        (?P<local>                                        # local version
            [a-z0-9]+
            (?:[._-][a-z0-9]+)*+
        )
    )?+
"""

_version_pattern = (
    _version_pattern.replace("*+", "*").replace("?+", "?")
    if (sys.implementation.name == "cpython" and sys.version_info < (3, 11, 5))
    or (sys.implementation.name == "pypy" and sys.version_info < (3, 11, 13))
    or sys.version_info < (3, 11)
    else _version_pattern
)

_regex_pattern = rf"""
(?P<quote>["'])
\s*
(?P<inner>
    (?P<package>                                              # package name
        \b[a-zA-Z0-9][a-zA-Z0-9._-]*\b
    )
    (?P<extras>                                               # extras
        (?:\s*\[(?:\w|[,. -])*\])?\s*>=\s*
    )
    (?P<version>
       {_version_pattern}
    )
    (?P<markers>                                              # everything else
        .*?
    )
)
(?P=quote)
"""

REQUIREMENT_REGEX = re.compile(_regex_pattern, flags=re.VERBOSE | re.IGNORECASE)


def _factory_replacer(versions: dict[str, str]) -> Callable[[re.Match[str]], str]:
    def replacer(match: re.Match[str]) -> str:
        original_string = match.group(0)
        try:
            dep = Requirement(match.group("inner"))
        except InvalidRequirement:
            return original_string

        name = canonicalize_name(dep.name)
        if (
            name in versions
            and len(dep.specifier) == 1
            and next(iter(dep.specifier)).operator == ">="
        ):
            s = f"{match.group('quote')}{match.group('package')}{match.group('extras')}{versions[name]}{match.group('markers')}{match.group('quote')}"
            if s != original_string:
                logger.info("replace %s with %s", original_string, s)
            return s

        return original_string

    return replacer


@dataclass
class Options:
    requirements: Path
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    paths: list[Path] = field(default_factory=list)
    ignore_non_toml: bool = True

    @classmethod
    def from_kws(cls, kws: Any) -> Options:
        return cls(**kws)


def _get_options(
    argv: Sequence[str] | None = None,
) -> Options:
    parser = ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "-r",
        "--requirements",
        required=True,
        type=Path,
        help="Requirements file to extract locked versions from.",
    )
    _ = parser.add_argument(
        "--include",
        default=[],
        action="append",
        help="""
        Package names to include. Default is to consider all packages in
        requirements file. Specifying ``--include`` will only update those
        packages. Can specify multiple times.
        """,
    )
    _ = parser.add_argument(
        "--exclude",
        default=[],
        action="append",
        help="""
        Packages to exclude. Default is to consider all packages in
        requirements file. Specifying ``--exclude`` will skip those packages.
        Can specify multiple times.
        """,
    )
    _ = parser.add_argument(
        "--no-ignore-non-toml",
        action="store_true",
        help="""
        Default is to only consider ``paths`` that end in ``".toml"``, which is
        useful for using ``sync-pre-commit-hooks`` via pre-commit. Passing
        ``--no-ignore-non-toml`` will not ignore any ``paths``.
        """,
    )
    _ = parser.add_argument(
        "paths", nargs="*", help="pyproject.toml files to process", type=Path
    )

    opts = parser.parse_args(argv)

    return Options(
        requirements=opts.requirements,
        include=opts.include,
        exclude=opts.exclude,
        paths=opts.paths,
        ignore_non_toml=not opts.no_ignore_non_toml,
    )


def _normalize_versions(
    versions: dict[str, str], include: list[str], exclude: list[str]
) -> dict[str, str]:

    # canonicalize names
    versions = {canonicalize_name(name): version for name, version in versions.items()}

    include_set, exclude_set = (
        {canonicalize_name(x) for x in o} for o in (include, exclude)
    )

    if include_set:
        versions = {
            name: version for name, version in versions.items() if name in include_set
        }
    if exclude_set:
        versions = {k: v for k, v in versions.items() if k not in exclude_set}

    return versions


def _normalize_paths(paths: list[Path], ignore_non_toml: bool) -> list[Path]:
    if not ignore_non_toml:
        return paths

    out: list[Path] = []
    for path in paths:
        if path.suffix != ".toml":
            logger.info("ignoring non toml path %s", path)
        else:
            out.append(path)
    return out


def main(argv: Sequence[str] | None = None) -> bool:
    """Main function"""
    opts = _get_options(argv)

    versions = _normalize_versions(
        versions=get_versions_from_requirements(opts.requirements),
        include=opts.include,
        exclude=opts.exclude,
    )
    if not versions:
        return False

    paths = _normalize_paths(opts.paths, opts.ignore_non_toml)
    replacer = _factory_replacer(versions)

    for path in paths:
        logger.info("processing %s", path)
        _ = path.write_text(
            REQUIREMENT_REGEX.sub(replacer, path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )

    return False


if __name__ == "__main__":
    raise SystemExit(main())
