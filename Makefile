# * Utilities -----------------------------------------------------------------
.PHONY: all clean clean-test clean-pyc clean-build help
.DEFAULT_GOAL := help

UVX = uvx
UVX_OPTS = --constraints=requirements/lock/uvx-tools.txt
UVRUN = uv run --frozen

TYPECHECK = $(UVRUN) --no-config tools/typecheck.py -v
NOX = $(UVX) --from "nox>=2024.10.9" nox
PRE_COMMIT = $(UVX) $(UVX_OPTS) --with=pre-commit-uv pre-commit

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

BROWSER := $(UVRUN) --no-config python -c "$$BROWSER_PYSCRIPT"

help:
	@$(UVRUN) python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

all: help

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
.PHONY: pre-commit-init lint codespell typos ruff ruff-format ruff-all checkmake
pre-commit-init: ## install pre-commit
	$(PRE_COMMIT) install

_PRE_COMMIT_RUN = $(PRE_COMMIT) run --all-files
_PRE_COMMIT_RUN_MANUAL = $(_PRE_COMMIT_RUN) --hook-stage=manual
lint: ## run pre-commit on all files
	$(_PRE_COMMIT_RUN)

lint-all: ## run pre-commit using manual stage
	$(_PRE_COMMIT_RUN_MANUAL)

codespell: ## run codespell. Note that this imports allowed words from docs/spelling_wordlist.txt
	$(_PRE_COMMIT_RUN) codespell
	$(_PRE_COMMIT_RUN) nbqa-codespell

typos:  ## run typos.
	$(_PRE_COMMIT_RUN_MANUAL) typos
	$(_PRE_COMMIT_RUN_MANUAL) nbqa-typos

ruff: ## run ruff linters
	$(_PRE_COMMIT_RUN) ruff

ruff-format: ## run ruff formatter
	$(_PRE_COMMIT_RUN) ruff-format

ruff-all: ## run ruff lint and format
	$(_PRE_COMMIT_RUN) ruff-all

checkmake:  ## run checkmake
	$(_PRE_COMMIT_RUN_MANUAL) checkmake


# * User setup -----------------------------------------------------------------
.PHONY: user-autoenv-zsh dev user-all
user-autoenv-zsh: ## create .autoenv.zsh files
	echo source ./.venv/bin/activate > .autoenv.zsh
	echo deactivate > .autoenv_leave.zsh

user-all: user-autoenv-zsh ## runs user scripts


# * Testing --------------------------------------------------------------------
.PHONY: test coverage
test: ## run tests quickly with the default Python
	$(UVRUN) pytest

test-accept: ## run tests and accept doctest results. (using pytest-accept)
	DOCFILLER_SUB=False $(UVRUN) pytest -v --accept


# * Versioning -----------------------------------------------------------------
.PHONY: version-scm version-import version

version-scm: ## check/update version of package from scm
	$(NOX) -s build -- ++build version

version-import: ## check version from python import
	-$(UVRUN) python -c 'import pyproject2conda; print(pyproject2conda.__version__)'

version: version-scm version-import


# * Requirements/Environment files ---------------------------------------------
.PHONY: requirements
requirements: ## rebuild all requirements/environment files
	$(NOX) -s requirements


# * Typing ---------------------------------------------------------------------
.PHONY: mypy pyright pyright-watch pylint _typecheck typecheck
PYLINT_OPTS = --enable-all-extensions
mypy: ## Run mypy
	$(TYPECHECK) $(UVX_OPTS) -x mypy
pyright: ## Run pyright
	$(TYPECHECK) $(UVX_OPTS) -x pyright
pyright-watch: ## Run pyright in watch mode
	$(TYPECHECK) $(UVX_OPTS) -x pyright -- -w
pylint: ## Run pylint
	$(UVRUN) pylint $(PYLINT_OPTS) src tests
_typecheck:
	$(TYPECHECK) $(UVX_OPTS) -x mypy -x pyright
typecheck: _typecheck pylint ## Run mypy and pyright

.PHONY: tools-typecheck
tools-typecheck:
	$(TYPECHECK) $(UVX_OPTS) -x mypy -- --strict noxfile.py tools/*.py
	$(TYPECHECK) $(UVX_OPTS) -x pyright -- noxfile.py tools/*.py
	$(UVRUN) pylint $(PYLINT_OPTS) noxfile.py tools

# * NOX ------------------------------------------------------------------------
# ** docs
.PHONY: docs-html docs-clean docs-clean-build docs-release
docs-html: ## build html docs
	$(NOX) -s docs -- +d html
docs-build: docs-html ## alias to docs-html
docs-clean: ## clean docs
	rm -rf docs/_build/*
	rm -rf docs/generated/*
	rm -rf docs/reference/generated/*
docs-clean-build: docs-clean docs-build ## clean and build
docs-release: ## release docs.
	$(UVX) $(UVX_OPTS) -x "ghp-import -o -n -m \"update docs\" -b nist-pages" docs/_build/html

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
.PHONY: typing-mypy typing-pyright typing-pylint typing-typecheck
typing-mypy: ## run mypy mypy_args=...
	$(NOX) -s typing -- +m mypy
typing-pyright: ## run pyright pyright_args=...
	$(NOX) -s typing -- +m pyright
typing-pylint: ## run pylint
	$(NOX) -s pylint -- +m pylint
typing-typecheck:
	$(NOX) -s typing -- +m mypy pyright pylint

# ** dist pypi
.PHONY: build publish publish-test
build: ## build dist
	$(NOX) -s build
publish: ## publish to pypi
	$(NOX) -s publish -- +p release
publish-test: ## publish to testpypi
	$(NOX) -s publish -- +p test

.PHONY: uv-publish uv-publish-test
_UV_PUBLISH = uv publish --username __token__ --keyring-provider subprocess
uv-publish: ## uv release
	$(_UV_PUBLISH)
uv-publish-test: ## uv test release on testpypi
	$(_UV_PUBLISH) --publish-url https://test.pypi.org/legacy/


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
	$(UVX) $(UVX_OPTS) -x check-wheel-contents dist/*.whl
check-dist: check-release check-wheel ## Run check-release and check-wheel

.PHONY:  list-wheel list-sdist list-dist
list-wheel: ## Cat out contents of wheel
	unzip -vl dist/*.whl
list-sdist: ## Cat out contents of sdist
	tar -tzvf dist/*.tar.gz
list-dist: list-wheel list-sdist ## Cat out sdist and wheel contents


# * NOTEBOOK -------------------------------------------------------------------
NOTEBOOKS ?= examples/usage
# NOTE: use this because nested call back in nox has errors with uv run...
_PYTHON = $(shell which python)
_NBQA_TYPECHECK = $(_PYTHON) tools/typecheck.py -v
NBQA = $(UVX) $(UVX_OPTS) nbqa --nbqa-shell "$(_NBQA_TYPECHECK) $(UVX_OPTS) $(_NBQA)" $(NOTEBOOKS)
.PHONY: notebook-mypy notebook-pyright notebook-pylint notebook-typecheck no	tebook-test
notebook-mypy: _NBQA = -x mypy
notebook-mypy: ## run nbqa mypy
	$(NBQA)
notebook-pyright: _NBQA = -x pyright
notebook-pyright: ## run nbqa pyright
	$(NBQA)
notebook-pylint:: ## run nbqa pylint
	$(UVX) $(UVX_OPTS) nbqa --nbqa-shell "$(_PYTHON) -m pylint $(PYLINT_OPTS)" $(NOTEBOOKS)
notebook-typecheck: _NBQA = -x mypy -x pyright
notebook-typecheck: notebook-pylint ## run nbqa mypy/pyright
	$(NBQA)

notebook-test:  ## run pytest --nbval
	$(UVRUN) pytest --nbval --nbval-current-env --nbval-sanitize-with=config/nbval.ini --dist loadscope -x $(NOTEBOOKS)

.PHONY: clean-kernelspec
clean-kernelspec: ## cleanup unused kernels (assuming notebooks handled by conda environment notebook)
	$(UVRUN) tools/clean_kernelspec.py

.PHONY: install-kernel
install-ipykernel:  ## install ipykernel
	$(NOX) -s install-ipykernel

# * Other tools ----------------------------------------------------------------
# Note that this requires `auto-changelog`, which can be installed with pip(x)
.PHONY: auto-changelog
auto-changelog: ## autogenerate changelog and print to stdout
	$(UVX) $(UVX_OPTS) auto-changelog -u -r usnistgov -v unreleased --tag-prefix v --stdout --template changelog.d/templates/auto-changelog/template.jinja2

.PHONY:
commitizen-changelog:
	$(UVX) $(UVX_OPTS) --from=commitizen cz changelog --unreleased-version unreleased --dry-run --incremental

# tuna analyze load time:
.PHONY: tuna-analyze
tuna-import	: ## Analyze load time for module
	$(UVRUN) python -X importtime -c 'import pyproject2conda' 2> tuna-loadtime.log
	$(UVX) $(UVX_OPTS) tuna tuna-loadtime.log
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
