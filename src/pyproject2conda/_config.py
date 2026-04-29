from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from packaging.utils import NormalizedName, canonicalize_name
from pydantic import ValidationError

from ._compat import tomllib
from ._schema import (
    Env,
    EnvRequirements,
    EnvYaml,
    PyProject2CondaSchema,
    PyProjectRequirementsSchema,
)
from ._utils import (
    conda_env_name_from_template,
    get_default_pythons_with_fallback,
    path_from_template,
    select_pythons,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from typing import Any

    from ._typing_compat import Self


def _dict_drop_null(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


@dataclass
class PyProject2CondaConfig:
    schema: PyProject2CondaSchema
    default_pythons: list[str] = field(default_factory=list)
    all_pythons: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    _cache: dict[NormalizedName | None, Env] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        # only include non null options
        self.options = _dict_drop_null(self.options)

    @classmethod
    def from_schema(
        cls,
        schema: PyProject2CondaSchema,
        *,
        default_pythons: Sequence[str] | None = (),
        all_pythons: Sequence[str] = (),
        options: dict[str, Any] | None = None,
    ) -> Self:
        if default_pythons is None:
            default_pythons = get_default_pythons_with_fallback()

        return cls(
            schema=schema,
            default_pythons=list(default_pythons),
            all_pythons=list(all_pythons),
            options=options or {},
        )

    @classmethod
    def from_string(
        cls,
        s: str,
        *,
        default_pythons: Sequence[str] | None = (),
        all_pythons: Sequence[str] | None = (),
        options: dict[str, Any] | None = None,
        keys: Sequence[str] = ("tool", "pyproject2conda"),
    ) -> Self:
        pyproject = tomllib.loads(s)
        section = pyproject
        if keys:
            for key in keys:
                section = section.get(key, {})

        schema = PyProject2CondaSchema.model_validate(section)

        if all_pythons is None:
            try:
                all_pythons = PyProjectRequirementsSchema.model_validate(
                    pyproject
                ).all_python_versions
            except ValidationError:
                all_pythons = []

        return cls.from_schema(
            schema=schema,
            default_pythons=default_pythons,
            all_pythons=list(all_pythons),
            options=options or {},
        )

    def update_options(self, options: dict[str, Any]) -> Self:
        return type(self)(
            schema=self.schema,
            default_pythons=self.default_pythons,
            all_pythons=self.all_pythons,
            options=options,
        )

    def get_env(self, env_name: NormalizedName | None) -> Env:
        if env_name not in self._cache:
            self._cache[env_name] = self.schema.get_env(env_name, self.options)
        return self._cache[env_name]

    def parse_pythons(
        self,
        python_include: str | None,
        python_version: str | None,
        python: str | None,
    ) -> tuple[str | None, str | None]:
        if python:
            python = select_pythons(
                [python],
                self.default_pythons,
                self.all_pythons,
            )[0]
            return f"python~={python}", python

        return python_include, python_version

    def _python(self, env_name: NormalizedName) -> list[str]:
        pythons = self.get_env(env_name).python
        if isinstance(pythons, str):
            pythons = [pythons]
        return select_pythons(pythons, self.default_pythons, self.all_pythons)

    def _iter_reqs(self, env_name: str) -> Iterator[tuple[str, EnvRequirements]]:
        env_name = canonicalize_name(env_name)

        env = self.get_env(env_name)
        if not (output := env.output):
            output = path_from_template(
                template=env.template,
                env_name=env_name,
                ext=env.requirements_ext,
            )

        yield (
            "requirements",
            env.as_requirements(update={"output": output}),
        )

    def _iter_yaml(self, env_name: str) -> Iterator[tuple[str, EnvYaml]]:
        env_name = canonicalize_name(env_name)
        env = self.get_env(env_name)
        if not (pythons := self._python(env_name)):
            yield (
                "yaml",
                env.as_yaml(
                    update={
                        "output": env.output
                        or path_from_template(
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
                ),
            )

        else:
            for python in pythons:
                yield (
                    "yaml",
                    env.as_yaml(
                        update={
                            "output": path_from_template(
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
                            "python": python,
                        }
                    ),
                )

    def iter_envs(
        self, envs: Iterable[str] | None = None
    ) -> Iterator[tuple[str, EnvRequirements | EnvYaml]]:
        if not envs:
            envs = self.schema.envs.keys()  # pylint: disable=no-member

        for env_name in (canonicalize_name(e) for e in envs):
            for style in self.get_env(env_name).style:
                if style == "yaml":
                    yield from self._iter_yaml(env_name)
                elif style == "requirements":
                    yield from self._iter_reqs(env_name)
                else:  # pragma: no cover
                    msg = f"unknown style {style}"
                    raise ValueError(msg)
