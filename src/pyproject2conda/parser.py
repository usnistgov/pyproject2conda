# pyright: reportUnknownMemberType=false, reportGeneralTypeIssues=false
"""
Parse `pyproject.toml` (:mod:`~pyproject2conda.parser`)
=======================================================

Main parser to turn `pyproject.toml` to other formats.
"""
from __future__ import annotations

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    cast,
)

if TYPE_CHECKING:
    from typing import (
        Any,
        Sequence,
        TextIO,
    )

    import tomlkit.container
    import tomlkit.items
    import tomlkit.toml_document

    from ._typing import OptStr, OptStrSeq
    from ._typing_compat import Self

import tomlkit
from packaging.requirements import Requirement
from ruamel.yaml import YAML

from pyproject2conda.utils import (
    get_in,
    list_to_str,
    unique_list,
)
from pyproject2conda.utils import (
    remove_whitespace_list as _remove_whitespace_list,
)

from .requirements import (
    OverrideDict,
    _add_header,
    _check_allow_empty,
    _clean_conda_strings,
    _clean_pip_reqs,
    _factory_empty_tomlkit_Array,
    _factory_empty_tomlkit_Table,
    _iter_value_comment_pairs,
    _optional_write,
    parse_p2c_comment,
)


def _matches_package_name(
    dep: OptStr,
    package_name: str,
) -> list[str] | None:
    """
    Check if `dep` matches pattern {package_name}[extra,..]

    If it does, return extras, else return None
    """
    if not dep:
        extras = None

    else:
        r = Requirement(dep)

        if r.name == package_name and r.extras:
            extras = list(r.extras)
        else:
            extras = None
    return extras


def _get_value_comment_pairs(
    package_name: str,
    deps: tomlkit.items.Array,
    extras: OptStrSeq = None,
    opts: tomlkit.items.Table | None = None,
    include_base_dependencies: bool = True,
) -> list[tuple[OptStr, OptStr]]:
    """Recursively build dependency, comment pairs from deps and extras."""
    if include_base_dependencies:
        out = list(_iter_value_comment_pairs(deps))
    else:
        out = []

    if extras is None:
        return out
    else:
        assert opts is not None

    if isinstance(extras, str):
        extras = [extras]

    for extra in extras:
        for value, comment in _iter_value_comment_pairs(
            cast(tomlkit.items.Array, opts[extra])
        ):
            if new_extras := _matches_package_name(value, package_name):
                out.extend(
                    _get_value_comment_pairs(
                        package_name=package_name,
                        extras=new_extras,
                        deps=deps,
                        opts=opts,
                        include_base_dependencies=False,
                    )
                )
            else:
                out.append((value, comment))

    return out


def _pyproject_to_value_comment_pairs(
    data: tomlkit.toml_document.TOMLDocument,
    extras: OptStrSeq = None,
    unique: bool = True,
    include_base_dependencies: bool = True,
) -> list[tuple[OptStr, OptStr]]:
    package_name = cast("str | None", get_in(["project", "name"], data, default=None))

    if package_name is None:
        raise ValueError("Must specify `project.package_name` in pyproject.toml")

    deps = cast(
        tomlkit.items.Array,
        get_in(["project", "dependencies"], data, factory=_factory_empty_tomlkit_Array),
    )

    value_comment_list = _get_value_comment_pairs(
        package_name=package_name,
        extras=extras,
        deps=deps,
        opts=get_in(
            ["project", "optional-dependencies"],
            data,
            factory=_factory_empty_tomlkit_Table,
        ),
        include_base_dependencies=include_base_dependencies,
    )

    if unique:
        value_comment_list = unique_list(value_comment_list)

    return value_comment_list


def _pyproject_to_value_parsed_pairs(
    value_comment_list: list[tuple[OptStr, OptStr]],
) -> list[tuple[str | None, OverrideDict]]:
    out = []
    for value, comment in value_comment_list:
        if comment and (parsed := parse_p2c_comment(comment)):
            out.append((value, parsed))
        elif value:
            out.append((value, {}))
    return out  # pyright: ignore


def _format_override_table(
    override_table: dict[str, OverrideDict]
) -> dict[str, OverrideDict]:
    out: dict[str, Any] = {}
    for name, v in override_table.items():
        new: OverrideDict = {
            "pip": v.get("pip", False),
            "skip": v.get("skip", False),
            "channel": v.get("channel", None),
            "packages": v.get("packages", []),
        }

        if new["channel"] is not None and new["channel"].strip() == "pip":
            new["pip"] = True
            new["channel"] = None

        if isinstance(new["packages"], str):
            new["packages"] = [new["packages"]]

        out[name] = new

    return out


def _apply_override_table(
    value_parsed_list: list[tuple[str | None, OverrideDict]],
    override_table: dict[str, OverrideDict],
) -> list[tuple[str | None, OverrideDict]]:
    out: list[tuple[str | None, OverrideDict]] = []

    override_table = _format_override_table(override_table)

    new_parsed: OverrideDict
    for value, parsed in value_parsed_list:
        if value and (name := Requirement(value).name) in override_table:
            new_parsed = dict(override_table[name], **parsed)  # type: ignore
        else:
            new_parsed = parsed

        out.append((value, new_parsed))

    return out


# * To dependency list
def value_comment_pairs_to_conda(
    value_comment_list: list[tuple[OptStr, OptStr]],
    sort: bool = True,
    deps: Sequence[str] | None = None,
    reqs: Sequence[str] | None = None,
    override_table: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert raw value/comment pairs to install lines"""

    conda_deps: list[str] = []
    pip_deps: list[str] = []

    def _check_value(value: Any) -> None:
        if not value:
            raise ValueError("trying to add value that does not exist")

    value_parsed_list = _pyproject_to_value_parsed_pairs(value_comment_list)

    if override_table:
        value_parsed_list = _apply_override_table(value_parsed_list, override_table)

    for value, parsed in value_parsed_list:
        if parsed:
            if parsed["pip"]:
                _check_value(value)
                pip_deps.append(value)  # type: ignore
            elif not parsed["skip"]:
                _check_value(value)
                if parsed["channel"]:
                    conda_deps.append("{}::{}".format(parsed["channel"], value))
                else:
                    conda_deps.append(value)  # type: ignore

            conda_deps.extend(parsed["packages"])
        elif value:
            conda_deps.append(value)

    if deps:
        conda_deps.extend(list(deps))

    if reqs:
        pip_deps.extend(list(reqs))

    if sort:
        conda_deps = sorted(conda_deps)
        pip_deps = sorted(pip_deps)

    return {"dependencies": conda_deps, "pip": pip_deps}


def pyproject_to_conda_lists(
    data: tomlkit.toml_document.TOMLDocument,
    extras: OptStrSeq = None,
    channels: OptStrSeq = None,
    python_include: OptStr = None,
    python_version: OptStr = None,
    include_base_dependencies: bool = True,
    sort: bool = True,
    deps: Sequence[str] | None = None,
    reqs: Sequence[str] | None = None,
    remove_whitespace: bool = True,
    override_table: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if python_include == "infer":
        # safer get
        if (x := get_in(["project", "requires-python"], data)) is None:
            raise ValueError("No value for `requires-python` in pyproject.toml file")
        else:
            python_include = "python" + x.unwrap()

    if channels is None:
        channels_doc = get_in(["tool", "pyproject2conda", "channels"], data, None)
        if channels_doc:
            channels = channels_doc.unwrap()

    if override_table is None:
        override_table_ = get_in(
            ["tool", "pyproject2conda", "dependencies"], data, None
        )
        if override_table_:
            override_table = override_table_.unwrap()

    if isinstance(channels, str):
        channels = [channels]

    value_comment_list = _pyproject_to_value_comment_pairs(
        data=data,
        extras=extras,
        include_base_dependencies=include_base_dependencies,
    )

    output = value_comment_pairs_to_conda(
        value_comment_list,
        sort=sort,
        deps=deps,
        reqs=reqs,
        override_table=override_table,
    )

    # clean up
    output["dependencies"] = _clean_conda_strings(
        output["dependencies"], python_version=python_version
    )
    output["pip"] = _clean_pip_reqs(output["pip"])

    if python_include:
        output["dependencies"].insert(0, python_include)
    if channels:
        output["channels"] = channels

    # # limit python version/remove python_verions <=> part
    # output["dependencies"] = _limit_deps_by_python_version(
    #     output["dependencies"], python_version
    # )

    if remove_whitespace:
        output = {k: _remove_whitespace_list(v) for k, v in output.items()}

    return output


def pyproject_to_conda(
    data: tomlkit.toml_document.TOMLDocument,
    extras: OptStrSeq = None,
    channels: OptStrSeq = None,
    name: OptStr = None,
    python_include: OptStr = None,
    stream: str | Path | TextIO | None = None,
    python_version: OptStr = None,
    include_base_dependencies: bool = True,
    header_cmd: OptStr = None,
    sort: bool = True,
    deps: Sequence[str] | None = None,
    reqs: Sequence[str] | None = None,
    allow_empty: bool = False,
    remove_whitespace: bool = True,
) -> str:
    output = pyproject_to_conda_lists(
        data=data,
        extras=extras,
        channels=channels,
        python_include=python_include,
        python_version=python_version,
        include_base_dependencies=include_base_dependencies,
        sort=sort,
        deps=deps,
        reqs=reqs,
        remove_whitespace=remove_whitespace,
    )
    return _output_to_yaml(
        **output,
        name=name,
        stream=stream,
        header_cmd=header_cmd,
        allow_empty=allow_empty,
    )


def _yaml_to_string(
    data: dict[str, Any],
    yaml: Any = None,
    add_final_eol: bool = False,
    header_cmd: str | None = None,
) -> str:
    import io

    if yaml is None:
        yaml = YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)

    buf = io.BytesIO()
    yaml.dump(data, buf)

    val = buf.getvalue()

    if not add_final_eol:
        val = val[:-1]
    return _add_header(val.decode("utf-8"), header_cmd)


def _output_to_yaml(
    dependencies: list[str] | None,
    channels: list[str] | None = None,
    pip: list[str] | None = None,
    name: OptStr = None,
    stream: str | Path | TextIO | None = None,
    header_cmd: str | None = None,
    allow_empty: bool = False,
) -> str:
    data: dict[str, Any] = {}
    if name:
        data["name"] = name

    if channels:
        data["channels"] = channels

    data["dependencies"] = []
    if dependencies:
        data["dependencies"].extend(dependencies)
    if pip:
        data["dependencies"].append("pip")
        data["dependencies"].append({"pip": pip})

    if not data["dependencies"]:
        return _check_allow_empty(allow_empty)
    else:
        # return data
        s = _yaml_to_string(data, add_final_eol=True, header_cmd=header_cmd)
        _optional_write(s, stream)
        return s


class PyProject2Conda:
    """Wrapper class to transform pyproject.toml -> environment.yaml"""

    def __init__(
        self,
        data: tomlkit.toml_document.TOMLDocument,
        name: OptStr = None,
        channels: OptStrSeq = None,
        python_include: OptStr = None,
    ) -> None:
        self.data = data
        self.name = name
        self.channels = channels
        self.python_include = python_include

    def to_conda_yaml(
        self,
        extras: OptStrSeq = None,
        name: OptStr = None,
        channels: OptStrSeq = None,
        python_include: OptStr = None,
        stream: str | Path | TextIO | None = None,
        python_version: OptStr = None,
        include_base_dependencies: bool = True,
        header_cmd: str | None = None,
        sort: bool = True,
        deps: Sequence[str] | None = None,
        reqs: Sequence[str] | None = None,
        allow_empty: bool = False,
        remove_whitespace: bool = True,
    ) -> str:
        self._check_extras(extras)

        return pyproject_to_conda(
            data=self.data,
            extras=extras,
            name=name or self.name,
            channels=channels or self.channels,
            python_include=python_include or self.python_include,
            stream=stream,
            python_version=python_version,
            include_base_dependencies=include_base_dependencies,
            header_cmd=header_cmd,
            sort=sort,
            deps=deps,
            reqs=reqs,
            allow_empty=allow_empty,
            remove_whitespace=remove_whitespace,
        )

    def to_conda_lists(
        self,
        extras: OptStrSeq = None,
        channels: OptStrSeq = None,
        python_include: OptStr = None,
        python_version: OptStr = None,
        include_base_dependencies: bool = True,
        sort: bool = True,
        deps: Sequence[str] | None = None,
        reqs: Sequence[str] | None = None,
        remove_whitespace: bool = True,
    ) -> dict[str, Any]:
        self._check_extras(extras)

        return pyproject_to_conda_lists(
            data=self.data,
            extras=extras,
            channels=channels or self.channels,
            python_include=python_include or self.python_include,
            python_version=python_version,
            include_base_dependencies=include_base_dependencies,
            sort=sort,
            deps=deps,
            reqs=reqs,
            remove_whitespace=remove_whitespace,
        )

    def to_requirement_list(
        self,
        extras: OptStrSeq = None,
        include_base_dependencies: bool = True,
        sort: bool = True,
        reqs: Sequence[str] | None = None,
        remove_whitespace: bool = True,
    ) -> list[str]:
        self._check_extras(extras)

        values = _pyproject_to_value_comment_pairs(
            data=self.data,
            extras=extras,
            include_base_dependencies=include_base_dependencies,
        )
        out = [x for x, _ in values if x is not None]

        if reqs:
            out.extend(list(reqs))

        # cleanup reqs:
        out = _clean_pip_reqs(out)

        if remove_whitespace:
            out = _remove_whitespace_list(out)

        if sort:
            return sorted(out)
        else:
            return out

    def to_requirements(
        self,
        extras: OptStrSeq = None,
        include_base_dependencies: bool = True,
        header_cmd: str | None = None,
        stream: str | Path | TextIO | None = None,
        sort: bool = True,
        reqs: Sequence[str] | None = None,
        allow_empty: bool = False,
        remove_whitespace: bool = True,
    ) -> str:
        """Create requirements.txt like file with pip dependencies."""

        self._check_extras(extras)

        reqs = self.to_requirement_list(
            extras=extras,
            include_base_dependencies=include_base_dependencies,
            sort=sort,
            reqs=reqs,
            remove_whitespace=remove_whitespace,
        )

        if not reqs:
            return _check_allow_empty(allow_empty)
        else:
            s = _add_header(list_to_str(reqs), header_cmd)
            _optional_write(s, stream)
            return s

    def to_conda_requirements(
        self,
        extras: OptStrSeq = None,
        channels: OptStrSeq = None,
        python_include: OptStr = None,
        python_version: OptStr = None,
        prepend_channel: bool = False,
        stream_conda: str | Path | TextIO | None = None,
        stream_pip: str | Path | TextIO | None = None,
        include_base_dependencies: bool = True,
        header_cmd: OptStr = None,
        sort: bool = True,
        deps: Sequence[str] | None = None,
        reqs: Sequence[str] | None = None,
        remove_whitespace: bool = True,
    ) -> tuple[str, str]:
        output = self.to_conda_lists(
            extras=extras,
            channels=channels,
            python_include=python_include,
            python_version=python_version,
            include_base_dependencies=include_base_dependencies,
            sort=sort,
            deps=deps,
            reqs=reqs,
            remove_whitespace=remove_whitespace,
        )

        deps = output.get("dependencies", None)
        reqs = output.get("pip", None)

        channels = output.get("channels", None)
        if channels and prepend_channel:
            assert len(channels) == 1
            channel = channels[0]
            # add in channel if none exists
            if deps:
                deps = [dep if "::" in dep else f"{channel}::{dep}" for dep in deps]

        deps_str = _add_header(list_to_str(deps), header_cmd)
        reqs_str = _add_header(list_to_str(reqs), header_cmd)

        if stream_conda and deps_str:
            _optional_write(deps_str, stream_conda)

        if stream_pip and reqs_str:
            _optional_write(reqs_str, stream_pip)

        return deps_str, reqs_str

    def _check_extras(self, extras: OptStrSeq) -> None:
        if extras is None:
            return
        elif isinstance(extras, str):
            sent: Sequence[str] = [extras]
        else:
            sent = extras

        available = self.list_extras()

        for s in sent:
            if s not in available:
                raise ValueError(f"{s} not in {available}")

    def _get_opts(self, *keys: str) -> list[str]:
        opts = get_in(keys, self.data, None)
        if opts:
            return list(opts.keys())
        else:
            return []

    def list_extras(self) -> list[str]:
        return self._get_opts("project", "optional-dependencies")

    @classmethod
    def from_string(
        cls,
        toml_string: str,
        name: OptStr = None,
        channels: OptStrSeq = None,
        python_include: OptStr = None,
    ) -> Self:
        data = tomlkit.parse(toml_string)
        return cls(
            data=data, name=name, channels=channels, python_include=python_include
        )

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        name: OptStr = None,
        channels: OptStrSeq = None,
        python_include: OptStr = None,
    ) -> Self:
        path = Path(path)

        if not path.exists():
            raise ValueError(f"{path} does not exist")

        with open(path, "rb") as f:
            data = tomlkit.load(f)
        return cls(
            data=data, name=name, channels=channels, python_include=python_include
        )
