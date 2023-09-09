"""Config file for nox."""
from __future__ import annotations

import shutil
import sys
from dataclasses import replace  # noqa
from itertools import product
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Callable,
    Iterator,
    Literal,
    Sequence,
    TypeAlias,
    TypeVar,
    cast,
)

import nox
from noxopt import NoxOpt, Option, Session

# Not sure why I need to adjust sys.path sometimes and not others.
# fmt: off
sys.path.append(".")
from tools.noxtools import (
    combine_list_str,
    load_nox_config,
    open_webpage,
    pkg_install_condaenv,
    pkg_install_venv,
    prepend_flag,
    session_environment_filename,
    session_run_commands,
    sort_like,
    update_target,
)

sys.path.pop()
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

# * Options ----------------------------------------------------------------------------

PYTHON_ALL_VERSIONS = ["3.8", "3.9", "3.10", "3.11"]
PYTHON_DEFAULT_VERSION = "3.10"

# conda/mamba
if shutil.which("mamba"):
    CONDA_BACKEND = "mamba"
elif shutil.which("conda"):
    CONDA_BACKEND = "conda"  # pyright: ignore
else:
    raise ValueError("neither conda or mamba found")

SESSION_DEFAULT_KWS = {"python": PYTHON_DEFAULT_VERSION, "venv_backend": CONDA_BACKEND}
SESSION_ALL_KWS = {"python": PYTHON_ALL_VERSIONS, "venv_backend": CONDA_BACKEND}


# * noxopt -----------------------------------------------------------------------------
group = NoxOpt(auto_tag=True)

F = TypeVar("F", bound=Callable[..., Any])
C: TypeAlias = Callable[[F], F]

DEFAULT_SESSION = cast(C[F], group.session(**SESSION_DEFAULT_KWS))  # type: ignore
ALL_SESSION = cast(C[F], group.session(**SESSION_ALL_KWS))  # type: ignore

DEFAULT_SESSION_VENV = cast(C[F], group.session(python=PYTHON_DEFAULT_VERSION))  # type: ignore
ALL_SESSION_VENV = cast(C[F], group.session(python=PYTHON_ALL_VERSIONS))  # type: ignore

OPTS_OPT = Option(nargs="*", type=str)
# SET_KERNEL_OPT = Option(type=bool, help="If True, try to set the kernel name")
RUN_OPT = Option(
    nargs="*",
    type=str,
    action="append",
    help="run passed command_demo using `external=True` flag",
)

CMD_OPT = Option(nargs="*", type=str, help="cmd to be run")
LOCK_OPT = Option(type=bool, help="If True, use conda-lock")


def opts_annotated(**kwargs: Any):  # type: ignore
    return Annotated[list[str], replace(OPTS_OPT, **kwargs)]


def cmd_annotated(**kwargs: Any):  # type: ignore
    return Annotated[list[str], replace(CMD_OPT, **kwargs)]


def run_annotated(**kwargs: Any):  # type: ignore
    return Annotated[list[list[str]], replace(RUN_OPT, **kwargs)]


LOCK_CLI = Annotated[bool, LOCK_OPT]
RUN_CLI = Annotated[list[list[str]], RUN_OPT]
TEST_OPTS_CLI = opts_annotated(help="extra arguments/flags to pytest")
DEV_EXTRAS_CLI = cmd_annotated(help="extras included in user dev environment")
PYTHON_PATHS_CLI = cmd_annotated(help="python paths to append to PATHS")


FORCE_REINSTALL_CLI = Annotated[
    bool,
    Option(
        type=bool,
        help="If True, force reinstall requirements and package even if environment unchanged",
    ),
]

VERSION_CLI = Annotated[
    str, Option(type=str, help="Version to substitute or check against")
]

LOG_SESSION_CLI = Annotated[
    bool,
    Option(
        type=bool,
        help="If flag included, log python and package (if installed) version",
    ),
]


# * Environments------------------------------------------------------------------------
# ** Development (conda)
@DEFAULT_SESSION
def dev(
    session: Session,
    dev_run: RUN_CLI = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
) -> None:
    """Create dev env using conda."""
    # using conda

    pkg_install_condaenv(
        session=session,
        name="dev",
        lock=lock,
        display_name=f"{PACKAGE_NAME}-dev",
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )
    session_run_commands(session, dev_run)


@DEFAULT_SESSION_VENV
def dev_venv(
    session: Session,
    dev_run: RUN_CLI = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
) -> None:
    """Create dev env using virtualenv."""
    # using conda

    pkg_install_venv(
        session=session,
        name="dev-venv",
        lock=lock,
        extras=load_nox_config()["environment-extras"].get("dev", ["nox", "dev"]),
        display_name=f"{PACKAGE_NAME}-dev-venv",
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )
    session_run_commands(session, dev_run)


@group.session(python=False)  # type: ignore
def config(
    session: Session,
    dev_extras: DEV_EXTRAS_CLI = [],  # type: ignore # noqa
    python_paths: PYTHON_PATHS_CLI = [],  # type: ignore # noqa
) -> None:
    """Create the file ./config/userconfig.toml"""

    args = []
    if dev_extras:
        args += ["--dev-extras"] + dev_extras
    if python_paths:
        args += ["--python-paths"] + python_paths

    session.run("python", "tools/projectconfig.py", *args)


@group.session(python=False)  # type: ignore
def bootstrap(session: Session):
    """Run config, reqs, and dev"""
    session.notify("config")
    session.notify("requirements")
    session.notify("dev")


@group.session(python=False)  # type: ignore
def pyproject2conda(
    session: Session,
    force_reinstall: FORCE_REINSTALL_CLI = False,
) -> None:
    """Alias to reqs"""
    session.notify("requirements")


@group.session
def requirements(
    session: Session,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    requirements_force: bool = False,
    log_session: bool = False,
) -> None:
    """
    Create environment.yaml and requirement.txt files from pyproject.toml using pyproject2conda.

    These will be placed in the directory "./environments".
    """
    pkg_install_venv(
        session=session,
        reqs=["."],
        name="reqs",
        force_reinstall=force_reinstall,
        log_session=log_session,
    )

    def create_env(
        python_version: str | None = None,
        cmd: Literal["yaml", "requirements"] = "yaml",
        name: str | None = None,
        output: str | None = None,
        extras: str | Sequence[str] | None = None,
        python_include: str | bool = True,
        base: bool = True,
    ) -> None:
        def _to_args(flag: str, val: str | Sequence[str] | None) -> list[str]:
            if val is None:
                return []
            if isinstance(val, str):
                val = [val]
            return prepend_flag(flag, *val)

        if output is None:
            assert name is not None
            output = session_environment_filename(
                python_version=python_version,
                name=name,
                ext={"yaml": ".yaml", "requirements": ".txt"}[cmd],
            )

        if (
            requirements_force
            or update_target(output, "pyproject.toml")
            or update_target(output, "config/userconfig.toml", allow_missing=True)
        ):
            args = [cmd, "-o", output] + _to_args("-e", extras)

            if cmd == "yaml":
                if python_version is not None:
                    args.extend(["--python-version", python_version])
                if isinstance(python_include, bool) and python_include:
                    python_include = f"python={python_version}"
                if isinstance(python_include, str):
                    args.extend(["--python-include", python_include])

            if not base:
                args.append("--no-base")

            session.run("pyproject2conda", *args)
        else:
            session.log(
                f"{output} up to data.  Pass --environments-force to force recreation"
            )

    extras = load_nox_config().get("environment-extras", {"dev": ["dev", "nox"]})
    extras["dev-base"] = ["dev"]

    # All versions:
    for env, python_version in product(["test", "typing"], PYTHON_ALL_VERSIONS):
        create_env(
            name=env,
            extras=extras.get(env, env),
            base=True,
            python_version=python_version,
        )

    for env, python_version in product(
        ["docs", "dev", "dev-base"], [PYTHON_DEFAULT_VERSION]
    ):
        create_env(
            name=env,
            extras=extras.get(env, env),
            base=True,
            python_version=python_version,
        )

    # need an isolated set of test requirements
    for python_version in PYTHON_ALL_VERSIONS:
        create_env(
            name="test-extras",
            extras="test",
            base=False,
            python_version=python_version,
        )

    # isolated
    for env in ["dist-pypi", "dist-conda"]:
        create_env(
            name=f"{env}",
            extras=env,
            base=False,
            python_version=PYTHON_DEFAULT_VERSION,
        )

    # isolated requirement files.
    # no python versioning for these
    for env, extras in [("test-extras", "test"), ("dist-pypi", "dist-pypi")]:
        create_env(name=f"{env}", cmd="requirements", extras=extras, base=False)


# ** conda-lock
@DEFAULT_SESSION_VENV
def conda_lock(
    session: Session,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    conda_lock_channel: cmd_annotated(help="conda channels to use") = (),  # type: ignore
    conda_lock_platform: cmd_annotated(  # type: ignore
        help="platforms to build lock files for",
        choices=["osx-64", "linux-64", "win-64", "all"],
    ) = (),
    conda_lock_cmd: cmd_annotated(  # type: ignore
        help="lock files to create",
        choices=["test", "typing", "dev", "dist-pypi", "dist-conda", "all"],
    ) = (),
    conda_lock_run: RUN_CLI = [],  # noqa
    conda_lock_mamba: bool = False,
    conda_lock_force: bool = False,
) -> None:
    """Create lock files using conda-lock."""

    pkg_install_venv(
        session,
        name="conda-lock",
        reqs=["conda-lock>=2.0.0"],
        force_reinstall=force_reinstall,
    )

    session.run("conda-lock", "--version")

    platform = cast(Sequence[str], conda_lock_platform)
    if not platform:
        platform = ["osx-64"]
    elif "all" in platform:
        platform = ["linux-64", "osx-64", "win-64"]
    channel = cast(Sequence[str], conda_lock_channel)
    if not channel:
        channel = ["conda-forge"]

    lock_dir = ROOT / "environment" / "lock"

    def create_lock(
        py: str,
        name: str,
        env_path: str | None = None,
    ) -> None:
        py = "py" + py.replace(".", "")

        if env_path is None:
            env_path = f"environment/{py}-{name}.yaml"

        lockfile = lock_dir / f"{py}-{name}-conda-lock.yml"

        deps = [env_path]
        # make sure this is last to make python version last
        # deps.append(lock_dir / f"{py}.yaml")

        if conda_lock_force or update_target(lockfile, *deps):
            session.log(f"creating {lockfile}")
            # insert -f for each arg
            if lockfile.exists():
                lockfile.unlink()
            session.run(
                "conda-lock",
                "--mamba" if conda_lock_mamba else "--no-mamba",
                *prepend_flag("-c", *channel),
                *prepend_flag("-p", *platform),
                *prepend_flag("-f", *deps),
                f"--lockfile={lockfile}",
            )

    session_run_commands(session, conda_lock_run)

    if not conda_lock_run and not conda_lock_cmd:
        conda_lock_cmd = ["all"]  # pyright: ignore
    if "all" in conda_lock_cmd:
        conda_lock_cmd = ["test", "typing", "dev", "dist-pypi", "dist-conda"]
    conda_lock_cmd = list(set(conda_lock_cmd))

    for c in conda_lock_cmd:
        if c == "test":
            for py in PYTHON_ALL_VERSIONS:
                create_lock(py, "test")
        elif c == "typing":
            for py in PYTHON_ALL_VERSIONS:
                create_lock(py, "typing")
        elif c == "dev":
            create_lock(PYTHON_DEFAULT_VERSION, "dev")
        elif c == "dist-pypi":
            create_lock(
                PYTHON_DEFAULT_VERSION,
                "dist-pypi",
            )
        elif c == "dist-conda":
            create_lock(
                PYTHON_DEFAULT_VERSION,
                "dist-conda",
            )


# ** testing
def _test(
    session: nox.Session,
    run: list[list[str]],
    test_no_pytest: bool,
    test_opts: list[str],
    no_cov: bool,
) -> None:
    session_run_commands(session, run)
    if not test_no_pytest:
        opts = combine_list_str(test_opts)
        if not no_cov:
            session.env["COVERAGE_FILE"] = str(Path(session.create_tmp()) / ".coverage")
            if "--cov" not in opts:
                opts.append("--cov")
        session.run("pytest", *opts)


@ALL_SESSION
def test(
    session: Session,
    test_no_pytest: bool = False,
    test_opts: TEST_OPTS_CLI = (),  # type: ignore
    test_run: RUN_CLI = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
    no_cov: bool = False,
) -> None:
    """Test environments with conda installs."""

    pkg_install_condaenv(
        session=session,
        name="test",
        lock=lock,
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )

    _test(
        session=session,
        run=test_run,
        test_no_pytest=test_no_pytest,
        test_opts=test_opts,
        no_cov=no_cov,
    )


@ALL_SESSION_VENV
def test_venv(
    session: Session,
    test_no_pytest: bool = False,
    test_opts: TEST_OPTS_CLI = (),  # type: ignore
    test_run: RUN_CLI = [],  # noqa
    lock: LOCK_CLI = False,  # pyright: ignore
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
    no_cov: bool = False,
) -> None:
    """Test environments virtualenv and pip installs."""

    pkg_install_venv(
        session=session,
        name="test-venv",
        extras="test",
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )

    _test(
        session=session,
        run=test_run,
        test_no_pytest=test_no_pytest,
        test_opts=test_opts,
        no_cov=no_cov,
    )


# ** coverage
def _coverage(
    session: nox.Session,
    run: list[list[str]],
    cmd: list[str],
    run_internal: list[list[str]],
) -> None:
    session_run_commands(session, run)

    if not cmd and not run and not run_internal:
        cmd = ["combine", "report"]

    session.log(f"{cmd}")

    for c in cmd:
        if c == "combine":
            paths = list(
                Path(session.virtualenv.location).parent.glob("test-3*/tmp/.coverage")
            )
            if update_target(".coverage", *paths):
                session.run("coverage", "combine", "--keep", "-a", *map(str, paths))
        elif c == "open":
            open_webpage(path="htmlcov/index.html")
        else:
            session.run("coverage", c)

    session_run_commands(session, run_internal, external=False)


@DEFAULT_SESSION_VENV
def coverage(
    session: Session,
    coverage_cmd: cmd_annotated(  # type: ignore
        choices=["erase", "combine", "report", "html", "open"]
    ) = (),
    coverage_run: RUN_CLI = [],  # noqa
    coverage_run_internal: run_annotated(  # type: ignore
        help="Arbitrary commands to run within the session"
    ) = [],  # noqa
    force_reinstall: FORCE_REINSTALL_CLI = False,
) -> None:
    pkg_install_venv(
        session,
        name="coverage",
        reqs=["coverage[toml]"],
        force_reinstall=force_reinstall,
    )

    _coverage(
        session=session,
        run=coverage_run,
        cmd=cast(list[str], coverage_cmd),
        run_internal=cast(list[list[str]], coverage_run_internal),
    )


# ** Docs
def _docs(
    session: nox.Session, run: list[list[str]], cmd: list[str], version: str
) -> None:
    if version:
        session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = version

    session_run_commands(session, run)

    if not run and not cmd:
        cmd = ["html"]

    if "symlink" in cmd:
        cmd.remove("symlink")
        _create_doc_examples_symlinks(session)

    if open_page := "open" in cmd:
        cmd.remove("open")

    if cmd:
        args = ["make", "-C", "docs"] + combine_list_str(cmd)
        session.run(*args, external=True)

    if open_page:
        open_webpage(path="./docs/_build/html/index.html")


@DEFAULT_SESSION
def docs(
    session: nox.Session,
    docs_cmd: cmd_annotated(  # type: ignore
        choices=[
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
        ],
        flags=("--docs-cmd", "-d"),
    ) = (),
    docs_run: RUN_CLI = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
) -> None:
    """Runs make in docs directory. For example, 'nox -s docs -- --docs-cmd html' -> 'make -C docs html'. With 'release' option, you can set the message with 'message=...' in posargs."""
    pkg_install_condaenv(
        session=session,
        name="docs",
        lock=lock,
        display_name=f"{PACKAGE_NAME}-docs",
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )

    _docs(
        session=session, cmd=docs_cmd, run=docs_run, version=version
    )  # pyright: ignore


@DEFAULT_SESSION_VENV
def docs_venv(
    session: nox.Session,
    docs_cmd: cmd_annotated(  # type: ignore
        choices=[
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
        ],
        flags=("--docs-cmd", "-d"),
    ) = (),
    docs_run: RUN_CLI = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
) -> None:
    """Runs make in docs directory. For example, 'nox -s docs -- --docs-cmd html' -> 'make -C docs html'. With 'release' option, you can set the message with 'message=...' in posargs."""
    pkg_install_venv(
        session=session,
        name="docs-venv",
        lock=lock,
        display_name=f"{PACKAGE_NAME}-docs-venv",
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
        extras="docs",
    )

    _docs(
        session=session, cmd=docs_cmd, run=docs_run, version=version
    )  # pyright: ignore


# ** Dist pypi
def _dist_pypi(
    session: nox.Session, run: list[list[str]], cmd: list[str], version: str
) -> None:
    if version:
        session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = version
    session_run_commands(session, run)
    if not run and not cmd:
        cmd = ["build"]
    if cmd:
        if "build" in cmd:
            cmd.append("clean")
        cmd = sort_like(cmd, ["clean", "build", "testrelease", "release"])

        session.log(f"cmd={cmd}")

        for command in cmd:
            if command == "clean":
                session.run("rm", "-rf", "dist", external=True)
            elif command == "build":
                session.run("python", "-m", "build", "--outdir", "dist/")

            elif command == "testrelease":
                session.run("twine", "upload", "--repository", "testpypi", "dist/*")

            elif command == "release":
                session.run("twine", "upload", "dist/*")


@DEFAULT_SESSION_VENV
def dist_pypi(
    session: nox.Session,
    dist_pypi_run: RUN_CLI = [],  # noqa
    dist_pypi_cmd: cmd_annotated(  # type: ignore
        choices=["clean", "build", "testrelease", "release"],
        flags=("--dist-pypi-cmd", "-p"),
    ) = (),
    lock: LOCK_CLI = False,  # pyright: ignore
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
) -> None:
    """Run 'nox -s dist-pypi -- {clean, build, testrelease, release}'."""

    pkg_install_venv(
        session=session,
        name="dist-pypi",
        requirement_paths=[session_environment_filename(name="dist-pypi.txt")],
        force_reinstall=force_reinstall,
        install_package=False,
        log_session=log_session,
    )

    _dist_pypi(
        session=session,
        run=dist_pypi_run,
        cmd=dist_pypi_cmd,  # pyright: ignore
        version=version,
    )


@DEFAULT_SESSION
def dist_pypi_condaenv(
    session: nox.Session,
    dist_pypi_run: RUN_CLI = [],  # noqa
    dist_pypi_cmd: cmd_annotated(  # type: ignore
        choices=["clean", "build", "testrelease", "release"],
        flags=("--dist-pypi-cmd", "-p"),
    ) = (),
    lock: LOCK_CLI = False,  # pyright: ignore
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
) -> None:
    """Run 'nox -s dist_pypi -- {clean, build, testrelease, release}'."""
    # conda

    pkg_install_condaenv(
        session=session,
        name="dist-pypi",
        install_package=False,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )

    _dist_pypi(
        session=session,
        run=dist_pypi_run,
        cmd=dist_pypi_cmd,  # pyright: ignore
        version=version,
    )


# ** Dist conda
@DEFAULT_SESSION
def dist_conda(
    session: nox.Session,
    dist_conda_run: RUN_CLI = [],  # noqa
    dist_conda_cmd: cmd_annotated(  # type: ignore
        choices=[
            "recipe",
            "build",
            "clean",
            "clean-recipe",
            "clean-build",
            "recipe-cat-full",
        ],
        flags=("--dist-conda-cmd", "-c"),
    ) = (),
    # lock: LOCK_CLI = False,
    sdist_path: str = "",
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
    version: VERSION_CLI = "",
) -> None:
    """Runs make -C dist-conda posargs."""
    pkg_install_condaenv(
        session=session,
        name="dist-conda",
        install_package=False,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )

    run, cmd = dist_conda_run, dist_conda_cmd
    session_run_commands(session, run)
    if not run and not cmd:
        cmd = ["recipe"]

    if cmd:
        if "recipe" in cmd:
            cmd.append("clean-recipe")
        if "build" in cmd:
            cmd.append("clean-build")
        if "clean" in cmd:
            cmd.extend(["clean-recipe", "clean-build"])
            cmd.remove("clean")

        cmd = sort_like(
            cmd, ["recipe-cat-full", "clean-recipe", "recipe", "clean-build", "build"]
        )

        if not sdist_path:
            sdist_path = PACKAGE_NAME
            if version:
                sdist_path = f"{sdist_path}=={version}"

        for command in cmd:
            if command == "clean-recipe":
                session.run("rm", "-rf", f"dist-conda/{PACKAGE_NAME}", external=True)
            elif command == "clean-build":
                session.run("rm", "-rf", "dist-conda/build", external=True)
            elif command == "recipe":
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
                session.run(
                    "cat", f"dist-conda/{PACKAGE_NAME}/meta.yaml", external=True
                )
            elif command == "recipe-cat-full":
                import tempfile

                with tempfile.TemporaryDirectory() as d:
                    session.run(
                        "grayskull",
                        "pypi",
                        sdist_path,
                        "-o",
                        d,
                    )
                    session.run(
                        "cat", str(Path(d) / PACKAGE_NAME / "meta.yaml"), external=True
                    )

            elif command == "build":
                session.run(
                    "conda",
                    "mambabuild",
                    "--output-folder=dist-conda/build",
                    "--no-anaconda-upload",
                    "dist-conda",
                )


def _append_recipe(recipe_path: str, append_path: str) -> None:
    with open(recipe_path) as f:
        recipe = f.readlines()

    with open(append_path) as f:
        append = f.readlines()

    with open(recipe_path, "w") as f:
        f.writelines(recipe + ["\n"] + append)


# ** type checking
def _typing(
    session: nox.Session,
    run: list[list[str]],
    cmd: list[str],
    run_internal: list[list[str]],
) -> None:
    session_run_commands(session, run)
    if not run and not run_internal and not cmd:
        cmd = ["mypy", "pyright"]

    if "all" in cmd:
        cmd = ["mypy", "pyright", "pytype"]

    # set the cache directory for mypy
    session.env["MYPY_CACHE_DIR"] = str(Path(session.create_tmp()) / ".mypy_cache")

    def _run_info(cmd: str) -> None:
        session.run("which", cmd, external=True)
        session.run(cmd, "--version", external=True)

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
    session_run_commands(session, run_internal, external=False)


@ALL_SESSION
def typing(
    session: nox.Session,
    typing_cmd: cmd_annotated(  # type: ignore
        choices=[
            "mypy",
            "pyright",
            "pytype",
            "all",
            "nbqa-mypy",
            "nbqa-pyright",
            "nbqa-typing",
        ],
        flags=("--typing-cmd", "-m"),
    ) = (),
    typing_run: RUN_CLI = [],  # noqa
    typing_run_internal: run_annotated(  # type: ignore
        help="run arbitrary (internal) commands.  For example, --typing-run-internal 'mypy --some-option'",
    ) = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
) -> None:
    """Run type checkers (mypy, pyright, pytype)."""

    pkg_install_condaenv(
        session=session,
        name="typing",
        lock=lock,
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )

    _typing(
        session=session,
        run=typing_run,
        cmd=typing_cmd,
        run_internal=typing_run_internal,
    )


@ALL_SESSION_VENV
def typing_venv(
    session: nox.Session,
    typing_cmd: cmd_annotated(  # type: ignore
        choices=[
            "mypy",
            "pyright",
            "pytype",
            "all",
            "nbqa-mypy",
            "nbqa-pyright",
            "nbqa-typing",
        ],
        flags=("--typing-cmd", "-m"),
    ) = (),
    typing_run: RUN_CLI = [],  # noqa
    typing_run_internal: run_annotated(  # type: ignore
        help="run arbitrary (internal) commands.  For example, --typing-run-internal 'mypy --some-option'",
    ) = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
) -> None:
    """Run type checkers (mypy, pyright, pytype)."""

    pkg_install_venv(
        session=session,
        name="typing",
        lock=lock,
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
        extras="typing",
    )

    _typing(
        session=session,
        run=typing_run,
        cmd=typing_cmd,
        run_internal=typing_run_internal,
    )


# ** testdist conda
@ALL_SESSION
def testdist_conda(
    session: Session,
    test_no_pytest: bool = False,
    test_opts: TEST_OPTS_CLI = (),  # type: ignore
    testdist_conda_run: RUN_CLI = [],  # noqa
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
) -> None:
    """Test conda distribution."""

    install_str = PACKAGE_NAME
    if version:
        install_str = f"{install_str}=={version}"

    pkg_install_condaenv(
        session=session,
        name="test-extras",
        deps=[install_str],
        channels=["conda-forge"],
        force_reinstall=force_reinstall,
        install_package=False,
        log_session=log_session,
    )

    # assert isinstance(session.python, str)
    # session_install_envs(
    #     session,
    #     session_environment_filename(
    #         python_version=session.python, name="test-extras.yaml"
    #     ),
    #     deps=[install_str],
    #     channels=["conda-forge"],
    #     force_reinstall=force_reinstall,
    #     install_package=False,
    # )

    if not test_no_pytest:
        opts = combine_list_str(test_opts)
        session.run("pytest", *opts)


# ** testdist pypi
@ALL_SESSION_VENV
def testdist_pypi(
    session: Session,
    test_no_pytest: bool = False,
    test_opts: TEST_OPTS_CLI = (),  # type: ignore
    testdist_pypi_run: RUN_CLI = [],  # noqa
    testdist_pypi_extras: cmd_annotated(help="extras to install") = (),  # type: ignore
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
) -> None:
    """Test pypi distribution."""
    extras = testdist_pypi_extras
    install_str = PACKAGE_NAME

    if extras:
        install_str = "{}[{}]".format(install_str, ",".join(extras))

    if version:
        install_str = f"{install_str}=={version}"

    pkg_install_venv(
        session=session,
        name="testdist-pypi",
        requirement_paths=[session_environment_filename(name="test-extras.txt")],
        reqs=[install_str],
        force_reinstall=force_reinstall,
        install_package=False,
        log_session=log_session,
    )

    _test(
        session=session,
        run=testdist_pypi_run,
        test_no_pytest=test_no_pytest,
        test_opts=test_opts,
        no_cov=True,
    )


@ALL_SESSION
def testdist_pypi_condaenv(
    session: Session,
    test_no_pytest: bool = False,
    test_opts: TEST_OPTS_CLI = (),  # type: ignore
    testdist_pypi_run: RUN_CLI = [],  # noqa
    testdist_pypi_extras: cmd_annotated(help="extras to install") = (),  # type: ignore
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
) -> None:
    """Test pypi distribution."""
    extras = testdist_pypi_extras
    install_str = PACKAGE_NAME

    if extras:
        install_str = "{}[{}]".format(install_str, ",".join(extras))

    if version:
        install_str = f"{install_str}=={version}"

    pkg_install_condaenv(
        session=session,
        name="test-extras",
        reqs=[install_str],
        channels=["conda-forge"],
        force_reinstall=force_reinstall,
        install_package=False,
        log_session=log_session,
    )

    # assert isinstance(session.python, str)
    # session_install_envs(
    #     session,
    #     session_environment_filename(
    #         python_version=session.python, name="test-extras.yaml"
    #     ),
    #     reqs=[install_str],
    #     channels=["conda-forge"],
    #     force_reinstall=force_reinstall,
    #     install_package=False,
    # )
    # if log_session:
    #     session_log_session(session, False)

    _test(
        session=session,
        run=testdist_pypi_run,
        test_no_pytest=test_no_pytest,
        test_opts=test_opts,
        no_cov=True,
    )


# * Utilities --------------------------------------------------------------------------
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


# # If want separate env for updating/reporting version with setuptools-scm
# # We do this from dev environment.
# # ** version report/update
# @DEFAULT_SESSION_VENV
# def version_scm(
#     session: Session,
#     version: VERSION_CLI = "",
#     force_reinstall: FORCE_REINSTALL_CLI = False,
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
#         force_reinstall=force_reinstall,
#         no_deps=True,
#     )

#     if version:
#         session.env["SETUPTOOLS_SCM_PRETEND_VERSION"] = version

#     session.run("python", "-m", "setuptools_scm")
