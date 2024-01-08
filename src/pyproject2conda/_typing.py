from __future__ import annotations

from typing import TYPE_CHECKING, Optional, TypeVar

R = TypeVar("R")
T = TypeVar("T")


OptStr = Optional[str]

if TYPE_CHECKING:
    from typing import Literal, Tuple

    from packaging.requirements import Requirement

    from .overrides import OverrideDeps
    from .utils import _Missing  # pyright: ignore[reportPrivateUsage]

    MISSING_TYPE = Literal[_Missing.MISSING]

    RequirementCommentPair = Tuple[Optional[Requirement], Optional[str]]
    RequirementOverridePair = Tuple[Optional[Requirement], Optional[OverrideDeps]]
