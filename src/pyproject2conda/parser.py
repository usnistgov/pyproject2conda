"""
Parsing (:mod:`pyproject2conda.parser`)
=======================================

Main parser to turn pyproject.toml -> environment.yaml
"""
from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TypeVar, Union

import tomlkit
from ruamel.yaml import YAML

# -- typing ----------------------------------------------------------------------------

Tstr_opt = Optional[str]
Tstr_seq_opt = Optional[Union[str, Sequence[str]]]


# --- Default parser -------------------------------------------------------------------

_DEFAULTS = {}


def _default_parser():
    if "parser" in _DEFAULTS:
        return _DEFAULTS["parser"]

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Channel to add to the pyproject requirement",
    )
    parser.add_argument(
        "-p",
        "--pip",
        action="store_true",
        help="If specified, install dependency on pyproject dependency (on this line) with pip",
    )
    parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        help="If specified skip pyproject dependency on this line",
    )
    parser.add_argument("package", nargs="*")

    _DEFAULTS["parser"] = parser

    return parser


# taken from https://github.com/conda/conda-lock/blob/main/conda_lock/common.py
def get_in(
    keys: Sequence[Any], nested_dict: Mapping[Any, Any], default: Any = None
) -> Any:
    """
    >>> foo = {'a': {'b': {'c': 1}}}
    >>> get_in(['a', 'b'], foo)
    {'c': 1}

    """
    import operator
    from functools import reduce

    try:
        return reduce(operator.getitem, keys, nested_dict)
    except (KeyError, IndexError, TypeError):
        return default


def _unique_list(values):
    """
    Return only unique values in list.
    Unlike using set(values), this preserves order.
    """
    output = []
    for v in values:
        if v not in output:
            output.append(v)
    return output


def _list_to_str(values, eol=True):
    if values:
        output = "\n".join(values)
        if eol:
            output += "\n"
    else:
        output = ""

    return output


def _iter_value_comment_pairs(
    array: tomlkit.items.Array,
) -> list[tuple(Tstr_opt, Tstr_opt)]:
    """Extract value and comments from array"""
    for v in array._value:
        if v.value is not None and not isinstance(v.value, tomlkit.items.Null):
            value = str(v.value)  # .as_string()
        else:
            value = None
        if v.comment:
            comment = v.comment.as_string()
        else:
            comment = None
        if value is None and comment is None:
            continue
        yield (value, comment)


def _matches_package_name(
    dep: Tstr_opt,
    package_name: str,
) -> list[str]:
    """
    Check if `dep` matches pattern {package_name}[extra,..]

    If it does, return extras, else return None
    """

    if not dep:
        return None

    pattern = rf"{package_name}\[(.*?)\]"
    match = re.match(pattern, dep)

    if match:
        extras = match.group(1).split(",")
    else:
        extras = None
    return extras


def get_value_comment_pairs(
    package_name: str,
    deps: tomlkit.items.Array,
    extras: Tstr_seq_opt = None,
    opts: tomlkit.items.Table | None = None,
    include_root: bool = True,
) -> list[tuple(Tstr_opt, Tstr_opt)]:
    """Recursively build dependency, comment pairs from deps and extras."""
    if include_root:
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
        for value, comment in _iter_value_comment_pairs(opts[extra]):
            if new_extras := _matches_package_name(value, package_name):
                out.extend(
                    get_value_comment_pairs(
                        package_name=package_name,
                        extras=new_extras,
                        deps=deps,
                        opts=opts,
                        include_root=False,
                    )
                )
            else:
                out.append((value, comment))

    return out


def _match_p2c_comment(comment: Tstr_opt) -> Tstr_opt:
    if not comment or not (match := re.match(r".*?#\s*p2c:\s*([^\#]*)", comment)):
        return None
    else:
        return match.group(1).strip()


def _parse_p2c(match: Tstr_opt) -> Tstr_opt:
    """Parse match from _match_p2c_comment"""

    if match:
        return vars(_default_parser().parse_args(shlex.split(match)))
    else:
        return None


def parse_p2c_comment(comment: Tstr_opt) -> Tstr_opt:
    if match := _match_p2c_comment(comment):
        return _parse_p2c(match)
    else:
        return None


def value_comment_pairs_to_conda(
    value_comment_list: list[tuple(Tstr_opt, Tstr_opt)]
) -> dict[str, Any]:
    """Convert raw value/comment pairs to install lines"""

    conda_deps = []
    pip_deps = []

    def _check_value(value):
        if not value:
            raise ValueError("trying to add value that does not exist")

    for value, comment in value_comment_list:
        if comment and (parsed := parse_p2c_comment(comment)):
            if parsed["pip"]:
                _check_value(value)
                pip_deps.append(value)
            elif not parsed["skip"]:
                _check_value(value)

                if parsed["channel"]:
                    v = "{}::{}".format(parsed["channel"], value)
                else:
                    v = value
                conda_deps.append(v)

            conda_deps.extend(parsed["package"])
        elif value:
            conda_deps.append(value)

    return {"dependencies": conda_deps, "pip": pip_deps}


def _pyproject_to_value_comment_pairs(
    data: tomlkit.toml_document.TOMLDocument,
    extras: Tstr_seq_opt = None,
    isolated: Tstr_seq_opt = None,
    unique: bool = True,
):
    project = data["project"]
    package_name = project["name"]

    deps = project["dependencies"]

    if isolated:
        value_comment_list = get_value_comment_pairs(
            package_name=package_name,
            extras=isolated,
            deps=deps,
            opts=get_in(["tool", "pyproject2conda", "isolated-dependencies"], data),
            include_root=False,
        )
    else:
        value_comment_list = get_value_comment_pairs(
            package_name=package_name,
            extras=extras,
            deps=deps,
            opts=get_in(["project", "optional-dependencies"], data),
        )

    if unique:
        value_comment_list = _unique_list(value_comment_list)

    return value_comment_list


def pyproject_to_conda_lists(
    data: str | Path | tomlkit.toml_document.TOMLDocument,
    extras: Tstr_seq_opt = None,
    isolated: Tstr_seq_opt = None,
    channels: Tstr_seq_opt = None,
    python: Tstr_opt = None,
):
    if python == "get":
        python = "python" + get_in(["project", "requires-python"], data).unwrap()

    if channels is None:
        channels = get_in(["tool", "pyproject2conda", "channels"], data, None)
        if channels:
            channels = channels.unwrap()
    if isinstance(channels, str):
        channels = [channels]

    value_comment_list = _pyproject_to_value_comment_pairs(
        data=data,
        extras=extras,
        isolated=isolated,
    )

    output = value_comment_pairs_to_conda(value_comment_list)

    if python:
        output["dependencies"].insert(0, python)

    if channels:
        output["channels"] = channels

    return output


def pyproject_to_conda(
    data: str | Path | tomlkit.toml_document.TOMLDocument,
    extras: Tstr_seq_opt = None,
    isolated: Tstr_seq_opt = None,
    channels: Tstr_seq_opt = None,
    name: Tstr_opt = None,
    python: Tstr_opt = None,
    stream: str | Path | None = None,
):
    output = pyproject_to_conda_lists(
        data=data,
        extras=extras,
        isolated=isolated,
        channels=channels,
        python=python,
    )
    return _output_to_yaml(**output, name=name, stream=stream)


def _yaml_to_string(yaml, data, add_final_eol=False) -> str:
    import io

    buf = io.BytesIO()
    yaml.dump(data, buf)

    val = buf.getvalue()

    if not add_final_eol:
        val = val[:-1]

    return val.decode("utf-8")


def _output_to_yaml(
    dependencies: list[str] | None,
    channels: list[str] | None = None,
    pip: list[str] | None = None,
    name: Tstr_opt = None,
    stream: str | Path | None = None,
):
    data = {}

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

    # return data

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

    if stream is None:
        return _yaml_to_string(yaml, data, add_final_eol=True)
    else:
        if isinstance(stream, (str, Path)):
            with open(stream, "wb") as f:
                yaml.dump(data, f)
        else:
            yaml.dump(data, stream)


T = TypeVar("T", bound="PyProject2Conda")


class PyProject2Conda:
    """Wrapper class to transform pyproject.toml -> environment.yaml"""

    def __init__(
        self,
        data: tomlkit.toml_document.TOMLDocument,
        name: Tstr_opt = None,
        channels: Tstr_seq_opt = None,
        python: Tstr_opt = None,
    ) -> None:
        self.data = data
        self.name = name
        self.channels = channels
        self.python = python

    def to_conda_yaml(
        self,
        extras: Tstr_seq_opt = None,
        isolated: Tstr_seq_opt = None,
        name: Tstr_opt = None,
        channels: Tstr_seq_opt = None,
        python: Tstr_opt = None,
        stream: str | Path | None = None,
    ):
        self._check_extras_isolated(extras, isolated)

        return pyproject_to_conda(
            data=self.data,
            extras=extras,
            isolated=isolated,
            name=name or self.name,
            channels=channels or self.channels,
            python=python or self.python,
            stream=stream,
        )

    def to_conda_lists(
        self,
        extras: Tstr_seq_opt = None,
        isolated: Tstr_seq_opt = None,
        channels: Tstr_seq_opt = None,
        python: Tstr_opt = None,
    ) -> dict[str, Any]:
        self._check_extras_isolated(extras, isolated)

        return pyproject_to_conda_lists(
            data=self.data,
            extras=extras,
            isolated=isolated,
            channels=channels or self.channels,
            python=python or self.python,
        )

    def to_requirement_list(
        self,
        extras: Tstr_seq_opt = None,
        isolated: Tstr_seq_opt = None,
    ) -> list[str]:
        self._check_extras_isolated(extras, isolated)

        values = _pyproject_to_value_comment_pairs(
            data=self.data, extras=extras, isolated=isolated
        )
        return [x for x, y in values if x is not None]

    def to_requirements(
        self,
        extras: Tstr_opt = None,
        isolated: Tstr_seq_opt = None,
        stream: str | Path | None = None,
    ):
        """Create requirements.txt like file with pip dependencies."""

        self._check_extras_isolated(extras, isolated)

        reqs = self.to_requirement_list(extras=extras, isolated=isolated)

        s = _list_to_str(reqs)

        if stream:
            with open(stream, "w") as f:
                f.write(s)
        else:
            return s

    def to_conda_requirements(
        self,
        extras: Tstr_opt = None,
        isolated: Tstr_seq_opt = None,
        channels: Tstr_seq_opt = None,
        python: Tstr_opt = None,
        prepend_channel: bool = False,
        stream_conda: str | Path | None = None,
        stream_pip: str | Path | None = None,
    ):
        output = self.to_conda_lists(
            extras=extras,
            isolated=isolated,
            channels=channels,
            python=python,
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

        deps_str = _list_to_str(deps)
        reqs_str = _list_to_str(reqs)

        if stream_conda and deps_str:
            with open(stream_conda, "w") as f:
                f.write(deps_str)

        if stream_pip and reqs_str:
            with open(stream_pip, "w") as f:
                f.write(reqs_str)

        return deps_str, reqs_str

    def _check_extras_isolated(self, extras, isolated):
        if extras and isolated:
            raise ValueError("can only specify extras or isolated, not both.")

        def _do_test(sent, available):
            if isinstance(sent, str):
                sent = [sent]
            for s in sent:
                if s not in available:
                    raise ValueError(f"{s} not in {available}")

        if extras:
            _do_test(extras, self.list_extras())

        if isolated:
            _do_test(isolated, self.list_isolated())

    def _get_opts(self, *keys):
        opts = get_in(keys, self.data, None)
        if opts:
            return list(opts.keys())
        else:
            return []

    def list_extras(self):
        return self._get_opts("project", "optional-dependencies")

    def list_isolated(self):
        return self._get_opts("tool", "pyproject2conda", "isolated-dependencies")

    @classmethod
    def from_string(
        cls: type[T],
        toml_string: str,
        name: Tstr_opt = None,
        channels: Tstr_seq_opt = None,
        python: Tstr_opt = None,
    ) -> T:
        data = tomlkit.parse(toml_string)
        return cls(data=data, name=name, channels=channels, python=python)

    @classmethod
    def from_path(
        cls: type[T],
        path: str | Path,
        name: Tstr_opt = None,
        channels: Tstr_seq_opt = None,
        python: Tstr_opt = None,
    ) -> T:
        path = Path(path)

        if not path.exists():
            raise ValueError(f"{path} does not exist")

        with open(path, "rb") as f:
            data = tomlkit.load(f)
        return cls(data=data, name=name, channels=channels, python=python)


def _list_to_stream(values, stream=None):
    value = "\n".join(values)
    if isinstance(stream, (str, Path)):
        with open(stream, "w") as f:
            f.write(value)

    elif stream is None:
        return value

    else:
        stream.write(value)
