from typing import Any, Callable, TypeVar

from ._typing_compat import TypeAlias

FuncType: TypeAlias = Callable[..., Any]

F = TypeVar("F", bound=FuncType)
R = TypeVar("R")

Dec: TypeAlias = Callable[[F], F]
