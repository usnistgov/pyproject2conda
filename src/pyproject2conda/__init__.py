"""
Top level API (:mod:`pyproject2conda`)
======================================
"""

from .parser import PyProject2Conda

# updated versioning scheme
try:
    from ._version import __version__
except Exception:  # pragma: no cover
    __version__ = "999"


__author__ = """William P. Krekelberg"""
__email__ = "wpk@nist.gov"


__all__ = [
    "__version__",
    "PyProject2Conda",
]
