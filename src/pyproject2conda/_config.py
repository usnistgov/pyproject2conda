from __future__ import annotations

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
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from typing import Any

    from ._typing_compat import Self


def _dict_drop_null(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


class PyProject2CondaConfig:
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
        # only include non null options
        self.options = [_dict_drop_null(option) for option in options]
        self._cache: dict[NormalizedName | None, Env] = {}

    @classmethod
    def from_string(cls, s: str, *options: dict[str, Any]) -> Self:
        pyproject = tomllib.loads(s)
        section = pyproject.get("tool", {}).get("pyproject2conda", {})
        config = PyProject2CondaSchema.model_validate(section)

        try:
            all_pythons = PyProjectRequirementsSchema.model_validate(
                pyproject
            ).all_python_versions
        except ValidationError:
            all_pythons = []

        return cls(
            *options,
            config=config,
            default_pythons=get_default_pythons_with_fallback(),
            all_pythons=all_pythons,
        )

    @classmethod
    def from_file(cls, path: Path, *options: dict[str, Any]) -> Self:
        return cls.from_string(path.read_text(encoding="utf-8"), *options)

    def update_options(self, *options: dict[str, Any]) -> Self:
        return type(self)(
            *options,
            config=self.config,
            default_pythons=self.default_pythons,
            all_pythons=self.all_pythons,
        )

    def get_env(self, env_name: NormalizedName | None) -> Env:
        if env_name not in self._cache:
            self._cache[env_name] = self.config.get_env(env_name, *self.options)
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
                ext=env.reqs_ext,
            )

        yield (
            "requirements",
            env.as_requirements(update={"output": output}),
        )

    def _iter_yaml(self, env_name: str) -> Iterator[tuple[str, EnvYaml]]:
        env_name = canonicalize_name(env_name)
        env = self.get_env(env_name)
        pythons = self._python(env_name)

        if not pythons:
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
            envs = self.config.envs.keys()

        for env_name in map(canonicalize_name, envs):
            for style in self.get_env(env_name).style:
                if style == "yaml":
                    yield from self._iter_yaml(env_name)
                elif style == "requirements":
                    yield from self._iter_reqs(env_name)
                else:  # pragma: no cover
                    msg = f"unknown style {style}"
                    raise ValueError(msg)
