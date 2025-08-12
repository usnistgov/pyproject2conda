# pylint: disable=wrong-import-position
"""Config file for nox."""

# * Imports ----------------------------------------------------------------------------
from __future__ import annotations

import shlex
import shutil
import sys
from dataclasses import dataclass
from functools import lru_cache, partial, wraps
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Literal,
    TypeAlias,
    TypedDict,
)

import nox
from nox.virtualenv import CondaEnv

sys.path.insert(0, ".")
from tools.dataclass_parser import (
    DataclassParser,
    add_option,
    option,
)
from tools.noxtools import (
    check_for_change_manager,
    combine_list_str,
    get_python_full_path,
    infer_requirement_path,
    open_webpage,
    session_run_commands,
)

sys.path.pop(0)


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from os import PathLike
    from typing import Any

    from nox import Session


# Should only use on python version > 3.10

# * Names ------------------------------------------------------------------------------

PACKAGE_NAME = "pyproject2conda"
IMPORT_NAME = "pyproject2conda"
KERNEL_NAME = "pyproject2conda"

# * nox options ------------------------------------------------------------------------

ROOT = Path(__file__).parent

nox.needs_version = ">=2024.10.9"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint", "typecheck", "test-all"]
nox.options.default_venv_backend = "uv"

# * Options ---------------------------------------------------------------------------

# if True, use uv lock/sync.  If False, use uv pip compile/sync...
UV_LOCK = True

PYTHON_ALL_VERSIONS = [
    c.split()[-1]
    for c in nox.project.load_toml("pyproject.toml")["project"]["classifiers"]
    if c.startswith("Programming Language :: Python :: 3.")
]
PYTHON_DEFAULT_VERSION = Path(".python-version").read_text(encoding="utf-8").strip()

UVX_LOCK_CONSTRAINTS = "requirements/lock/uvx-tools.txt"
UVX_MIN_CONSTRAINTS = "requirements/uvx-tools.txt"
PIP_COMPILE_CONFIG = "requirements/uv.toml"


class SessionOptionsDict(TypedDict, total=False):
    """Dict for options to nox.session."""

    python: str | list[str]
    venv_backend: str | Callable[..., CondaEnv]


CONDA_DEFAULT_KWS: SessionOptionsDict = {
    "python": PYTHON_DEFAULT_VERSION,
    "venv_backend": "micromamba|mamba|conda",
}
CONDA_ALL_KWS: SessionOptionsDict = {
    "python": PYTHON_ALL_VERSIONS,
    "venv_backend": "micromamba|mamba|conda",
}

DEFAULT_KWS: SessionOptionsDict = {"python": PYTHON_DEFAULT_VERSION}
ALL_KWS: SessionOptionsDict = {"python": PYTHON_ALL_VERSIONS}


# * Session command line options -------------------------------------------------------

OPT_TYPE: TypeAlias = list[str] | None
RUN_TYPE: TypeAlias = list[list[str]] | None

RUN_ANNO = Annotated[
    RUN_TYPE,
    option(
        help="Run external commands in session.  Specify multiple times for multiple commands.",
    ),
]
OPT_ANNO = Annotated[OPT_TYPE, option(help="Options to command.")]


@dataclass
class SessionParams(DataclassParser):
    """Holds all cli options."""

    # common parameters
    lock: bool = False
    no_lock: bool = False
    update: bool = add_option("--update", "-U", help="update dependencies/package")
    version: str | None = add_option(
        "--version", "-V", help="pretend version", default=None
    )
    prune: bool = add_option(default=False, help="Pass `--prune` to conda env update")
    uv_sync_options: list[str] = add_option(
        help="options to uv sync. Default='--locked'", default=("--locked",)
    )
    reinstall_package: bool = add_option(
        "--reinstall-package",
        "-P",
        help="reinstall package.  Only works with uv sync and editable installs",
    )
    installpkg: str | None = add_option(
        "--installpkg",
        help="Use this package instead of editable or built package",
        default=None,
    )

    # test
    test_no_pytest: bool = False
    test_options: OPT_TYPE = add_option(
        "--test-options", "-t", help="Options to pytest"
    )
    test_run: RUN_ANNO = None
    no_cov: bool = False

    # coverage
    coverage: list[Literal["erase", "combine", "report", "html", "open"]] | None = None

    # docs
    docs: (
        list[
            Literal[
                "html",
                "build",
                "clean",
                "livehtml",
                "linkcheck",
                "spelling",
                "showlinks",
                "open",
                "serve",
            ]
        ]
        | None
    ) = add_option("--docs", "-d", help="doc commands")
    docs_run: RUN_ANNO = None
    docs_options: OPT_TYPE = add_option(
        "--docs-options", help="Options to sphinx-build"
    )
    # lint
    lint_options: OPT_TYPE = add_option(help="Options to pre-commit")

    # typecheck
    typecheck: list[
        Literal[
            "clean",
            "mypy",
            "pyright",
            "pylint",
            "all",
            "mypy-notebook",
            "pyright-notebook",
            "pylint-notebook",
            "typecheck-notebook",
            "ty",
            "pyrefly",
            "ty-notebook",
            "pyrefly-notebook",
        ]
    ] = add_option("--typecheck", "-m")
    typecheck_run: RUN_ANNO = None
    typecheck_options: OPT_TYPE = add_option(help="Options to type checkers")

    # build
    build: list[Literal["build", "version"]] | None = None
    build_run: RUN_ANNO = None
    build_isolation: bool = False
    build_out_dir: str = "./dist"
    build_options: OPT_ANNO = None
    build_silent: bool = False

    # conda-recipe/grayskull
    conda_recipe: list[Literal["recipe", "recipe-full"]] | None = None
    conda_recipe_sdist_path: str | None = None

    # conda-build
    conda_build: list[Literal["build", "clean"]] | None = None
    conda_build_run: RUN_ANNO = None


@lru_cache
def parse_posargs(*posargs: str) -> SessionParams:
    """
    Get Parser using `+` for session option prefix.

    Note that using `+` allows for passing underlying `-` options
    without escaping.
    """
    opts = SessionParams.from_posargs(posargs=posargs, prefix_char="+")

    if opts.no_lock:
        opts.lock = False
    else:
        opts.lock = opts.lock or UV_LOCK

    return opts


def add_opts(
    func: Callable[[Session, SessionParams], None],
) -> Callable[[Session], None]:
    """Fill in `opts` from cli options."""

    @wraps(func)
    def wrapped(session: Session) -> None:
        opts = parse_posargs(*session.posargs)
        return func(session, opts)

    return wrapped


# * Dependencies --------------------------------------------------------------
def install_dependencies(
    session: Session,
    *args: str,
    name: str,
    opts: SessionParams,
    python_version: str | None = None,
    location: str | None = None,
    no_dev: bool = True,
    no_default_groups: bool = False,
    only_group: bool = False,
    include_editable_package: bool = False,
    lock: bool | None = None,
) -> None:
    """General dependencies installer."""
    if python_version is None:
        assert isinstance(session.python, str)  # noqa: S101
        python_version = session.python

    lock = lock if lock is not None else opts.lock

    if isinstance(session.virtualenv, CondaEnv):
        environment_file = infer_requirement_path(
            name,
            ext=".yaml",
            python_version=python_version,
            lock=False,
        )
        with check_for_change_manager(
            environment_file,
            hash_path=Path(session.create_tmp()) / "env.json",
        ) as changed:
            if changed or opts.update:
                session.run_install(
                    session.virtualenv.conda_cmd,
                    "env",
                    "update",
                    "--yes",
                    *(["--prune"] if opts.prune else []),
                    "-f",
                    environment_file,
                    "--prefix",
                    session.virtualenv.location,
                    *args,
                )
            else:
                session.log("Using cached install")

        if include_editable_package:
            install_package(session, editable=True, update=True)

    elif lock:  # pylint: disable=confusing-consecutive-elif
        session.run_install(
            "uv",
            "sync",
            *(["-U"] if opts.update else opts.uv_sync_options),
            *(
                ["--no-default-groups"]
                if no_default_groups
                else ["--no-dev"]
                if no_dev
                else []
            ),
            *(["--only-group"] if only_group else ["--group"]),
            name,
            # Handle package install here?
            # "--no-editable",
            # "--reinstall-package",
            *([] if include_editable_package else ["--no-install-project"]),
            *(
                [f"--reinstall-package={PACKAGE_NAME}"]
                if opts.reinstall_package and include_editable_package
                else []
            ),
            *(
                []
                if any("--python" in a for a in args)
                else [f"--python={python_version}"]
            ),
            *args,
            env={"UV_PROJECT_ENVIRONMENT": location or session.virtualenv.location},
        )

    else:
        session.run_install(
            "uv",
            "pip",
            "sync",
            f"--config-file={PIP_COMPILE_CONFIG}",
            infer_requirement_path(
                name,
                ext=".txt",
                python_version=python_version,
                lock=True,
            ),
            *args,
        )

        if include_editable_package:
            install_package(session, editable=True, update=True)


def install_package(
    session: Session,
    *args: str,
    editable: bool = False,
    update: bool = True,
    installpkg: str | None = None,
) -> None:
    """Install current package."""
    if installpkg is not None:
        run = session.run
        opts = [*args, installpkg]
    elif editable:
        run = session.run if update else session.run_install
        opts = [*args, "-e", "."]
    else:
        run = session.run
        opts = [*args, get_package_wheel(session)]

    run(
        "uv",
        "pip",
        "install",
        *opts,
        "--no-deps",
        "--force-reinstall",
        external=True,
    )


def get_package_wheel(
    session: Session,
    opts: str | Iterable[str] | None = None,
    extras: str | Iterable[str] | None = None,
    reuse: bool = True,
) -> str:
    """
    Build the package in return the build location.

    This is similar to how tox does isolated builds.

    Note that the first time this is called,

    Should be straightforward to extend this to isolated builds
    that depend on python version (something like have session build-3.11 ....)
    """
    dist_location = Path(session.cache_dir) / "dist"
    if reuse and getattr(get_package_wheel, "_called", False):
        session.log("Reuse isolated build")
    else:
        cmd = f"nox -s build -- ++build-out-dir {dist_location} ++build-options --wheel ++build-silent"
        session.run_always(*shlex.split(cmd), external=True)

        # save that this was called:
        if reuse:
            get_package_wheel._called = True  # type: ignore[attr-defined]  # noqa: SLF001  # pylint: disable=protected-access

    paths = list(dist_location.glob("*.whl"))
    if len(paths) != 1:
        msg = f"something wonky with paths {paths}"
        raise ValueError(msg)

    path = f"{PACKAGE_NAME}@{paths[0]}"
    if extras:
        if not isinstance(extras, str):
            extras = ",".join(extras)
        path = f"{path}[{extras}]"

    if opts:
        if not isinstance(opts, str):
            opts = " ".join(opts)
        path = f"{path} {opts}"

    return path


# * uvx runner ----------------------------------------------------------------
def get_uvx_constraint_args(locked: bool = True) -> tuple[str, ...]:
    """Get constraints file for uvx."""
    if locked and Path(UVX_LOCK_CONSTRAINTS).exists():
        return (f"--constraints={UVX_LOCK_CONSTRAINTS}",)
    if Path(UVX_MIN_CONSTRAINTS).exists():
        return (f"--constraints={UVX_MIN_CONSTRAINTS}",)
    return ()


def uvx_run(
    session: Session, *args: str | PathLike[str], locked: bool = True, **kwargs: Any
) -> Any:
    """Run command using uvx"""
    return session.run("uvx", *get_uvx_constraint_args(locked), *args, **kwargs)


def pre_commit_run(session: Session, *args: str | PathLike[str], **kwargs: Any) -> Any:
    """Run pre-commit via uvx."""
    return uvx_run(
        session,
        "--with=pre-commit-uv",
        "pre-commit",
        "run",
        *args,
        **kwargs,
        locked=False,
    )


# * Sessions ------------------------------------------------------------------
# ** test-all
@nox.session(name="test-all", python=False)
def test_all(session: Session) -> None:
    """Run all tests and coverage."""
    session.notify("coverage-erase")
    for py in PYTHON_ALL_VERSIONS:
        session.notify(f"test-{py}")
    session.notify("coverage")


# ** dev
@nox.session(name="dev", python=False)
@add_opts
def dev(
    session: Session,
    opts: SessionParams,
) -> None:
    """Create development environment."""
    session.run("uv", "venv", ".venv", "--allow-existing", "--prompt", PACKAGE_NAME)

    python_opt = "--python=.venv/bin/python"

    install_dependencies(
        session,
        python_opt,
        name="dev",
        opts=opts,
        python_version=PYTHON_DEFAULT_VERSION,
        location=".venv",
        no_dev=False,
        include_editable_package=True,
    )
    session.notify("install-ipykernel")


@nox.session(name="install-ipykernel", python=False)
@add_opts
def install_ipykernel(session: Session, opts: SessionParams) -> None:
    """Install ipykernel for .venv"""
    session.run(
        "uv",
        "run",
        *opts.uv_sync_options,
        "--python=.venv/bin/python",
        "python",
        "-m",
        "ipykernel",
        "install",
        "--user",
        "--name",
        KERNEL_NAME,
        "--display-name",
        f"Python [venv: {KERNEL_NAME}]",
        success_codes=[0, 1],
    )


# ** testing
def _test(
    session: nox.Session,
    run: RUN_TYPE,
    test_no_pytest: bool,
    test_options: OPT_TYPE,
    no_cov: bool,
) -> None:
    import os

    tmpdir = os.environ.get("TMPDIR", None)

    session_run_commands(session, run)
    if not test_no_pytest:
        opts = combine_list_str(test_options or [])
        if not no_cov:
            session.env["COVERAGE_FILE"] = str(Path(session.create_tmp()) / ".coverage")

            if not any(o.startswith("--cov") for o in opts):
                opts.append(f"--cov={IMPORT_NAME}")

        # Because we are testing if temporary folders
        # have git or not, we have to make sure we're above the
        # not under this repo
        # so revert to using the top level `TMPDIR`
        if tmpdir:
            session.env["TMPDIR"] = tmpdir

        session.run("pytest", *opts)


# *** Basic tests
@add_opts
def test(
    session: Session,
    opts: SessionParams,
) -> None:
    """Test environments with conda installs."""
    install_dependencies(session, name="test", opts=opts)
    install_package(session, editable=False, update=True, installpkg=opts.installpkg)

    _test(
        session=session,
        run=opts.test_run,
        test_no_pytest=opts.test_no_pytest,
        test_options=opts.test_options,
        no_cov=opts.no_cov,
    )


nox.session(**ALL_KWS)(test)
nox.session(name="test-conda", **CONDA_ALL_KWS)(test)


@nox.session(name="test-notebook", **DEFAULT_KWS)
@add_opts
def test_notebook(session: nox.Session, opts: SessionParams) -> None:
    """Run pytest --nbval."""
    install_dependencies(session, name="test-notebook", opts=opts)
    install_package(session, editable=False, update=True, installpkg=opts.installpkg)

    test_nbval_opts = shlex.split(
        """
    --nbval
    --nbval-current-env
    --nbval-sanitize-with=config/nbval.ini
    --dist loadscope
   """,
    )

    test_options = (
        (opts.test_options or [])
        + test_nbval_opts
        + [str(p) for p in Path("examples/usage").glob("*.ipynb")]
    )

    session.log(f"{test_options = }")

    _test(
        session=session,
        run=opts.test_run,
        test_no_pytest=opts.test_no_pytest,
        test_options=test_options,
        no_cov=opts.no_cov,
    )


@nox.session(python=False)
@add_opts
def coverage(
    session: Session,
    opts: SessionParams,
) -> None:
    """Run coverage."""
    cmd = opts.coverage or ["combine", "html", "report"]

    paths = list(Path(".nox").glob("test-*/tmp/.coverage*"))

    if "erase" in cmd:
        for path in paths:
            if path.exists():
                session.log(f"removing {path}")
                path.unlink()

    for c in cmd:
        if c == "combine":
            uvx_run(
                session,
                "coverage",
                "combine",
                "--keep",
                "-a",
                *paths,
            )
        elif c == "open":
            open_webpage(path="htmlcov/index.html")

        else:
            uvx_run(
                session,
                "coverage",
                c,
            )


@nox.session(name="coverage-erase", python=False)
def coverage_erase(session: Session) -> None:
    """Alias to `nox -s coverage -- ++coverage erase`"""
    session.run("nox", "-s", "coverage", "--", "++coverage", "erase")


# *** testdist (conda)
@add_opts
def testdist(
    session: Session,
    opts: SessionParams,
) -> None:
    """Test conda distribution."""
    install_str = PACKAGE_NAME
    if opts.version:
        install_str = f"{install_str}=={opts.version}"

    install_dependencies(session, name="test-extras", only_group=True, opts=opts)

    if isinstance(session.virtualenv, CondaEnv):
        session.conda_install(install_str)
    else:
        session.install(install_str)

    _test(
        session=session,
        run=opts.test_run,
        test_no_pytest=opts.test_no_pytest,
        test_options=opts.test_options,
        no_cov=opts.no_cov,
    )


nox.session(name="testdist-pypi", **ALL_KWS)(testdist)
nox.session(name="testdist-conda", **CONDA_ALL_KWS)(testdist)


# # ** Docs
@nox.session(name="docs", **DEFAULT_KWS)
@add_opts
def docs(  # noqa: C901
    session: nox.Session,
    opts: SessionParams,
) -> None:
    """Build/serve docs."""
    cmd = opts.docs or []
    cmd = ["html"] if not opts.docs_run and not cmd else list(cmd)
    name = (
        "docs-live"
        if "livehtml" in cmd
        else "docs-spelling"
        if "spelling" in cmd
        else "docs"
    )

    install_dependencies(session, name=name, opts=opts, include_editable_package=True)

    if opts.version:
        session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = opts.version
    session_run_commands(session, opts.docs_run)

    if open_page := "open" in cmd:
        cmd.remove("open")

    if serve := "serve" in cmd:
        open_webpage(url="http://localhost:8000")
        cmd.remove("serve")

    if cmd:
        common_opts = [
            "--doctree-dir=docs/_build/doctree",
            *(opts.docs_options or ()),
        ]
        for c in combine_list_str(cmd):
            if c == "clean":
                for d in ("docs/_build", "generated", "reference/generated"):
                    shutil.rmtree(Path(d), ignore_errors=True)
                session.log("cleaned docs")
            elif c == "livehtml":
                session.run(
                    "sphinx-autobuild",
                    "-b",
                    "html",
                    "docs",
                    "docs/_build/html",
                    *common_opts,
                    "--open-browser",
                    *(
                        f"--ignore='*/{d}/*'"
                        for d in (
                            "_build",
                            "generated",
                            "jupyter_execute",
                            ".ipynb_checkpoints",
                        )
                    ),
                )
            elif c == "showlinks":
                session.run(
                    "python",
                    "-m",
                    "sphinx.ext.intersphinx",
                    "docs/_build/html/objects.inv",
                )
            else:
                session.run(
                    "sphinx-build", "-b", c, *common_opts, "docs", f"docs/_build/{c}"
                )

    if open_page:
        open_webpage(path="./docs/_build/html/index.html")

    if serve and "livehtml" not in cmd:
        session.run(
            "python",
            "-m",
            "http.server",
            "-d",
            "docs/_build/html",
            "-b",
            "127.0.0.1",
            "8000",
        )


# ** lint
@nox.session(python=False)
@add_opts
def lint(
    session: nox.Session,
    opts: SessionParams,
) -> None:
    """
    Run linters with pre-commit.

    Defaults to `pre-commit run --all-files`.
    To run something else pass, e.g.,
    `nox -s lint -- --lint-run "pre-commit run --hook-stage manual --all-files`
    """
    pre_commit_run(session, "--all-files", *(opts.lint_options or []))


# ** type checking
@nox.session(name="typecheck", **ALL_KWS)
@add_opts
def typecheck(  # noqa: C901
    session: nox.Session,
    opts: SessionParams,
) -> None:
    """Run type checkers (mypy, pyright, etc)."""
    install_dependencies(
        session, name="typecheck", opts=opts, include_editable_package=True
    )
    session_run_commands(session, opts.typecheck_run)

    cmd = opts.typecheck or []
    if not opts.typecheck_run and not cmd:
        cmd = ["mypy", "pyright"]

    if "all" in cmd:
        cmd = ["mypy", "pyright", "pylint"]

    # set the cache directory for mypy
    session.env["MYPY_CACHE_DIR"] = str(Path(session.create_tmp()) / ".mypy_cache")

    if "clean" in cmd:
        cmd = list(cmd)
        cmd.remove("clean")

        for name in (".mypy_cache", ".pytype"):
            p = Path(session.create_tmp()) / name
            if p.exists():
                session.log(f"removing cache {p}")
                shutil.rmtree(p)

    if not isinstance(session.python, str):
        raise TypeError

    for c in cmd:
        if c.endswith("-notebook"):
            session.run("just", c, external=True)
        elif c in {"mypy", "pyright", "ty", "pyrefly"}:
            session.run(
                "python",
                "tools/typecheck.py",
                *get_uvx_constraint_args(),
                "--verbose",
                f"--checker={c}",
                "--",
                *(
                    opts.typecheck_options
                    or (["src", "tests"] if c in {"ty", "pyrefly"} else [])
                ),
                *(["--color-output"] if c == "mypy" else []),
            )
        elif c == "pylint":
            session.run(
                "pylint",
                # A bit dangerous, but needed to allow pylint
                # to work across versions.
                "--disable=unrecognized-option",
                "--enable-all-extensions",
                "src",
                "tests",
            )
        else:
            session.log(f"Skipping unknown command {c}")


# ** Dist pypi
# NOTE: you can skip having the build environment and
# just use uv build, but faster to use environment ...
USE_ENVIRONMENT_FOR_BUILD = False
_build_dec = nox.session(
    python=PYTHON_DEFAULT_VERSION if USE_ENVIRONMENT_FOR_BUILD else False
)


@_build_dec
@add_opts
def build(session: nox.Session, opts: SessionParams) -> None:  # noqa: C901
    """
    Build the distribution.

    Note that default is to not use build isolation.
    Pass `--build-isolation` to use build isolation.
    """
    if USE_ENVIRONMENT_FOR_BUILD:
        install_dependencies(session, name="build", opts=opts, lock=False)

    if opts.version:
        session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = opts.version

    for cmd in opts.build or ["build"]:
        if cmd == "version":
            if USE_ENVIRONMENT_FOR_BUILD:
                session.run(get_python_full_path(session), "-m", "hatchling", "version")  # pyright: ignore[reportPossiblyUnboundVariable]
            else:
                uvx_run(
                    session, "--with=hatch-vcs", "hatchling", "version", external=True
                )
        elif cmd == "build":
            outdir = opts.build_out_dir
            shutil.rmtree(outdir, ignore_errors=True)

            args = shlex.split(f"uv build --out-dir={outdir}")
            if USE_ENVIRONMENT_FOR_BUILD and not opts.build_isolation:
                args.append("--no-build-isolation")

            if opts.build_options:
                args.extend(opts.build_options)

            out = session.run(*args, silent=opts.build_silent)
            if opts.build_silent:
                if not isinstance(out, str):
                    msg = "session.run output not a string"
                    raise ValueError(msg)
                session.log(out.strip().split("\n")[-1])


# # ** Dist conda
@nox.session(name="conda-recipe", python=False)
@add_opts
def conda_recipe(
    session: nox.Session,
    opts: SessionParams,
) -> None:
    """Run grayskull to create recipe."""
    commands = opts.conda_recipe or ["recipe"]

    run = partial(uvx_run, session, external=True)

    if not (sdist_path := opts.conda_recipe_sdist_path):
        sdist_path = PACKAGE_NAME
        if opts.version:
            sdist_path = f"{sdist_path}=={opts.version}"

    for command in commands:
        if command == "recipe":
            # make directory?
            if not (d := Path("./dist-conda")).exists():
                d.mkdir()

            run(
                "grayskull",
                "pypi",
                sdist_path,
                "--sections",
                "package",
                "source",
                "build",
                "requirements",
                "-o",
                "dist-conda",
            )

            _append_recipe(
                f"dist-conda/{PACKAGE_NAME}/meta.yaml",
                "config/recipe-append.yaml",
            )
            session.run("cat", f"dist-conda/{PACKAGE_NAME}/meta.yaml", external=True)

        elif command == "recipe-full":
            import tempfile

            with tempfile.TemporaryDirectory() as d:  # type: ignore[assignment,unused-ignore]
                run(
                    "grayskull",
                    "pypi",
                    sdist_path,
                    "-o",
                    str(d),
                )
                path = Path(d) / PACKAGE_NAME / "meta.yaml"
                session.log(f"cat {path}:")
                with path.open() as f:
                    for line in f:
                        print(line, end="")  # noqa: T201


@nox.session(name="conda-build", **CONDA_DEFAULT_KWS)
@add_opts
def conda_build(session: nox.Session, opts: SessionParams) -> None:
    """Run `conda mambabuild`."""
    session.conda_install("boa", "anaconda-client")
    cmds, run = opts.conda_build, opts.conda_build_run

    session_run_commands(session, run)

    if not run and not cmds:
        cmds = ["build", "clean"]

    if cmds is None:
        cmds = []

    cmds = list(cmds)
    if "clean" in cmds:
        cmds.remove("clean")
        session.log("removing directory dist-conda/build")
        shutil.rmtree(Path("./dist-conda/build"), ignore_errors=True)

    for cmd in cmds:
        if cmd == "build":
            if not (d := Path(f"./dist-conda/{PACKAGE_NAME}/meta.yaml")).exists():
                msg = f"no file {d}"
                raise ValueError(msg)

            session.run(
                "conda",
                "mambabuild",
                "--output-folder=dist-conda/build",
                "--no-anaconda-upload",
                "dist-conda",
            )


# * Utilities -------------------------------------------------------------------------
def _append_recipe(recipe_path: str | Path, append_path: str | Path) -> None:
    recipe_path = Path(recipe_path)
    append_path = Path(append_path)

    with recipe_path.open() as f:
        recipe = f.readlines()

    with append_path.open() as f:
        append = f.readlines()

    with recipe_path.open("w") as f:
        f.writelines([*recipe, "\n", *append])
