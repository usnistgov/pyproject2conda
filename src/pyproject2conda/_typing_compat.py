# pyright: reportUnreachable=false
import sys
from typing import Self, TypeAlias

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


__all__ = [
    "Self",
    "TypeAlias",
    "override",
]
