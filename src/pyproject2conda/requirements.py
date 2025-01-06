"""
Requirements parsing (:mod:`~pyproject2conda.requirements`)
===========================================================
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Iterable,
        Sequence,
    )

    from ._typing import (
        MISSING_TYPE,
    )
    from ._typing_compat import Self

from copy import copy

from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet

from pyproject2conda.utils import (
    MISSING,
    get_in,
    list_to_str,
    unique_list,
)
from pyproject2conda.utils import (
    remove_whitespace_list as _remove_whitespace_list,
)

from .overrides import OverrideDeps


# * Utilities --------------------------------------------------------------------------
def _check_allow_empty(allow_empty: bool) -> str:
    msg = "No dependencies for this environment\n"
    if allow_empty:
        return msg
    raise ValueError(msg)


def _clean_pip_reqs(reqs: list[str]) -> list[str]:
    out: list[str] = []
    for req in reqs:
        try:
            r = str(Requirement(req))
        except InvalidRequirement:
            # trust that user knows what they're doing
            r = req
        out.append(r)

    return out


def _clean_conda_requirement(
    requirement: Requirement,
    python_version: str | None = None,
    channel: str | None = None,
) -> Requirement | None:
    if (
        python_version
        and requirement.marker
        and (not requirement.marker.evaluate({"python_version": python_version}))
    ):
        return None

    requirement = _update_requirement(requirement, marker=None, extras=None)
    if channel:
        requirement.name = f"{channel}::{requirement.name}"
    return requirement


def _clean_conda_strings(
    deps: list[str], python_version: str | None = None
) -> list[str]:
    out: list[str] = []
    for dep in deps:
        # if have a channel, take it out
        if "::" in dep:
            channel, d = dep.split("::")
        else:
            channel, d = None, dep

        r = _clean_conda_requirement(
            Requirement(d), python_version=python_version, channel=channel
        )
        if r is not None:
            out.append(str(r))
    return out


def _update_requirement(  # noqa: C901, PLR0912
    requirement: str | Requirement,
    name: str | MISSING_TYPE = MISSING,
    url: str | MISSING_TYPE | None = MISSING,
    extras: str | Iterable[str] | MISSING_TYPE | None = MISSING,
    specifier: str | SpecifierSet | MISSING_TYPE | None = MISSING,
    marker: str | Marker | MISSING_TYPE | None = MISSING,
) -> Requirement:  # pragma: no cover
    if isinstance(requirement, str):
        requirement = Requirement(requirement)
    else:
        requirement = copy(requirement)

    if name is not MISSING:
        requirement.name = name

    if url is not MISSING:
        requirement.url = url

    if extras is not MISSING:
        if extras is None:
            extras = set()
        elif isinstance(extras, str):
            extras = {extras}
        else:
            extras = set(extras)
        requirement.extras = extras

    if specifier is not MISSING:
        if specifier is None:
            specifier = SpecifierSet()
        elif isinstance(specifier, str):
            specifier = SpecifierSet(specifier)
        requirement.specifier = specifier

    if marker is not MISSING:
        if isinstance(marker, str):
            marker = Marker(marker)

        requirement.marker = marker

    return requirement


# ** Dependencices
def resolve_extras(
    extras: str | Iterable[str],
    package_name: str,
    unresolved: dict[str, list[Requirement]],
) -> list[Requirement]:
    """Resolve extras"""
    if isinstance(extras, str):
        extras = [extras]

    out: list[Requirement] = []
    for extra in extras:
        for requirement in unresolved[extra]:
            if requirement.name == package_name:
                out.extend(
                    resolve_extras(
                        extras=requirement.extras,
                        package_name=package_name,
                        unresolved=unresolved,
                    )
                )
            else:
                out.append(requirement)
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

    if cmd:
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
        if len(line.strip()) == 0:
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
        f.write(string)


# * Main class
class ParseDepends:
    """
    Parse pyproject.toml file for dependencies

    Parameters
    ----------
    data : dict
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def get_in(
        self, *keys: str, default: Any = None, factory: Callable[[], Any] | None = None
    ) -> Any:
        """Generic getter."""
        return get_in(
            keys=keys, nested_dict=self.data, default=default, factory=factory
        )

    @cached_property
    def package_name(self) -> str:
        """Clean name of package."""
        if (out := self.get_in("project", "name")) is None:
            msg = "Must specify `project.name`"
            raise ValueError(msg)
        return cast("str", out)

    @cached_property
    def dependencies(self) -> list[str]:
        """project.dependencies"""
        return cast(
            "list[str]",
            self.get_in(
                "project",
                "dependencies",
                factory=list,
            ),
        )

    @cached_property
    def build_system_requires(self) -> list[str]:
        """build-system.requires"""
        return cast(
            "list[str]",
            self.get_in(
                "build-system",
                "requires",
                factory=list,
            ),
        )

    @cached_property
    def optional_dependencies(self) -> dict[str, Any]:
        """project.optional-dependencies"""
        return cast(
            "dict[str, Any]",
            self.get_in(
                "project",
                "optional-dependencies",
                factory=dict,
            ),
        )

    @cached_property
    def dependency_groups(self) -> dict[str, Any]:
        """dependency-groups"""
        return cast(
            "dict[str, Any]",
            self.get_in(
                "dependency-groups",
                factory=dict,
            ),
        )

    @cached_property
    def override_table(self) -> dict[str, OverrideDeps]:
        """
        tool.pyproject2conda.dependencies

        Mapping from requirement name to OverrideDeps instance

        """
        out = self.get_in("tool", "pyproject2conda", "dependencies", factory=dict)
        if out:
            out = {k: OverrideDeps(**v) for k, v in out.items()}
        return cast("dict[str, OverrideDeps]", out)

    @cached_property
    def channels(self) -> list[str]:
        """tool.pyproject2conda.channels"""
        channels = self.get_in("tool", "pyproject2conda", "channels", factory=list)

        if isinstance(channels, str):
            channels = [channels]
        return channels  # type: ignore[no-any-return]

    @property
    def extras(self) -> list[str]:
        """Available extras"""
        return [*self.optional_dependencies, "build-system.requires"]

    @property
    def groups(self) -> list[str]:
        """Available groups"""
        return [*self.dependency_groups, "build-system.requires"]

    @cached_property
    def requirements_base(self) -> list[Requirement]:
        """Base requirements"""
        return [Requirement(x) for x in self.dependencies]

    @cached_property
    def requirements_extras(self) -> dict[str, list[Requirement]]:
        """Extras requirements"""
        unresolved: dict[str, list[Requirement]] = {
            k: [Requirement(x) for x in v]
            for k, v in self.optional_dependencies.items()
        }

        resolved = {
            extra: resolve_extras(
                extra, package_name=self.package_name, unresolved=unresolved
            )
            for extra in unresolved
        }

        # add in build-system.requires
        resolved["build-system.requires"] = [
            Requirement(x) for x in self.build_system_requires
        ]

        return resolved

    @cached_property
    def requirements_groups(self) -> dict[str, list[Requirement]]:
        """Groups requirements"""
        from .vendored.dependency_groups._implementation import resolve

        resolved: dict[str, list[Requirement]] = {
            group: [Requirement(x) for x in resolve(self.dependency_groups, group)]
            for group in self.dependency_groups
        }

        # add in build-system.requires
        resolved["build-system.requires"] = [
            Requirement(x) for x in self.build_system_requires
        ]

        return resolved

    @staticmethod
    def _check_prop(vals: str | Iterable[str] | None, keys: list[str]) -> list[str]:
        if vals is None:
            return []

        if isinstance(vals, str):
            vals = [vals]

        out: list[str] = []
        for val in vals:
            if val not in keys:
                msg = f"{vals} not in {keys}"
                raise ValueError(msg)
            out.append(val)

        return out

    def _resolve_extras_and_groups(
        self,
        extras: str | Iterable[str] | None,
        groups: str | Iterable[str] | None,
        extras_or_groups: str | Iterable[str] | None,
    ) -> tuple[list[str], list[str]]:
        """Update extras and groups from extras_or_groups."""
        extras = self._check_prop(extras, self.extras)
        groups = self._check_prop(groups, self.groups)

        if extras_or_groups:
            if isinstance(extras_or_groups, str):
                extras_or_groups = [extras_or_groups]

            for extra_or_group in extras_or_groups:
                if extra_or_group in self.extras:
                    extras.append(extra_or_group)
                elif extra_or_group in self.groups:
                    groups.append(extra_or_group)
                else:  # pragma: no cover
                    msg = f"extra-or-group {extra_or_group} not in extras or groups"
                    raise ValueError(msg)

        return extras, groups

    @staticmethod
    def _cleanup(
        values: list[str],
        remove_whitespace: bool = True,
        unique: bool = True,
        sort: bool = True,
    ) -> list[str]:
        if remove_whitespace:
            values = _remove_whitespace_list(values)

        if unique:  # pragma: no cover
            values = unique_list(values)

        if sort:
            values = sorted(values)

        return values

    def _get_requirements(
        self,
        extras: Iterable[str],
        groups: Iterable[str],
        skip_package: bool = False,
    ) -> list[Requirement]:
        out: list[Requirement] = []

        if not skip_package:
            out.extend(self.requirements_base)

        def _extend_extra_or_group(
            extras: Iterable[str],
            requirements_mapping: dict[str, list[Requirement]],
        ) -> None:
            for extra in extras:
                out.extend(requirements_mapping[extra])

        _extend_extra_or_group(extras, self.requirements_extras)
        _extend_extra_or_group(groups, self.requirements_groups)

        return out

    def pip_requirements(
        self,
        *,
        extras: str | Iterable[str] | None = None,
        groups: str | Iterable[str] | None = None,
        extras_or_groups: str | Iterable[str] | None = None,
        skip_package: bool = False,
        pip_deps: str | Iterable[str] | None = None,
        unique: bool = True,
        remove_whitespace: bool = True,
        sort: bool = True,
    ) -> list[str]:
        """Pip dependencies."""
        extras, groups = self._resolve_extras_and_groups(
            extras, groups, extras_or_groups
        )

        out: list[str] = [
            str(requirement)
            for requirement in self._get_requirements(
                extras=extras,
                groups=groups,
                skip_package=skip_package,
            )
        ]

        if pip_deps:
            pip_deps = [pip_deps] if isinstance(pip_deps, str) else list(pip_deps)
            out.extend(_clean_pip_reqs(pip_deps))

        return self._cleanup(
            out, remove_whitespace=remove_whitespace, unique=unique, sort=sort
        )

    def conda_and_pip_requirements(  # noqa: C901
        self,
        *,
        extras: str | Iterable[str] | None = None,
        groups: str | Iterable[str] | None = None,
        extras_or_groups: str | Iterable[str] | None = None,
        skip_package: bool = False,
        pip_deps: str | Iterable[str] | None = None,
        conda_deps: str | Iterable[str] | None = None,
        unique: bool = True,
        remove_whitespace: bool = True,
        sort: bool = True,
        python_version: str | None = None,
        python_include: str | None = None,
    ) -> tuple[list[str], list[str]]:
        """Conda and pip requirements."""

        def _init_deps(deps: str | Iterable[str] | None) -> list[str]:
            if deps is None:
                return []
            if isinstance(deps, str):
                return [deps]
            return list(deps)

        extras, groups = self._resolve_extras_and_groups(
            extras, groups, extras_or_groups
        )

        if python_include == "infer":
            # safer get
            if (x := self.get_in("project", "requires-python")) is None:
                msg = "No value for `requires-python` in pyproject.toml file"
                raise ValueError(msg)
            python_include = "python" + str(x)

        pip_deps = _clean_pip_reqs(_init_deps(pip_deps))
        conda_deps = _clean_conda_strings(
            _init_deps(conda_deps), python_version=python_version
        )

        override_table = self.override_table
        for requirement in self._get_requirements(
            extras=extras,
            groups=groups,
            skip_package=skip_package,
        ):
            override = override_table.get(requirement.name)
            if override is not None:
                if override.pip:
                    pip_deps.append(str(requirement))

                elif not override.skip:
                    r = _clean_conda_requirement(
                        requirement,
                        python_version=python_version,
                        channel=override.channel,
                    )

                    if r is not None:
                        conda_deps.append(str(r))

                conda_deps.extend(
                    _clean_conda_strings(
                        override.packages, python_version=python_version
                    )
                )
            else:
                r = _clean_conda_requirement(requirement, python_version=python_version)
                if r is not None:  # pragma: no cover
                    conda_deps.append(str(r))

        pip_deps, conda_deps = (
            self._cleanup(
                x, remove_whitespace=remove_whitespace, unique=unique, sort=sort
            )
            for x in (pip_deps, conda_deps)
        )

        if python_include is not None:
            conda_deps = [
                *self._cleanup([python_include], remove_whitespace=remove_whitespace),
                *conda_deps,
            ]

        # special if have pip requirements or just pip in conda_deps
        # in this case, make sure pip is last
        if "pip" in conda_deps:
            conda_deps.remove("pip")
            conda_deps.append("pip")
        elif pip_deps:
            conda_deps.append("pip")

        return conda_deps, pip_deps

    def to_conda_yaml(  # noqa: PLR0913
        self,
        *,
        extras: str | Iterable[str] | None = None,
        groups: str | Iterable[str] | None = None,
        extras_or_groups: str | Iterable[str] | None = None,
        pip_deps: str | Iterable[str] | None = None,
        conda_deps: str | Iterable[str] | None = None,
        name: str | None = None,
        channels: str | Iterable[str] | None = None,
        python_include: str | None = None,
        python_version: str | None = None,
        skip_package: bool = False,
        header_cmd: str | None = None,
        output: str | Path | None = None,
        sort: bool = True,
        remove_whitespace: bool = True,
        unique: bool = True,
        allow_empty: bool = False,
    ) -> str:
        """Create yaml string."""
        conda_deps, pip_deps = self.conda_and_pip_requirements(
            extras=extras,
            groups=groups,
            extras_or_groups=extras_or_groups,
            skip_package=skip_package,
            pip_deps=pip_deps,
            conda_deps=conda_deps,
            unique=unique,
            remove_whitespace=remove_whitespace,
            sort=sort,
            python_include=python_include,
            python_version=python_version,
        )

        if not conda_deps and not pip_deps:
            return _check_allow_empty(allow_empty)

        out = _conda_yaml(
            name=name,
            channels=channels or self.channels,
            conda_deps=conda_deps,
            pip_deps=pip_deps,
        )

        out = _add_header(out, header_cmd)

        _optional_write(out, output)

        return out

    def to_requirements(
        self,
        *,
        extras: str | Iterable[str] | None = None,
        groups: str | Iterable[str] | None = None,
        extras_or_groups: str | Iterable[str] | None = None,
        skip_package: bool = False,
        header_cmd: str | None = None,
        output: str | Path | None = None,
        sort: bool = True,
        pip_deps: Sequence[str] | None = None,
        allow_empty: bool = False,
        remove_whitespace: bool = True,
    ) -> str:
        """Create requirements string."""
        pip_deps = self.pip_requirements(
            extras=extras,
            groups=groups,
            extras_or_groups=extras_or_groups,
            skip_package=skip_package,
            pip_deps=pip_deps,
            remove_whitespace=remove_whitespace,
            sort=sort,
        )

        if not pip_deps:
            return _check_allow_empty(allow_empty)

        out = _add_header(list_to_str(pip_deps), header_cmd)

        _optional_write(out, output)
        return out

    def to_conda_requirements(  # noqa: PLR0913
        self,
        *,
        extras: str | Iterable[str] | None = None,
        groups: str | Iterable[str] | None = None,
        extras_or_groups: str | Iterable[str] | None = None,
        channels: str | Iterable[str] | None = None,
        python_include: str | None = None,
        python_version: str | None = None,
        prepend_channel: bool = False,
        output_conda: str | Path | None = None,
        output_pip: str | Path | None = None,
        skip_package: bool = False,
        header_cmd: str | None = None,
        sort: bool = True,
        unique: bool = True,
        conda_deps: str | Iterable[str] | None = None,
        pip_deps: str | Iterable[str] | None = None,
        remove_whitespace: bool = True,
    ) -> tuple[str, str]:
        """Create conda and pip requirements files."""
        conda_deps, pip_deps = self.conda_and_pip_requirements(
            extras=extras,
            groups=groups,
            extras_or_groups=extras_or_groups,
            skip_package=skip_package,
            pip_deps=pip_deps,
            conda_deps=conda_deps,
            unique=unique,
            remove_whitespace=remove_whitespace,
            sort=sort,
            python_include=python_include,
            python_version=python_version,
        )

        if channels:
            channels = (
                [channels] if isinstance(channels, str) else list(channels)
            )  # pragma: no cover
        else:
            channels = self.channels

        if conda_deps and channels and prepend_channel:
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

    @classmethod
    def from_string(
        cls,
        toml_string: str,
    ) -> Self:
        """Create object from string."""
        from ._compat import tomllib

        data = tomllib.loads(toml_string)
        return cls(data=data)

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        """Create object from path."""
        from ._compat import tomllib

        with Path(path).open("rb") as f:
            data = tomllib.load(f)
        return cls(data=data)
