"""Config file for nox"""
from __future__ import annotations

import shutil
from dataclasses import replace  # noqa
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Any, Callable, Collection, TypeVar, cast

import nox
from noxopt import NoxOpt, Option, Session

from tools.noxtools import (
    combine_list_str,
    load_nox_config,
    open_webpage,
    prepend_flag,
    session_install_envs,
    session_install_envs_lock,
    # session_install_package,
    session_install_pip,
    session_run_commands,
    sort_like,
    update_target,
)

# * nox options ------------------------------------------------------------------------
ROOT = Path(__file__).parent

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["test"]

# * Options ----------------------------------------------------------------------------

PACKAGE_NAME = "pyproject2conda"
IMPORT_NAME = "pyproject2conda"
KERNEL_BASE = "pyproject2conda"

PYTHON_ALL_VERSIONS = ["3.8", "3.9", "3.10", "3.11"]
PYTHON_DEFAULT_VERSION = "3.10"

# conda/mamba
if shutil.which("mamba"):
    CONDA_BACKEND = "mamba"
elif shutil.which("conda"):
    CONDA_BACKEND = "conda"
else:
    raise ValueError("neither conda or mamba found")

SESSION_DEFAULT_KWS = {"python": PYTHON_DEFAULT_VERSION, "venv_backend": CONDA_BACKEND}
SESSION_ALL_KWS = {"python": PYTHON_ALL_VERSIONS, "venv_backend": CONDA_BACKEND}


# * User config ------------------------------------------------------------------------

CONFIG = load_nox_config()

# * noxopt -----------------------------------------------------------------------------
group = NoxOpt(auto_tag=True)

F = TypeVar("F", bound=Callable[..., Any])
C = Callable[[F], F]

DEFAULT_SESSION = cast(C, group.session(**SESSION_DEFAULT_KWS))  # type: ignore
ALL_SESSION = cast(C, group.session(**SESSION_ALL_KWS))  # type: ignore

DEFAULT_SESSION_VENV = cast(C, group.session(python=PYTHON_DEFAULT_VERSION))  # type: ignore
ALL_SESSION_VENV = cast(C, group.session(python=PYTHON_ALL_VERSIONS))  # type: ignore

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


def opts_annotated(**kwargs):
    return Annotated[list[str], replace(OPTS_OPT, **kwargs)]


def cmd_annotated(**kwargs):
    return Annotated[list[str], replace(CMD_OPT, **kwargs)]


def run_annotated(**kwargs):
    return Annotated[list[list[str]], replace(RUN_OPT, **kwargs)]


LOCK_CLI = Annotated[bool, LOCK_OPT]
RUN_CLI = Annotated[list[list[str]], RUN_OPT]
TEST_OPTS_CLI = opts_annotated(help="extra arguments/flags to pytest")

# CMD_CLI = Annotated[list[str], CMD_OPT]

FORCE_REINSTALL_CLI = Annotated[
    bool,
    Option(type=bool, help="If True, force reinstall even if environment unchanged"),
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


# * Installation command ---------------------------------------------------------------
def pkg_install_condaenv(
    session: nox.Session,
    name: str,
    lock: bool = False,
    display_name: str | None = None,
    install_package: bool = True,
    force_reinstall: bool = False,
    log_session: bool = False,
    deps: Collection[str] | None = None,
    reqs: Collection[str] | None = None,
    channels: Collection[str] | None = None,
    **kwargs,
):
    """Install requirements.  If need fine control, do it in calling func"""

    if lock:
        py = session.python.replace(".", "")  # type: ignore
        session_install_envs_lock(
            session=session,
            lockfile=f"./environment/lock/py{py}-{name}-conda-lock.yml",
            display_name=display_name,
            force_reinstall=force_reinstall,
            install_package=install_package,
            **kwargs,
        )

    else:
        session_install_envs(
            session,
            f"./environment/{name}.yaml",
            display_name=display_name,
            force_reinstall=force_reinstall,
            deps=deps,
            reqs=reqs,
            channels=channels,
            install_package=install_package,
            **kwargs,
        )

    if log_session:
        session_log_session(session, install_package)


def pkg_install_venv(
    session: nox.Session,
    name: str,
    lock: bool = False,
    requirement_paths: Collection[str] | None = None,
    constraint_paths: Collection[str] | None = None,
    extras: str | Collection[str] | None = None,
    reqs: Collection[str] | None = None,
    display_name: str | None = None,
    force_reinstall: bool = False,
    install_package: bool = False,
    no_deps: bool = False,
    log_session: bool = False,
):
    if lock:
        raise ValueError("lock not yet supported for install_pip")

    else:
        session_install_pip(
            session=session,
            requirement_paths=requirement_paths,
            constraint_paths=constraint_paths,
            extras=extras,
            reqs=reqs,
            display_name=display_name,
            force_reinstall=force_reinstall,
            install_package=install_package,
            no_deps=no_deps,
        )

    if log_session:
        session_log_session(session, install_package)


def session_log_session(session, has_package=False):
    session.run("python", "--version")
    if has_package:
        session.run(
            "python",
            "-c",
            dedent(
                f"""
        import {IMPORT_NAME}
        print({IMPORT_NAME}.__version__)
        """
            ),
        )


# * Environments------------------------------------------------------------------------
# ** Development (conda)
@DEFAULT_SESSION
def dev(
    session: Session,
    dev_run: RUN_CLI = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
):
    """Create dev env"""
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
):
    """Create dev env"""
    # using conda

    pkg_install_venv(
        session=session,
        name="dev-venv",
        lock=lock,
        extras=["dev"],
        display_name=f"{PACKAGE_NAME}-dev-venv",
        install_package=True,
        force_reinstall=force_reinstall,
        log_session=log_session,
    )
    session_run_commands(session, dev_run)


# ** pyproject2conda (create environment.yaml and requirement.txt files)
@DEFAULT_SESSION_VENV
def pyproject2conda(
    session: Session,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    pyproject2conda_force: bool = False,
):
    """Create environment.yaml files from pyproject.toml using pyproject2conda."""
    pkg_install_venv(
        session=session,
        name="pyporject2conda",
        reqs=["."],
        force_reinstall=force_reinstall,
    )

    def create_env(output, extras=None, python="get", base=True, cmd="yaml"):
        def _to_args(flag, val):
            if val is None:
                return []
            if isinstance(val, str):
                val = [val]
            return prepend_flag(flag, val)

        if pyproject2conda_force or update_target(output, "pyproject.toml"):
            args = [cmd, "-o", output] + _to_args("-e", extras)

            if python and cmd == "yaml":
                args.extend(["--python-include", python])

            if not base:
                args.append("--no-base")

            session.run("pyproject2conda", *args)
        else:
            session.log(
                f"{output} up to data.  Pass --pyproject2conda-force to force recreation"
            )

    # create root environment
    create_env("environment/base.yaml")

    extras = CONFIG["environment-extras"]
    for k in ["test", "typing", "docs", "dev"]:
        create_env(f"environment/{k}.yaml", extras=extras.get(k, k), base=True)

    # isolated
    for k in ["dist-pypi", "dist-conda"]:
        create_env(f"environment/{k}.yaml", extras=k, base=False)
        if k == "dist-pypi":
            create_env(f"environment/{k}.txt", extras=k, base=False, cmd="requirements")

    # need an isolated set of test requirements
    create_env("environment/test-extras.yaml", extras="test", base=False)
    create_env(
        "environment/test-extras.txt", extras="test", base=False, cmd="requirements"
    )


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
):
    """Create lock files using conda-lock"""

    pkg_install_venv(
        session,
        name="conda-lock",
        reqs=["conda-lock>=2.0.0"],
        force_reinstall=force_reinstall,
    )

    session.run("conda-lock", "--version")

    platform = conda_lock_platform
    if not platform:
        platform = ["osx-64"]
    elif "all" in platform:
        platform = ["linux-64", "osx-64", "win-64"]
    channel = conda_lock_channel
    if not channel:
        channel = ["conda-forge"]

    lock_dir = ROOT / "environment" / "lock"

    def create_lock(
        py,
        name,
        env_path=None,
    ):
        py = "py" + py.replace(".", "")

        if env_path is None:
            env_path = f"environment/{name}.yaml"

        lockfile = lock_dir / f"{py}-{name}-conda-lock.yml"

        deps = [env_path]
        # make sure this is last to make python version last
        deps.append(lock_dir / f"{py}.yaml")

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
        conda_lock_cmd = ["all"]
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
def _test(session, run, test_no_pytest, test_opts, no_cov):
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
):
    """Test environments with conda installs"""

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
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
    no_cov: bool = False,
):
    """Test environments virtualenv and pip installs"""

    pkg_install_venv(
        session=session,
        name="test-pip",
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
def _coverage(session, run, cmd, run_internal):
    session_run_commands(session, run)

    if not cmd and not run and not run_internal:
        cmd = ["combine", "report"]

    session.log(f"{cmd}")

    for c in cmd:
        if c == "combine":
            paths = list(Path(".nox").glob("test*/tmp/.coverage"))
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
):
    pkg_install_venv(
        session,
        name="coverage",
        reqs=["coverage[toml]"],
        force_reinstall=force_reinstall,
    )

    _coverage(
        session=session,
        run=coverage_run,
        cmd=coverage_cmd,
        run_internal=coverage_run_internal,
    )


# ** Docs
def _docs(session, run, cmd, version):
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
):
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

    _docs(session=session, cmd=docs_cmd, run=docs_run, version=version)


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
):
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

    _docs(session=session, cmd=docs_cmd, run=docs_run, version=version)


# ** Dist pypi
def _dist_pypi(session, run, cmd, version):
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
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
):
    """Run 'nox -s dist-pypi -- {clean, build, testrelease, release}'"""

    pkg_install_venv(
        session=session,
        name="dist-pypi",
        requirement_paths=["environment/dist-pypi.txt"],
        force_reinstall=force_reinstall,
        install_package=False,
    )

    _dist_pypi(
        session=session,
        run=dist_pypi_run,
        cmd=dist_pypi_cmd,
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
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    version: VERSION_CLI = "",
    log_session: bool = False,
):
    """Run 'nox -s dist_pypi -- {clean, build, testrelease, release}'"""
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
        cmd=dist_pypi_cmd,
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
):
    """Runs make -C dist-conda posargs"""
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
                    f"dist-conda/{PACKAGE_NAME}/meta.yaml", ".recipe-append.yaml"
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


def _append_recipe(recipe_path, append_path):
    with open(recipe_path) as f:
        recipe = f.readlines()

    with open(append_path) as f:
        append = f.readlines()

    with open(recipe_path, "w") as f:
        f.writelines(recipe + ["\n"] + append)


# type checking
def _typing(session, run, cmd, run_internal):
    session_run_commands(session, run)
    if not run and not run_internal and not cmd:
        cmd = ["mypy"]
    for c in cmd:
        if c == "mypy":
            session.run("mypy", "--color-output")
        elif c == "pyright":
            session.run("pyright", external=True)
        elif c == "pytype":
            session.run("pytype")
    session_run_commands(session, run_internal, external=False)


@ALL_SESSION
def typing(
    session: nox.Session,
    typing_cmd: cmd_annotated(  # type: ignore
        choices=["mypy", "pyright", "pytype"],
        flags=("--typing-cmd", "-m"),
    ) = (),
    typing_run: RUN_CLI = [],  # noqa
    typing_run_internal: run_annotated(  # type: ignore
        help="run arbitrary (internal) commands.  For example, --typing-run-internal 'mypy --some-option'",
    ) = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
):
    """Run type checkers (mypy, pyright, pytype)"""

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
        choices=["mypy", "pyright", "pytype"],
        flags=("--typing-cmd", "-m"),
    ) = (),
    typing_run: RUN_CLI = [],  # noqa
    typing_run_internal: run_annotated(  # type: ignore
        help="run arbitrary (internal) commands.  For example, --typing-run-internal 'mypy --some-option'",
    ) = [],  # noqa
    lock: LOCK_CLI = False,
    force_reinstall: FORCE_REINSTALL_CLI = False,
    log_session: bool = False,
):
    """Run type checkers (mypy, pyright, pytype)"""

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
):
    """Test conda distribution"""

    install_str = PACKAGE_NAME
    if version:
        install_str = f"{install_str}=={version}"

    session_install_envs(
        session,
        "environment/test-extras.yaml",
        deps=[install_str],
        channels=["conda-forge"],
        force_reinstall=force_reinstall,
        install_package=False,
    )

    if log_session:
        session_log_session(session, False)

    session_run_commands(session, testdist_conda_run)

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
):
    """Test pypi distribution"""
    extras = testdist_pypi_extras
    install_str = PACKAGE_NAME

    if extras:
        install_str = "{}[{}]".format(install_str, ",".join(extras))

    if version:
        install_str = f"{install_str}=={version}"

    pkg_install_venv(
        session=session,
        name="testdist-pypi",
        requirement_paths=["environment/test-extras.txt"],
        reqs=[install_str],
        force_reinstall=force_reinstall,
        install_package=False,
    )

    if log_session:
        session_log_session(session, False)

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
):
    """Test pypi distribution"""
    extras = testdist_pypi_extras
    install_str = PACKAGE_NAME

    if extras:
        install_str = "{}[{}]".format(install_str, ",".join(extras))

    if version:
        install_str = f"{install_str}=={version}"

    session_install_envs(
        session,
        "environment/test-extras.yaml",
        reqs=[install_str],
        channels=["conda-forge"],
        force_reinstall=force_reinstall,
        install_package=False,
    )
    if log_session:
        session_log_session(session, False)

    _test(
        session=session,
        run=testdist_pypi_run,
        test_no_pytest=test_no_pytest,
        test_opts=test_opts,
        no_cov=True,
    )


# * Utilities --------------------------------------------------------------------------
def _create_doc_examples_symlinks(session, clean=True):
    """Create symlinks from docs/examples/*.md files to /examples/usage/..."""

    import os

    def usage_paths(path):
        with path.open("r") as f:
            for line in f:
                if line.startswith("usage/"):
                    yield Path(line.strip())

    def get_target_path(usage_path, prefix_dir="./examples", exts=(".md", ".ipynb")):
        path = Path(prefix_dir) / Path(usage_path)

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
