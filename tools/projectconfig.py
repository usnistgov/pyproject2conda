"""
Methods to work with config file (for personal setup) of nox and other project tools.

Right now, this is only for user specific nox config.  But leaving open it could be used
for other things in the future.
"""
from __future__ import annotations

import configparser
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from typing_extensions import Self


class ProjectConfig:
    """
    Read/write/update userconfig.toml

    This uses a combination of ini/json to read/write the config file.
    This is to avoid having to import from tomli/tomli_w.

    If/when move to python>3.11, can go back to just using toml.


    Parameters
    ----------
    python_paths : list of str, optional
        Paths to append to "PATH" to find python interpreters.
        Note that this can include wildcards.
    env_extras : mapping from str to list of str, option
    """

    def __init__(
        self,
        python_paths: list[str] | None = None,
        env_extras: Mapping[str, Mapping[str, Any]] | None = None,
        copy: bool = True,
    ) -> None:
        python_paths = python_paths or []
        env_extras = {} if env_extras is None else dict(env_extras)

        if copy:
            python_paths = deepcopy(python_paths)
            env_extras = deepcopy(env_extras)

        self.python_paths = python_paths
        self.env_extras = env_extras

    def new_like(
        self,
        python_paths: list[str] | None = None,
        env_extras: Mapping[str, Mapping[str, Any]] | None = None,
        copy: bool = True,
    ) -> Self:
        return type(self)(
            python_paths=python_paths or self.python_paths,
            env_extras=env_extras or self.env_extras,
            copy=copy,
        )

    @staticmethod
    def _path_to_params(
        path: str | Path,
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        path = Path(path)

        python_paths: list[str] = []
        env_extras: dict[str, dict[str, Any]] = {}

        if path.exists():
            config = configparser.ConfigParser()
            config.read(path)

            # nox.python
            if "nox.python" in config and "paths" in config["nox.python"]:
                python_paths = json.loads(config["nox.python"]["paths"])

            for header, table in config.items():
                if "tool.pyproject2conda" in header:
                    env_extras[header] = {k: json.loads(v) for k, v in table.items()}

        return python_paths, env_extras

    @classmethod
    def from_path(cls, path: str | Path = "./config/userconfig.toml") -> Self:
        path = Path(path)

        if path.exists():
            python_paths, env_extras = cls._path_to_params(path)
            return cls(python_paths=python_paths, env_extras=env_extras)
        else:
            return cls()

    @staticmethod
    def _params_to_string(
        python_paths: list[str], env_extras: dict[str, Mapping[str, Any]]
    ) -> str:
        import configparser
        import json
        from io import StringIO
        from textwrap import dedent

        config = configparser.ConfigParser()

        if python_paths:
            config.add_section("nox.python")
            config.set("nox.python", "paths", json.dumps(python_paths))

        if env_extras:
            for header, table in env_extras.items():
                config.add_section(header)
                for k, v in table.items():
                    config.set(header, k, json.dumps(v))

        with StringIO() as f:
            config.write(f)
            s = f.getvalue()

        header = dedent(
            """\
        # This file is for setting user specific config for use
        # with nox and other project tools and applications.
        #
        # THIS FILE SHOULD NOT BE TRACKED BY GIT!!!!
        #
        # Example usage:
        #
        # [nox.python]
        # paths = ["~/.conda/envs/python-3.*/bin"]
        #
        # [tool.pyproject2conda.envs.dev]
        # extras = ["dev-complete"]
        """
        )

        return header + s

    def to_path(self, path: str | Path | None = None) -> str:
        s = self._params_to_string(
            python_paths=self.python_paths, env_extras=self.env_extras
        )

        if path is not None:
            with open(path, "w") as f:
                f.write(s)
        return s

    def __repr__(self) -> str:
        return f"<ProjectConfig(python_paths={self.python_paths}, env_extras={self.env_extras})>"

    def expand_python_paths(self) -> list[str]:
        from glob import glob

        paths = []
        for p in self.python_paths:
            paths.extend(glob(os.path.expanduser(p)))
        return paths

    def add_paths_to_environ(
        self, paths: list[str] | None, prepend: bool = True
    ) -> None:
        if paths is None:
            paths = self.expand_python_paths()
        paths_str = ":".join(map(str, paths))
        if prepend:
            fmt = "{path_new}:{path_old}"
        else:
            fmt = "{path_old}:{path_new}"
        os.environ["PATH"] = fmt.format(path_new=paths_str, path_old=os.environ["PATH"])

    def to_nox_config(
        self, add_paths_to_environ: bool = True, prepend: bool = True
    ) -> dict[str, Any]:
        config: dict[str, Any] = {}

        if self.python_paths:
            config["paths"] = self.expand_python_paths()

            if add_paths_to_environ:
                self.add_paths_to_environ(config["paths"], prepend=prepend)

        if self.env_extras:
            config["environment-extras"] = self.env_extras
        else:
            config["environment-extras"] = {"dev": ["nox", "dev"]}

        return config


def glob_envs_to_paths(globs: list[str]) -> list[str]:
    import fnmatch

    from .common_utils import get_conda_environment_map

    env_map = get_conda_environment_map()

    out = []
    for glob in globs:
        found_envs = fnmatch.filter(env_map.keys(), glob)
        out.extend([f"{env_map[k]}/bin" for k in found_envs])

    return out


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Create the file config/userconfig.toml")

    p.add_argument(
        "-p",
        "--python-paths",
        nargs="+",
        help="""
        Specify paths to add to search path for python interpreters.
        This can include the wildcard '*'.
        """,
    )
    p.add_argument(
        "-e",
        "--env",
        nargs="+",
        help="""
        Conda environment name patterns to extract `--python-paths` from
        """,
    )
    p.add_argument(
        "-d",
        "--dev-extras",
        nargs="+",
        help="extras (from pyproject.toml) to include in development environment",
    )

    p.add_argument(
        "-f",
        "--file",
        help="file to store configuration",
        type=str,
        default="./config/userconfig.toml",
    )

    args = p.parse_args()

    n = ProjectConfig.from_path(path=args.file)

    if args.python_paths:
        python_paths = args.python_paths
    elif args.env:
        python_paths = glob_envs_to_paths(args.env)
    else:
        python_paths = None

    if python_paths:
        n.python_paths = python_paths

    if args.dev_extras:
        n.env_extras["tool.pyproject2conda.envs.dev"] = {"extras": args.dev_extras}

    n.to_path(args.file)


if __name__ == "__main__":
    if __package__ is None:
        # Magic to be able to run script as either
        #   $ python -m tools.create_python
        # or
        #   $ python tools/create_python.py
        here = Path(__file__).absolute()
        __package__ = here.parent.name

    main()
