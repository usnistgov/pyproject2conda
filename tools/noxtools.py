"""Utilities to work with nox."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Literal, Sequence, TextIO, cast

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from collections.abc import Collection

    import nox


# * Top level installation functions ---------------------------------------------------
def py_prefix(python_version: Any) -> str:
    if isinstance(python_version, str):
        return "py" + python_version.replace(".", "")
    else:
        raise ValueError(f"passed non-string value {python_version}")


def session_environment_filename(
    name: str | None,
    ext: str | None = None,
    python_version: str | None = None,
    lock: bool = False,
) -> str:
    """Get filename for a conda yaml or pip requirements file."""
    if name is None:
        raise ValueError("must supply name")

    filename = name
    if ext is not None:
        filename = filename + ext
    if python_version is not None:
        filename = f"{py_prefix(python_version)}-{filename}"

    if lock:
        if filename.endswith(".yaml"):
            filename = filename.rstrip(".yaml") + "-conda-lock.yml"
        elif filename.endswith(".yml"):
            filename = filename.rstrip(".yml") + "-conda-lock.yml"
        elif filename.endswith(".txt"):
            pass
        else:
            raise ValueError(f"unknown file extension for {filename}")

        return f"./requirements/lock/{filename}"
    else:
        return f"./requirements/{filename}"


def pkg_install_condaenv(
    session: nox.Session,
    name: str,
    lock: bool = False,
    display_name: str | None = None,
    install_package: bool = True,
    update: bool = False,
    log_session: bool = False,
    deps: Collection[str] | None = None,
    reqs: Collection[str] | None = None,
    channels: Collection[str] | None = None,
    filename: str | None = None,
    **kwargs: Any,
) -> None:
    """Install requirements.  If need fine control, do it in calling func."""

    def check_filename(filename: str | Path) -> str:
        if not Path(filename).exists():
            raise ValueError(f"file {filename} does not exist")
        session.log(f"Environment file: {filename}")
        return str(filename)

    assert isinstance(session.python, str)
    filename = filename or session_environment_filename(
        name=name, ext=".yaml", python_version=session.python, lock=lock
    )

    if lock:
        session_install_envs_lock(
            session=session,
            lockfile=check_filename(filename),
            display_name=display_name,
            update=update,
            install_package=install_package,
            **kwargs,
        )

    else:
        session_install_envs(
            session,
            check_filename(filename),
            display_name=display_name,
            update=update,
            deps=deps,
            reqs=reqs,
            channels=channels,
            install_package=install_package,
            **kwargs,
        )

    if log_session:
        session_log_session(session, conda=True)


def pkg_install_venv(
    session: nox.Session,
    name: str,  # pyright: ignore
    lock: bool = False,
    requirement_paths: Collection[str] | None = None,
    constraint_paths: Collection[str] | None = None,
    extras: str | Collection[str] | None = None,
    reqs: Collection[str] | None = None,
    display_name: str | None = None,
    update: bool = False,
    install_package: bool = False,
    no_deps: bool = True,
    log_session: bool = False,
) -> None:
    if lock:
        raise ValueError("lock not yet supported for install_pip")

    session_install_pip(
        session=session,
        requirement_paths=requirement_paths,
        constraint_paths=constraint_paths,
        extras=extras,
        reqs=reqs,
        display_name=display_name,
        update=update,
        install_package=install_package,
        no_deps=no_deps,
        lock=lock,
    )

    if log_session:
        session_log_session(session, conda=False)


def session_log_session(session: nox.Session, conda: bool = True) -> None:
    logfile = Path(session.create_tmp()) / "env_info.txt"

    session.log(f"writing environment log to {logfile}")

    with logfile.open("w") as f:
        if conda:
            session.run("conda", "list", stdout=f)
        else:
            session.run("python", "--version", stdout=f)
            session.run("pip", "list", stdout=f)


# * User config ------------------------------------------------------------------------
def load_nox_config(path: str | Path = "./config/userconfig.toml") -> dict[str, Any]:
    """
    Load user toml config file.

    File should look something like:

    [nox.python]
    paths = ["~/.conda/envs/python-3.*/bin"]

    # Extras for environments
    # for example, could have
    # dev = ["dev", "nox", "tools"]
    [nox.extras]
    dev = ["dev", "nox"]
    """

    from .projectconfig import ProjectConfig

    return ProjectConfig.from_path(path).to_nox_config()


# * Basic utilities --------------------------------------------------------------------
def combine_list_str(opts: list[str]) -> list[str]:
    if opts:
        return shlex.split(" ".join(opts))
    else:
        return []


def combine_list_list_str(opts: list[list[str]]) -> Iterable[list[str]]:
    return (combine_list_str(opt) for opt in opts)


def sort_like(values: Collection[Any], like: Sequence[Any]) -> list[Any]:
    """Sort `values` in order of `like`."""
    # only unique
    sorter = {k: i for i, k in enumerate(like)}
    return sorted(set(values), key=lambda k: sorter[k])


def update_target(
    target: str | Path, *deps: str | Path, allow_missing: bool = False
) -> bool:
    """Check if target is older than deps:"""
    target = Path(target)

    deps_filtered = []
    for d in map(Path, deps):
        if d.exists():
            deps_filtered.append(d)
        elif not allow_missing:
            raise ValueError(f"dependency {d} does not exist")

    if not target.exists():
        return True
    else:
        target_time = target.stat().st_mtime

        update = any(target_time < dep.stat().st_mtime for dep in deps_filtered)

    return update


def prepend_flag(flag: str, *args: str | Sequence[str]) -> list[str]:
    """
    Add in a flag before each arg.

    >>> prepent_flag("-k", "a", "b")
    ["-k", "a", "-k", "b"]
    """

    args_ = []
    for x in args:
        if isinstance(x, str):
            args_.append(x)
        else:
            args_.extend(x)

    return sum([[flag, _] for _ in args_], [])


def open_webpage(path: str | Path | None = None, url: str | None = None) -> None:
    """
    Open webpage from path or url.

    Useful if want to view webpage with javascript, etc., as well as static html.
    """
    import webbrowser
    from urllib.request import pathname2url

    if path:
        url = "file://" + pathname2url(str(Path(path).absolute()))
    if url:
        webbrowser.open(url)


# * Package install --------------------------------------------------------------------
# ** Utilities
def session_skip_install(session: nox.Session) -> bool:
    """
    Utility to check if we're skipping install and reusing existing venv
    This is a hack and may need to change if upstream changes.
    """
    return session._runner.global_config.no_install and session._runner.venv._reused  # type: ignore


def session_run_commands(
    session: nox.Session, commands: list[list[str]], external: bool = True, **kws: Any
) -> None:
    """Run commands command."""

    if commands:
        kws.update(external=external)
        for opt in combine_list_list_str(commands):
            session.run(*opt, **kws)


def session_set_ipykernel_display_name(
    session: nox.Session, display_name: str | None, check_skip_install: bool = True
) -> None:
    """Rename ipython kernel display name."""
    if not display_name or (check_skip_install and session_skip_install(session)):
        return
    else:
        command = f"python -m ipykernel install --sys-prefix --display-name {display_name}".split()
        # continue if fails
        session.run(*command, success_codes=[0, 1])


def session_install_package(
    session: nox.Session,
    package: str = ".",
    develop: bool = True,
    no_deps: bool = True,
    *args: str,
    **kwargs: Any,
) -> None:
    """Install package into session."""

    if session_skip_install(session):
        return

    if develop:
        command = ["-e"]
    else:
        command = []

    command.append(package)

    if no_deps:
        command.append("--no-deps")

    session.install(*command, *args, **kwargs)


# ** conda-lock
def session_install_envs_lock(
    session: nox.Session,
    lockfile: str | Path,
    extras: str | list[str] | None = None,
    display_name: str | None = None,
    update: bool = False,
    install_package: bool = False,
) -> bool:
    """Install dependencies using conda-lock."""

    if session_skip_install(session):
        return True

    unchanged, hashes = env_unchanged(
        session, lockfile, prefix="lock", other=dict(install_package=install_package)
    )
    if unchanged and not update:
        return unchanged

    if extras:
        if isinstance(extras, str):
            extras = extras.split(",")
        extras = cast(list[str], sum([["--extras", _] for _ in extras], []))
    else:
        extras = []

    session.run(
        "conda-lock",
        "install",
        "--mamba",
        *extras,
        "-p",
        str(session.virtualenv.location),
        str(lockfile),
        silent=True,
        external=True,
    )

    if install_package:
        session_install_package(session)

    session_set_ipykernel_display_name(session, display_name)

    write_hashfile(hashes, session=session, prefix="lock")

    return unchanged


# ** Conda
def parse_envs(
    *paths: str | Path,
    remove_python: bool = True,
    deps: Collection[str] | None = None,
    reqs: Collection[str] | None = None,
    channels: Collection[str] | None = None,
) -> tuple[set[str], set[str], set[str], str | None]:
    """Parse an `environment.yaml` file."""
    import re

    def _default(x: str | Iterable[str] | None) -> set[str]:
        if x is None:
            return set()
        elif isinstance(x, str):
            x = [x]
        return set(x)

    channels = _default(channels)
    deps = _default(deps)
    reqs = _default(reqs)
    name = None

    python_match = re.compile(r"\s*(python)\s*[~<=>].*")

    def _get_context(path: str | Path | TextIO) -> TextIO | Path:
        if hasattr(path, "readline"):
            from contextlib import nullcontext

            return nullcontext(path)  # type: ignore
        else:
            return Path(path).open("r")

    for path in paths:
        with _get_context(path) as f:
            data = YAML(typ="safe", pure=True).load(f)

        channels.update(data.get("channels", []))
        name = data.get("name", name)

        # check dependencies for pip
        for d in data.get("dependencies", []):
            if isinstance(d, dict):
                reqs.update(cast(list[str], d.get("pip")))
            else:
                if remove_python and not python_match.match(d):
                    deps.add(d)

    return channels, deps, reqs, name


def session_install_envs(
    session: nox.Session,
    *paths: str | Path,
    remove_python: bool = True,
    deps: Collection[str] | None = None,
    reqs: Collection[str] | None = None,
    channels: Collection[str] | None = None,
    conda_install_kws: dict[str, Any] | None = None,
    install_kws: dict[str, Any] | None = None,
    display_name: str | None = None,
    update: bool = False,
    install_package: bool = False,
) -> bool:
    """Parse and install everything. Pass an already merged yaml file."""

    if session_skip_install(session):
        return True

    channels, deps, reqs, name = parse_envs(
        *paths,
        remove_python=remove_python,
        deps=deps,
        reqs=reqs,
        channels=channels,
    )

    unchanged, hashes = env_unchanged(
        session,
        prefix="env",
        other=dict(
            deps=deps,
            reqs=reqs,
            channels=channels,
            install_package=install_package,
        ),
    )
    if unchanged and not update:
        return unchanged

    if not channels:
        channels = ""
    if deps:
        conda_install_kws = conda_install_kws or {}
        conda_install_kws.update(channel=channels)
        if update:
            deps = ["--update-all"] + list(deps)

        session.conda_install(*deps, **(conda_install_kws or {}))

    if reqs:
        if update:
            reqs = ["--upgrade"] + list(reqs)
        session.install(*reqs, **(install_kws or {}))

    if install_package:
        session_install_package(session)

    session_set_ipykernel_display_name(session, display_name)

    write_hashfile(hashes, session=session, prefix="env")

    return unchanged


# ** Pip
def session_install_pip(
    session: nox.Session,
    requirement_paths: str | Collection[str] | None = None,
    constraint_paths: str | Collection[str] | None = None,
    extras: str | Collection[str] | None = None,
    reqs: str | Collection[str] | None = None,
    display_name: str | None = None,
    update: bool = False,
    install_package: bool = False,
    no_deps: bool = True,
    lock: bool = False,
) -> bool:
    if session_skip_install(session):
        return True

    def _check_param(x: None | str | list[str] | Iterable[str]) -> list[str]:
        if x is None:
            return []
        elif isinstance(x, str):
            return [x]
        elif isinstance(x, list):
            return x
        else:
            return list(x)

    def _verify_paths(paths: str | list[str]) -> list[str]:
        if isinstance(paths, str):
            paths = [paths]

        out = []
        for path in paths:
            if Path(path).exists():
                out.append(path)
            else:
                inferred = session_environment_filename(name=path, lock=lock)
                if Path(inferred).exists():
                    out.append(inferred)
                else:
                    raise ValueError(f"no file {path} found/inferred")
        return out

    # parameters
    extras = _check_param(extras)
    if extras:
        install_package = True
        extras = ",".join(extras)
        install_package_args = ["-e", f".[{extras}]"]
    elif install_package:
        install_package_args = ["-e", "."]
    else:
        install_package_args = []

    if install_package and no_deps:
        install_package_args.append("--no-deps")

    requirement_paths = _verify_paths(_check_param(requirement_paths))
    constraint_paths = _verify_paths(_check_param(constraint_paths))
    reqs = _check_param(reqs)
    paths = list(requirement_paths) + list(constraint_paths)

    # check update
    unchanged, hashes = env_unchanged(
        session,
        *paths,
        prefix="pip",
        other=dict(
            reqs=reqs, extras=extras, install_package=install_package, no_deps=no_deps
        ),
    )

    if unchanged and not update:
        return unchanged

    # do install
    install_args = (
        prepend_flag("-r", *requirement_paths)
        + prepend_flag("-c", *constraint_paths)
        + list(reqs)
    )

    if install_args:
        if update:
            install_args = ["--upgrade"] + list(install_args)
        session.install(*install_args)

    if install_package:
        session.install(*install_package_args)

    session_set_ipykernel_display_name(session, display_name)
    write_hashfile(hashes, session=session, prefix="pip")

    return unchanged


# ** Hash environment

PREFIX_HASH_EXTS = Literal["env", "lock", "pip"]


def env_unchanged(
    session: nox.Session,
    *paths: str | Path,
    prefix: PREFIX_HASH_EXTS,
    verbose: bool = True,
    hashes: dict[str, str] | None = None,
    other: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, str]]:
    hashfile = hashfile_path(session, prefix)

    if hashes is None:
        hashes = get_hashes(*paths, other=other)

    if hashfile.exists():
        if verbose:
            session.log(f"hash file {hashfile} exists")
        unchanged = hashes == read_hashfile(hashfile)
    else:
        unchanged = False

    if unchanged:
        session.log(f"session {session.name} unchanged")
    else:
        session.log(f"session {session.name} changed")

    return unchanged, hashes


def get_hashes(
    *paths: str | Path,
    other: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get md5 hashes for paths."""

    out: dict[str, Any] = {"path": {str(path): _get_file_hash(path) for path in paths}}

    if other:
        import hashlib

        other_hashes = {}
        for k, v in other.items():
            if isinstance(v, str):
                s = v
            else:
                try:
                    s = str(sorted(v))
                except Exception:
                    s = str(v)
            other_hashes[k] = hashlib.md5(s.encode("utf-8")).hexdigest()

        out["other"] = other_hashes

    return out


def hashfile_path(session: nox.Session, prefix: PREFIX_HASH_EXTS) -> Path:
    """Path for hashfile for this session."""
    return Path(session.create_tmp()) / f"{prefix}.json"


def write_hashfile(
    hashes: dict[str, str],
    session: nox.Session,
    prefix: PREFIX_HASH_EXTS,
) -> None:
    import json

    path = hashfile_path(session, prefix)

    with open(path, "w") as f:
        json.dump(hashes, f)


def read_hashfile(
    path: str | Path,
) -> dict[str, str]:
    import json

    with open(path) as f:
        data = json.load(f)
    return cast(dict[str, str], data)


def _get_file_hash(path: str | Path, buff_size: int = 65536) -> str:
    import hashlib

    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            data = f.read(buff_size)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


# * Old stuff --------------------------------------------------------------------------
# def session_install_envs_merge(
#     session,
#     *paths,
#     remove_python=True,
#     deps=None,
#     reqs=None,
#     channels=None,
#     conda_install_kws=None,
#     install_kws=None,
#     display_name=None,
#     update=False,
# ) -> bool:
#     """Merge files (using conda-merge) and then create env"""

#     if session_skip_install(session):
#         return True

#     unchanged, hashes = env_unchanged(
#         session, *paths, prefix="env", other=dict(deps=deps, reqs=reqs)
#     )
#     if unchanged and not update:
#         return unchanged

#     # first create a temporary file for the environment
#     with tempfile.TemporaryDirectory() as d:
#         yaml = Path(d) / "tmp_env.yaml"
#         with yaml.open("w") as f:
#             session.run("conda-merge", *paths, stdout=f, external=True)
#         session.run("cat", str(yaml), external=True, silent=True)

#         channels, deps, reqs, _ = parse_envs(
#             yaml, remove_python=remove_python, deps=deps, reqs=reqs, channels=channels
#         )

#     if deps:
#         if conda_install_kws is None:
#             conda_install_kws = {}
#         conda_install_kws.update(channel=channels)
#         session.conda_install(*deps, **conda_install_kws)

#     if reqs:
#         if install_kws is None:
#             install_kws = {}
#         session.install(*reqs, **install_kws)

#     session_set_ipykernel_display_name(session, display_name)

#     write_hashfile(hashes, session=session, prefix="env")

#     return unchanged


# def _remove_python_from_yaml(path):
#     from yaml import safe_dump

#     path = Path(path)

#     with path.open("r") as f:
#         data = safe_load(f)

#     from copy import deepcopy

#     out = deepcopy(data)

#     for dep in list(out["dependencies"]):
#         if isinstance(dep, str) and dep[: len("python")] == "python":
#             out["dependencies"].remove(dep)

#     path_out = path.with_suffix(".final.yaml")

#     with path_out.open("w") as f:
#         safe_dump(out, f)

#     return path_out


# def session_install_envs_update(
#     session: nox.Session,
#     conda_backend: str,
#     *paths: str | Path,
#     remove_python: bool = True,
#     deps: Sequence[str] | None = None,
#     reqs: Sequence[str] | None = None,
#     conda_install_kws: Mapping[str, str] | None = None,
#     install_kws: Mapping[str, str] | None = None,
#     display_name: str | None = None,
# ) -> None:
#     """Install multiple 'environment.yaml' files."""

#     if session_skip_install(session):
#         return

#     from shutil import which

#     if not which("conda-merge"):
#         session.conda_install("conda-merge")

#     # pin the python version

#     with tempfile.TemporaryDirectory() as d:
#         yaml = Path(d) / "tmp_env.yaml"
#         with yaml.open("w") as f:
#             session.run("conda-merge", *paths, stdout=f, external=True)

#         if remove_python:
#             yaml = _remove_python_from_yaml(yaml)

#         session.run("cat", str(yaml), external=True, silent=False)

#         session.run(
#             conda_backend,
#             "env",
#             "update",
#             "--prefix",
#             session.virtualenv.location,
#             "--file",
#             str(yaml),
#             silent=True,
#             external=True,
#         )

#     session_set_ipykernel_display_name(session, display_name)


# def pin_python_version(session: nox.Session):
#     path = Path(session.virtualenv.location) / "conda-meta" / "pinned"

#     with path.open("w") as f:
#         session.run(
#             "python",
#             "-c",
#             """import sys; print("python=={v.major}.{v.minor}.{v.micro}".format(v=sys.version_info))""",
#             stdout=f,
#         )

# def session_install_envs_update_pin(
#     session: nox.Session,
#     conda_backend: str,
#     *paths: str | Path,
#         display_name: str | None = None,
#     **kws,
# ) -> None:
#     """Install multiple 'environment.yaml' files."""

#     if session_skip_install(session):
#         return

#     from shutil import which

#     if not which("conda-merge"):
#         session.conda_install("conda-merge")

#     # pin the python version
#     pin_python_version(session)

#     with tempfile.TemporaryDirectory() as d:
#         yaml = Path(d) / "tmp_env.yaml"
#         with yaml.open("w") as f:
#             session.run("conda-merge", *paths, stdout=f, external=True)

#         session.run("cat", str(yaml), external=True, silent=False)

#         session.run(
#             conda_backend,
#             "env",
#             "update",
#             "--prefix",
#             session.virtualenv.location,
#             "--file",
#             str(yaml),
#             silent=True,
#             external=True,
#             **kws,
#         )

#     session_set_ipykernel_display_name(session, display_name)


# def parse_args_for_flag(args, flag, action="value"):
#     """
#     Parse args for flag and pop it off args

#     Parameters
#     ----------
#     args : iterable
#         For example, session.posargs.
#     flag : string
#         For example, `flag='--run-external'
#     action : {'value', 'values', 'store_true', 'store_false'}

#     If flag can take multiple values, they should be separated by commas

#     If multiples, return a tuple, else return a string.
#     """
#     flag = flag.strip()
#     n = len(flag)

#     def process_value(arg):
#         if action == "store_true":
#             value = True
#         elif action == "store_false":
#             value = False
#         else:
#             s = arg.split("=")
#             if len(s) != 2:
#                 raise ValueError(f"must supply {flag}=value")
#             if action == "value":
#                 value = s[-1].strip()
#             else:
#                 value = tuple(_.strip() for _ in s[-1].split(","))

#         return value

#     def check_for_flag(arg):
#         s = arg.strip()
#         if action.startswith("value"):
#             return s[:n] == f"{flag}"
#         else:
#             return s == flag

#     # initial value
#     if action == "store_true":
#         value = False
#     elif action == "store_false":
#         value = True
#     elif action in ["value", "values"]:
#         value = None
#     else:
#         raise ValueError(
#             f"action {action} must be one of [store_true, store_false, value, values]"
#         )

#     out = []
#     for arg in args:
#         if check_for_flag(arg):
#             value = process_value(arg)
#         else:
#             out.append(arg)

#     return value, out


# def parse_args_run_external(args):
#     """Parse (and pop) for --run-external flag"""
#     return parse_args_for_flag(args, flag="--run-external", action="store_true")


# def parse_args_test_version(args):
#     """Parse for flag --test-version=..."""
#     return parse_args_for_flag(args, flag="--test-version", action="value")


# def parse_args_pip_extras(args, default=None, join=True):
#     """Parse for flag '--pip-extras=..."""
#     extras, args = parse_args_for_flag(args, flag="--pip-extras", action="values")

#     if extras:
#         extras = set(extras)

#     if default:
#         if extras is None:
#             extras = set()
#         if isinstance(default, str):
#             default = (default,)
#         for d in default:
#             extras.update(d.split(","))

#     if extras and join:
#         extras = ",".join(extras)

#     return extras, args


# def check_args_with_default(args, default=None):
#     """If no args and have a default, place it in args."""
#     if not args and default:
#         if isinstance(default, str):
#             default = default.split()
#         args = default
#     return args


# def run_with_external_check(
#     session, args=None, default=None, check_run_external=True, **kws
# ):
#     """
#     Use session.run with session.posargs.
#     Perform `seesion.run(*args)`, where `args` comes from posargs.
#     If no posargs, then use default.
#     Also, check for flag '--run-external'.  If present,
#     call `session.run(*args, external=True)`
#     """

#     if args is None:
#         args = session.posargs

#     if check_run_external:
#         external, args = parse_args_run_external(args)
#     else:
#         external = False

#     args = check_args_with_default(args, default=default)

# #     session.log(f"args {args}")
# #     session.log(f"external {external}")
# #     session.run(*args, external=external, **kws)


## This should actually go in the noxfile.  Keeping here
## in case want it again in the future.
# @group.session(python=PYTHON_DEFAULT_VERSION)
# def conda_merge(
#     session: Session,
#     conda_merge_force: bool = False,
#     update: FORCE_REINSTALL_CLI = False,
# ):
#     """Merge environments using conda-merge."""
#     import tempfile
#     session_install_envs(
#         session,
#         reqs=["conda-merge", "ruamel.yaml"],
#         update=update,
#     )

#     env_base = ROOT / "environment.yaml"
#     env_dir = ROOT / "environment"

#     def create_env(*extras, others=None, name=None, base=True):
#         if name is None:
#             name = extras[0]
#         env = env_dir / f"{name}.yaml"

#         deps = []
#         if base:
#             deps.append(str(env_base))
#         for extra in extras:
#             deps.append(str(env_dir / f"{extra}-extras.yaml"))

#         if conda_merge_force or update_target(env, *deps):
#             session.log(f"creating {env}")

#             args = ["conda-merge"] + deps
#             with tempfile.TemporaryDirectory() as d:
#                 tmp_path = Path(d) / "tmp_env.yaml"

#                 with tmp_path.open("w") as f:
#                     session.run(*args, stdout=f)

#                 run_str = dedent(
#                     f"""
#                 from ruamel.yaml import YAML; from pathlib import Path;
#                 pin, pout = Path("{tmp_path}"), Path("{env}")
#                 y = YAML(); y.indent(mapping=2, sequence=4, offset=2)
#                 y.dump(y.load(pin.open("r")), pout.open("w"))
#                 """
#                 )

#                 session.run("python", "-c", run_str, silent=True)

#     for extra in ["test", "docs"]:
#         create_env(extra, base=True)

#     create_env("test", "typing", name="typing", base=True)
#     create_env("dev", "test", "typing", "nox", name="dev", base=True)
