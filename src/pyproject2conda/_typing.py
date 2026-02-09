from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal  # noqa: F401

    from ._typing_compat import TypeAlias
    from .utils import _Missing  # pyright: ignore[reportPrivateUsage]  # noqa: F401

    MISSING_TYPE: TypeAlias = (
        "Literal[_Missing.MISSING]"  # pyrefly: ignore[type-alias-error]
    )
