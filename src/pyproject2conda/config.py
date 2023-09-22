"""
Read/use config/pyproject.toml file (:mod:`~pyproject2conda.config`)
====================================================================
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from pyproject2conda.utils import filename_from_template, get_in

if TYPE_CHECKING:
    from typing import Any, Iterator, Sequence

    from typing_extensions import Self


# * Utilities


class Config:
    """Class to parse toml file with [tool.pyproject2conda] section"""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def get_in(self, *keys: str, default: Any = None) -> Any:
        """Utility to extract from nested dict."""
        keys = keys
        return get_in(keys=keys, nested_dict=self.data, default=default)

    @cached_property
    def overrides(self) -> list[Any]:
        """All overrides sections from `[[tool.pyproject2conda.overrides]]`"""
        out: list[dict[str, Any]] = []
        for x in self.get_in("overrides", default=[]):
            if "envs" not in x:
                raise ValueError("must specify env in overrides")
            out.append(x)
        return out

    @property
    def envs(self) -> dict[str, Any]:
        """All environments"""
        return self.get_in("envs", default={})  # type: ignore

    def _get_override(self, env: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for override in self.overrides:
            if env in override["envs"]:
                out.update(**override)
        if "envs" in out:
            del out["envs"]
        return out

    # def _get_env(self, env_name: str) -> dict[str, Any]:
    #     env = self.get_in("envs", env_name)
    #     env.update(**self._get_override(env_name))
    #     return env  # type: ignore

    def _get_value(
        self,
        key: str,
        env_name: str | None = None,
        inherit: bool = True,
        as_list: bool = False,
        default: Any = None,
    ) -> Any:
        """Get a value from thing"""

        if env_name is None:
            value = self.get_in(key, default=None)

        else:
            # try to get from env definition
            assert env_name in self.data["envs"], f"env {env_name} not in config"

            value = self.get_in("envs", env_name, key, default=None)

            if inherit:
                # try to get from override
                if value is None:
                    value = self._get_override(env_name).get(key, None)

                # finally, try to get from top level
                if value is None:
                    value = self.get_in(key, default=None)

        if value is None:
            if callable(default):
                value = default()
            else:
                value = default

        if value is not None and as_list:
            if not isinstance(value, list):
                value = [value]

        return value

    def channels(
        self, env_name: str | None = None, inherit: bool = True
    ) -> list[str] | None:
        """Channels getter"""
        return self._get_value(  # type: ignore
            key="channels", env_name=env_name, inherit=inherit, as_list=True
        )

    def python(
        self, env_name: str | None = None, inherit: bool = True, default: Any = list
    ) -> list[str]:
        """Python getter"""

        # if callable(default):
        #     default = default()

        return self._get_value(  # type: ignore
            key="python",
            env_name=env_name,
            inherit=inherit,
            as_list=True,
            default=default,
        )

    def extras(self, env_name: str) -> list[str]:
        """Extras getter"""
        return self._get_value(  # type: ignore
            key="extras",
            env_name=env_name,
            inherit=False,
            as_list=True,
            default=env_name or [],
        )

    def output(self, env_name: str | None = None) -> str | None:
        """Output getter"""
        return self._get_value(key="output", env_name=env_name, inherit=False)  # type: ignore

    def sort(
        self, env_name: str | None = None, inherit: bool = True, default: bool = True
    ) -> bool:
        """Sort getter"""
        return self._get_value(  # type: ignore
            key="sort", env_name=env_name, inherit=inherit, default=default
        )

    # def inherit(self, env_name: str, default: bool = True) -> bool:
    #     return self._get_value(  # type: ignore
    #         key="inherit", env_name=env_name, inherit=True, default=default
    #     )

    def base(self, env_name: str, default: bool = True) -> bool:
        """Base getter."""
        return self._get_value(key="base", env_name=env_name, default=default)  # type: ignore

    def name(self, env_name: str) -> bool:
        return self._get_value(key="name", env_name=env_name)  # type: ignore

    def header(self, env_name: str) -> bool:
        """Header getter"""
        return self._get_value(key="header", env_name=env_name)  # type: ignore

    def style(self, env_name: str | None = None, default: str = "yaml") -> str:
        """Style getter.  One of `yaml`, `requirements`"""
        out = self._get_value(
            key="style", env_name=env_name, default=default, as_list=True
        )
        for k in out:
            assert k in ["yaml", "requirements", "conda-requirements", "json"]
        return out  # type: ignore

    def python_include(self, env_name: str | None = None) -> str | None:
        """Flag python_include"""
        return self._get_value(key="python_include", env_name=env_name)  # type: ignore

    def python_version(self, env_name: str | None = None) -> str | None:
        """Flag python_version"""
        return self._get_value(key="python_version", env_name=env_name)  # type: ignore

    def overwrite(self, env_name: str | None = None, default: str = "check") -> str:
        """Flag overwrite"""
        return self._get_value(key="overwrite", env_name=env_name, default=default)  # type: ignore

    def verbose(self, env_name: str | None = None, default: bool = True) -> bool:
        """Flag verbose"""
        return self._get_value(key="verbose", env_name=env_name, default=default)  # type: ignore

    def template(self, env_name: str, default: str = "{env}") -> str:
        """Flag for template"""
        return self._get_value(key="template", env_name=env_name, default=default)  # type: ignore

    def template_python(self, env_name: str, default: str = "py{py}-{env}") -> str:
        """Flag for template_python."""
        return self._get_value(  # type: ignore
            key="template_python", env_name=env_name, default=default
        )

    def deps(self, env_name: str, default: Any = None) -> list[str]:
        return self._get_value(  # type: ignore
            key="deps",
            env_name=env_name,
            default=default,
        )

    def reqs(self, env_name: str, default: Any = None) -> list[str]:
        return self._get_value(  # type: ignore
            key="reqs",
            env_name=env_name,
            default=default,
        )

    def user_config(self, env_name: str | None = None) -> str | None:  # pyright: ignore
        """Flag user_config"""
        return self._get_value(key="user_config", default=None)  # type: ignore

    def assign_user_config(self, user: Self) -> Self:
        """Assign user_config to self."""
        from copy import deepcopy

        data = deepcopy(self.data)

        # get user envs

        if "envs" not in data:
            data["envs"] = {}

        if "overrides" not in data:
            data["overrides"] = []

        for key in ["envs", "overrides"]:
            u = user.get_in(key)
            if u is not None:
                d = data[key]
                if isinstance(d, list):
                    d.extend(u)
                elif isinstance(d, dict):
                    d.update(**u)

        return type(self)(data)

    def _get_output_and_templates(
        self, env_name: str, **defaults: Any
    ) -> list[str | None]:
        return [
            defaults.get(k, getattr(self, k)(env_name))
            for k in ["output", "template", "template_python"]
        ]

    def _iter_yaml(
        self, env_name: str, **defaults: Any
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        pythons = self.python(env_name)
        output, template, template_python = self._get_output_and_templates(
            env_name, **defaults
        )

        keys = [
            "extras",
            "sort",
            "base",
            "header",
            "overwrite",
            "verbose",
            "reqs",
            "deps",
            "name",
            "channels",
        ]

        data = {k: defaults.get(k, getattr(self, k)(env_name)) for k in keys}

        if not pythons:
            if output is None:
                output = filename_from_template(
                    template=template, env_name=env_name, ext="yaml"
                )

            if python_include := self.python_include(env_name):
                data.update(python_include=python_include)

            if python_version := self.python_version(env_name):
                data.update(python_version=python_version)

            data.update(output=output)
            yield ("yaml", data)

        else:
            for python in pythons:
                output = filename_from_template(
                    template=template_python,
                    python=python,
                    env_name=env_name,
                    ext="yaml",
                )
                data.update(python=python, output=output)
                yield ("yaml", data)

    def _iter_reqs(
        self, env_name: str, **defaults: Any
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        keys = ["extras", "sort", "base", "header", "overwrite", "verbose", "reqs"]

        output, template, _ = self._get_output_and_templates(env_name, **defaults)

        data = {k: defaults.get(k, getattr(self, k)(env_name)) for k in keys}

        output = self.output(env_name)
        if not output:
            output = filename_from_template(
                template=template, env_name=env_name, ext="txt"
            )
        data.update(output=output)

        yield ("requirements", data)

    def iter(
        self, envs: Sequence[str] | None = None, **defaults: Any
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        """Iterate over configs"""

        # filter defaults.  Only include values of not None:
        defaults = {k: v for k, v in defaults.items() if v is not None}

        if not envs:
            envs = list(self.envs.keys())

        for env in envs:
            for style in self.style(env):
                if style == "yaml":
                    yield from self._iter_yaml(env, **defaults)
                elif style == "requirements":
                    yield from self._iter_reqs(env, **defaults)
                else:
                    raise ValueError(f"unknown style {style}")  # pragma: no cover

    @classmethod
    def from_toml_dict(
        cls, data: dict[str, Any], user_config: dict[str, Any] | None = None
    ) -> Self:
        """Create from toml dictionaries."""
        data = get_in(["tool", "pyproject2conda"], data, default={})

        if "default_envs" in data:
            default_envs = data.pop("default_envs")

            if "envs" not in data:
                data["envs"] = {}

            for env in default_envs:
                data["envs"][env] = {}

        c = cls(data)

        # add in "default_envs"

        if user_config:  # pragma: no cover
            u = cls.from_toml_dict(data=user_config)
            c = c.assign_user_config(user=u)

        return c

    @classmethod
    def from_string(cls, s: str, user_config: str | None = None) -> Self:
        """Create from string representation of toml file."""
        import tomli

        c = cls.from_toml_dict(tomli.loads(s))

        if user_config:
            u = cls.from_string(user_config)
            c = c.assign_user_config(user=u)
        return c

    @classmethod
    def from_file(
        cls, path: str | Path, user_config: str | Path | None = "infer"
    ) -> Self:
        """Create from toml file(s)."""
        import tomli

        with open(path, "rb") as f:
            data = tomli.load(f)

        c = cls.from_toml_dict(data)

        if user_config == "infer":
            if (user_config := c.user_config()) is not None:
                # relative path
                user_config = Path(path).parent / Path(user_config)

        if user_config:
            if Path(user_config).exists():
                u = cls.from_file(user_config)
                c = c.assign_user_config(u)

        return c
