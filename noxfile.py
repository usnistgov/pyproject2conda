"""Config file for nox."""
# * Imports ----------------------------------------------------------------------------
from __future__ import annotations

import shlex
import shutil
import sys
from functools import lru_cache, wraps

# Should only use on python version > 3.10
if sys.version_info < (3, 10):
    msg = "python>=3.10 required"
    raise RuntimeError(msg)

from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Callable,
    Iterable,
    Iterator,
    Literal,
    Sequence,
    TypeAlias,
    TypedDict,
)

# fmt: off
sys.path.insert(0, ".")
from tools.dataclass_parser import DataclassParser, add_option, option
from tools.noxtools import (
    Installer,
    check_for_change_manager,
    combine_list_str,
    factory_conda_backend,
    factory_virtualenv_backend,
    infer_requirement_path,
    is_conda_session,
    load_nox_config,
    open_webpage,
    prepend_flag,
    session_run_commands,
    update_target,
)

sys.path.pop(0)

# make sure these afeter
import nox  # type: ignore[unused-ignore,import]

# fmt: on

if TYPE_CHECKING:
    from nox import Session
    from nox.virtualenv import CondaEnv


# * Names ------------------------------------------------------------------------------

PACKAGE_NAME = "pyproject2conda"
IMPORT_NAME = "pyproject2conda"
KERNEL_BASE = "pyproject2conda"

# * nox options ------------------------------------------------------------------------

ROOT = Path(__file__).parent

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["test"]

# * User Config ------------------------------------------------------------------------

CONFIG = load_nox_config()

# * Options ---------------------------------------------------------------------------

LOCK = True

PYTHON_ALL_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12"]
PYTHON_DEFAULT_VERSION = "3.11"

# conda/mamba
for backend in ["mamba", "micromamba", "conda"]:
    if shutil.which(backend):
        CONDA_BACKEND: Literal["mamba", "micromamba", "conda"] = backend  # type: ignore[assignment]
        break
else:
    msg = "no conda-like backend found"
    raise ValueError(msg)


class SessionOptionsDict(TypedDict, total=False):
    """Dict for options to nox.session"""

    python: str | list[str]
    venv_backend: str | Callable[..., CondaEnv]


CONDA_DEFAULT_KWS: SessionOptionsDict = {
    "python": PYTHON_DEFAULT_VERSION,
    "venv_backend": factory_conda_backend(CONDA_BACKEND),
}
CONDA_ALL_KWS: SessionOptionsDict = {
    "python": PYTHON_ALL_VERSIONS,
    "venv_backend": factory_conda_backend(CONDA_BACKEND),
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
    """Holds all cli options"""

    # common parameters
    lock: bool = False
    update: bool = add_option("--update", "-U", help="update dependencies/package")
    update_package: bool = add_option(
        "--update-package",
        "-P",
        help="update package only",
    )
    log_session: bool = add_option("--log-session")
    version: str | None = None

    # dev
    dev_run: RUN_ANNO = None
    dev_envname: Literal["dev", "dev-complete", "dev-user"] = add_option(
        help="Name of environment to use for development session",
        default="dev",
    )

    # config
    dev_extras: OPT_TYPE = add_option(help="`extras` to include in dev environment")
    python_paths: OPT_TYPE = add_option(help="paths to python executables")

    # requirements
    requirements_force: bool = False
    requirements_run: RUN_ANNO = None
    requirements_no_notify: bool = add_option(
        default=False,
        help="Skip notification of pip-compile",
    )

    # conda-lock
    conda_lock_channel: OPT_TYPE = add_option(help="conda channels")
    conda_lock_platform: list[
        Literal["osx-64", "linux-64", "win-64", "osx-arm64", "all"]
    ] | None = add_option(help="platform(s) to buiuld lock file for.")
    conda_lock_include: OPT_TYPE = add_option(help="lock files to create")
    conda_lock_run: RUN_ANNO = None
    conda_lock_mamba: bool = False
    conda_lock_force: bool = False

    # pip-compile
    pip_compile_force: bool = False
    pip_compile_upgrade: bool = add_option(
        "--pip-compile-upgrade",
        "-L",
        help="Upgrade all packages in lock file",
        default=False,
    )
    pip_compile_upgrade_package: OPT_TYPE = add_option(
        help="Upgrade package(s) in lock file",
        default=None,
    )
    pip_compile_opts: OPT_TYPE = add_option(help="options to pip-compile")
    pip_compile_run: RUN_ANNO = None
    pip_compile_run_internal: RUN_ANNO = None

    # test
    test_no_pytest: bool = False
    test_opts: OPT_TYPE = add_option(help="Options to pytest")
    test_run: RUN_ANNO = None
    no_cov: bool = False

    # coverage
    coverage: list[Literal["erase", "combine", "report", "html", "open"]] | None = None
    coverage_run: RUN_ANNO = None
    coverage_run_internal: RUN_TYPE = None

    # testdist
    testdist_run: RUN_ANNO = None

    # docs
    docs: list[
        Literal[
            "html",
            "build",
            "symlink",
            "clean",
            "livehtml",
            "linkcheck",
            "spelling",
            "showlinks",
            "release",
            "open",
            "serve",
        ]
    ] | None = add_option("--docs", "-d", help="doc commands")
    docs_run: RUN_ANNO = None

    # lint (pre-commit)
    lint_run: RUN_ANNO = None

    # typing
    typing: list[
        Literal[
            "clean",
            "mypy",
            "pyright",
            "pytype",
            "all",
            "mypy-notebook",
            "pyright-notebook",
            "typing-notebook",
        ]
    ] = add_option("--typing", "-m")
    typing_run: RUN_ANNO = None
    typing_run_internal: RUN_TYPE = add_option(
        help="Run internal (in session) commands.",
    )

    # build
    build: list[Literal["build", "version"]] | None = None
    build_run: RUN_ANNO = None
    build_isolation: bool = False
    build_outdir: str = "./dist"
    build_opts: OPT_ANNO = None
    build_silent: bool = False

    # publish
    publish: list[Literal["release", "test"]] | None = add_option("-p", "--publish")
    publish_run: RUN_ANNO = None

    # conda-recipe/grayskull
    conda_recipe: list[Literal["recipe", "recipe-full"]] | None = None
    conda_recipe_run: RUN_ANNO = None
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
    opts.lock = opts.lock or LOCK

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


# * Environments------------------------------------------------------------------------
# ** Dev (conda)
@add_opts
def dev(
    session: Session,
    opts: SessionParams,
) -> None:
    """Create development environment using either conda (dev) or virtualenv (dev-venv) in location `.venv`"""
    (
        Installer.from_envname(
            session=session,
            envname=opts.dev_envname,
            lock=opts.lock,
            update=opts.update,
            package=True,
        )
        .install_all(
            update_package=opts.update_package,
            log_session=opts.log_session,
        )
        .set_ipykernel_display_name(name=f"{PACKAGE_NAME}-dev", update=True)
        .run_commands(opts.dev_run)
    )


nox.session(
    name="dev-venv",
    python=PYTHON_DEFAULT_VERSION,
    venv_backend=factory_virtualenv_backend(location="./.venv"),
)(dev)
nox.session(
    name="dev",
    python=PYTHON_DEFAULT_VERSION,
    venv_backend=factory_conda_backend(backend=CONDA_BACKEND, location="./.venv"),
)(dev)


@nox.session(python=False)
@add_opts
def config(
    session: Session,
    opts: SessionParams,
) -> None:
    """Create the file ./config/userconfig.toml"""
    args: list[str] = []
    if opts.dev_extras:
        args += ["--dev-extras", *opts.dev_extras]
    if opts.python_paths:
        args += ["--python-paths", *opts.python_paths]

    session.run("python", "tools/projectconfig.py", *args)


# ** requirements
@nox.session(python=False)
def pyproject2conda(
    session: Session,
) -> None:
    """Alias to reqs"""
    session.notify("requirements")


@nox.session
@add_opts
def requirements(
    session: Session,
    opts: SessionParams,
) -> None:
    """
    Create environment.yaml and requirement.txt files from pyproject.toml using pyproject2conda.

    These will be placed in the directory "./requirements".
    """
    runner = Installer(
        session=session,
        pip_deps="pyproject2conda>=0.11.0",
        update=opts.update,
    ).install_all(log_session=opts.log_session)

    if opts.requirements_run:
        runner.run_commands(opts.requirements_run)
    else:
        session.run(
            "pyproject2conda",
            "project",
            "--verbose",
            *(["--overwrite", "force"] if opts.requirements_force else []),
        )

        if not opts.requirements_no_notify and opts.lock:
            for py in PYTHON_ALL_VERSIONS:
                session.notify(f"pip-compile-{py}")


# # ** conda-lock
@nox.session(name="conda-lock", **DEFAULT_KWS)
@add_opts
def conda_lock(
    session: Session,
    opts: SessionParams,
) -> None:
    """Create lock files using conda-lock."""
    (
        Installer(
            session=session,
            pip_deps="conda-lock>=2.2.0",
            update=opts.update,
        ).install_all()
    )

    session.run("conda-lock", "--version")

    conda_lock_exclude = ["test-extras"]
    conda_lock_include = opts.conda_lock_include or [
        "test",
        "dev",
        "dev-complete",
        "nox",
    ]

    platform = opts.conda_lock_platform
    if platform is None or "all" in platform:
        # for now, skip osx-arm64 and win-64.  Leads to some problems.
        platform = ["osx-64", "linux-64"]  # , "win-64"]

    channel = opts.conda_lock_channel
    if not channel:
        channel = ["conda-forge"]

    def create_lock(path: Path) -> None:
        name = path.with_suffix("").name
        lockfile = path.parent / "lock" / f"{name}-conda-lock.yml"
        deps = [str(path)]

        # check if skip
        env = "-".join(name.split("-")[1:])
        if conda_lock_include and not any(c == env for c in conda_lock_include):
            session.log(f"Skipping {lockfile} (include)")
            return

        if conda_lock_exclude and any(c == env for c in conda_lock_exclude):
            session.log(f"Skipping {lockfile} (exclude)")
            return

        # check hashes

        with check_for_change_manager(
            *deps,
            target_path=lockfile,
            force_write=opts.conda_lock_force,
        ) as changed:
            if opts.conda_lock_force or changed:
                session.log(f"Creating {lockfile}")
                # insert -f for each arg
                if lockfile.exists():
                    lockfile.unlink()
                session.run(
                    "conda-lock",
                    "--mamba" if opts.conda_lock_mamba else "--no-mamba",
                    *prepend_flag("-c", *channel),
                    *prepend_flag("-p", *platform),
                    *prepend_flag("-f", *deps),
                    f"--lockfile={lockfile}",
                )
            else:
                session.log(f"Skipping {lockfile} (exists)")

    session_run_commands(session, opts.conda_lock_run)
    for path in (ROOT / "requirements").relative_to(ROOT.cwd()).glob("py*.yaml"):
        create_lock(path)


@nox.session(name="pip-compile", **ALL_KWS)
@add_opts
def pip_compile(  # noqa: C901
    session: Session,
    opts: SessionParams,
) -> None:
    """Run pip-compile.

    Note that this session is also used to run pip-sync with correct python version for
    tests/typing/etc.
    """
    runner = Installer(
        session=session,
        pip_deps=["pip-tools"],
        update=opts.update,
    ).install_all(log_session=opts.log_session)

    if opts.pip_compile_run:
        # run commands and exit
        runner.run_commands(opts.pip_compile_run)
        return

    if opts.pip_compile_run_internal:
        runner.run_commands(opts.pip_compile_run_internal, external=False)
        return

    options = opts.pip_compile_opts or []

    force = (
        opts.pip_compile_force
        or opts.pip_compile_upgrade
        or bool(opts.pip_compile_upgrade_package)
    )

    if opts.pip_compile_upgrade:
        options = [*options, "-U"]

    if opts.pip_compile_upgrade_package:
        options = options + prepend_flag("-P", opts.pip_compile_upgrade_package)

    envs_all = ["test", "typing"]
    envs_dev = ["dev", "dev-complete", "docs"]
    envs_dev_optional = ["test-notebook"]

    if session.python == PYTHON_DEFAULT_VERSION:
        envs = envs_all + envs_dev + envs_dev_optional
    else:
        envs = envs_all

    for env in envs:
        if not isinstance(session.python, str):
            msg = "session.python must be a string"
            raise TypeError(msg)

        reqspath = infer_requirement_path(env, ext=".txt", check_exists=False)
        if not reqspath.is_file():
            if env in envs_dev_optional:
                continue
            msg = f"Missing file {reqspath}"
            raise ValueError(msg)

        lockpath = infer_requirement_path(
            env,
            ext=".txt",
            python_version=session.python,
            lock=True,
            check_exists=False,
        )

        with check_for_change_manager(
            reqspath,
            target_path=lockpath,
            force_write=force,
        ) as changed:
            if force or changed:
                session.log(f"Creating {lockpath}")
                session.run("pip-compile", *options, "-o", str(lockpath), str(reqspath))

            else:
                session.log(f"Skipping {lockpath}")


# ** testing
def _test(
    session: nox.Session,
    run: RUN_TYPE,
    test_no_pytest: bool,
    test_opts: OPT_TYPE,
    no_cov: bool,
) -> None:
    import os

    tmpdir = os.environ.get("TMPDIR", None)

    session_run_commands(session, run)
    if not test_no_pytest:
        opts = combine_list_str(test_opts or [])
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
    (
        Installer.from_envname(
            session=session,
            envname="test",
            lock=opts.lock,
            # To use editable install
            # package=True,
            # To use full install
            package=get_package_wheel(session, opts="--no-deps --force-reinstall"),
            update=opts.update,
        ).install_all(log_session=opts.log_session, update_package=opts.update_package)
    )

    _test(
        session=session,
        run=opts.test_run,
        test_no_pytest=opts.test_no_pytest,
        test_opts=opts.test_opts,
        no_cov=opts.no_cov,
    )


nox.session(name="test", **ALL_KWS)(test)
nox.session(name="test-conda", **CONDA_ALL_KWS)(test)


@nox.session(name="test-notebook", **DEFAULT_KWS)
@add_opts
def test_notebook(session: nox.Session, opts: SessionParams) -> None:
    """Run pytest --nbval."""
    (
        Installer.from_envname(
            session=session,
            envname="test-notebook",
            lock=opts.lock,
            package=get_package_wheel(session, opts="--no-deps --force-reinstall"),
            update=opts.update,
        ).install_all(log_session=opts.log_session, update_package=opts.update_package)
    )

    test_nbval_opts = shlex.split(
        """
    --nbval
    --nbval-current-env
    --nbval-sanitize-with=config/nbval.ini
    --dist loadscope
     examples/usage
   """,
    )

    test_opts = (opts.test_opts or []) + test_nbval_opts

    session.log(f"{test_opts = }")

    _test(
        session=session,
        run=opts.test_run,
        test_no_pytest=opts.test_no_pytest,
        test_opts=test_opts,
        no_cov=opts.no_cov,
    )


# *** coverage
@nox.session
@add_opts
def coverage(
    session: Session,
    opts: SessionParams,
) -> None:
    """Run coverage."""
    runner = Installer(
        session=session,
        pip_deps="coverage[toml]",
        update=opts.update,
    ).install_all()

    runner.run_commands(opts.coverage_run)

    cmd = opts.coverage or []
    if not cmd and not opts.coverage_run and not opts.coverage_run_internal:
        cmd = ["combine", "html", "report"]

    session.log(f"{cmd}")

    for c in cmd:
        if c == "combine":
            paths = list(
                Path(session.virtualenv.location).parent.glob("test-*/tmp/.coverage"),
            )
            if update_target(".coverage", *paths):
                session.run("coverage", "combine", "--keep", "-a", *map(str, paths))
        elif c == "open":
            open_webpage(path="htmlcov/index.html")
        else:
            session.run("coverage", c)

    runner.run_commands(opts.coverage_run_internal)


# *** testdist (conda)
def testdist(
    session: Session,
) -> None:
    """Test conda distribution."""
    opts = parse_posargs(*session.posargs)

    install_str = PACKAGE_NAME
    if opts.version:
        install_str = f"{install_str}=={opts.version}"

    if is_conda_session(session):
        pip_deps, conda_deps = None, install_str
    else:
        pip_deps, conda_deps = install_str, None

    (
        Installer.from_envname(
            session=session,
            envname="test-extras",
            conda_deps=conda_deps,
            pip_deps=pip_deps,
            update=opts.update,
            channels="conda-forge",
        ).install_all(log_session=opts.log_session)
    )

    _test(
        session=session,
        run=opts.testdist_run,
        test_no_pytest=opts.test_no_pytest,
        test_opts=opts.test_opts,
        no_cov=opts.no_cov,
    )


nox.session(name="testdist-pypi", **ALL_KWS)(testdist)
nox.session(name="testdist-conda", **CONDA_ALL_KWS)(testdist)


# # ** Docs
@add_opts
def docs(
    session: nox.Session,
    opts: SessionParams,
) -> None:
    """
    Run `make` in docs directory.

    For example, 'nox -s docs -- +d html'
    calls 'make -C docs html'. With 'release' option, you can set the
    message with 'message=...' in posargs.
    """
    runner = Installer.from_envname(
        session=session,
        envname="docs",
        lock=opts.lock,
        package=True,
        update=opts.update,
    ).install_all(
        update_package=opts.update_package,
        log_session=opts.log_session,
    )

    if opts.version:
        session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = opts.version

    runner.run_commands(opts.docs_run)

    cmd = opts.docs or []
    if not opts.docs_run and not cmd:
        cmd = ["html"]

    if "symlink" in cmd:
        cmd.remove("symlink")
        _create_doc_examples_symlinks(session)

    if open_page := "open" in cmd:
        cmd.remove("open")

    if serve := "serve" in cmd:
        open_webpage(url="http://localhost:8000")
        cmd.remove("serve")

    if cmd:
        args = ["make", "-C", "docs", *combine_list_str(cmd)]
        session.run(*args, external=True)

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


nox.session(name="docs", **DEFAULT_KWS)(docs)
nox.session(name="docs-conda", **CONDA_DEFAULT_KWS)(docs)


# ** lint
@nox.session
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
    runner = Installer(
        session=session,
        pip_deps="pre-commit",
        update=opts.update,
    ).install_all(log_session=opts.log_session)

    if opts.lint_run:
        runner.run_commands(opts.lint_run, external=True)
    else:
        session.run("pre-commit", "run", "--all-files")


# ** type checking
@add_opts
def typing(  # noqa: C901
    session: nox.Session,
    opts: SessionParams,
) -> None:
    """Run type checkers (mypy, pyright, pytype)."""
    runner = (
        Installer.from_envname(
            session=session,
            envname="typing",
            lock=opts.lock,
            update=opts.update,
            # need package for nbqa checks
            package=True,
        )
        .install_all(log_session=opts.log_session)
        .run_commands(opts.typing_run)
    )

    cmd = opts.typing or []
    if not opts.typing_run and not opts.typing_run_internal and not cmd:
        cmd = ["mypy", "pyright"]

    if "all" in cmd:
        cmd = ["mypy", "pyright", "pytype"]

    # set the cache directory for mypy
    session.env["MYPY_CACHE_DIR"] = str(Path(session.create_tmp()) / ".mypy_cache")

    def _run_info(cmd: str) -> None:
        session.run("which", cmd, external=True)
        session.run(cmd, "--version", external=True)

    if "clean" in cmd:
        cmd.remove("clean")

        for name in [".mypy_cache", ".pytype"]:
            p = Path(session.create_tmp()) / name
            if p.exists():
                session.log(f"removing cache {p}")
                shutil.rmtree(str(p))

    for c in cmd:
        if c.endswith("-notebook"):
            session.run("make", c, external=True)
            continue

        _run_info(c)

        if c == "mypy":
            session.run("mypy", "--color-output")
        elif c == "pyright":
            session.run("pyright", external=True)
        elif c == "pytype":
            session.run("pytype", "-o", str(Path(session.create_tmp()) / ".pytype"))
        else:
            session.log(f"skipping unknown command {c}")

    runner.run_commands(opts.typing_run_internal, external=False)


nox.session(name="typing", **ALL_KWS)(typing)
nox.session(name="typing-conda", **CONDA_ALL_KWS)(typing)


# # ** Dist pypi
@nox.session
@add_opts
def build(session: nox.Session, opts: SessionParams) -> None:
    """
    Build the distribution.

    Note that default is to not use build isolation.
    Pass `--build-isolation` to use build isolation.
    """
    (
        Installer.from_envname(
            session=session,
            envname="build",
            update=opts.update,
        ).install_all(log_session=opts.log_session)
    )

    if opts.version:
        session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = opts.version

    for cmd in opts.build or ["build"]:
        if cmd == "version":
            session.run("python", "-m", "hatchling", "version")

        elif cmd == "build":
            if Path(outdir := opts.build_outdir).exists():
                shutil.rmtree(outdir)

            args = f"python -m build --outdir {outdir}".split()
            if not opts.build_isolation:
                args.append("--no-isolation")

            if opts.build_opts:
                args.extend(opts.build_opts)

            out = session.run(*args, silent=opts.build_silent)
            if opts.build_silent:
                if not isinstance(out, str):
                    msg = "session.run output not a string"
                    raise ValueError(msg)
                session.log(out.strip().split("\n")[-1])


def get_package_wheel(
    session: Session,
    opts: str | Iterable[str] | None = None,
    extras: str | Iterable[str] | None = None,
    reuse: bool = True,
) -> str:
    """
    Build the package in return the build location

    This is similar to how tox does isolated builds.

    Note that the first time this is called,

    Should be straightforward to extend this to isolated builds
    that depend on python version (something like have session build-3.11 ....)
    """
    dist_location = Path(session.cache_dir) / "dist"
    if reuse and getattr(get_package_wheel, "_called", False):
        session.log("Reuse isolated build")
    else:
        cmd = f"nox -s build -- ++build-outdir {dist_location} ++build-opts -w ++build-silent"
        session.run(*shlex.split(cmd), external=True)

        # save that this was called:
        if reuse:
            get_package_wheel._called = True  # type: ignore[attr-defined]  # noqa: SLF001

    paths = list(dist_location.glob("*.whl"))
    if len(paths) != 1:
        msg = "something wonky with paths {paths}"
        raise ValueError(msg)

    path = str(paths[0])

    if extras:
        if not isinstance(extras, str):
            extras = ",".join(extras)
        path = f"{path}[{extras}]"

    if opts:
        if not isinstance(opts, str):
            opts = " ".join(opts)
        path = f"{path} {opts}"

    return path


@nox.session
@add_opts
def publish(session: nox.Session, opts: SessionParams) -> None:
    """Publish the distribution"""
    (
        Installer(session=session, pip_deps="twine", update=opts.update)
        .install_all(log_session=opts.log_session)
        .run_commands(opts.publish_run)
    )

    for cmd in opts.publish or []:
        if cmd == "test":
            session.run("twine", "upload", "--repository", "testpypi", "dist/*")

        elif cmd == "release":
            session.run("twine", "upload", "dist/*")


# # ** Dist conda
@nox.session(name="conda-recipe")
@add_opts
def conda_recipe(
    session: nox.Session,
    opts: SessionParams,
) -> None:
    """Run grayskull to create recipe"""
    runner = Installer(
        session=session,
        pip_deps=["grayskull"],
        update=opts.update,
    ).install_all(log_session=opts.log_session)

    run, commands = opts.conda_recipe_run, opts.conda_recipe

    runner.run_commands(run)

    if not run and not commands:
        commands = ["recipe"]

    if not commands:
        return

    sdist_path = opts.conda_recipe_sdist_path
    if not sdist_path:
        sdist_path = PACKAGE_NAME
        if opts.version:
            sdist_path = f"{sdist_path}=={opts.version}"

    for command in commands:
        if command == "recipe":
            # make directory?
            if not (d := Path("./dist-conda")).exists():
                d.mkdir()

            session.run(
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
                session.run(
                    "grayskull",
                    "pypi",
                    sdist_path,
                    "-o",
                    str(d),
                )
                session.run(
                    "cat",
                    str(Path(d) / PACKAGE_NAME / "meta.yaml"),
                    external=True,
                )


@nox.session(name="conda-build", **CONDA_DEFAULT_KWS)
@add_opts
def conda_build(session: nox.Session, opts: SessionParams) -> None:
    """Run `conda mambabuild`."""
    runner = Installer.from_envname(
        session=session,
        update=opts.update,
        conda_deps=["boa", "anaconda-client"],
    ).install_all(log_session=opts.log_session)

    cmds, run = opts.conda_build, opts.conda_build_run

    runner.run_commands(run)

    if not run and not cmds:
        cmds = ["build", "clean"]

    if cmds is None:
        cmds = []

    if "clean" in cmds:
        cmds.remove("clean")
        session.log("removing directory dist-conda/build")
        if Path("./dist-conda/build").exists():
            shutil.rmtree("./dist-conda/build")

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


# ** Other utilities
@nox.session
@add_opts
def cog(session: nox.Session, opts: SessionParams) -> None:
    """Run cog."""
    Installer.from_envname(
        session=session,
        update=opts.update,
        pip_deps="cogapp",
    ).install_all(log_session=opts.log_session)
    session.run("cog", "-rP", "README.md", env={"COLUMNS": "100"})


# * Utilities -------------------------------------------------------------------------
def _create_doc_examples_symlinks(session: nox.Session, clean: bool = True) -> None:  # noqa: C901
    """Create symlinks from docs/examples/*.md files to /examples/usage/..."""
    import os

    def usage_paths(path: Path) -> Iterator[Path]:
        with path.open("r") as f:
            for line in f:
                if line.startswith("usage/"):
                    yield Path(line.strip())

    def get_target_path(
        usage_path: str | Path,
        prefix_dir: str | Path = "./examples",
        exts: Sequence[str] = (".md", ".ipynb"),
    ) -> Path:
        path = Path(prefix_dir) / Path(usage_path)

        if not all(ext.startswith(".") for ext in exts):
            msg = "Bad extensions.  Should start with '.'"
            raise ValueError(msg)

        if path.exists():
            return path

        for ext in exts:
            p = path.with_suffix(ext)
            if p.exists():
                return p

        msg = f"no path found for base {path}"
        raise ValueError(msg)

    root = Path("./docs/examples/")
    if clean:
        import shutil

        shutil.rmtree(root / "usage", ignore_errors=True)

    # get all md files
    paths = list(root.glob("*.md"))

    # read usage lines
    for path in paths:
        for usage_path in usage_paths(path):
            target = get_target_path(usage_path)
            link = root / usage_path.parent / target.name

            if link.exists():
                link.unlink()

            link.parent.mkdir(parents=True, exist_ok=True)

            target_rel = os.path.relpath(target, start=link.parent)
            session.log(f"linking {target_rel} -> {link}")

            os.symlink(target_rel, link)


def _append_recipe(recipe_path: str | Path, append_path: str | Path) -> None:
    recipe_path = Path(recipe_path)
    append_path = Path(append_path)

    with recipe_path.open() as f:
        recipe = f.readlines()

    with append_path.open() as f:
        append = f.readlines()

    with recipe_path.open("w") as f:
        f.writelines([*recipe, "\n", *append])
