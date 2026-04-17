from __future__ import annotations

from collections import ChainMap
from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Literal

from packaging.utils import NormalizedName, canonicalize_name
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from ._compat import tomllib
from .utils import (
    conda_env_name_from_template,
    filename_from_template,
    get_all_pythons,
    get_default_pythons_with_fallback,
    select_pythons,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping
    from pathlib import Path
    from typing import Any

    from ._typing_compat import Self


def _validate_list_of_str(s: str | Iterable[str]) -> list[str]:
    if isinstance(s, list):
        return s
    if isinstance(s, str):
        return [s]
    return list(s)


def _validate_list_of_normalizedname(s: Any) -> list[NormalizedName]:
    if isinstance(s, str):
        s = [s]
    return [canonicalize_name(name) for name in s]


ListString = Annotated[list[str], BeforeValidator(_validate_list_of_str)]
ListNormalizedName = Annotated[
    list[NormalizedName], BeforeValidator(_validate_list_of_normalizedname)
]


class BaseOptions(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: field_name.replace("_", "-"),
        validate_by_name=True,
        validate_by_alias=True,
        extra="forbid",
    )

    # output
    template_python: str = r"py{py}-{env}"
    template: str = r"{env}"
    style: Annotated[
        list[Literal["yaml", "requirements", "conda-requirements", "json"]],
        BeforeValidator(_validate_list_of_str),
    ] = Field(default=["yaml"])
    reqs_ext: str = ".txt"
    yaml_ext: str = ".yaml"
    # python info
    python: ListString = Field(default_factory=list)
    python_include: str | None = None
    python_version: str | None = None
    # config
    allow_empty: bool = False
    sort: bool = True
    header: bool | None = None
    custom_command: str | None = None
    skip_package: bool = False
    overwrite: Literal["check", "skip", "force"] = "check"
    # yaml
    name: str | None = None
    channels: ListString = Field(default_factory=list)
    pip_only: bool = False
    # dependencies
    reqs: ListString = Field(default_factory=list)
    deps: ListString = Field(default_factory=list)


class Dependencies(BaseModel):
    """Dependency mapping table"""

    pip: bool = False
    skip: bool = False
    channel: str | None = None
    packages: ListNormalizedName = Field(default_factory=list)


class Env(BaseOptions):
    """Environment table"""

    output: str | None = None
    groups: ListNormalizedName = Field(default_factory=list)
    extras: ListNormalizedName = Field(default_factory=list)
    extras_or_groups: ListNormalizedName = Field(default_factory=list)


class OverrideEnvs(Env):
    """Override envs table"""

    envs: ListNormalizedName = Field(default_factory=list)

    @field_validator("envs", mode="after")
    @classmethod
    def validate_envs(cls, envs: ListNormalizedName) -> ListNormalizedName:
        if not envs:
            msg = "must specify env in overrides"
            raise ValueError(msg)
        return envs


class PyProject2CondaSchema(BaseOptions):
    """Total schema"""

    default_envs: ListNormalizedName = Field(default_factory=list)

    dependencies: dict[str, Dependencies] = Field(default_factory=dict)
    envs: dict[NormalizedName, Env] = Field(default_factory=dict)
    overrides: list[OverrideEnvs] = Field(default_factory=list)

    @field_validator("envs", mode="before")
    @classmethod
    def _validate_envs(cls, envs: Mapping[Any, Env]) -> dict[NormalizedName, Env]:
        return {canonicalize_name(name): config for name, config in envs.items()}

    @model_validator(mode="after")
    def _validate_model_after(self) -> Self:
        for env in self.default_envs:
            self.envs[env] = Env(extras_or_groups=[env])
        return self

    @classmethod
    def from_path(cls, path: Path) -> Self:
        return cls.from_string(path.read_text(encoding="utf-8"))

    @classmethod
    def from_string(cls, s: str) -> Self:
        pyproject = tomllib.loads(s)
        section = pyproject.get("tool", {}).get("pyproject2conda", {})
        return cls.model_validate(section)

    @cached_property
    def _base_dict(self) -> dict[str, Any]:
        return self.model_dump(
            exclude={"default_envs", "dependencies", "envs", "overrides"},
            exclude_unset=True,
        )

    @cached_property
    def base_options(self) -> BaseOptions:
        return BaseOptions.model_validate(self._base_dict)

    def _get_env_dict(self, env_name: NormalizedName) -> dict[str, Any]:
        if env_name in self.envs:
            return self.envs[env_name].model_dump(exclude_unset=True)
        return {}

    def _get_overrides_dict(self, env_name: NormalizedName) -> Iterator[dict[str, Any]]:
        return reversed([
            override.model_dump(exclude={"envs"}, exclude_unset=True)
            for override in self.overrides
            if env_name in override.envs
        ])

    def _chainmap_env(
        self,
        env_name: str | None,
        *options: dict[str, Any],
    ) -> ChainMap[str, Any]:

        if env_name is None:
            env_options = []
        else:
            env_name = canonicalize_name(env_name)
            env_options = [
                *self._get_overrides_dict(env_name),
                self._get_env_dict(env_name),
            ]

        return ChainMap(
            *options,
            *env_options,
            self._base_dict,
        )

    def env_config(
        self,
        env_name: str | None,
        *options: dict[str, Any],
    ) -> Env:
        return Env.model_validate(self._chainmap_env(env_name, *options))


class Config:
    def __init__(
        self,
        *options: dict[str, Any],
        config: PyProject2CondaSchema,
        default_pythons: list[str],
        all_pythons: list[str],
    ) -> None:
        self.config = config
        self.default_pythons = default_pythons
        self.all_pythons = all_pythons
        self.options = options
        self._cache: dict[NormalizedName | None, Env] = {}

    def update_options(self, *options: dict[str, Any]) -> Self:
        return type(self)(
            *options,
            config=self.config,
            default_pythons=self.default_pythons,
            all_pythons=self.all_pythons,
        )

    def _get_env(self, env_name: NormalizedName | None) -> Env:
        if env_name not in self._cache:
            self._cache[env_name] = self.config.env_config(env_name, *self.options)
        return self._cache[env_name]

    def _python(self, env_name: NormalizedName) -> list[str]:
        out = self._get_env(env_name).python
        return select_pythons(out, self.default_pythons, self.all_pythons)

    @classmethod
    def from_string(cls, s: str, *options: dict[str, Any]) -> Self:
        pyproject = tomllib.loads(s)
        section = pyproject.get("tool", {}).get("pyproject2conda", {})
        config = PyProject2CondaSchema.model_validate(section)

        return cls(
            *options,
            config=config,
            default_pythons=get_default_pythons_with_fallback(),
            all_pythons=get_all_pythons(pyproject),
        )

    @classmethod
    def from_file(cls, path: Path, *options: dict[str, Any]) -> Self:
        return cls.from_string(path.read_text(encoding="utf-8"), *options)

    def _iter_reqs(self, env_name: str) -> Iterator[tuple[str, Env]]:
        env_name = canonicalize_name(env_name)

        env = self._get_env(env_name)
        if not (output := env.output):
            output = filename_from_template(
                template=env.template,
                env_name=env_name,
                ext=env.reqs_ext,
            )

            yield (
                "requirements",
                env.model_validate(
                    env.model_copy(
                        update={"style": ["requirements"], "output": output}
                    ).model_dump()
                ),
            )

    def _iter_yaml(self, env_name: str) -> Iterator[tuple[str, Env]]:
        env_name = canonicalize_name(env_name)
        env = self._get_env(env_name)
        pythons = self._python(env_name)

        if not pythons:
            yield (
                "yaml",
                env.model_validate(
                    env.model_copy(
                        update={
                            "style": ["yaml"],
                            "output": env.output
                            or filename_from_template(
                                template=env.template,
                                env_name=env_name,
                                ext=env.yaml_ext,
                            ),
                            "name": conda_env_name_from_template(
                                name=env.name,
                                python_version=env.python_version,
                                env_name=env_name,
                            ),
                        }
                    ).model_dump()
                ),
            )

        else:
            for python in pythons:
                yield (
                    "yaml",
                    env.model_validate(
                        env.model_copy(
                            update={
                                "style": ["yaml"],
                                "output": filename_from_template(
                                    template=env.template_python,
                                    python_version=python,
                                    env_name=env_name,
                                    ext=env.yaml_ext,
                                ),
                                "name": conda_env_name_from_template(
                                    name=env.name,
                                    python_version=python,
                                    env_name=env_name,
                                ),
                                "python": [python],
                            }
                        ).model_dump()
                    ),
                )

    def iter_envs(self, envs: Iterable[str] | None = None) -> Iterator[tuple[str, Env]]:
        if not envs:
            envs = self.config.envs.keys()

        for env_name in map(canonicalize_name, envs):
            for style in self._get_env(env_name).style:
                if style == "yaml":
                    yield from self._iter_yaml(env_name)
                elif style == "requirements":
                    yield from self._iter_reqs(env_name)
                else:  # pragma: no cover
                    msg = f"unknown style {style}"
                    raise ValueError(msg)
