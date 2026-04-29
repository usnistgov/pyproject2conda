from __future__ import annotations

from collections import ChainMap
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from packaging.utils import NormalizedName, canonicalize_name
from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)

from ._utils import (
    validate_dict_normalizedname,
    validate_list_of_normalizedname,
    validate_list_of_str,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from ._typing_compat import Self


# * Validation ----------------------------------------------------------------

ListString = Annotated[list[str], BeforeValidator(validate_list_of_str)]
ListNormalizedName = Annotated[
    list[NormalizedName], BeforeValidator(validate_list_of_normalizedname)
]


# * PyProject2Conda -----------------------------------------------------------
class Overwrite(str, Enum):
    """Options for ``--overwrite``"""

    check = "check"
    skip = "skip"
    force = "force"


class _BaseOptionsRequirements(BaseModel):
    # config
    skip_package: bool = False
    allow_empty: bool = False
    header: bool | None = None
    custom_command: str | None = None
    overwrite: Overwrite = Overwrite.check
    verbose: int = 0
    # dependencies
    pip_deps: ListString = Field(
        default_factory=list,
        validation_alias=AliasChoices("reqs", "pip-deps"),
    )


class _BaseOptionsYaml(_BaseOptionsRequirements):
    # python info
    python: str | list[str] = Field(default_factory=list)
    python_include: str | None = None
    python_version: str | None = None
    # yaml
    name: str | None = None
    channels: ListString = Field(default_factory=list)
    pip_only: bool = False
    # dependencies
    conda_deps: ListString = Field(
        default_factory=list,
        validation_alias=AliasChoices("deps", "conda-deps"),
    )


class _BaseOptions(_BaseOptionsYaml):
    model_config = ConfigDict(
        alias_generator=lambda field_name: field_name.replace("_", "-"),
        validate_by_name=True,
        validate_by_alias=True,
        extra="forbid",
    )

    # output
    template: str = r"{env}"
    template_python: str = r"py{py}-{env}"
    requirements_ext: str = Field(
        default=".txt", validation_alias=AliasChoices("reqs_ext", "reqs-ext")
    )
    yaml_ext: str = ".yaml"

    style: Annotated[
        list[Literal["yaml", "requirements", "conda-requirements", "json"]],
        BeforeValidator(validate_list_of_str),
    ] = Field(default=["yaml"])


class _EnvMixin(BaseModel):
    output: Path | None = None
    groups: ListNormalizedName = Field(default_factory=list)
    extras: ListNormalizedName = Field(default_factory=list)
    extras_or_groups: ListNormalizedName = Field(default_factory=list)


class EnvRequirements(_BaseOptionsRequirements, _EnvMixin):
    pass


class EnvYaml(_BaseOptionsYaml, _EnvMixin):
    pass


class Env(_BaseOptions, _EnvMixin):
    """Environment table"""

    def as_requirements(
        self, update: Mapping[Any, Any] | None = None
    ) -> EnvRequirements:
        new = self.model_copy(update=update) if update else self
        return EnvRequirements.model_validate(new.model_dump(exclude_unset=True))

    def as_yaml(self, update: Mapping[Any, Any] | None = None) -> EnvYaml:
        new = self.model_copy(update=update) if update else self
        return EnvYaml.model_validate(new.model_dump(exclude_unset=True))


class _OverrideEnvs(Env):
    """Override envs table"""

    envs: ListNormalizedName


class DependencyMapping(BaseModel):
    """Dependency mapping table"""

    pip: bool = False
    skip: bool = False
    channel: str | None = None
    packages: ListString = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        if self.channel is not None and self.channel.strip().lower() in {"pip", "pypi"}:
            self.channel = None
            self.pip = True
        return self


class _Dependencies(BaseModel):
    dependencies: Annotated[
        dict[NormalizedName, DependencyMapping],
        BeforeValidator(validate_dict_normalizedname),
    ] = Field(default_factory=dict)


class PyProject2CondaSchema(_BaseOptions, _Dependencies):
    """Total schema"""

    default_envs: ListNormalizedName = Field(default_factory=list)

    envs: Annotated[
        dict[NormalizedName, Env], BeforeValidator(validate_dict_normalizedname)
    ] = Field(default_factory=dict)
    overrides: list[_OverrideEnvs] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_model_after(self) -> Self:
        for env in self.default_envs:
            self.envs[env] = Env(extras_or_groups=[env])
        return self

    # access
    @cached_property
    def _base_dict(self) -> dict[str, Any]:
        return self.model_dump(
            exclude={"default_envs", "dependencies", "envs", "overrides"},
            exclude_unset=True,
        )

    def _chainmap_env(
        self,
        env_name: str | None,
        *options: dict[str, Any],
    ) -> ChainMap[str, Any]:

        if env_name is None:
            env_options = []
        else:
            if (env_name := canonicalize_name(env_name)) not in self.envs:
                msg = f"env {env_name} not in config"
                raise ValueError(msg)
            env_options = [
                *reversed([
                    override.model_dump(exclude={"envs"}, exclude_unset=True)
                    for override in self.overrides
                    if env_name in override.envs
                ]),
                self.envs[env_name].model_dump(exclude_unset=True),
            ]

        return ChainMap(
            *options,
            *env_options,
            self._base_dict,
        )

    def get_env(
        self,
        env_name: str | None,
        *options: dict[str, Any],
    ) -> Env:
        return Env.model_validate(self._chainmap_env(env_name, *options))


# * PyProject Schema ----------------------------------------------------------


class _PyProjectBaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: field_name.replace("_", "-"),
        validate_by_alias=True,
        validate_by_name=True,
    )


class _ProjectSchema(_PyProjectBaseSchema):
    name: Annotated[NormalizedName, BeforeValidator(canonicalize_name)]
    classifiers: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    optional_dependencies: Annotated[
        dict[NormalizedName, list[str]],
        BeforeValidator(validate_dict_normalizedname),
    ] = Field(default_factory=dict)

    requires_python: str | None = None


class _BuildSystemSchema(_PyProjectBaseSchema):
    requires: list[str] = Field(default_factory=list)


class PyProjectRequirementsSchema(_PyProjectBaseSchema):
    build_system: _BuildSystemSchema = Field(default_factory=_BuildSystemSchema)
    project: _ProjectSchema
    dependency_groups: Annotated[
        dict[NormalizedName, list[str | dict[str, str]]],
        BeforeValidator(validate_dict_normalizedname),
    ] = Field(default_factory=dict)

    @cached_property
    def all_python_versions(self) -> list[str]:
        import re

        pattern = re.compile(r"Programming Language :: Python :: (\d+\.\d+)$")
        return [
            match.group(1)
            for classifier in self.project.classifiers
            if (match := pattern.match(classifier))
        ]


class _ToolSchema(BaseModel):
    pyproject2conda: PyProject2CondaSchema = Field(
        default_factory=PyProject2CondaSchema
    )


class PyProjectRequirementsWith2CondaSchema(
    PyProjectRequirementsSchema,
):
    tool: _ToolSchema = Field(default_factory=_ToolSchema)
