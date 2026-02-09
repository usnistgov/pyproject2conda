"""Utilities to wonferrk with nox"""

from __future__ import annotations

import locale
import os
import shlex
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from nox.logger import logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any

    from nox import Session

    PathLike = str | Path


# * Top level installation functions ---------------------------------------------------
def py_prefix(python_version: Any) -> str:
    """
    Get python prefix.

    `python="3.8` -> "py38"
    """
    if isinstance(python_version, str):
        return "py" + python_version.replace(".", "")
    msg = f"passed non-string value {python_version}"
    raise ValueError(msg)


def infer_requirement_path_with_fallback(
    name: str | None,
    ext: str | None = None,
    python_version: str | None = None,
    lock: bool = False,
    check_exists: bool = True,
    lock_fallback: bool = False,
) -> tuple[bool, Path]:
    """Get the requirements file from options with fallback."""
    if lock_fallback:
        try:
            path = infer_requirement_path(
                name=name,
                ext=ext,
                python_version=python_version,
                lock=lock,
                check_exists=True,
            )
        except FileNotFoundError:
            logger.info("Falling back to non-locked")
            lock = False
            path = infer_requirement_path(
                name=name,
                ext=ext,
                python_version=python_version,
                lock=lock,
                check_exists=True,
            )

    else:
        path = infer_requirement_path(
            name=name,
            ext=ext,
            python_version=python_version,
            lock=lock,
            check_exists=check_exists,
        )
    return lock, path


def infer_requirement_path(
    name: str | None,
    ext: str | None = None,
    python_version: str | None = None,
    lock: bool = False,
    check_exists: bool = True,
) -> Path:
    """Get filename for a conda yaml or pip requirements file."""
    if name is None:
        msg = "must supply name"
        raise ValueError(msg)

    # adjust filename
    filename = name
    if ext is not None and not filename.endswith(ext):
        filename += ext
    if python_version is not None and ext != ".txt":
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
            msg = f"unknown file extension for {filename}"
            raise ValueError(msg)

        filename = f"./requirements/lock/{filename}"
    else:
        filename = f"./requirements/{filename}"

    path = Path(filename)
    if check_exists and not path.is_file():
        msg = f"{path} does not exist"
        raise FileNotFoundError(msg)

    return path


def get_python_full_path(session: Session) -> str:
    """Full path to session python executable."""
    path = session.run_always(
        "python",
        "-c",
        "import sys; print(sys.executable)",
        silent=True,
    )
    if not isinstance(path, str):
        msg = "accessing python_full_path with value None"
        raise TypeError(msg)
    return path.strip()


# * Utilities --------------------------------------------------------------------------
def combine_list_str(opts: str | Iterable[str]) -> list[str]:
    """Cleanup str/list[str] to list[str]"""
    if not opts:
        return []

    if isinstance(opts, str):
        opts = [opts]
    return shlex.split(" ".join(opts))


def combine_list_list_str(opts: Iterable[str | Iterable[str]]) -> Iterable[list[str]]:
    """Cleanup Iterable[str/list[str]] to Iterable[list[str]]."""
    return (combine_list_str(opt) for opt in opts)


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
        _ = webbrowser.open(url)


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
            _ = session.run(*opt, **kws)


# * Caching -------------------------------------------------------------------
@contextmanager
def check_for_change_manager(
    *deps: str | Path,
    hash_path: str | Path | None = None,
    target_path: str | Path | None = None,
    force_write: bool = False,
) -> Iterator[bool]:
    """
    Context manager to look for changes in dependencies.

    Yields
    ------
    changed: bool

    If exit normally, write hashes to hash_path file

    """
    # pylint: disable=try-except-raise,no-else-raise, too-many-try-statements
    try:
        changed, hashes, hash_path = check_hash_path_for_change(
            *deps,
            target_path=target_path,
            hash_path=hash_path,
        )

        yield changed

    except Exception:  # noqa: TRY203
        raise

    else:
        if force_write or changed:
            logger.info(f"Writing {hash_path}")

            # make sure the parent directory exists:
            hash_path.parent.mkdir(parents=True, exist_ok=True)
            write_hashes(hash_path=hash_path, hashes=hashes)


def check_hash_path_for_change(
    *deps: str | Path,
    target_path: str | Path | None = None,
    hash_path: str | Path | None = None,
) -> tuple[bool, dict[str, str], Path]:
    """
    Checks a json file `hash_path` for hashes of `other_paths`.

    if specify target_path and no hash_path, set `hash_path=target_path.parent / (target_path.name + ".hash.json")`.
    if specify hash_path and no target, set

    Parameters
    ----------
    *deps :
        files on which target_path/hash_path depends.
    hash_path :
        Path of file containing hashes of `deps`.
    target_path :
        Target file (i.e., the final file to be created).
        Defaults to hash_path.


    Returns
    -------
    changed : bool
    hashes : dict[str, str]
    hash_path : Path

    """
    import json

    msg = "Must specify target_path or hash_path"

    if target_path is None:
        if hash_path is None:
            raise ValueError(msg)
        target_path = hash_path = Path(hash_path)
    else:
        target_path = Path(target_path)
        if hash_path is None:
            hash_path = target_path.parent / (target_path.name + ".hash.json")
        else:
            hash_path = Path(hash_path)

    hashes: dict[str, str] = {
        os.path.relpath(k, hash_path.parent): _get_file_hash(k) for k in deps
    }

    if not target_path.is_file():
        changed = True

    elif hash_path.is_file():
        with hash_path.open() as f:
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

    return changed, hashes, hash_path


def write_hashes(hash_path: str | Path, hashes: dict[str, Any]) -> None:
    """Write hashes to json file."""
    import json

    with Path(hash_path).open("w", encoding=locale.getpreferredencoding(False)) as f:
        json.dump(hashes, f, indent=2)
        _ = f.write("\n")


def _get_file_hash(path: str | Path, buff_size: int = 65536) -> str:
    import hashlib

    md5 = hashlib.md5()  # noqa: S324
    with Path(path).open("rb") as f:
        while data := f.read(buff_size):  # pylint: disable=while-used
            md5.update(data)
    return md5.hexdigest()
