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

from typing import TYPE_CHECKING, Sequence, TypeVar

if TYPE_CHECKING:
    from ._typing_compat import TypeAlias


R = TypeVar("R")
T = TypeVar("T")

OptStr: TypeAlias = str | None
OptStrSeq: TypeAlias = str | Sequence[str] | None
