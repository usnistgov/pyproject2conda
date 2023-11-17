# from typing import Any, Callable, TypeVar

# from ._typing_compat import TypeAlias

# FuncType: TypeAlias = Callable[..., Any]

# F = TypeVar("F", bound=FuncType)
# R = TypeVar("R")

# Dec: TypeAlias = Callable[[F], F]


# Tstr_opt = Optional[str]
# Tstr_seq_opt = Optional[Union[str, Sequence[str]]]

# T = TypeVar("T")

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, TypeVar

R = TypeVar("R")
T = TypeVar("T")


OptStr = Optional[str]

if TYPE_CHECKING:
    from typing import Literal, Tuple

    from packaging.requirements import Requirement

    from .overrides import OverrideDeps
    from .utils import _Missing  # pyright: ignore

    MISSING_TYPE = Literal[_Missing.MISSING]

    RequirementCommentPair = Tuple[Optional[Requirement], Optional[str]]
    RequirementOverridePair = Tuple[Optional[Requirement], Optional[OverrideDeps]]
