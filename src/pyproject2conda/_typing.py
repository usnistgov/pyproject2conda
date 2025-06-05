from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

R = TypeVar("R")
T = TypeVar("T")


if TYPE_CHECKING:
    from typing import Literal  # noqa: F401

    from packaging.requirements import (
        Requirement,  # pyright: ignore[reportUnusedImport]  # noqa: F401
    )

    from ._typing_compat import TypeAlias
    from .overrides import (
        OverrideDeps,  # pyright: ignore[reportUnusedImport]  # noqa: F401
    )
    from .utils import _Missing  # pyright: ignore[reportPrivateUsage]  # noqa: F401

MISSING_TYPE: TypeAlias = "Literal[_Missing.MISSING]"  # pyre-ignore[type-alias-error]

RequirementCommentPair: TypeAlias = (
    "tuple[Requirement | None, str | None]"  # pyre-ignore[type-alias-error]
)
RequirementOverridePair: TypeAlias = (
    "tuple[Requirement | None, OverrideDeps | None]"  # pyre-ignore[type-alias-error]
)
