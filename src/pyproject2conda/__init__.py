"""
Top level API (:mod:`pyproject2conda`)
======================================
"""

from .parser import PyProject2Conda

# updated versioning scheme
try:
    from importlib.metadata import version as _version

    __version__ = _version("pyproject2conda")
except Exception:  # pragma: no cover
    # Local copy or not installed with setuptools.
    # Disable minimum version checks on downstream libraries.
    __version__ = "999"  # pragma: no cover


__author__ = """William P. Krekelberg"""
__email__ = "wpk@nist.gov"


__all__ = [
    "__version__",
    "PyProject2Conda",
]
