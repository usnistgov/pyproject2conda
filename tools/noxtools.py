"""Utilities to work with nox"""
from __future__ import annotations

import os
import shlex
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ruamel.yaml import YAML

if TYPE_CHECKING:
    import sys
    from typing import Any, Iterable, TextIO, Union

    from nox import Session

    PathLike = Union[str, Path]

    if sys.version_info < (3, 11):
        from typing_extensions import Self
    else:
        from typing import Self


# * Top level installation functions ---------------------------------------------------
def py_prefix(python_version: Any) -> str:
    if isinstance(python_version, str):
        return "py" + python_version.replace(".", "")
    else:
        raise ValueError(f"passed non-string value {python_version}")


def _verify_path(
    path: PathLike,
) -> str:
    if not Path(path).is_file():
        raise ValueError(f"Path {path} is not a file")
    return str(path)


def _verify_paths(
    paths: PathLike | Iterable[PathLike] | None,
) -> list[str]:
    if paths is None:
        return []
    elif isinstance(paths, (str, Path)):
        paths = [paths]

    return [_verify_path(p) for p in paths]


def infer_requirement_path(
    name: str | None,
    ext: str | None = None,
    python_version: str | None = None,
    lock: bool = False,
    check_exists: bool = True,
) -> str:
    """Get filename for a conda yaml or pip requirements file."""
    if name is None:
        raise ValueError("must supply name")

    # adjust filename
    filename = name
    if ext is not None and not filename.endswith(ext):
        filename = filename + ext
    if python_version is not None:
        prefix = py_prefix(python_version)
        if not filename.startswith(prefix):
            filename = f"{prefix}-{filename}"

    if lock:
        if filename.endswith(".yaml"):
            filename = filename.rstrip(".yaml") + "-conda-lock.yml"
        elif filename.endswith(".yml"):
            filename = filename.rstrip(".yml") + "-conda-lock.yml"
        elif filename.endswith(".txt"):
            pass
        else:
            raise ValueError(f"unknown file extension for {filename}")

        filename = f"./requirements/lock/{filename}"
    else:
        filename = f"./requirements/{filename}"

    if check_exists:
        assert Path(filename).is_file(), f"{filename} does not exist."

    return filename


def _infer_requirement_paths(
    names: str | Iterable[str] | None,
    lock: bool = False,
    ext: str | None = None,
    python_version: str | None = None,
) -> list[str]:
    if names is None:
        return []
    elif isinstance(names, str):
        names = [names]

    return [
        infer_requirement_path(name, lock=lock, ext=ext, python_version=python_version)
        for name in names
    ]


def is_conda_session(session: Session) -> bool:
    from nox.virtualenv import CondaEnv

    return isinstance(session.virtualenv, CondaEnv)


# * Main class ----------------------------------------------------------------


class Installer:
    """
    Class to handle installing package/dependecies

    Parameters
    ----------
    session : nox.Session
    update : bool, default=False
    lock : bool, default=False
    package: str, optional
    pip_deps : str or list of str, optional
        pip dependencies
    requirements : str or list of str
        pip requirement file(s) (pip install -r requirements[0] ...)
        Can either be a full path or a envname (for example,
        "test" will get resolved to ./requirements/test.txt)
    constraints : str or list of str
        pip constraint file(s) (pip install -c ...)
    config_path :
        Where to save env config for furture comparison.  Defaults to
        `session.create_tmp() / "env.json"`.
    """

    def __init__(
        self,
        session: Session,
        *,
        update: bool = False,
        lock: bool = False,
        package: str | bool | None = None,
        package_extras: str | Iterable[str] | None = None,
        pip_deps: str | Iterable[str] | None = None,
        requirements: PathLike | Iterable[PathLike] | None = None,
        constraints: PathLike | Iterable[PathLike] | None = None,
        config_path: PathLike | None = None,
        # conda specific things:
        conda_deps: str | Iterable[str] | None = None,
        conda_lock_path: PathLike | None = None,
        channels: str | Iterable[str] | None = None,
    ) -> None:
        self.session = session

        self.update = update
        self.lock = lock

        if config_path is None:
            config_path = Path(self.session.create_tmp()) / "env.json"
        else:
            config_path = Path(config_path)
        self.config_path = config_path

        if isinstance(package, bool):
            package = "." if package else None
        self.package = package
        self.package_extras = _to_list_of_str(package_extras)

        self.pip_deps: list[str] = sorted(_remove_whitespace_list(pip_deps or []))

        self.requirements = sorted(_verify_paths(requirements))
        self.constraints = sorted(_verify_paths(constraints))

        # conda stuff
        self.conda_deps: list[str] = sorted(_remove_whitespace_list(conda_deps or []))
        self.channels: list[str] = sorted(_remove_whitespace_list(channels or []))

        if not self.is_conda_session:
            if self.conda_deps or self.channels or conda_lock_path:
                raise ValueError("passing conda parameters to non conda session")

        if self.lock:
            if not self.is_conda_session:
                if (not self.requirements) or self.pip_deps or self.constraints:
                    raise ValueError("Can only pass requirements for locked virtualenv")

            else:
                if conda_lock_path is None:
                    raise ValueError("Must pass conda_lock_path")
                elif (
                    self.conda_deps
                    or self.channels
                    or self.pip_deps
                    or self.requirements
                    or self.constraints
                ):
                    raise ValueError(
                        "Can not pass conda_deps, channels, pip_deps, requirements, constraints if using conda-lock"
                    )

                conda_lock_path = _verify_path(conda_lock_path)

        self.conda_lock_path = conda_lock_path

    @cached_property
    def config(self) -> dict[str, Any]:
        """Dictionary of relavent info for this session"""
        out: dict[str, Any] = {}
        out["lock"] = self.lock

        for k in ["package", "package_extras", "pip_deps", "conda_deps", "channels"]:
            if v := getattr(self, k):
                out[k] = v

        # file hashses
        for k in ["requirements", "constraints", "conda_lock_path"]:
            if v := getattr(self, k):
                if isinstance(v, str):
                    v = [v]
                out[k] = {str(path): _get_file_hash(path) for path in v}

        return out

    def save_config(self) -> Self:
        import json

        # in case config path got clobbered
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self.session.log(f"saving config to {self.config_path}")
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)
        return self

    def log_session(self) -> Self:
        logfile = Path(self.session.create_tmp()) / "env_info.txt"
        self.session.log(f"writing environment log to {logfile}")

        with logfile.open("w") as f:
            self.session.run("python", "--version", stdout=f)

            if self.is_conda_session:
                self.session.run("conda", "list", stdout=f, external=True)
            else:
                self.session.run("pip", "list", stdout=f)

        return self

    @cached_property
    def previous_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        else:
            import json

            with self.config_path.open("r") as f:
                return json.load(f)  # type: ignore

    # Interface
    @property
    def python_version(self) -> str:
        return cast(str, self.session.python)

    @cached_property
    def is_conda_session(self) -> bool:
        return is_conda_session(self.session)

    @cached_property
    def skip_install(self) -> bool:
        try:
            return self.session._runner.global_config.no_install and self.session._runner.venv._reused  # type: ignore
        except Exception:
            return False

    @cached_property
    def changed(self) -> bool:
        out = self.config != self.previous_config

        msg = "changed" if out else "unchanged"
        self.session.log(f"session {self.session.name} {msg}")

        return out

        # if (out := self.config != self.previous_config):
        #     for k in (self.config.keys() | self.previous_config.keys()):
        #         current = self.config.get(k, None)
        #         previous = self.previous_config.get(k, None)

        #         if current != previous:
        #             print(self.session.log(f"{k} current : {current}"))
        #             print(self.session.log(f"{k} previous: {previous}"))
        # return out

    # Smart runners
    def run_commands(
        self,
        commands: Iterable[str | Iterable[str]] | None,
        external: bool = True,
        **kwargs: Any,
    ) -> Self:
        if commands:
            kwargs.update(external=external)
            for opt in combine_list_list_str(commands):
                self.session.run(*opt, **kwargs)
        return self

    def set_ipykernel_display_name(
        self,
        display_name: str | None = None,
        update: bool = False,
    ) -> Self:
        if not display_name or (not self.is_conda_session) or self.skip_install:
            pass
        elif self.changed or update or self.update:
            command = f"python -m ipykernel install --sys-prefix --display-name {display_name}".split()
            # continue if fails
            self.session.run(*command, success_codes=[0, 1])

        return self

    @property
    def _package_str(self) -> str:
        if self.package is None:
            raise ValueError("Attempting to use unset package")

        if self.package_extras:
            package_extras = ",".join(self.package_extras)
            return f"{self.package}[{package_extras}]"
        else:
            return self.package

    def install_all(
        self,
        update_package: bool = False,
        log_session: bool = False,
        save_config: bool = True,
        display_name: str | None = None,
    ) -> Self:
        out = (
            (self.conda_install_deps() if self.is_conda_session else self)
            .pip_install_deps()
            .pip_install_package(update=update_package)
            .set_ipykernel_display_name(display_name=display_name)
        )

        if log_session:
            out = out.log_session()

        if save_config:
            out = out.save_config()

        return out

    def pip_install_package(
        self,
        *args: Any,
        update: bool = False,
        develop: bool = True,
        no_deps: bool = True,
        opts: str | list[str] | None = None,
        **kwargs: Any,
    ) -> Self:
        """Install the package"""
        if self.package is None or self.skip_install:
            pass

        elif self.changed or (update := self.update or update):
            command = [self._package_str]

            if develop:
                command.insert(0, "-e")

            if no_deps:
                command.append("--no-deps")

            if update:
                command.append("--upgrade")

            if opts:
                command.extend(combine_list_str(opts))

            self.session.install(*command, *args, **kwargs)

        return self

    def pip_install_deps(
        self,
        *args: Any,
        update: bool = False,
        opts: str | Iterable[str] | None = None,
        **kwargs: Any,
    ) -> Self:
        if self.skip_install:
            pass

        elif self.changed or (update := update or self.update):
            install_args: list[str] = (
                prepend_flag("-r", *self.requirements)
                + prepend_flag("-c", *self.constraints)
                + self.pip_deps
            )

            if install_args:
                if update:
                    install_args = ["--upgrade"] + install_args

                if opts:
                    install_args.extend(combine_list_str(opts))
                self.session.install(*install_args, *args, **kwargs)

        return self

    def conda_install_deps(
        self,
        *args: Any,
        update: bool = False,
        prune: bool = True,
        extras: str | Iterable[str] | None = None,
        opts: str | Iterable[str] | None = None,
        channels: str | Iterable[str] | None = None,
        **kwargs: Any,
    ) -> Self:
        if self.lock:
            return self._conda_install_lock(
                update=update, extras=extras, opts=opts, **kwargs
            )
        else:
            return self._conda_install_deps(
                update=update, opts=opts, channels=channels, prune=prune, **kwargs
            )

    def _conda_install_lock(
        self,
        update: bool = False,
        extras: str | Iterable[str] | None = None,
        opts: str | Iterable[str] | None = None,
        **kwargs: Any,
    ) -> Self:
        if (not self.conda_lock_path) or self.skip_install:
            pass

        elif self.changed or (update := (update or self.update)):
            if extras:
                if isinstance(extras, str):
                    extras = extras.split(",")
                extras = prepend_flag("--extras", extras)
            else:
                extras = []

            if opts:
                opts = combine_list_str(opts)
            else:
                opts = []

            kwargs.setdefault("silent", True)
            kwargs["external"] = True

            if tmpdir := os.environ.get("TMPDIR"):
                kwargs["env"] = {"TMPDIR": tmpdir}

            self.session.run_always(
                "conda-lock",
                "install",
                "--mamba",
                *extras,
                *opts,
                "-p",
                str(self.session.virtualenv.location),
                str(self.conda_lock_path),
                **kwargs,
            )

        return self

    def _conda_install_deps(
        self,
        update: bool = False,
        opts: str | Iterable[str] | None = None,
        channels: str | Iterable[str] | None = None,
        prune: bool = True,
        **kwargs: Any,
    ) -> Self:
        if (not self.conda_deps) or self.skip_install:
            pass

        elif self.changed or (update := (update or self.update)):
            channels = channels or self.channels
            if channels:
                kwargs.update(channel=channels)

            deps = list(self.conda_deps)
            if update:
                deps.insert(0, "--update-all")

            if prune:
                deps.insert(0, "--prune")

            if opts:
                deps.extend(combine_list_str(opts))

            self.session.conda_install(*deps, **kwargs)

        return self

    # Super convenience methods
    @classmethod
    def from_yaml(
        cls,
        session: Session,
        envname: str | Iterable[str] | None = None,
        paths: PathLike | Iterable[PathLike] | None = None,
        conda_deps: str | Iterable[str] | None = None,
        pip_deps: str | Iterable[str] | None = None,
        channels: str | Iterable[str] | None = None,
        remove_python: bool = True,
        **kwargs: Any,
    ) -> Self:
        if paths or envname:
            assert isinstance(session.python, str)

            paths = _infer_requirement_paths(
                envname, ext=".yaml", lock=False, python_version=session.python
            ) + _verify_paths(paths)

            channels, conda_deps, pip_deps, _ = parse_envs(
                *paths,
                remove_python=remove_python,
                deps=conda_deps,
                reqs=pip_deps,
                channels=channels,
            )

        return cls(
            session=session,
            conda_deps=conda_deps,
            pip_deps=pip_deps,
            channels=channels,
            **kwargs,
        )

    @classmethod
    def _from_envname_pip(
        cls,
        session: Session,
        envname: str | Iterable[str] | None = None,
        lock: bool = False,
        requirements: PathLike | Iterable[PathLike] | None = None,
        **kwargs: Any,
    ) -> Self:
        if lock:
            assert isinstance(session.python, str)
            requirements = _verify_paths(requirements) + _infer_requirement_paths(
                envname, ext=".txt", lock=lock, python_version=session.python
            )

        else:
            if envname is not None:
                requirements = _verify_paths(requirements) + _infer_requirement_paths(
                    envname, ext=".txt"
                )

        return cls(
            session=session,
            lock=lock,
            requirements=requirements,
            **kwargs,
        )

    @classmethod
    def _from_envname_conda(
        cls,
        session: Session,
        envname: str | Iterable[str] | None = None,
        lock: bool = False,
        conda_lock_path: PathLike | None = None,
        **kwargs: Any,
    ) -> Self:
        """
        Parameters
        ----------
        envname :
            Base name for file.  For example, passing
            envname = "dev" will convert to
            `requirements/py{py}-dev.yaml` for `filename`
        """

        if lock:
            # get files from envname

            if conda_lock_path is None:
                assert isinstance(
                    envname, str
                ), "Must supply conda_lock_path or envname"
                conda_lock_path = infer_requirement_path(envname, ext=".yaml", python_version=session.python, lock=lock)  # type: ignore

            return cls(
                session=session, lock=lock, conda_lock_path=conda_lock_path, **kwargs
            )

        else:
            return cls.from_yaml(session=session, envname=envname, lock=lock, **kwargs)

    @classmethod
    def from_envname(
        cls,
        session: Session,
        envname: str | Iterable[str] | None = None,
        lock: bool = False,
        fallback: bool | None = None,
        **kwargs: Any,
    ) -> Self:
        if fallback is None:
            fallback = is_conda_session(session)

        if fallback and lock:
            try:
                return cls.from_envname(
                    session=session,
                    envname=envname,
                    lock=lock,
                    fallback=False,
                    **kwargs,
                )
            except Exception:
                session.log("Falling back to non-locked")
                return cls.from_envname(
                    session=session,
                    envname=envname,
                    lock=False,
                    fallback=False,
                    **kwargs,
                )

        elif is_conda_session(session):
            return cls._from_envname_conda(
                session=session, envname=envname, lock=lock, **kwargs
            )
        else:
            return cls._from_envname_pip(
                session=session, envname=envname, lock=lock, **kwargs
            )


# * Utilities --------------------------------------------------------------------------
def _to_list_of_str(x: str | Iterable[str] | None) -> list[str]:
    if x is None:
        return []
    elif isinstance(x, str):
        return [x]
    elif isinstance(x, list):
        return x
    else:
        return list(x)


def _remove_whitespace(s: str) -> str:
    import re

    return re.sub(r"\s+", "", s)


def _remove_whitespace_list(s: str | Iterable[str]) -> list[str]:
    if isinstance(s, str):
        s = [s]
    return [_remove_whitespace(x) for x in s]


def combine_list_str(opts: str | Iterable[str]) -> list[str]:
    if isinstance(opts, str):
        opts = [opts]

    if opts:
        return shlex.split(" ".join(opts))
    else:
        return []


def combine_list_list_str(opts: Iterable[str | Iterable[str]]) -> Iterable[list[str]]:
    return (combine_list_str(opt) for opt in opts)


def sort_like(values: Iterable[Any], like: Iterable[Any]) -> list[Any]:
    """Sort `values` in order of `like`."""
    # only unique
    sorter = {k: i for i, k in enumerate(like)}
    return sorted(set(values), key=lambda k: sorter[k])


def update_target(
    target: str | Path, *deps: str | Path, allow_missing: bool = False
) -> bool:
    """Check if target is older than deps:"""
    target = Path(target)

    deps_filtered: list[Path] = []
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


def prepend_flag(flag: str, *args: str | Iterable[str]) -> list[str]:
    """
    Add in a flag before each arg.

    >>> prepent_flag("-k", "a", "b")
    ["-k", "a", "-k", "b"]
    """

    args_: list[str] = []
    for x in args:
        if isinstance(x, str):
            args_.append(x)
        else:
            args_.extend(x)

    return sum([[flag, _] for _ in args_], [])  # pyright: ignore


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


def check_hash_path_for_change(
    target: str | Path, *deps: str | Path, hash_path: str | Path | None = None
) -> tuple[bool, Path, dict[str, Any]]:
    """
    Checks a json file `hash_path` for hashes of `other_paths`.

    If there is a change, return True.
    If no change, return False.
    """
    import json

    target = Path(target)
    if hash_path is None:
        hash_path = target.parent / (target.name + ".hash.json")
    else:
        hash_path = Path(hash_path)

    hashes: dict[str, str] = {
        os.path.relpath(k, hash_path.parent): _get_file_hash(k) for k in deps
    }

    if not target.is_file():
        changed = True

    elif hash_path.is_file():
        with open(hash_path) as f:
            previous_hashes: dict[str, Any] = json.load(f)

        changed = False
        for k, h in hashes.items():
            previous = previous_hashes.get(k)
            if previous is None or previous != h:
                changed = True
                hashes = {**previous_hashes, **hashes}
                break

    else:
        changed = True

    return changed, hash_path, hashes


def write_hashes(hash_path: str | Path, hashes: dict[str, Any]) -> None:
    import json

    with open(hash_path, "w") as f:
        json.dump(hashes, f, indent=2)
        f.write("\n")


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


def session_run_commands(
    session: Session,
    commands: list[list[str]] | None,
    external: bool = True,
    **kws: Any,
) -> None:
    """Run commands command."""

    if commands:
        kws.update(external=external)
        for opt in combine_list_list_str(commands):
            session.run(*opt, **kws)


# ** Conda -----------------------------------------------------------------------------
def parse_envs(
    *paths: str | Path,
    remove_python: bool = True,
    deps: str | Iterable[str] | None = None,
    reqs: str | Iterable[str] | None = None,
    channels: str | Iterable[str] | None = None,
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
        if isinstance(path, str):
            return open(path)
        elif isinstance(path, Path):
            return path
        else:
            from contextlib import nullcontext

            return nullcontext(path)  # type: ignore

        # if hasattr(path, "readline"):
        #     from contextlib import nullcontext

        #     return nullcontext(path)  # type: ignore
        # else:
        #     return Path(path).open("r")

    for path in paths:
        with _get_context(path) as f:
            data = YAML(typ="safe", pure=True).load(f)

        channels.update(data.get("channels", []))
        name = data.get("name", name)

        # check dependencies for pip
        for d in data.get("dependencies", []):
            if isinstance(d, dict):
                reqs.update(cast(list[str], d.get("pip")))  # pyright: ignore
            else:
                if remove_python and not python_match.match(d):
                    deps.add(d)

    return channels, deps, reqs, name


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
