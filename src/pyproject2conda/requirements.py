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
        Generator,
        Iterable,
        Sequence,
        TextIO,
    )

    import tomlkit.container
    import tomlkit.items
    import tomlkit.toml_document

    from ._typing import (
        MISSING_TYPE,
        OptStr,
        RequirementCommentPair,
        RequirementOverridePair,
    )
    from ._typing_compat import Self

from copy import copy

import tomlkit
from packaging.markers import Marker
from packaging.requirements import Requirement
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

from .overrides import OverrideDeps, OverrideDict


# * Utilities --------------------------------------------------------------------------
def _check_allow_empty(allow_empty: bool) -> str:
    msg = "No dependencies for this environment\n"
    if allow_empty:
        return msg
    else:
        raise ValueError(msg)


def _clean_pip_reqs(reqs: list[str]) -> list[str]:
    return [str(Requirement(r)) for r in reqs]


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
    else:
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


def _update_requirement(
    requirement: str | Requirement,
    name: str | MISSING_TYPE = MISSING,
    url: str | None | MISSING_TYPE = MISSING,
    extras: str | Iterable[str] | None | MISSING_TYPE = MISSING,
    specifier: str | SpecifierSet | None | MISSING_TYPE = MISSING,
    marker: str | Marker | None | MISSING_TYPE = MISSING,
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
def _iter_value_comment_pairs(
    array: tomlkit.items.Array,  # pyright: ignore
) -> Generator[tuple[OptStr, OptStr], None, None]:
    """Extract value and comments from array"""
    for v in array._value:  # pyright: ignore
        if v.value is not None and not isinstance(
            v.value, tomlkit.items.Null
        ):  # pyright: ignore
            value = str(v.value)  # pyright: ignore
        else:
            value = None
        if v.comment:  # pyright: ignore
            comment = v.comment.as_string()
        else:
            comment = None
        if value is None and comment is None:
            continue
        yield (value, comment)


def _requirement_comment_pairs(
    array: tomlkit.items.Array,
) -> list[RequirementCommentPair]:
    out: list[RequirementCommentPair] = []
    for value, comment in _iter_value_comment_pairs(array):
        if value is None:
            r = None
        else:
            r = Requirement(value)
        out.append((r, comment))
    return out


def _resolve_extras(
    extras: str | Iterable[str],
    package_name: str,
    mapping_requirement_comment_pairs: dict[str, list[RequirementCommentPair]],
) -> list[RequirementCommentPair]:
    if isinstance(extras, str):
        extras = [extras]

    out: list[RequirementCommentPair] = []
    for extra in extras:
        for requirement, comment in mapping_requirement_comment_pairs[extra]:
            if requirement is not None and requirement.name == package_name:
                out.extend(
                    _resolve_extras(
                        extras=requirement.extras,
                        package_name=package_name,
                        mapping_requirement_comment_pairs=mapping_requirement_comment_pairs,
                    )
                )
            else:
                out.append((requirement, comment))
    return out


# ** factories
def _factory_empty_tomlkit_Array() -> tomlkit.items.Array:
    return tomlkit.items.Array([], tomlkit.items.Trivia())


def _factory_empty_tomlkit_Table() -> tomlkit.items.Table:
    return tomlkit.items.Table(
        value=tomlkit.container.Container(),
        trivia=tomlkit.items.Trivia(),
        is_aot_element=False,
    )


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
        else:
            return x

    if not conda_deps and not pip_deps:
        raise ValueError

    out: list[str] = []
    if name is not None:
        out.append(f"name: {name}")

    if channels is not None:
        out.append("channels:")

        for channel in _as_list(channels):
            out.append(f"  - {channel}")

    out.append("dependencies:")

    if conda_deps is not None:
        for dep in _as_list(conda_deps):
            out.append(f"  - {dep}")

    if pip_deps:
        out.append("  - pip")
        out.append("  - pip:")

        for dep in _as_list(pip_deps):
            out.append(f"      - {dep}")

    s = "\n".join(out)

    if add_file_eol:
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
    header = "\n".join(lines)
    # header = "\n".join(["# " + line for line in header.split("\n")])
    return header


def _add_header(string: str, header_cmd: str | None) -> str:
    if header_cmd is not None:
        return _create_header(header_cmd) + "\n" + string
    else:
        return string


def _optional_write(
    string: str, stream: str | Path | TextIO | None, mode: str = "w"
) -> None:
    if stream is None:
        return
    if isinstance(stream, (str, Path)):
        with open(stream, mode) as f:
            f.write(string)
    else:
        stream.write(string)


# * Main class
class ParseDepends:
    """
    Parse pyproject.toml file for dependencies

    Parameters
    ----------
    data : tomlkit
    """

    def __init__(self, data: tomlkit.toml_document.TOMLDocument):
        self.data = data

    def get_in(
        self, *keys: str, default: Any = None, factory: Callable[[], Any] | None = None
    ) -> Any:
        return get_in(
            keys=keys, nested_dict=self.data, default=default, factory=factory
        )

    @cached_property
    def package_name(self) -> str:
        if (out := self.get_in("project", "name")) is None:
            raise ValueError("Must specify `project.name`")
        return cast(str, out)

    @cached_property
    def dependencies(self) -> tomlkit.items.Array:
        """project.dependencies"""
        return cast(
            "tomlkit.items.Array",
            self.get_in(
                "project", "dependencies", factory=_factory_empty_tomlkit_Array
            ),
        )

    @cached_property
    def build_system_requires(self) -> tomlkit.items.Array:
        """build-system.requires"""
        return cast(
            "tomlkit.items.Array",
            self.get_in(
                "build-system", "requires", factory=_factory_empty_tomlkit_Array
            ),
        )

    @cached_property
    def optional_dependencies(self) -> tomlkit.items.Table:
        """project.optional-dependencies"""
        return cast(
            "tomlkit.items.Table",
            self.get_in(
                "project", "optional-dependencies", factory=_factory_empty_tomlkit_Table
            ),
        )

    @cached_property
    def override_table(self) -> dict[str, OverrideDict]:
        out = self.get_in("tool", "pyproject2conda", "dependencies", default=MISSING)
        if out is MISSING:
            out = {}
        else:
            out = out.unwrap()
        return cast("dict[str, OverrideDict]", out)

    @cached_property
    def channels(self) -> list[str]:
        channels_doc = self.get_in("tool", "pyproject2conda", "channels")
        if channels_doc:
            channels = channels_doc.unwrap()
            if isinstance(channels, str):
                channels = [channels]
            else:
                channels = list(channels)
        else:
            channels = []

        return channels  # type: ignore

    @property
    def extras(self) -> list[str]:
        return list(self.optional_dependencies.keys()) + [  # pyright: ignore
            "build-system.requires"
        ]

    @cached_property
    def _requirement_override_pairs_base(
        self,
    ) -> list[RequirementOverridePair]:
        return OverrideDeps.requirement_comment_to_override_pairs(
            requirement_comment_pairs=_requirement_comment_pairs(self.dependencies),
            override_table=self.override_table,
        )

    @cached_property
    def _requirement_override_pairs_extras(
        self,
    ) -> dict[str, list[RequirementOverridePair]]:
        """
        Mapping[extra_name] -> [(requirement, comment)]

        Note that this also resolves self references of the form
        "package_name[extra,..]" to the actual dependencies.
        """
        unresolved: dict[str, list[RequirementCommentPair]] = {
            k: _requirement_comment_pairs(v)  # pyright: ignore
            for k, v in self.optional_dependencies.items()  # pyright: ignore
        }

        resolved = {
            k: _resolve_extras(
                extras=k,
                package_name=self.package_name,
                mapping_requirement_comment_pairs=unresolved,
            )
            for k in unresolved
        }

        # comments -> overrides
        out = {
            k: OverrideDeps.requirement_comment_to_override_pairs(
                requirement_comment_pairs=v, override_table=self.override_table
            )
            for k, v in resolved.items()
        }

        # add in build-system.requires
        out[
            "build-system.requires"
        ] = OverrideDeps.requirement_comment_to_override_pairs(
            requirement_comment_pairs=_requirement_comment_pairs(
                self.build_system_requires
            ),
            override_table=self.override_table,
        )

        return out

    @staticmethod
    def _cleanup(
        values: list[str],
        remove_whitespace: bool = True,
        unique: bool = True,
        sort: bool = True,
    ) -> list[str]:
        if remove_whitespace:
            values = _remove_whitespace_list(values)

        if unique:
            values = unique_list(values)

        if sort:
            values = sorted(values)

        return values

    def _get_requirement_override_pairs(
        self, extras: str | Iterable[str] | None = None, include_base: bool = True
    ) -> list[RequirementOverridePair]:
        out: list[RequirementOverridePair] = []

        if include_base:
            out.extend(self._requirement_override_pairs_base)

        if extras is not None:
            if isinstance(extras, str):
                extras = [extras]
            for extra in extras:
                out.extend(self._requirement_override_pairs_extras[extra])

        return out

    def _check_extras(self, extras: str | Iterable[str] | None) -> None:
        if extras is None:
            return
        elif isinstance(extras, str):
            extras = [extras]

        for extra in extras:
            if extra not in self.extras:
                raise ValueError(f"{extras} not in {self.extras}")

    def pip_requirements(
        self,
        extras: str | Iterable[str] | None = None,
        include_base: bool = True,
        pip_deps: str | Iterable[str] | None = None,
        unique: bool = True,
        remove_whitespace: bool = True,
        sort: bool = True,
    ) -> list[str]:
        self._check_extras(extras)

        out: list[str] = [
            str(requirement)
            for requirement, _ in self._get_requirement_override_pairs(
                extras=extras, include_base=include_base
            )
            if requirement is not None
        ]

        # TODO: extra checks?
        if pip_deps:
            if isinstance(pip_deps, str):
                pip_deps = [pip_deps]
            else:
                pip_deps = list(pip_deps)
            out.extend(_clean_pip_reqs(pip_deps))

        return self._cleanup(
            out, remove_whitespace=remove_whitespace, unique=unique, sort=sort
        )

    def conda_pip_requirements(
        self,
        extras: str | Iterable[str] | None = None,
        include_base: bool = True,
        pip_deps: str | Iterable[str] | None = None,
        conda_deps: str | Iterable[str] | None = None,
        unique: bool = True,
        remove_whitespace: bool = True,
        sort: bool = True,
        python_version: str | None = None,
        python_include: str | None = None,
    ) -> tuple[list[str], list[str]]:
        self._check_extras(extras)

        if python_include == "infer":
            # safer get
            if (x := self.get_in("project", "requires-python")) is None:
                raise ValueError(
                    "No value for `requires-python` in pyproject.toml file"
                )
            else:
                python_include = "python" + str(x)

        def _init_deps(deps: str | Iterable[str] | None) -> list[str]:
            if deps is None:
                return []
            elif isinstance(deps, str):
                return [deps]
            else:
                return list(deps)

        pip_deps = _clean_pip_reqs(_init_deps(pip_deps))
        conda_deps = _clean_conda_strings(
            _init_deps(conda_deps), python_version=python_version
        )

        for requirement, override in self._get_requirement_override_pairs(
            extras=extras, include_base=include_base
        ):
            if override is not None:
                if override.pip:
                    assert requirement is not None
                    pip_deps.append(str(requirement))
                elif not override.skip:
                    assert requirement is not None

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

            elif requirement:
                r = _clean_conda_requirement(requirement, python_version=python_version)

                if r is not None:
                    conda_deps.append(str(r))

        pip_deps, conda_deps = (
            self._cleanup(
                x, remove_whitespace=remove_whitespace, unique=unique, sort=sort
            )
            for x in (pip_deps, conda_deps)
        )

        if python_include is not None:
            conda_deps = (
                self._cleanup([python_include], remove_whitespace=remove_whitespace)
                + conda_deps
            )

        return conda_deps, pip_deps

    def to_conda_yaml(
        self,
        extras: OptStr | Iterable[str] = None,
        pip_deps: str | Iterable[str] | None = None,
        conda_deps: str | Iterable[str] | None = None,
        name: OptStr = None,
        channels: OptStr | Iterable[str] = None,
        python_include: OptStr = None,
        python_version: OptStr = None,
        include_base: bool = True,
        header_cmd: str | None = None,
        stream: str | Path | TextIO | None = None,
        sort: bool = True,
        remove_whitespace: bool = True,
        unique: bool = True,
        allow_empty: bool = False,
    ) -> str:
        self._check_extras(extras)

        conda_deps, pip_deps = self.conda_pip_requirements(
            extras=extras,
            include_base=include_base,
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

        _optional_write(out, stream)

        return out

    def to_requirements(
        self,
        extras: OptStr | Iterable[str] = None,
        include_base: bool = True,
        header_cmd: str | None = None,
        stream: str | Path | TextIO | None = None,
        sort: bool = True,
        pip_deps: Sequence[str] | None = None,
        allow_empty: bool = False,
        remove_whitespace: bool = True,
    ) -> str:
        pip_deps = self.pip_requirements(
            extras=extras,
            include_base=include_base,
            pip_deps=pip_deps,
            remove_whitespace=remove_whitespace,
            sort=sort,
        )

        if not pip_deps:
            return _check_allow_empty(allow_empty)

        out = _add_header(list_to_str(pip_deps), header_cmd)

        _optional_write(out, stream)
        return out

    def to_conda_requirements(
        self,
        extras: str | Iterable[str] | None = None,
        channels: str | Iterable[str] | None = None,
        python_include: str | None = None,
        python_version: str | None = None,
        prepend_channel: bool = False,
        stream_conda: str | Path | TextIO | None = None,
        stream_pip: str | Path | TextIO | None = None,
        include_base: bool = True,
        header_cmd: str | None = None,
        sort: bool = True,
        unique: bool = True,
        conda_deps: str | Iterable[str] | None = None,
        pip_deps: str | Iterable[str] | None = None,
        remove_whitespace: bool = True,
    ) -> tuple[str, str]:
        conda_deps, pip_deps = self.conda_pip_requirements(
            extras=extras,
            include_base=include_base,
            pip_deps=pip_deps,
            conda_deps=conda_deps,
            unique=unique,
            remove_whitespace=remove_whitespace,
            sort=sort,
            python_include=python_include,
            python_version=python_version,
        )

        if channels:
            if isinstance(channels, str):  # pragma: no cover
                channels = [channels]
            else:
                channels = list(channels)
        else:
            channels = self.channels

        if conda_deps and channels and prepend_channel:
            assert len(channels) == 1
            channel = channels[0]
            # add in channel if none exists
            conda_deps = [
                dep if "::" in dep else f"{channel}::{dep}" for dep in conda_deps
            ]

        conda_deps_str = _add_header(list_to_str(conda_deps), header_cmd)
        pip_deps_str = _add_header(list_to_str(pip_deps), header_cmd)

        if stream_conda and conda_deps_str:
            _optional_write(conda_deps_str, stream_conda)

        if stream_pip and pip_deps_str:
            _optional_write(pip_deps_str, stream_pip)

        return conda_deps_str, pip_deps_str

    @classmethod
    def from_string(
        cls,
        toml_string: str,
    ) -> Self:
        data = tomlkit.parse(toml_string)
        return cls(data=data)

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        with open(path, "rb") as f:
            data = tomlkit.load(f)
        return cls(data=data)

    # Output
