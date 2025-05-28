# * Variables ------------------------------------------------------------------

PACKAGE_NAME := "pyproject2conda"
IMPORT_NAME := "pyproject2conda"
NOTEBOOKS := "examples/usage"
UVX := "uvx"
UVX_OPTS := "--constraints=requirements/lock/uvx-tools.txt"
UVX_WITH_OPTS := UVX + " " + UVX_OPTS
UVRUN := "uv run --frozen"
TYPECHECK := UVRUN + " --no-config tools/typecheck.py -v"
NOX := UVX + " --from 'nox>=2025.5.1' nox"

# For pre-commit, just use a minimum version...

PRE_COMMIT := UVX + " --constraints=requirements/uvx-tools.txt --with=pre-commit-uv pre-commit"
PYTHON_PATH := which("python")
PYLINT_OPTS := "--enable-all-extensions"

set unstable := true

# * Defaults
default:
    @just --list

# * Clean ----------------------------------------------------------------------

_find_and_clean first *other:
    find ./src \( -name {{ quote(first) }} {{ prepend("-o -name '", append("'", other)) }} \) -print -exec  rm -fr {} +

_clean *dirs:
    rm -fr {{ dirs }}

[group("clean")]
clean: clean-build clean-test clean-cache

[group("clean")]
clean-all: clean clean-pyc clean-venvs clean-docs

# remove build artifacts
[group("clean")]
[group("dist")]
clean-build: (_clean "build/" "docs/_build/" "dist/" "dist-conda/")

# remove Python file artifact
[group("clean")]
clean-pyc: (_find_and_clean "*.pyc" "*.pyo" "*~" "*.nbi" "*.nbc" "__pycache__") (_clean ".numba_cache/*")

# remove all .*_cache directories
[group("clean")]
clean-cache: (_clean ".*_cache")

# remove test and coverage artifacts
[group("clean")]
[group("test")]
clean-test: (_clean ".coverage" "htmlcov" ".pytest_cache")

[group("clean")]
[group("docs")]
clean-docs: (_clean "docs/_build/*" "docs/generated/*" "docs/reference/generated/*")

# remove all .nox/.venv files
[group("clean")]
clean-venvs: (_clean ".nox" ".venv")

# * Pre-commit -----------------------------------------------------------------

# run pre-commit on all files
[group("lint")]
lint command="":
    {{ PRE_COMMIT }} run --all-files {{ command }}

# run pre-commit using manual stage
[group("lint")]
lint-manual command="":
    {{ PRE_COMMIT }} run --all-files --hook-stage=manual {{ command }}

alias lint-all := lint-manual

# run codespell. Note that this imports allowed words from docs/spelling_wordlist.txt
[group("lint")]
codespell: (lint "codespell") (lint "nbqa-codespell")

# run typos.
[group("lint")]
typos: (lint-manual "typos") (lint-manual "nbqa-typos")

# run prettier
[group("lint")]
prettier: (lint "pyproject-fmt") (lint-manual "prettier") (lint-manual "markdownlint")

# run pyproject validators
[group("lint")]
validate-pyproject: (lint-manual "validate-pyproject-full") (lint-manual "sp-repo-review")

[group("lint")]
ruff-check: (lint "ruff-check")

[group("lint")]
ruff-format: (lint "ruff-format")

[group("lint")]
ruff: (lint "ruff")

alias ruff-all := ruff

[group("lint")]
checkmake: (lint-manual "checkmake")

[group("lint")]
just-fmt: (lint-manual "just-fmt")

# * User setup -----------------------------------------------------------------

# Create .autoenv.zsh files
user-all:
    echo source ./.venv/bin/activate > .autoenv.zsh
    echo deactivate > .autoenv_leave.zsh

# * Testing --------------------------------------------------------------------

# run tests quickly with the default Python
[group("test")]
test *options="":
    {{ UVRUN }} pytest {{ options }}

# test across versions
[group("test")]
test-all *options="":
    {{ NOX }} -s test-all -- ++test-options {{ options }}

# run tests and accept doctest results. (using pytest-accept)
[group("test")]
test-accept *options="":
    DOCFILLER_SUB=False {{ UVRUN }} pytest -v --accept {{ options }}

# * Versioning -----------------------------------------------------------------

# check/update version of package from scm
[group("version")]
version-scm:
    {{ NOX }} -s build -- ++build version

# check version from python import
[group("version")]
version-import:
    -{{ UVRUN }} python -c 'import {{ IMPORT_NAME }}; print({{ IMPORT_NAME }}.__version__)'

[group("version")]
version: version-scm version-import

# * Requirements/Environment files ---------------------------------------------

# Rebuild all requirements files
[group("requirements")]
requirements *options:
    {{ NOX }} -s requirements -- {{ options }}

# Update all requirement files
[group("requirements")]
requirements-update: (requirements "+L +U")

# * Typing ---------------------------------------------------------------------
_typecheck checker *options:
    {{ TYPECHECK }} {{ UVX_OPTS }} -x {{ checker }} -- {{ options }}

# Run mypy (with optional args)
[group("typecheck")]
mypy *options: (_typecheck "mypy" options)

# Run pyright (with optional args)
[group("typecheck")]
pyright *options: (_typecheck "pyright" options)

# Run pyright (with watch and optional args)
[group("typecheck")]
pyright-watch *options: (pyright "-w" options)

# Run pylint (with optional args)
[group("lint")]
[group("typecheck")]
pylint *options="src tests":
    {{ UVRUN }} pylint {{ PYLINT_OPTS }} {{ options }}

# Run all checkers (with optional directories)
[group("typecheck")]
typecheck *options: (mypy options) (pyright options) (pylint options "src" "tests")

[group("tools")]
[group("typecheck")]
typecheck-tools *files="noxfile.py tools/*.py": (mypy "--strict" files) (pyright files) (pylint files)

# * NOX ------------------------------------------------------------------------
# ** docs

# build docs.  Optioons {html, spelling, livehtml, linkcheck, open}.
[group("docs")]
docs *options="html":
    {{ NOX }} -s docs -- +d {{ options }}

[group("docs")]
docs-html: (docs "html")

[group("docs")]
docs-clean-build: clean-docs docs

# create a release
[group("docs")]
docs-release message="update docs" branch="nist-pages":
    {{ UVX_WITH_OPTS }} ghp-import -o -n -m "{{ message }}" -b {{ branch }} docs/_build/html

[group("docs")]
docs-open: (docs "open")

[group("docs")]
docs-spelling: (docs "spelling")

[group("docs")]
docs-livehtml: (docs "livehtml")

[group("docs")]
docs-linkcheck: (docs "linkcheck")

# ** type check

# typecheck across versions with nox
[group("typecheck")]
typecheck-all *options="mypy pyright pylint":
    {{ NOX }} -s typecheck -- +m {{ options }}

[group("typecheck")]
mypy-all: (typecheck-all "mypy")

[group("typecheck")]
pyright-all: (typecheck-all "pyright")

[group("typecheck")]
pylint-all: (typecheck-all "pylint")

# * dist ----------------------------------------------------------------------

[group("dist")]
build *options:
    {{ NOX }} -s build -- {{ options }}

[group("dist")]
publish:
    {{ NOX }} -s publish -- +p release

[group("dist")]
publish-test:
    {{ NOX }} -s publish -- +p test

_uv-publish *options:
    uv publish --username __token__ --keyring-provider subprocess {{ options }}

_open_page site:
    uv run --no-project python -c "import webbrowser; webbrowser.open('https://{{ site }}/project/{{ PACKAGE_NAME }}')"

# uv release
[group("dist")]
uv-publish: _uv-publish && (_open_page "pypi.org")

# uv test release on testpypi
[group("dist")]
uv-publish-test: (_uv-publish "--publish-url https://test.pypi.org/legacy/") && (_open_page "test.pypi.org")

# run twine check on dist
[group("dist")]
[group("lint")]
lint-dist:
    {{ NOX }} -s publish -- +p check
    {{ UVX_WITH_OPTS }} check-wheel-contents dist/*.whl

[group("dist")]
list-dist:
    tar -tzvf dist/*.tar.gz
    unzip -vl dist/*.whl
    du -skhc dist/*

# * NOTEBOOK -------------------------------------------------------------------
_nbqa_typecheck checker *files:
    {{ UVX_WITH_OPTS }} nbqa --nbqa-shell "{{ PYTHON_PATH }} tools/typecheck.py -v {{ UVX_OPTS }} -x {{ checker }}" {{ files }}

[group("notebook")]
[group("typecheck")]
mypy-notebook *files=NOTEBOOKS: (_nbqa_typecheck "mypy" files)

[group("notebook")]
[group("typecheck")]
pyright-notebook *files=NOTEBOOKS: (_nbqa_typecheck "pyright" files)

[group("lint")]
[group("notebook")]
[group("typecheck")]
pylint-notebook *files=NOTEBOOKS:
    {{ UVX_WITH_OPTS }} nbqa --nbqa-shell "{{ PYTHON_PATH }} -m pylint {{ PYLINT_OPTS }}" {{ files }}

[group("notebook")]
[group("typecheck")]
typecheck-notebook *files=NOTEBOOKS: (mypy-notebook files) (pyright-notebook files) (pylint-notebook files)

[group("notebook")]
[group("test")]
test-notebook *files=NOTEBOOKS:
    {{ UVRUN }} pytest --nbval --nbval-current-env --nbval-sanitize-with=config/nbval.ini --dist loadscope -x {{ files }}

[group("notebook")]
install-ipykernel:
    {{ NOX }} -s install-ipykernel

# * Other tools ----------------------------------------------------------------

auto-changelog:
    {{ UVX_WITH_OPTS }} auto-changelog -u -r usnistgov -v unreleased --tag-prefix v --stdout --template changelog.d/templates/auto-changelog/template.jinja2

commitizen-changelog:
    {{ UVX_WITH_OPTS }} --from=commitizen cz changelog --unreleased-version unreleased --dry-run --incremental

# tuna analyze load time:
tuna-import:
    {{ UVRUN }} python -X importtime -c 'import {{ IMPORT_NAME }}' 2> tuna-loadtime.log
    {{ UVX_WITH_OPTS }} tuna tuna-loadtime.log
    rm tuna-loadtime.log

# apply cog to README.md
cog-readme:
    {{ NOX }} -s cog
    {{ PRE_COMMIT }} run markdownlint --files README.md

# create README.pdf
readme-pdf:
    pandoc -V colorlinks -V geometry:margin=0.8in README.md -o README.pdf
