from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeVar

R = TypeVar("R")
T = TypeVar("T")


if TYPE_CHECKING:
    from packaging.requirements import (
        Requirement,  # pyright: ignore[reportUnusedImport]  # noqa: F401
    )

    from .overrides import (
        OverrideDeps,  # pyright: ignore[reportUnusedImport]  # noqa: F401
    )
    from .utils import _Missing  # pyright: ignore[reportPrivateUsage]

    MISSING_TYPE = Literal[_Missing.MISSING]

    RequirementCommentPair = "tuple[Requirement | None, str | None]"
    RequirementOverridePair = "tuple[Requirement | None, OverrideDeps | None]"
