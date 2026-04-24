from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.utils import canonicalize_name

from ._normalized_requirements import (
    CondaRequirement,
    NormalizedRequirement,
    canonicalize_pip_requirement,
    canonicalize_str_requirement,
)
from ._schema import PyProjectRequirementsSchema
from .resolve_dependencies import (
    ResolveDependencyGroups,
    ResolveOptionalDependencies,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from packaging.utils import NormalizedName

    from ._schema import DependencyMapping
    from ._typing_compat import Self


# * Pyproject schema


def _check_allow_empty(allow_empty: bool) -> str:
    msg = "No dependencies for this environment\n"
    if allow_empty:
        return msg
    raise ValueError(msg)


@dataclass
class ParseRequirements:
    package_name: NormalizedName
    dependencies: list[NormalizedRequirement]
    optional_dependencies: ResolveOptionalDependencies
    dependency_groups: ResolveDependencyGroups
    build_system_requires: list[NormalizedRequirement]
    dependency_map: dict[NormalizedName, DependencyMapping] = field(
        default_factory=dict
    )
    requires_python: str | None = None

    @classmethod
    def from_string(
        cls,
        s: str,
        dependency_map: dict[NormalizedName, DependencyMapping] | None = None,
    ) -> Self:

        from ._compat import tomllib

        data = tomllib.loads(s)

        pyproject = PyProjectRequirementsSchema.model_validate(data)

        optional_dependencies = ResolveOptionalDependencies(
            package_name=pyproject.project.name,
            unresolved={
                name: [canonicalize_str_requirement(req) for req in reqs]
                for name, reqs in pyproject.project.optional_dependencies.items()
            },
        )

        dependency_groups = ResolveDependencyGroups(
            package_name=pyproject.project.name,
            unresolved=pyproject.dependency_groups,
            optional_dependencies=optional_dependencies,
        )

        return cls(
            package_name=pyproject.project.name,
            dependencies=[
                canonicalize_str_requirement(dep)
                for dep in pyproject.project.dependencies
            ],
            optional_dependencies=optional_dependencies,
            dependency_groups=dependency_groups,
            build_system_requires=[
                canonicalize_str_requirement(dep)
                for dep in pyproject.build_system.requires
            ],
            dependency_map=dependency_map or {},
            requires_python=pyproject.project.requires_python,
        )

    @classmethod
    def from_file(
        cls,
        p: Path,
        dependency_map: dict[NormalizedName, DependencyMapping] | None = None,
    ) -> Self:
        return cls.from_string(p.read_text(encoding="utf-8"), dependency_map)

    def _resolve_extras_and_groups(
        self,
        extras: Iterable[str] = (),
        groups: Iterable[str] = (),
        extras_or_groups: Iterable[str] = (),
    ) -> tuple[list[NormalizedName], list[NormalizedName]]:

        extras_out = [canonicalize_name(x) for x in extras]
        groups_out = [canonicalize_name(x) for x in groups]

        for extra_or_group in map(canonicalize_name, extras_or_groups):
            if extra_or_group in self.optional_dependencies.unresolved:
                extras_out.append(extra_or_group)
            elif extra_or_group in self.dependency_groups.unresolved:
                groups_out.append(extra_or_group)
            else:
                msg = f"extra-or-group {extra_or_group} not in extras or groups"
                raise ValueError(msg)

        return extras_out, groups_out

    def pip_requirements(
        self,
        *,
        extras: Iterable[str] = (),
        groups: Iterable[str] = (),
        extras_or_groups: Iterable[str] = (),
        skip_package: bool = False,
        reqs: Iterable[str] = (),
    ) -> set[NormalizedRequirement]:
        """Iterator of requirements"""
        extras, groups = self._resolve_extras_and_groups(
            extras, groups, extras_or_groups
        )

        out: set[NormalizedRequirement] = {
            canonicalize_pip_requirement(req) for req in reqs
        }

        if not skip_package:
            out.update(self.dependencies)

        out.update(self.optional_dependencies.get(extras))
        out.update(self.dependency_groups.get(groups))

        return out

    def conda_and_pip_requirements(  # noqa: C901
        self,
        *,
        extras: Iterable[str] = (),
        groups: Iterable[str] = (),
        extras_or_groups: Iterable[str] = (),
        skip_package: bool = False,
        pip_deps: Iterable[str] = (),
        pip_only: bool = False,
        conda_deps: Iterable[str] = (),
        python_version: str | None = None,
        python_include: str | None = None,
    ) -> tuple[set[CondaRequirement], set[NormalizedRequirement]]:

        if python_include == "infer":
            if self.requires_python is None:
                msg = "No value for `requires-python` in pyproject.toml file"
                raise ValueError(msg)
            python_include = str(
                NormalizedRequirement(f"python {self.requires_python}")
            )

        pip_reqs = {canonicalize_pip_requirement(req) for req in pip_deps}
        env = {"python_version": python_version} if python_version else {}
        conda_reqs = {
            dep.update(marker=None, extras=None)
            for dep in map(CondaRequirement, conda_deps)
            if dep.evaluate(env)
        }

        override_table = self.dependency_map
        for dep in self.pip_requirements(
            extras=extras,
            groups=groups,
            extras_or_groups=extras_or_groups,
            skip_package=skip_package,
        ):
            name = dep.name
            if pip_only and name != "python":
                pip_reqs.add(dep)

            elif (override := override_table.get(name)) is not None:
                if override.pip:
                    pip_reqs.add(dep)
                elif not override.skip and (
                    cdep := CondaRequirement(str(dep))
                ).evaluate(env):
                    conda_reqs.add(
                        cdep.update(marker=None, extras=None, channel=override.channel)
                    )

                conda_reqs.update(
                    cdep
                    for cdep in (CondaRequirement(p) for p in override.packages)
                    if cdep.evaluate(env)
                )
            elif (cdep := CondaRequirement(str(dep))).evaluate(env):
                conda_reqs.add(cdep.update(marker=None, extras=None))

        if pip_reqs and not any(dep.name == "pip" for dep in conda_reqs):
            conda_reqs.add(CondaRequirement("pip"))

        if python_include:
            conda_reqs.add(CondaRequirement(python_include))

        return conda_reqs, pip_reqs

    def to_conda_yaml(
        self,
        *,
        extras: Iterable[str] = (),
        groups: Iterable[str] = (),
        extras_or_groups: Iterable[str] = (),
        pip_deps: Iterable[str] = (),
        conda_deps: Iterable[str] = (),
        name: str | None = None,
        channels: Iterable[str] = (),
        python_include: str | None = None,
        python_version: str | None = None,
        skip_package: bool = False,
        pip_only: bool = False,
        header_cmd: str | None = None,
        output: str | Path | None = None,
        allow_empty: bool = False,
    ) -> str:
        """Create yaml string."""
        conda_reqs, pip_reqs = self.conda_and_pip_requirements(
            extras=extras,
            groups=groups,
            extras_or_groups=extras_or_groups,
            skip_package=skip_package,
            pip_only=pip_only,
            pip_deps=pip_deps,
            conda_deps=conda_deps,
            python_include=python_include,
            python_version=python_version,
        )

        if not conda_reqs and not pip_reqs:
            return _check_allow_empty(allow_empty)

        pip_deps = sorted(map(str, pip_reqs))
        order = defaultdict(lambda: 1, {"python": 0, "pip": 2})
        conda_deps = [
            str(_).replace("~=", "=")
            for _ in sorted(conda_reqs, key=lambda x: (order[x.name], x.name))
        ]

        out = _conda_yaml(
            name=name,
            channels=channels,
            conda_deps=conda_deps,
            pip_deps=pip_deps,
        )

        out = _add_header(out, header_cmd)

        _optional_write(out, output)

        return out


# ** output ----------------------------------------------------------------------------
def _conda_yaml(
    name: str | None = None,
    channels: str | Iterable[str] | None = None,
    conda_deps: str | Iterable[str] | None = None,
    pip_deps: str | Iterable[str] | None = None,
    add_file_eol: bool = True,
) -> str:
    def _as_list(x: str | Iterable[str]) -> Iterable[str]:
        if isinstance(x, str):
            return [x]
        return x

    if not conda_deps:
        msg = "Must have at least one conda dependency (i.e., pip)"
        raise ValueError(msg)

    out: list[str] = []
    if name is not None:
        out.append(f"name: {name}")

    if channels:
        out.append("channels:")
        out.extend(f"  - {channel}" for channel in _as_list(channels))

    out.append("dependencies:")
    out.extend(f"  - {dep}" for dep in _as_list(conda_deps))

    if pip_deps:
        if "pip" not in conda_deps:  # pragma: no cover
            msg = "Must have pip in conda_deps"
            raise ValueError(msg)
        out.append("  - pip:")
        out.extend(f"      - {dep}" for dep in _as_list(pip_deps))

    s = "\n".join(out)

    if add_file_eol:  # pragma: no cover
        s += "\n"

    return s


def _create_header(cmd: str | None = None) -> str:
    from textwrap import dedent

    if cmd:  # pylint: disable=consider-ternary-expression
        header = dedent(
            f"""
        This file is autogenerated by pyproject2conda
        with the following command:

            $ {cmd}

        You should not manually edit this file.
        Instead edit the corresponding pyproject.toml file.
        """
        )
    else:
        header = dedent(
            """
        This file is autogenerated by pyproject2conda.
        You should not manually edit this file.
        Instead edit the corresponding pyproject.toml file.
        """
        )

    # prepend '# '
    lines: list[str] = []
    for line in header.split("\n"):
        if not line.strip():
            lines.append("#")
        else:
            lines.append("# " + line)
    return "\n".join(lines)


def _add_header(string: str, header_cmd: str | None) -> str:
    if header_cmd is not None:
        return _create_header(header_cmd) + "\n" + string
    return string


def _optional_write(
    string: str,
    output: str | Path | None,
    mode: str = "w",  # force: bool = False,
) -> None:
    if output is None:
        return

    path = Path(output)

    with path.open(mode) as f:
        _ = f.write(string)
