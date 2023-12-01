"""Config file for nox."""
# * Imports ----------------------------------------------------------------------------
from __future__ import annotations

import shutil
import sys
from functools import lru_cache, wraps

# Should only use on python version > 3.10
assert sys.version_info >= (3, 10)

from dataclasses import dataclass
from pathlib import Path
from typing import (
    Annotated,
    Callable,
    Iterator,
    Literal,
    Sequence,
    TypeAlias,
    TypedDict,
)

import nox  # type: ignore[unused-ignore,import]
from nox import Session

# fmt: off
sys.path.insert(0, ".")

from tools.dataclass_parser import DataclassParser, add_option, option
from tools.noxtools import (
    Installer,
    check_hash_path_for_change,
    combine_list_str,
    infer_requirement_path,
    is_conda_session,
    load_nox_config,
    open_webpage,
    prepend_flag,
    session_run_commands,
    update_target,
    write_hashes,
)

sys.path.pop(0)
# fmt: on


# * Names ------------------------------------------------------------------------------

PACKAGE_NAME = "pyproject2conda"
IMPORT_NAME = "pyproject2conda"
KERNEL_BASE = "pyproject2conda"

# * nox options ------------------------------------------------------------------------

ROOT = Path(__file__).parent

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["test"]
# Using ".nox/{project-name}/envs" instead of ".nox" to store environments.
# This fixes problems with ipykernel/nb_conda_kernel and some other dev tools
# that expect conda environments to be in something like ".../a/path/miniforge/envs/env".
nox.options.envdir = f".nox/{PACKAGE_NAME}/envs"

# * User Config ------------------------------------------------------------------------

CONFIG = load_nox_config()

# * Options ---------------------------------------------------------------------------

LOCK = True

PYTHON_ALL_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12"]
PYTHON_DEFAULT_VERSION = "3.11"

# conda/mamba
if shutil.which("mamba"):
    CONDA_BACKEND = "mamba"
elif shutil.which("conda"):
    CONDA_BACKEND = "conda"  # pyright: ignore
else:
    raise ValueError("neither conda or mamba found")


class SessionOptionsDict(TypedDict, total=False):
    """Dict for options to nox.session"""

    python: str | list[str]
    venv_backend: str


CONDA_DEFAULT_KWS: SessionOptionsDict = {
    "python": PYTHON_DEFAULT_VERSION,
    "venv_backend": CONDA_BACKEND,
}
CONDA_ALL_KWS: SessionOptionsDict = {
    "python": PYTHON_ALL_VERSIONS,
    "venv_backend": CONDA_BACKEND,
}

DEFAULT_KWS: SessionOptionsDict = {"python": PYTHON_DEFAULT_VERSION}
ALL_KWS: SessionOptionsDict = {"python": PYTHON_ALL_VERSIONS}


# * Session command line options -------------------------------------------------------

OPT_TYPE: TypeAlias = list[str] | None
RUN_TYPE: TypeAlias = list[list[str]] | None

RUN_ANNO = Annotated[
    RUN_TYPE,
    option(
        help="Run external commands in session.  Specify multiple times for multiple commands."
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
        "--update-package", "-P", help="update package only"
    )
    log_session: bool = add_option("--log-session", "-L")
    version: str | None = None

    # dev
    dev_run: RUN_ANNO = None

    # config
    dev_extras: OPT_TYPE = add_option(help="`extras` to include in dev environment")
    python_paths: OPT_TYPE = add_option(help="paths to python executables")

    # requirements
    requirements_force: bool = False

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
            "nbqa-mypy",
            "nbqa-pyright",
            "nbqa-typing",
        ]
    ] = add_option("--typing", "-m")
    typing_run: RUN_ANNO = None
    typing_run_internal: RUN_TYPE = add_option(
        help="Run internal (in session) commands."
    )

    # build
    build: list[Literal["build", "version"]] | None = None
    build_run: RUN_ANNO = None
    build_isolation: bool = False

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
    func: Callable[[Session, SessionParams], None]
) -> Callable[[Session], None]:
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
    """Create development environment using either conda (dev) or virtualenv (dev-venv)."""

    (
        Installer.from_envname(
            session=session,
            envname="dev",
            lock=opts.lock,
            update=opts.update,
            package=".",
        )
        .install_all(
            update_package=opts.update_package,
            log_session=opts.log_session,
            display_name=f"{PACKAGE_NAME}-{session.name}",
        )
        .run_commands(opts.dev_run)
    )


nox.session(name="dev-venv", **DEFAULT_KWS)(dev)
nox.session(name="dev", **CONDA_DEFAULT_KWS)(dev)


# ** bootstrap
@nox.session(python=False)
def bootstrap(session: Session) -> None:
    """Run config, reqs, and dev"""

    session.notify("config")
    session.notify("requirements")
    session.notify("dev")


# ** config
@nox.session(python=False)
@add_opts
def config(
    session: Session,
    opts: SessionParams,
) -> None:
    """Create the file ./config/userconfig.toml"""
    args: list[str] = []
    if opts.dev_extras:
        args += ["--dev-extras"] + opts.dev_extras
    if opts.python_paths:
        args += ["--python-paths"] + opts.python_paths

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

    (
        Installer(
            session=session,
            pip_deps="pyproject2conda>=0.11.0",
            update=opts.update,
        ).install_all(log_session=opts.log_session)
    )

    session.run(
        "pyproject2conda",
        "project",
        "--verbose",
        *(["--overwrite", "force"] if opts.requirements_force else []),
    )

    if opts.lock:
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

    conda_lock_exclude = ["test-extras", "dev"]

    platform = opts.conda_lock_platform
    if platform is None or "all" in platform:
        # for now, skip osx-arm64 and win-64.  Leads to some problems.
        platform = ["osx-64", "linux-64"]

    channel = opts.conda_lock_channel
    if not channel:
        channel = ["conda-forge"]

    def create_lock(path: Path) -> None:
        name = path.with_suffix("").name
        lockfile = path.parent / "lock" / f"{name}-conda-lock.yml"
        deps = [str(path)]

        # check if skip
        env = "-".join(name.split("-")[1:])
        if opts.conda_lock_include:
            if not any(c == env for c in opts.conda_lock_include):  # pyright: ignore
                session.log(f"Skipping {lockfile} (include)")
                return

        if conda_lock_exclude:
            if any(c == env for c in conda_lock_exclude):  # pyright: ignore
                session.log(f"Skipping {lockfile} (exclude)")
                return

        # check hashes
        changed, hash_path, hashes = check_hash_path_for_change(lockfile, *deps)
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
            write_hashes(hash_path, hashes)
        else:
            session.log(f"Skipping {lockfile} (exists)")

    session_run_commands(session, opts.conda_lock_run)
    for path in (ROOT / "requirements").relative_to(ROOT.cwd()).glob("py*.yaml"):
        create_lock(path)


@nox.session(name="pip-compile", **ALL_KWS)
@add_opts
def pip_compile(
    session: Session,
    opts: SessionParams,
) -> None:
    """Run pip-compile."""

    (
        Installer(
            session=session, pip_deps=["pip-tools"], update=opts.update
        ).install_all(log_session=opts.log_session)
    )

    envs_all = ["test", "typing"]
    envs_dev = ["dev", "dev-complete", "dev-base", "docs"]

    if session.python == PYTHON_DEFAULT_VERSION:
        envs = envs_all + envs_dev
    else:
        envs = envs_all

    for env in envs:
        assert isinstance(session.python, str)
        reqspath = infer_requirement_path(env, ext=".txt")
        lockpath = infer_requirement_path(
            env,
            ext=".txt",
            python_version=session.python,
            lock=True,
            check_exists=False,
        )

        changed, hash_path, hashes = check_hash_path_for_change(lockpath, reqspath)
        if opts.pip_compile_force or changed:
            session.log(f"Creating {lockpath}")
            session.run("pip-compile", "-U", "-o", lockpath, reqspath)
            write_hashes(hash_path, hashes)

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

            if "--cov" not in opts:
                opts.append("--cov")

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
            package=".",
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


# *** coverage
@nox.session
@add_opts
def coverage(
    session: Session,
    opts: SessionParams,
) -> None:
    runner = Installer(
        session=session, pip_deps="coverage[toml]", update=opts.update
    ).install_all()

    runner.run_commands(opts.coverage_run)

    cmd = opts.coverage or []
    if not cmd and not opts.coverage_run and not opts.coverage_run_internal:
        cmd = ["combine", "html", "report"]

    session.log(f"{cmd}")

    for c in cmd:
        if c == "combine":
            paths = list(
                Path(session.virtualenv.location).parent.glob("test-*/tmp/.coverage")
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
        no_cov=True,
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
    Runs make in docs directory. For example, 'nox -s docs -- +d html'
    calls 'make -C docs html'. With 'release' option, you can set the
    message with 'message=...' in posargs.
    """
    runner = Installer.from_envname(
        session=session, envname="docs", lock=opts.lock, package=".", update=opts.update
    ).install_all(
        update_package=opts.update_package,
        log_session=opts.log_session,
        display_name=f"{PACKAGE_NAME}-{session.name}",
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
        args = ["make", "-C", "docs"] + combine_list_str(cmd)
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
        session=session, pip_deps="pre-commit", update=opts.update
    ).install_all(log_session=opts.log_session)

    if opts.lint_run:
        runner.run_commands(opts.lint_run, external=True)
    else:
        session.run("pre-commit", "run", "--all-files")


# ** type checking
@add_opts
def typing(
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
        cmd = [x for x in cmd if x != "clean"]

        for name in [".mypy_cache", ".pytype"]:
            p = Path(session.create_tmp()) / name
            if p.exists():
                session.log(f"removing cache {p}")
                shutil.rmtree(str(p))

    for c in cmd:
        if not c.startswith("nbqa"):
            _run_info(c)
        if c == "mypy":
            session.run("mypy", "--color-output")
        elif c == "pyright":
            session.run("pyright", external=True)
        elif c == "pytype":
            session.run("pytype", "-o", str(Path(session.create_tmp()) / ".pytype"))
        elif c.startswith("nbqa"):
            session.run("make", c, external=True)
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
            session.run("python", "-m", "setuptools_scm")

        elif cmd == "build":
            if Path("dist").exists():
                shutil.rmtree("./dist")

            args = "python -m build --outdir dist".split()
            if not opts.build_isolation:
                args.append("--no-isolation")

            session.run(*args)


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
        session=session, pip_deps=["grayskull"], update=opts.update
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
                f"dist-conda/{PACKAGE_NAME}/meta.yaml", "config/recipe-append.yaml"
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
                    "cat", str(Path(d) / PACKAGE_NAME / "meta.yaml"), external=True
                )


@nox.session(name="conda-build", **CONDA_DEFAULT_KWS)
@add_opts
def conda_build(session: nox.Session, opts: SessionParams) -> None:
    runner = Installer.from_envname(
        session=session, update=opts.update, conda_deps=["boa", "anaconda-client"]
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
                raise ValueError(f"no file {d}")

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
        envname="cog",
        package=".",
    ).install_all(log_session=opts.log_session)
    session.run("cog", "-rP", "README.md", env={"COLUMNS": "100"})


# * Utilities -------------------------------------------------------------------------
def _create_doc_examples_symlinks(session: nox.Session, clean: bool = True) -> None:
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

        assert all(ext.startswith(".") for ext in exts)

        if path.exists():
            return path
        else:
            for ext in exts:
                p = path.with_suffix(ext)
                if p.exists():
                    return p

        raise ValueError(f"no path found for base {path}")

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


def _append_recipe(recipe_path: str, append_path: str) -> None:
    with open(recipe_path) as f:
        recipe = f.readlines()

    with open(append_path) as f:
        append = f.readlines()

    with open(recipe_path, "w") as f:
        f.writelines(recipe + ["\n"] + append)


# # If want separate env for updating/reporting version with setuptools-scm
# # We do this from dev environment.
# # ** version report/update
# @nox.session(**DEFAULT_KWS)
# def version_scm(
#     session: Session,
#     version: VERSION_CLI = "",
#     update: UPDATE_CLI = False,
# ):
#     """
#     Get current version from setuptools-scm

#     Note that the version of editable installs can get stale.
#     This will show the actual current version.
#     Avoids need to include setuptools-scm in develop/docs/etc.
#     """

#     pkg_install_venv(
#         session=session,
#         name="version-scm",
#         install_package=True,
#         reqs=["setuptools_scm"],
#         update=opts.update,
#         no_deps=True,
#     )

#     if version:
#         session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = version

#     session.run("python", "-m", "setuptools_scm")
