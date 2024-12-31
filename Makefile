# * Utilities -----------------------------------------------------------------
.PHONY: clean clean-test clean-pyc clean-build help
.DEFAULT_GOAL := help


_PY_DEFAULT = 311
UVXRUN = uv run --no-config --frozen tools/uvxrun.py
UVXRUN_OPTS = -r requirements/lock/py$(_PY_DEFAULT)-uvxrun-tools.txt -v
UVXRUN_NO_PROJECT = uv run --with "packaging" --no-project tools/uvxrun.py
NOX=uvx --from "nox>=2024.10.9" nox
PRE_COMMIT = uvx pre-commit

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_/.-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := uv run --no-config --frozen python -c "$$BROWSER_PYSCRIPT"

help:
	@uv run --frozen python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr docs/_build/
	rm -fr dist/
	rm -fr dist-conda/


clean-pyc: ## remove Python file artifacts
	find ./src -name '*.pyc' -exec rm -f {} +
	find ./src -name '*.pyo' -exec rm -f {} +
	find ./src -name '*~' -exec rm -f {} +
	find ./src -name '__pycache__' -exec rm -fr {} +

clean-nox: ## remove all nox artifacts
	rm -fr .nox

clean-test: ## remove test and coverage artifacts
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache


# * Pre-commit -----------------------------------------------------------------
.PHONY: pre-commit-init pre-commit pre-commit-all
pre-commit-init: ## install pre-commit
	$(PRE_COMMIT) install

pre-commit-all: ## run pre-commit on all files
	$(PRE_COMMIT) run --all-files

pre-commit-codespell: ## run codespell. Note that this imports allowed words from docs/spelling_wordlist.txt
	$(PRE_COMMIT) run --all-files codespell
	$(PRE_COMMIT) run --all-files nbqa-codespell

pre-commit-typos:  ## run typos.
	$(PRE_COMMIT) run --all-files --hook-stage manual typos
	$(PRE_COMMIT) run --all-files --hook-stage manual nbqa-typos

pre-commit-ruff-all: ## run ruff lint and format
	$(PRE_COMMIT) run ruff-all --all-files

pre-commit-checkmake:  ## run checkmake
	$(PRE_COMMIT) run --all-files --hook-stage manual checkmake


# * User setup -----------------------------------------------------------------
.PHONY: user-autoenv-zsh dev user-all
user-autoenv-zsh: ## create .autoenv.zsh files
	echo source ./.venv/bin/activate > .autoenv.zsh
	echo deactivate > .autoenv_leave.zsh

user-all: user-autoenv-zsh ## runs user scripts


# * Dev environment ------------------------------------------------------------
.PHONY: _dev
_dev:
	uv venv .venv
	uv pip sync -p .venv/bin/python requirements/lock/py$(_PY_DEFAULT)-dev.txt
	uv pip install -p .venv/bin/python -e .

dev: _dev install-kernel

# * Testing --------------------------------------------------------------------
.PHONY: test coverage
test: ## run tests quickly with the default Python
	uv run --frozen pytest -x -v

test-accept: ## run tests and accept doctest results. (using pytest-accept)
	DOCFILLER_SUB=False uv run --frozen pytest -v --accept


# * Versioning -----------------------------------------------------------------
.PHONY: version-scm version-import version

version-scm: ## check/update version of package from scm
	$(NOX) -s build -- ++build version

version-import: ## check version from python import
	-uv run --frozen python -c 'import pyproject2conda; print(pyproject2conda.__version__)'

version: version-scm version-import


# * Requirements/Environment files ---------------------------------------------
.PHONY: requirements
requirements: ## rebuild all requirements/environment files
	$(NOX) -s requirements


# * Typing ---------------------------------------------------------------------
.PHONY: mypy pyright
mypy: ## Run mypy
	$(UVXRUN) $(UVXRUN_OPTS) -c mypy
pyright: ## Run pyright
	$(UVXRUN) $(UVXRUN_OPTS) -c pyright
pyright-watch: ## Run pyright in watch mode
	$(UVXRUN) $(UVXRUN_OPTS) -c "pyright -w"
typecheck: ## Run mypy and pyright
	$(UVXRUN) $(UVXRUN_OPTS) -c mypy -c pyright

.PHONY: typecheck-tools
typecheck-tools:
	$(UVXRUN) $(UVXRUN_OPTS) -c "mypy --strict" -c pyright -- noxfile.py tools/*.py


# * NOX ------------------------------------------------------------------------
# ** docs
.PHONY: docs-build docs-clean docs-clean-build docs-release
docs-build: ## build docs in isolation
	$(NOX) -s docs -- +d build
docs-clean: ## clean docs
	rm -rf docs/_build/*
	rm -rf docs/generated/*
	rm -rf docs/reference/generated/*
docs-clean-build: docs-clean docs-build ## clean and build
docs-release: ## release docs.
	$(UVXRUN_NO_PROJECT) $(UVXRUN_OPTS) -c "ghp-import -o -n -m \"update docs\" -b nist-pages" docs/_build/html

.PHONY: docs-open docs-spelling docs-livehtml docs-linkcheck
docs-open: ## open the build
	$(NOX) -s docs -- +d open
docs-spelling: ## run spell check with sphinx
	$(NOX) -s docs -- +d spelling
docs-livehtml: ## use autobuild for docs
	$(NOX) -s docs -- +d livehtml
docs-linkcheck: ## check links
	$(NOX) -s docs -- +d linkcheck

# ** typing
.PHONY: typing-mypy typing-pyright typing-typecheck
typing-mypy: ## run mypy mypy_args=...
	$(NOX) -s typing -- +m mypy
typing-pyright: ## run pyright pyright_args=...
	$(NOX) -s typing -- +m pyright
typing-typecheck:
	$(NOX) -s typing -- +m mypy pyright

# ** dist pypi
.PHONY: build testrelease release
build: ## build dist
	$(NOX) -s build
testrelease: ## test release on testpypi
	$(NOX) -s publish -- +p test
release: ## release to pypi, can pass posargs=...
	$(NOX) -s publish -- +p release

# ** dist conda
.PHONY: conda-recipe conda-build
conda-recipe: ## build conda recipe can pass posargs=...
	$(NOX) -s conda-recipe
conda-build: ## build conda recipe can pass posargs=...
	$(NOX) -s conda-build

# ** list all options
.PHONY: nox-list
nox-list:
	$(NOX) --list


# ** sdist/wheel check ---------------------------------------------------------
.PHONY: check-release check-wheel check-dist
check-release: ## run twine check on dist
	$(NOX) -s publish -- +p check
check-wheel: ## Run check-wheel-contents (requires check-wheel-contents to be installed)
	$(UVXRUN_NO_PROJECT) -c check-wheel-contents dist/*.whl
check-dist: check-release check-wheel ## Run check-release and check-wheel

.PHONY:  list-wheel list-sdist list-dist
list-wheel: ## Cat out contents of wheel
	unzip -vl dist/*.whl
list-sdist: ## Cat out contents of sdist
	tar -tzvf dist/*.tar.gz
list-dist: list-wheel list-sdist ## Cat out sdist and wheel contents


# * NOTEBOOK -------------------------------------------------------------------
NOTEBOOKS ?= examples/usage
NBQA = $(UVXRUN) $(UVXRUN_OPTS) -c "nbqa --nbqa-shell \"$(UVXRUN)\" $(NOTEBOOKS) $(UVXRUN_OPTS) $(_NBQA)"
.PHONY: mypy-notebook pyright-notebook typecheck-notebook test-notebook
mypy-notebook: _NBQA = -c mypy
mypy-notebook: ## run nbqa mypy
	$(NBQA)
pyright-notebook: _NBQA = -c pyright
pyright-notebook: ## run nbqa pyright
	$(NBQA)
typecheck-notebook: _NBQA = -c mypy -c pyright
typecheck-notebook: ## run nbqa mypy/pyright
	$(NBQA)
test-notebook:  ## run pytest --nbval
	uv run --frozen pytest --nbval --nbval-current-env --nbval-sanitize-with=config/nbval.ini --dist loadscope -x $(NOTEBOOKS)

.PHONY: clean-kernelspec
clean-kernelspec: ## cleanup unused kernels (assuming notebooks handled by conda environment notebook)
	uv run --frozen tools/clean_kernelspec.py

.PHONY: install-kernel
install-kernel:  ## install kernel
	uv run --frozen python -m ipykernel install --user \
	--name pyproject2conda-dev \
    --display-name "Python [venv: pyproject2conda-dev]"


# * Other tools ----------------------------------------------------------------
# Note that this requires `auto-changelog`, which can be installed with pip(x)
.PHONY: auto-changelog
auto-changelog: ## autogenerate changelog and print to stdout
	uvx auto-changelog -u -r usnistgov -v unreleased --tag-prefix v --stdout --template changelog.d/templates/auto-changelog/template.jinja2

.PHONY:
commitizen-changelog:
	uvx --from="commitizen" cz changelog --unreleased-version unreleased --dry-run --incremental

# tuna analyze load time:
.PHONY: tuna-analyze
tuna-import	: ## Analyze load time for module
	uv run --frozen python -X importtime -c 'import pyproject2conda' 2> tuna-loadtime.log
	uvx tuna tuna-loadtime.log
	rm tuna-loadtime.log

.PHONY: cog-readme
cog-readme: ## apply cog to README.md
	nox -s cog
	pre-commit run markdownlint --files README.md

# NOTE: Some special stuff for README.pdf
# Can't seem to convert
.PHONY: README.pdf
README.pdf: ## create README.pdf
	pandoc -V colorlinks -V geometry:margin=0.8in README.md -o README.pdf
