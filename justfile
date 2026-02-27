#!/usr/bin/env -S just --justfile

import "tools/shared.just"
import? "tools/notebook.just"

set unstable := true
set shell := ["bash", "-c"]

# * Defaults
_default:
    @just --list --unsorted

# * Clean ----------------------------------------------------------------------

# find and remove files from `path` with `name`
find_and_clean path name *other_names:
    find {{ path }} \
    -not -path "./.nox/*" \
    -not -path "./.venv/*" \
    \( -name {{ quote(name) }} {{ prepend("-o -name '", append("'", other_names)) }} \) \
    -print -exec  rm -fr {} +

_clean *dirs:
    rm -fr {{ dirs }}

# clean .nox, build, docs, test, backups, cache
[group("clean")]
clean: (_clean ".nox") clean-build clean-docs clean-test clean-cache clean-backups

# clean plus artifacts (keep .venv)
[group("clean")]
clean-all: clean clean-artifacts

# clean build artifacts
[group("clean")]
[group("dist")]
clean-build: (_clean "build/" "dist/" "dist-conda/")

# clean docs artifacts
[group("clean")]
[group("docs")]
clean-docs: (_clean "docs/_build" "README.pdf") (find_and_clean "docs" "generated")

# clean test and coverage artifacts
[group("clean")]
[group("test")]
clean-test: (_clean ".coverage" "htmlcov")

# clean cache files
[group("clean")]
clean-cache: (_clean ".dmypy.json" ".pytype" "tuna-loadtime.log" ".nox/*/tmp" ".nox/.cache") (find_and_clean "." ".*cache")

# clean backup/checkpoint files
[group("clean")]
clean-backups: (find_and_clean "." ".ipynb_checkpoints" "*~")

# clean python artifacts
[group("clean")]
clean-artifacts: (_clean ".numba_cache/*") (find_and_clean "." "__pycache__") (find_and_clean "." "*.pyd" "*.pyc" "*.pyo" "*.nbi" "*.nbc")

# clean ignored/untracked files. Defaults to dry run.  Pass `-i` for interactive or `-f` for force remove.  Pass `-e ".venv"` to keep .venv.
[group("clean")]
sterilize +options="-n":
    git clean -x -d {{ options }}

# * Pre-commit -----------------------------------------------------------------

# run pre-commit on all files
[group("lint")]
lint *commands: (pre-commit "run --all-files" commands)

# run pre-commit using manual stage on all files
[group("lint")]
lint-manual *commands: (pre-commit "run --all-files --hook-stage=manual" commands)

alias lint-all := lint-manual

# run prettier/markdownlint/pypoject-fmt
[group("lint")]
prettier: (lint "pyproject-fmt") (lint-manual "markdownlint")

[group("lint")]
ruff: (lint "ruff")

[group("lint")]
cog: (lint-manual "cog" "--verbose")

# update all supported additional dependencies
[group("lint")]
lint-upgrade:
    just pre-commit autoupdate
    uv run --no-project --script tools/requirements_lock.py --upgrade requirements/pre-commit-additional-dependencies.txt
    just pre-commit run -v sync-pre-commit-deps -a

# * User setup -----------------------------------------------------------------

# Create .autoenv.zsh files
user-all:
    echo source ./.venv/bin/activate > .autoenv.zsh
    echo deactivate > .autoenv_leave.zsh

# * Testing --------------------------------------------------------------------

# run tests quickly with the default Python
[group("test")]
test *options:
    {{ UVRUN }} --group="test" --no-dev pytest {{ options }}

# test across versions
[group("nox")]
[group("test")]
test-all *options: (nox "-s test-all -- ++test-options" options)

# run tests and accept doctest results. (using pytest-accept)
[group("test")]
test-accept *options:
    DOCFILLER_SUB=False {{ UVRUN }} --group="test" --group="pytest-accept" --no-dev \
    pytest -v --accept {{ options }}

# coverage report
[group("test")]
coverage *options: (nox "-s coverage -- ++coverage" options)

# * Versioning -----------------------------------------------------------------

# check/update version of package from scm
[group("version")]
version-scm:
    {{ UVX_WITH_OPTS }} hatchling version

# check version from python import
[group("version")]
version-import:
    {{ UVRUN }} --no-dev python -c 'import {{ IMPORT_NAME }}; print({{ IMPORT_NAME }}.__version__)' || true

[group("version")]
version: version-scm version-import

# * Requirements/Environment files ---------------------------------------------

_requirements *options:
    just pre-commit run pyproject2conda-project --all-files --verbose || true
    uv run --no-project tools/requirements_lock.py --all-files {{ options }}

# Rebuild requirements, lock requirements, and run uv sync.  Pass --upgrade/-U to upgrade
[group("requirements")]
sync *options: (_requirements "--sync" options)

# Rebuild requirements, lock requirements, and run uv lock.  Pass --upgrade/-U to upgrade
[group("requirements")]
lock *options: (_requirements "--lock" options)

# Rebuild requirements, lock requirements, and run uv sync if .venv exists or uv lock if not.  Pass --upgrade/-U to upgrade
[group("requirements")]
requirements *options: (_requirements "--sync-or-lock" options)

# * Typecheck ---------------------------------------------------------------------

TYPECHECK_UVRUN_OPTS := "--only-group=type"

_typecheck *check_options:
    {{ UVRUN }} {{ TYPECHECK_UVRUN_OPTS }} {{ TYPECHECK }} {{ UVX_OPTS }} {{ check_options }}

# Run mypy (with optional args)
[group("typecheck")]
mypy *options: (_typecheck "-cmypy[faster-cache]" options)

# Run pyright (with optional args)
[group("typecheck")]
pyright *options: (_typecheck "-cpyright" options)

# Run pyright (with watch and optional args)
[group("typecheck")]
pyright-watch *options: (_typecheck "-c'pyright -w'" options)

# Run basedpyright (with optional args)
[group("typecheck")]
basedpyright *options: (_typecheck "-cbasedpyright" options)

# Run basedpyright (with watch and optional args)
[group("typecheck")]
basedpyright-watch *options: (_typecheck "-c'basedpyright -w'" options)

# Run basedpyright (with --verifytypes <package>)
[group("typecheck")]
basedpyright-verifytypes:
    {{ UVRUN }} --group=basedpyright --no-dev basedpyright --verifytypes {{ IMPORT_NAME }}

# Run ty (NOTE: in alpha)
[group("typecheck")]
ty *options: (_typecheck "-cty" options)

# Run pyrefly (Note: in alpha)
[group("typecheck")]
pyrefly *options: (_typecheck "-cpyrefly" options)

# Run pylint (with optional args)
[group("lint")]
[group("typecheck")]
pylint *options="src tests":
    {{ UVRUN }} {{ TYPECHECK_UVRUN_OPTS }} pylint {{ PYLINT_OPTS }} {{ options }}

# Run all checkers (with optional directories)
[group("typecheck")]
typecheck *options: (_typecheck "-cmypy[faster-cache] -cbasedpyright -cpyrefly -cty" options)

# Run checkers on tools
[group("tools")]
[group("typecheck")]
@typecheck-tools *files="noxfile.py tools/*.py":
    -just TYPECHECK_UVRUN_OPTS="--only-group=nox --only-group=typecheck-runner" mypy -- --strict {{ files }}
    just TYPECHECK_UVRUN_OPTS="--only-group=nox --only-group=typecheck-runner" basedpyright -- {{ files }}
    just TYPECHECK_UVRUN_OPTS="--only-group=nox --only-group=pylint" pylint {{ files }}

# ** typecheck all

# typecheck across versions with nox (options are mypy, pyright, basedpyright, pylint, ty, pyrefly)
[group("nox")]
[group("typecheck")]
typecheck-all *checkers="mypy basedpyright": (nox "-s typecheck -- +m" checkers)

# * docs -----------------------------------------------------------------------

# build docs.  Optioons {html, spelling, livehtml, linkcheck, open}.
[group("docs")]
[group("nox")]
docs *options="html": (nox "-s docs -- +d" options)

[group("docs")]
docs-version version="": (docs "html" prepend("++version=", version))

[group("docs")]
docs-html: (docs "html")

[group("docs")]
docs-clean-build: clean-docs docs

# create a release
[group("dist")]
[group("docs")]
docs-release message="update docs" branch="nist-pages":
    {{ UVX_WITH_OPTS }} ghp-import -o -n -m "{{ message }}" -b {{ branch }} docs/_build/html

[group("docs")]
docs-open: (docs "open")

[group("docs")]
docs-livehtml: (docs "livehtml")

# * dist ----------------------------------------------------------------------

[group("dist")]
build:
    -rm -f dist/*
    uv build

_twine *options:
    {{ UVX_WITH_OPTS }} twine {{ options }}

[group("dist")]
publish: (_twine "upload dist/*")

[group("dist")]
publish-test: (_twine "upload --repository testpypi dist/*")

_uv-publish *options:
    uv publish --username __token__ --keyring-provider subprocess {{ options }}

_open_page site:
    uv run --no-project python -c "import webbrowser; webbrowser.open('https://{{ site }}/project/{{ PACKAGE_NAME }}')"

# uv publish
[group("dist")]
uv-publish: _uv-publish && (_open_page "pypi.org")

# uv publish to testpypi
[group("dist")]
uv-publish-test: (_uv-publish "--publish-url https://test.pypi.org/legacy/") && (_open_page "test.pypi.org")

# lint distribution
[group("dist")]
[group("lint")]
lint-dist: (_twine "check --strict dist/*")
    {{ UVX_WITH_OPTS }} check-wheel-contents dist/*.whl

# check the dist versions are correct
[group("dist")]
[group("lint")]
check-dist-version version:
    uv run --script tools/check_dist_version.py --version {{ version }} dist/*.whl dist/*.tar.gz

[group("dist")]
list-dist:
    tar -tzvf dist/*.tar.gz
    unzip -vl dist/*.whl
    du -skhc dist/*

# * GitHub cli -----------------------------------------------------------------

# sync labels with template
[group("tools")]
gh-label-sync:
    gh label clone usnistgov/cookiecutter-nist-python

# * Other tools ----------------------------------------------------------------

# Run ipython with ephemeral current environment
[group("tools")]
ipython *options:
    {{ UVRUN }} --group=ipython ipython {{ options }}

# update templates
[group("tools")]
copier-update *options="":
    {{ UVX_WITH_OPTS }} --with copier-template-extensions \
    copier update --trust -A \
    -r main \
    {{ options }}

# create changelog snippet with scriv
[group("tools")]
scriv-create *options="--add --edit":
    {{ UVX_WITH_OPTS }} scriv create {{ options }}

[group("tools")]
scriv-collect version *options="--keep":
    {{ UVX_WITH_OPTS }} scriv collect --version {{ version }} {{ options }}
    uv run --no-project tools/remove_changelog_html_tag.py CHANGELOG.md
    git add CHANGELOG.md

[group("tools")]
auto-changelog:
    {{ UVX_WITH_OPTS }} \
    auto-changelog \
    -u \
    -r usnistgov \
    -v unreleased \
    --tag-prefix v \
    --stdout \
    --template changelog.d/templates/auto-changelog/template.jinja2

[group("tools")]
commitizen-changelog:
    {{ UVX_WITH_OPTS }} --from=commitizen \
    cz changelog \
    --unreleased-version unreleased \
    --dry-run \
    --incremental

# tuna analyze load time:
[group("tools")]
tuna-import:
    {{ UVRUN }} --no-dev python -X importtime -c 'import {{ IMPORT_NAME }}' 2> tuna-loadtime.log
    {{ UVX_WITH_OPTS }} tuna tuna-loadtime.log
    rm tuna-loadtime.log

# create README.pdf
[group("tools")]
readme-pdf:
    pandoc -V colorlinks -V geometry:margin=0.8in README.md -o README.pdf
