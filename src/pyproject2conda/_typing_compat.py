import sys
from typing import TypeAlias

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self  # pyright: ignore[reportUnreachable]


__all__ = [
    "Self",
    "TypeAlias",
]
