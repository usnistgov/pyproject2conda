from typing import Any, Callable, TypeVar

from typing_extensions import TypeAlias

FuncType: TypeAlias = Callable[..., Any]

F = TypeVar("F", bound=FuncType)

Dec: TypeAlias = Callable[[F], F]
