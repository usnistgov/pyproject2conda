"""
Read/use config/pyproject.toml file (:mod:`~pyproject2conda.config`)
====================================================================
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from pyproject2conda.utils import (
    filename_from_template,
    get_all_pythons,
    get_default_pythons_with_fallback,
    get_in,
    select_pythons,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any

    from ._typing_compat import Self


# * Utilities
class Config:  # noqa: PLR0904
    """Class to parse toml file with [tool.pyproject2conda] section"""

    def __init__(
        self,
        data: dict[str, Any],
        default_pythons: list[str] | None = None,
        all_pythons: list[str] | None = None,
    ) -> None:
        self.data = data
        self.default_pythons: list[str] = (
            [] if default_pythons is None else default_pythons
        )
        self.all_pythons: list[str] = [] if all_pythons is None else all_pythons

    def get_in(self, *keys: str, default: Any = None) -> Any:
        """Utility to extract from nested dict."""
        return get_in(keys=keys, nested_dict=self.data, default=default)

    @cached_property
    def overrides(self) -> list[Any]:
        """All overrides sections from `[[tool.pyproject2conda.overrides]]`"""
        out: list[dict[str, Any]] = []
        for x in self.get_in("overrides", default=[]):
            if "envs" not in x:
                msg = "must specify env in overrides"
                raise ValueError(msg)
            out.append(x)
        return out

    @property
    def envs(self) -> dict[str, Any]:
        """All environments"""
        return self.get_in("envs", default={})  # type: ignore[no-any-return]

    def _get_override(self, env: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for override in self.overrides:
            if env in override["envs"]:
                out.update(**override)
        out.pop("envs", None)
        return out

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
            if env_name not in self.data["envs"]:
                msg = f"env {env_name} not in config"
                raise ValueError(msg)

            value = self.get_in("envs", env_name, key, default=None)

            if inherit:
                # If have override, use it.
                if (value_ := self._get_override(env_name).get(key)) is not None:
                    value = value_

                # finally, try to get from top level
                if value is None:
                    value = self.get_in(key, default=None)

        if value is None:
            value = default() if callable(default) else default

        if value is not None and as_list and not isinstance(value, list):
            value = [value]

        return value  # pyright: ignore[reportUnknownVariableType]

    def channels(
        self, env_name: str | None = None, inherit: bool = True
    ) -> list[str] | None:
        """Channels getter"""
        return self._get_value(  # type: ignore[no-any-return]
            key="channels", env_name=env_name, inherit=inherit, as_list=True
        )

    def python(
        self, env_name: str | None = None, inherit: bool = True, default: Any = list
    ) -> list[str]:
        """Python getter"""
        out: list[str] = self._get_value(
            key="python",
            env_name=env_name,
            inherit=inherit,
            as_list=True,
            default=default,
        )
        return select_pythons(out, self.default_pythons, self.all_pythons)

    def _get_extras(
        self, key: str, env_name: str, default: Any, inherit: bool = True
    ) -> list[str]:
        val = self._get_value(
            key=key,
            env_name=env_name,
            inherit=inherit,
            default=default,
        )

        if isinstance(val, bool):
            return [env_name] if val else []

        if not isinstance(val, list):
            val = [val]
        return val  # type: ignore[no-any-return]

    def extras(self, env_name: str, inherit: bool = True) -> list[str]:
        """
        Extras getter

        * If value is `True` (default), then return [env_name]
        * If value is `False`, return []
        * else return list of extras
        """
        return self._get_extras(
            key="extras", env_name=env_name, default=list, inherit=inherit
        )

    def groups(self, env_name: str, inherit: bool = True) -> list[str]:
        """
        Groups getter.

        Same style as `self.extras`
        """
        return self._get_extras(
            key="groups", env_name=env_name, default=list, inherit=inherit
        )

    def extras_or_groups(self, env_name: str, inherit: bool = True) -> list[str]:
        """
        Extras_or_Groups getter.

        These will need to be resolved after the fact.
        """
        return self._get_extras(
            key="extras_or_groups", env_name=env_name, default=list, inherit=inherit
        )

    def output(self, env_name: str | None = None) -> str | None:
        """Output getter"""
        return self._get_value(key="output", env_name=env_name, inherit=False)  # type: ignore[no-any-return]

    def sort(
        self, env_name: str | None = None, inherit: bool = True, default: bool = True
    ) -> bool:
        """Sort getter"""
        return self._get_value(  # type: ignore[no-any-return]
            key="sort", env_name=env_name, inherit=inherit, default=default
        )

    def skip_package(self, env_name: str, default: bool = False) -> bool:
        """skip_package getter."""
        return self._get_value(key="skip_package", env_name=env_name, default=default)  # type: ignore[no-any-return]

    def name(self, env_name: str) -> bool:
        """Name option."""
        return self._get_value(key="name", env_name=env_name)  # type: ignore[no-any-return]

    def header(self, env_name: str) -> bool:
        """Header getter"""
        return self._get_value(key="header", env_name=env_name)  # type: ignore[no-any-return]

    def style(self, env_name: str | None = None, default: str = "yaml") -> str:
        """Style getter.  One of `yaml`, `requirements`"""
        out = self._get_value(
            key="style", env_name=env_name, default=default, as_list=True
        )
        for k in out:
            if k not in {"yaml", "requirements", "conda-requirements", "json"}:
                msg = f"unknown style {k}"
                raise ValueError(msg)
        return out  # type: ignore[no-any-return]

    def python_include(self, env_name: str | None = None) -> str | None:
        """Flag python_include"""
        return self._get_value(key="python_include", env_name=env_name)  # type: ignore[no-any-return]

    def python_version(self, env_name: str | None = None) -> str | None:
        """Flag python_version"""
        return self._get_value(key="python_version", env_name=env_name)  # type: ignore[no-any-return]

    def overwrite(self, env_name: str | None = None, default: str = "check") -> str:
        """Flag overwrite"""
        return self._get_value(key="overwrite", env_name=env_name, default=default)  # type: ignore[no-any-return]

    def verbose(
        self, env_name: str | None = None, default: int | None = None
    ) -> int | None:
        """Flag verbose"""
        return self._get_value(key="verbose", env_name=env_name, default=default)  # type: ignore[no-any-return]

    def template(self, env_name: str, default: str = "{env}") -> str:
        """Flag for template"""
        return self._get_value(key="template", env_name=env_name, default=default)  # type: ignore[no-any-return]

    def template_python(self, env_name: str, default: str = "py{py}-{env}") -> str:
        """Flag for template_python."""
        return self._get_value(  # type: ignore[no-any-return]
            key="template_python", env_name=env_name, default=default
        )

    def reqs_ext(self, env_name: str, default: str = ".txt") -> str:
        """Requirements extension"""
        return self._get_value(  # type: ignore[no-any-return]
            key="reqs_ext",
            env_name=env_name,
            default=default,
        )

    def yaml_ext(self, env_name: str, default: str = ".yaml") -> str:
        """Conda yaml extension"""
        return self._get_value(  # type: ignore[no-any-return]
            key="yaml_ext",
            env_name=env_name,
            default=default,
        )

    def deps(self, env_name: str, default: Any = None) -> list[str]:
        """Conda dependencies option."""
        return self._get_value(  # type: ignore[no-any-return]
            key="deps",
            env_name=env_name,
            default=default,
        )

    def reqs(self, env_name: str, default: Any = None) -> list[str]:
        """Pip dependencies option."""
        return self._get_value(  # type: ignore[no-any-return]
            key="reqs",
            env_name=env_name,
            default=default,
        )

    def user_config(self, env_name: str | None = None) -> str | None:  # noqa: ARG002
        """Flag user_config"""
        return self._get_value(key="user_config", default=None)  # type: ignore[no-any-return]

    def allow_empty(self, env_name: str | None = None, default: bool = False) -> bool:
        """Allow empty option."""
        return self._get_value(  # type: ignore[no-any-return]
            key="allow_empty", env_name=env_name, default=default
        )

    def remove_whitespace(
        self, env_name: str | None = None, default: bool = True
    ) -> bool:
        """Remove whitespace option."""
        return self._get_value(  # type: ignore[no-any-return]
            key="remove_whitespace",
            env_name=env_name,
            default=default,
        )

    def assign_user_config(self, user: Self) -> Self:
        """Assign user_config to self."""
        from copy import deepcopy

        data = deepcopy(self.data)

        # get user envs

        if "envs" not in data:
            data["envs"] = {}

        if "overrides" not in data:
            data["overrides"] = []

        for key in ("envs", "overrides"):
            if (u := user.get_in(key)) is not None:
                d = data[key]
                if isinstance(d, list):
                    if not isinstance(u, list):
                        msg = f"expected list, got {type(u)}"
                        raise TypeError(msg)
                    d.extend(u)  # pyright: ignore[reportUnknownMemberType]
                elif isinstance(d, dict):  # pragma: no cover
                    if not isinstance(u, dict):
                        msg = f"expected dict, got {type(u)}"
                        raise TypeError(msg)
                    d.update(**u)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]

        return type(self)(data)

    def _get_output_and_templates(
        self, env_name: str, **defaults: Any
    ) -> list[str | None]:
        return [
            defaults.get(k, getattr(self, k)(env_name))
            for k in ("output", "template", "template_python")
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
            "groups",
            "extras_or_groups",
            "sort",
            "skip_package",
            "header",
            "overwrite",
            "verbose",
            "reqs",
            "deps",
            "name",
            "channels",
            "allow_empty",
            "remove_whitespace",
        ]

        data = {k: defaults.get(k, getattr(self, k)(env_name)) for k in keys}

        if not pythons:
            if output is None:
                output = filename_from_template(
                    template=template,
                    env_name=env_name,
                    ext=defaults.get("yaml_ext", self.yaml_ext(env_name)),
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
                    ext=defaults.get("yaml_ext", self.yaml_ext(env_name)),
                )
                yield ("yaml", dict(data, python=python, output=output))

    def _iter_reqs(
        self, env_name: str, remove_whitespace: bool | None = None, **defaults: Any
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        keys = [
            "extras",
            "groups",
            "extras_or_groups",
            "sort",
            "skip_package",
            "header",
            "overwrite",
            "verbose",
            "reqs",
            "allow_empty",
        ]

        output, template, _ = self._get_output_and_templates(env_name, **defaults)

        data = {k: defaults.get(k, getattr(self, k)(env_name)) for k in keys}

        # different default from yaml
        data["remove_whitespace"] = (
            remove_whitespace
            if remove_whitespace is not None
            else self.remove_whitespace(env_name, default=False)
        )

        if not (output := self.output(env_name)):  # pragma: no cover
            output = filename_from_template(
                template=template,
                env_name=env_name,
                ext=defaults.get("reqs_ext", self.reqs_ext(env_name)),
            )
        data.update(output=output)

        yield ("requirements", data)

    def iter_envs(
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
                else:  # pragma: no cover
                    msg = f"unknown style {style}"
                    raise ValueError(msg)

    @classmethod
    def from_toml_dict(
        cls, data_toml: dict[str, Any], user_config: dict[str, Any] | None = None
    ) -> Self:
        """Create from toml dictionaries."""
        data = get_in(["tool", "pyproject2conda"], data_toml, default={})

        if "default_envs" in data:
            default_envs = data.pop("default_envs")

            if "envs" not in data:
                data["envs"] = {}

            for env in default_envs:
                data["envs"][env] = {"extras_or_groups": True}

        c = cls(
            data,
            default_pythons=get_default_pythons_with_fallback(),
            all_pythons=get_all_pythons(data_toml),
        )

        # add in "default_envs"

        if user_config:  # pragma: no cover
            u = cls.from_toml_dict(user_config)
            c = c.assign_user_config(user=u)

        return c

    @classmethod
    def from_string(cls, s: str, user_config: str | None = None) -> Self:
        """Create from string representation of toml file."""
        from ._compat import tomllib

        c = cls.from_toml_dict(tomllib.loads(s))

        if user_config:
            u = cls.from_string(user_config)
            c = c.assign_user_config(user=u)
        return c

    @classmethod
    def from_file(
        cls, path: str | Path, user_config: str | Path | None = "infer"
    ) -> Self:
        """Create from toml file(s)."""
        from ._compat import tomllib

        with Path(path).open("rb") as f:
            data = tomllib.load(f)

        c = cls.from_toml_dict(data)

        if user_config == "infer" and (user_config := c.user_config()) is not None:
            # relative path
            user_config = Path(path).parent / Path(user_config)

        if user_config and Path(user_config).exists():
            u = cls.from_file(user_config)
            c = c.assign_user_config(u)

        return c
