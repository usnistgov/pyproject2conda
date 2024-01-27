"""
Override dependencies (:mod:`~pyproject2conda.overrides`)
=========================================================
"""

from __future__ import annotations

import argparse
import re
import shlex
from functools import lru_cache
from typing import TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    from ._typing import OptStr, RequirementCommentPair, RequirementOverridePair
    from ._typing_compat import Self


# * Comment parsing --------------------------------------------------------------------
@lru_cache
def p2c_argparser() -> argparse.ArgumentParser:
    """Parser for p2c comment options."""
    parser = argparse.ArgumentParser(
        description="Parser searches for comments '# p2c: [OPTIONS] CONDA-PACKAGES'"
    )

    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Channel to add to the pyproject requirement",
    )
    parser.add_argument(
        "-p",
        "--pip",
        action="store_true",
        help="If specified, install pyproject dependency with pip",
    )
    parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        help="If specified skip pyproject dependency on this line",
    )

    parser.add_argument("packages", nargs="*")

    return parser


def _match_p2c_comment(comment: OptStr) -> OptStr:
    if not comment or not (match := re.match(r".*?#\s*p2c:\s*([^\#]*)", comment)):
        return None
    if re.match(r".*?##\s*p2c:", comment):
        # This checks for double ##.  If found, ignore line
        return None
    return match.group(1).strip()


def _parse_p2c(match: OptStr) -> OverrideDict | None:
    """Parse match from _match_p2c_comment"""
    if match:
        return cast(OverrideDict, vars(p2c_argparser().parse_args(shlex.split(match))))
    return None


def _parse_p2c_comment(comment: OptStr) -> OverrideDict | None:
    if match := _match_p2c_comment(comment):
        return _parse_p2c(match)
    return None


# * Main classes -----------------------------------------------------------------------
class OverrideDict(TypedDict, total=False):
    """Dict for storing override options."""

    pip: bool
    skip: bool
    channel: str | None
    packages: str | list[str]


class OverrideDeps:
    """Class to work with overrides from comment or table"""

    def __init__(
        self,
        pip: bool = False,
        skip: bool = False,
        packages: str | list[str] | None = None,
        channel: str | None = None,
    ) -> None:
        if channel is not None and channel.strip() in {"pip", "pypi"}:
            channel = None
            pip = True

        self.pip = pip
        self.skip = skip
        self.channel = channel

        if packages is None:
            packages = []
        elif isinstance(packages, str):
            packages = [packages]
        self.packages = packages

    def __repr__(self) -> str:  # pragma: no cover
        return repr(self.__dict__)

    @classmethod
    def from_comment(
        cls, comment: str | None, default: OverrideDict | None = None
    ) -> Self | None:
        """Create from comment."""
        parsed = _parse_p2c_comment(comment)

        kws: OverrideDict
        if parsed is None:
            if default is None:
                return None
            kws = default
        elif default:
            kws = dict(default, **parsed)  # type: ignore[assignment]
        else:
            kws = parsed

        return cls(**kws)

    @classmethod
    def requirement_comment_to_override_pairs(
        cls,
        requirement_comment_pairs: list[RequirementCommentPair],
        override_table: dict[str, OverrideDict],
    ) -> list[RequirementOverridePair]:
        """Create from override pairs."""
        out: list[RequirementOverridePair] = []
        for requirement, comment in requirement_comment_pairs:
            if requirement is not None:
                default = override_table.get(requirement.name, None)
            else:
                default = None

            if (
                override := cls.from_comment(comment=comment, default=default)
            ) is not None or requirement is not None:
                out.append((requirement, override))
        return out
