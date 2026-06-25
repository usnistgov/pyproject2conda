"""Sync minimum versions of dependencies in pyproject.toml or pep723 section of python scripts to locked requirement file."""
# ruff: noqa: D101, D102, D103
# pylint: disable=missing-class-docstring
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "packaging>=26.2",
#     "requirements-parser>=0.13.1",
# ]
# ///

from __future__ import annotations

import logging
import re
import sys
from argparse import ArgumentParser
from dataclasses import dataclass, field
from functools import lru_cache, partial
from itertools import chain
from pathlib import Path
from subprocess import check_output
from typing import TYPE_CHECKING, cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from typing import Any, Literal

    from packaging.utils import NormalizedName

    SCRIPT_LOCK = Literal["requirements", "infer", "force"]


FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("sync-pyproject-min-versions")


@lru_cache
def get_versions_from_requirements(
    requirements_string_or_path: str | Path | None,
) -> dict[str, str]:
    if requirements_string_or_path is None:
        return {}

    requirements_string = (
        requirements_string_or_path.read_text(encoding="utf-8")
        if isinstance(requirements_string_or_path, Path)
        else requirements_string_or_path
    )

    from requirements import (  # type: ignore[attr-defined]  # pylint: disable=no-name-in-module
        parse,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]  # pyrefly: ignore[missing-module-attribute]  # ty: ignore[unresolved-import]
    )

    versions: dict[str, str] = {}
    for requirement in parse(requirements_string):  # pyright: ignore[reportUnknownVariableType]
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


def _factory_quoted_requirement_replacer(
    versions: dict[NormalizedName, str],
) -> Callable[[str], str]:
    def quoted_requirement_replacer(match: re.Match[str]) -> str:
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

    return partial(REQUIREMENT_REGEX.sub, quoted_requirement_replacer)


def _replace_pep723_section(
    quoted_requirement_replacer: Callable[[str], str], contents: str
) -> str:
    out: list[str] = []
    found = False
    lines = iter(contents.splitlines(keepends=True))

    for line in lines:
        if not found and re.match(r"^#\s+///\s+script$", line):
            found = True
            out.append(line)
            continue

        if found and re.match(r"^#\s+///$", line):
            return "".join(chain(out, [line], lines))

        out.append(
            quoted_requirement_replacer(line)
            if found and re.match(r"^#", line)
            else line
        )

    if found:
        logger.warning("Skipping update.  Found pep723 script start but no end")

    # if got here, didn't find pep723 data
    return contents


@dataclass(frozen=True)
class Options:
    requirements: Path | None = None
    include: frozenset[NormalizedName] = field(default_factory=frozenset)
    exclude: frozenset[NormalizedName] = field(default_factory=frozenset)
    toml_paths: tuple[Path, ...] = field(default_factory=tuple)
    script_paths: tuple[Path, ...] = field(default_factory=tuple)
    script_lock: SCRIPT_LOCK = "infer"

    def normalize_versions(self, versions: dict[str, str]) -> dict[NormalizedName, str]:
        out = {canonicalize_name(name): version for name, version in versions.items()}

        if self.include:
            out = {
                name: version for name, version in out.items() if name in self.include
            }
        if self.exclude:
            out = {k: v for k, v in out.items() if k not in self.exclude}

        return out

    @classmethod
    def from_params(
        cls,
        requirements: Path | None = None,
        include: Iterable[str] = (),
        exclude: Iterable[str] = (),
        paths: Iterable[Path] = (),
        script_lock: SCRIPT_LOCK = "infer",
    ) -> Options:
        # parse paths
        toml_paths: list[Path] = []
        script_paths: list[Path] = []
        for path in paths:
            suffix = path.suffix
            if suffix == ".toml":
                toml_paths.append(path)
            elif suffix == ".py":
                script_paths.append(path)
            else:
                logger.info("ignoring path %s", path)

        return cls(
            requirements=requirements,
            include=frozenset(canonicalize_name(x) for x in include),
            exclude=frozenset(canonicalize_name(x) for x in exclude),
            toml_paths=tuple(toml_paths),
            script_paths=tuple(script_paths),
            script_lock=script_lock,
        )

    @classmethod
    def from_kws(cls, kws: Any) -> Options:
        return cls.from_params(**kws)

    @classmethod
    def from_argv(cls, argv: Sequence[str] | None = None) -> Options:
        parser = ArgumentParser(description=__doc__)
        _ = parser.add_argument(
            "-r",
            "--requirements",
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
            "--script-lock",
            choices=("requirements", "infer", "force"),
            default="infer",
            help="""
            How to determine locked dependencies for scripts.

            * infer (default): Use ``uv export --script script.py`` if ``script.py.lock`` exists or fallback to ``requirements``
            * force: Use output of ``uv export --script script.py`` always.
            * requirements:  Use passed ``--requirements`` file
            """,
        )
        _ = parser.add_argument(
            "paths", nargs="*", help="pyproject.toml/script files to process", type=Path
        )

        opts = parser.parse_args(argv)

        return cls.from_params(
            requirements=opts.requirements,
            include=opts.include,
            exclude=opts.exclude,
            paths=opts.paths,
            script_lock=opts.script_lock,
        )


@lru_cache
def _get_replacer(
    requirements: str | Path | None,
    opts: Options,
    script_replacer: bool = False,
) -> Callable[[str], str] | None:

    if script_replacer:
        quoted_requirement_replacer = _get_replacer(requirements, opts, False)
        return (
            partial(_replace_pep723_section, quoted_requirement_replacer)
            if quoted_requirement_replacer is not None
            else None
        )

    versions = opts.normalize_versions(
        versions=get_versions_from_requirements(requirements),
    )
    return _factory_quoted_requirement_replacer(versions) if versions else None


def _get_requirements_from_script(
    script_path: Path,
    requirements: str | Path | None,
    script_lock: SCRIPT_LOCK,
) -> str | Path | None:

    lock_exists = script_path.with_suffix(".py.lock").exists()
    if script_lock == "force" or (script_lock == "infer" and lock_exists):
        logger.info("Run: uv export --no-color --script %s", script_path)
        return check_output([
            "uv",
            "export",
            *(["--locked"] if lock_exists else []),
            "--quiet",
            "--no-color",
            "--script",
            str(script_path),
        ]).decode("utf-8")
    return requirements


def _process_path(path: Path, replacer: Callable[[str], str]) -> None:
    logger.info("processing %s", path)
    contents = path.read_text(encoding="utf-8")
    out = replacer(contents)
    if contents != out:
        logger.info("update %s", path)
        _ = path.write_text(out, encoding="utf-8")
    else:
        logger.info("no change %s", path)


def main(argv: Sequence[str] | None = None) -> bool:
    """Main function"""
    opts = Options.from_argv(argv)

    replacer = _get_replacer(opts.requirements, opts, False)
    if opts.toml_paths and replacer:
        for path in opts.toml_paths:
            _process_path(path=path, replacer=replacer)

    if (replacer or opts.script_lock in {"infer", "force"}) and opts.script_paths:
        for path in opts.script_paths:
            lock_replacer = _get_replacer(
                requirements=_get_requirements_from_script(
                    path, opts.requirements, opts.script_lock
                ),
                opts=opts,
                script_replacer=True,
            )

            if lock_replacer:
                _process_path(path=path, replacer=lock_replacer)

    return False


if __name__ == "__main__":
    raise SystemExit(main())
