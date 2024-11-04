import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


__all__ = ["tomllib"]
