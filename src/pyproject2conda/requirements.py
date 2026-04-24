"""
Requirements parsing (:mod:`~pyproject2conda.requirements`)
===========================================================
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.utils import NormalizedName, canonicalize_name

from ._normalized_requirements import (
    CondaRequirement,
    NormalizedRequirement,
    canonicalize_pip_requirement,
    canonicalize_requirement,
)
from ._resolve_dependencies import (
    ResolveDependencyGroups,
    ResolveOptionalDependencies,
)
from ._schema import PyProjectRequirementsWith2CondaSchema
from ._utils import list_to_str

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ._schema import DependencyMapping
    from ._typing_compat import Self


# * Pyproject schema


def _check_allow_empty(allow_empty: bool) -> str:
    msg = "No dependencies for this environment\n"
    if allow_empty:
        return msg
    raise ValueError(msg)


def _pip_reqs_to_list(pip_reqs: set[NormalizedRequirement]) -> list[str]:
    return sorted(map(str, pip_reqs))


def _conda_reqs_to_list(conda_reqs: set[CondaRequirement]) -> list[str]:
    order = defaultdict(lambda: 1, {"python": 0, "pip": 2})
    return [
        str(_).replace("~=", "=")
        for _ in sorted(conda_reqs, key=lambda x: (order[x.name], str(x)))
    ]


def _validate_iterable_str(x: Iterable[str]) -> Iterable[str]:
    if isinstance(x, str):
        return [x]
    return x


def conda_and_pip_reqs_to_list(
    conda_reqs: set[CondaRequirement], pip_reqs: set[NormalizedRequirement]
) -> tuple[list[str], list[str]]:
    """Convert requirements to sorted lists"""
    return _conda_reqs_to_list(conda_reqs), _pip_reqs_to_list(pip_reqs)


@dataclass
class ParseRequirements:
    """Parse requirements"""

    package_name: NormalizedName
    dependencies: list[NormalizedRequirement]
    optional_dependencies: ResolveOptionalDependencies
    dependency_groups: ResolveDependencyGroups
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
        """Create from toml string."""
        from ._compat import tomllib

        data = tomllib.loads(s)

        pyproject = PyProjectRequirementsWith2CondaSchema.model_validate(data)

        build_system = (
            {
                canonicalize_name(
                    "build-system.requires"
                ): pyproject.build_system.requires
            }
            if pyproject.build_system.requires
            else {}
        )

        optional_dependencies = ResolveOptionalDependencies(
            package_name=pyproject.project.name,
            unresolved={
                name: [canonicalize_requirement(req) for req in reqs]
                for name, reqs in {
                    **build_system,
                    **pyproject.project.optional_dependencies,
                }.items()
            },
        )

        dependency_groups = ResolveDependencyGroups(
            package_name=pyproject.project.name,
            unresolved={**build_system, **pyproject.dependency_groups},  # type: ignore[dict-item]
            optional_dependencies=optional_dependencies,
        )

        if dependency_map is None:
            dependency_map = pyproject.tool.pyproject2conda.dependencies

        return cls(
            package_name=pyproject.project.name,
            dependencies=[
                canonicalize_requirement(dep) for dep in pyproject.project.dependencies
            ],
            optional_dependencies=optional_dependencies,
            dependency_groups=dependency_groups,
            dependency_map=dependency_map or {},
            requires_python=pyproject.project.requires_python,
        )

    @classmethod
    def from_path(
        cls,
        p: str | Path,
        dependency_map: dict[NormalizedName, DependencyMapping] | None = None,
    ) -> Self:
        """Create from toml path."""
        return cls.from_string(Path(p).read_text(encoding="utf-8"), dependency_map)

    def _resolve_extras_and_groups(
        self,
        extras: Iterable[str] = (),
        groups: Iterable[str] = (),
        extras_or_groups: Iterable[str] = (),
    ) -> tuple[list[NormalizedName], list[NormalizedName]]:

        extras_out = [canonicalize_name(x) for x in _validate_iterable_str(extras)]
        groups_out = [canonicalize_name(x) for x in _validate_iterable_str(groups)]

        for extra_or_group in map(
            canonicalize_name, _validate_iterable_str(extras_or_groups)
        ):
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
            canonicalize_pip_requirement(req) for req in _validate_iterable_str(reqs)
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
        """To conda and pip requirements."""
        if python_include == "infer":
            if self.requires_python is None:
                msg = "No value for `requires-python` in pyproject.toml file"
                raise ValueError(msg)
            python_include = str(
                NormalizedRequirement(f"python {self.requires_python}")
            )

        pip_reqs = {
            canonicalize_pip_requirement(req)
            for req in _validate_iterable_str(pip_deps)
        }
        env = {"python_version": python_version} if python_version else {}
        conda_reqs = {
            dep.update(marker=None, extras=None)
            for dep in map(CondaRequirement, _validate_iterable_str(conda_deps))
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
                    cdep.update(marker=None, extras=None)
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
        extras: Iterable[str] | None = None,
        groups: Iterable[str] | None = None,
        extras_or_groups: Iterable[str] | None = None,
        pip_deps: Iterable[str] | None = None,
        conda_deps: Iterable[str] | None = None,
        name: str | None = None,
        channels: Iterable[str] | None = None,
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
            extras=extras or (),
            groups=groups or (),
            extras_or_groups=extras_or_groups or (),
            skip_package=skip_package,
            pip_only=pip_only,
            pip_deps=pip_deps or (),
            conda_deps=conda_deps or (),
            python_include=python_include,
            python_version=python_version,
        )

        if not conda_reqs and not pip_reqs:
            return _check_allow_empty(allow_empty)

        out = _conda_yaml(
            name=name,
            channels=channels,
            conda_deps=_conda_reqs_to_list(conda_reqs),
            pip_deps=_pip_reqs_to_list(pip_reqs),
        )

        out = _add_header(out, header_cmd)

        _optional_write(out, output)

        return out

    def to_requirements(
        self,
        *,
        extras: Iterable[str] | None = None,
        groups: Iterable[str] | None = None,
        extras_or_groups: Iterable[str] | None = None,
        skip_package: bool = False,
        header_cmd: str | None = None,
        output: str | Path | None = None,
        pip_deps: Iterable[str] | None = None,
        allow_empty: bool = False,
    ) -> str:
        """Create requirements string."""
        pip_reqs = self.pip_requirements(
            extras=extras or (),
            groups=groups or (),
            extras_or_groups=extras_or_groups or (),
            skip_package=skip_package,
            reqs=pip_deps or (),
        )

        if not pip_reqs:
            return _check_allow_empty(allow_empty)

        out = _add_header(list_to_str(_pip_reqs_to_list(pip_reqs)), header_cmd)

        _optional_write(out, output)
        return out

    def to_conda_requirements(
        self,
        *,
        extras: Iterable[str] | None = None,
        groups: Iterable[str] | None = None,
        extras_or_groups: Iterable[str] | None = None,
        channels: Sequence[str] | None = None,
        python_include: str | None = None,
        python_version: str | None = None,
        prepend_channel: bool = False,
        output_conda: Path | None = None,
        output_pip: Path | None = None,
        skip_package: bool = False,
        header_cmd: str | None = None,
        conda_deps: str | Iterable[str] | None = None,
        pip_deps: str | Iterable[str] | None = None,
    ) -> tuple[str, str]:
        """Create conda and pip requirements files."""
        conda_deps, pip_deps = conda_and_pip_reqs_to_list(
            *self.conda_and_pip_requirements(
                extras=extras or (),
                groups=groups or (),
                extras_or_groups=extras_or_groups or (),
                skip_package=skip_package,
                pip_deps=pip_deps or (),
                conda_deps=conda_deps or (),
                python_include=python_include,
                python_version=python_version,
            )
        )

        if conda_deps and channels and prepend_channel:
            channels = list(channels)
            if len(channels) != 1:
                msg = "Can only pass single channel to prepend."
                raise ValueError(msg)
            channel = channels[0]
            # add in channel if none exists

            conda_deps = [
                dep if "::" in dep else f"{channel}::{dep}" for dep in conda_deps
            ]

        conda_deps_str = _add_header(list_to_str(conda_deps), header_cmd)
        pip_deps_str = _add_header(list_to_str(pip_deps), header_cmd)

        if output_conda and conda_deps_str:
            _optional_write(conda_deps_str, output_conda)

        if output_pip and pip_deps_str:
            _optional_write(pip_deps_str, output_pip)

        return conda_deps_str, pip_deps_str


# ** output ----------------------------------------------------------------------------
def _conda_yaml(
    name: str | None = None,
    channels: Iterable[str] | None = None,
    conda_deps: Iterable[str] | None = None,
    pip_deps: Iterable[str] | None = None,
    add_file_eol: bool = True,
) -> str:
    if not conda_deps:
        msg = "Must have at least one conda dependency (i.e., pip)"
        raise ValueError(msg)

    out: list[str] = []
    if name is not None:
        out.append(f"name: {name}")

    if channels:
        out.append("channels:")
        out.extend(f"  - {channel}" for channel in _validate_iterable_str(channels))

    out.append("dependencies:")
    out.extend(f"  - {dep}" for dep in _validate_iterable_str(conda_deps))

    if pip_deps:
        out.append("  - pip:")
        out.extend(f"      - {dep}" for dep in _validate_iterable_str(pip_deps))

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
