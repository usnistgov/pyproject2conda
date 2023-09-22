################################################################################
# * Utilities
################################################################################
.PHONY: clean clean-test clean-pyc clean-build help
.DEFAULT_GOAL := help

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

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr docs/_build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .nox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache



################################################################################
# * Pre-commit
################################################################################
.PHONY: pre-commit-init pre-commit pre-commit-all
pre-commit-init: ## install pre-commit
	pre-commit install

pre-commit: ## run pre-commit
	pre-commit run

pre-commit-all: ## run pre-commit on all files
	pre-commit run --all-files

.PHONY: pre-commit-lint pre-commit-lint-notebooks pre-commit-prettier pre-commit-lint-markdown
pre-commit-lint: ## run ruff and black on on all files
	pre-commit run --all-files ruff
	pre-commit run --all-files black
	pre-commit run --all-files blacken-docs

pre-commit-lint-notebooks: ## Run nbqa linting
	pre-commit run --all-files nbqa-ruff
	pre-commit run --all-files nbqa-black

pre-commit-prettier: ## run prettier on all files.
	pre-commit run --all-files prettier

pre-commit-lint-markdown: ## run markdown linter.
	pre-commit run --all-files --hook-stage manual markdownlint-cli2

.PHONY: pre-commit-lint-extra pre-commit-mypy pre-commit-codespell
pre-commit-lint-extra: ## run all extra linting (isort, flake8, pyupgrade, nbqa isort and pyupgrade)
	pre-commit run --all-files --hook-stage manual isort
	pre-commit run --all-files --hook-stage manual flake8
	pre-commit run --all-files --hook-stage manual pyupgrade
	pre-commit run --all-files --hook-stage manual nbqa-pyupgrade
	pre-commit run --all-files --hook-stage manual nbqa-isort

pre-commit-mypy: ## run mypy
	pre-commit run --all-files --hook-stage manual mypy

pre-commit-pyright: ## run pyright
	pre-commit run --all-files --hook-stage manual pyright

pre-commit-codespell: ## run codespell. Note that this imports allowed words from docs/spelling_wordlist.txt
	pre-commit run --all-files --hook-stage manual codespell

################################################################################
# * User setup
################################################################################
.PHONY: user-venv user-autoenv-zsh user-all
user-venv: ## create .venv file with name of conda env
	echo $${PWD}/.nox/pyproject2conda/envs/dev > .venv

user-autoenv-zsh: ## create .autoenv.zsh files
	echo conda activate $$(cat .venv) > .autoenv.zsh
	echo conda deactivate > .autoenv_leave.zsh

user-all: user-venv user-autoenv-zsh ## runs user scripts


################################################################################
# * Testing
################################################################################
.PHONY: test coverage
test: ## run tests quickly with the default Python
	pytest -x -v

test-accept: ## run tests and accept doctest results. (using pytest-accept)
	DOCFILLER_SUB=False pytest -v --accept

coverage: ## check code coverage quickly with the default Python
	coverage run --source pyproject2conda -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html


################################################################################
# * Versioning
################################################################################
.PHONY: version-scm version-import version

version-scm: ## check/update version of package with setuptools-scm
	python -m setuptools_scm

version-import: ## check version from python import
	-python -c 'import pyproject2conda; print(pyproject2conda.__version__)'

version: version-scm version-import

################################################################################
# * Requirements/Environment files
################################################################################
.PHONY: requirements
requirements: ## rebuild all requirements/environment files
	nox -s requirements

requirements/%.yaml: pyproject.toml requirements
requirements/%.txt: pyproject.toml requirements

################################################################################
# * NOX
###############################################################################
# NOTE: Below, we use requirement of the form "requirements/dev.txt"
# Since any of these files will trigger a rebuild of all requirements,
# the actual "txt" or "yaml" file doesn't matter
# ** dev
NOX=nox
.PHONY: dev-env
dev-env: requirements/dev.txt ## create development environment using nox
	$(NOX) -e dev

# ** testing
.PHONY: test-all
test-all: requirements/test.txt ## run tests on every Python version with nox.
	$(NOX) -s test

# ** docs
.PHONY: docs-build docs-release docs-clean docs-command
docs-build: ## build docs in isolation
	$(NOX) -s docs -- -d build
docs-clean: ## clean docs
	rm -rf docs/_build/*
	rm -rf docs/generated/*
	rm -rf docs/reference/generated/*
docs-clean-build: docs-clean docs-build ## clean and build
docs-release: ## release docs.
	$(NOX) -s docs -- -d release
docs-command: ## run arbitrary command with command=...
	$(NOX) -s docs -- --docs-run $(command)

.PHONY: .docs-spelling docs-nist-pages docs-open docs-livehtml docs-clean-build docs-linkcheck
docs-spelling: ## run spell check with sphinx
	$(NOX) -s docs -- -d spelling
docs-livehtml: ## use autobuild for docs
	$(NOX) -s docs -- -d livehtml
docs-open: ## open the build
	$(NOX) -s docs -- -d open
docs-linkcheck: ## check links
	$(NOX) -s docs -- -d linkcheck

docs-build docs-release docs-command docs-clean docs-livehtml docs-linkcheck: requirements/docs.txt

# ** typing
.PHONY: typing-mypy typing-pyright typing-pytype typing-all typing-command
typing-mypy: ## run mypy mypy_args=...
	$(NOX) -s typing -- -m mypy
typing-pyright: ## run pyright pyright_args=...
	$(NOX) -s typing -- -m pyright
typing-pytype: ## run pytype pytype_args=...
	$(NOX) -s typing -- -m pytype
typing-all:
	$(NOX) -s typing -- -m mypy pyright pytype
typing-command:
	$(NOX) -s typing -- --typing-run $(command)
typing-mypy typing-pyright typing-pytype typing-all typing-command: requirements/typing.txt

# ** dist pypi
.PHONY: dist-pypi-build dist-pypi-testrelease dist-pypi-release dist-pypi-command

dist-pypi-build: ## build dist
	$(NOX) -s dist-pypi -- -p build
dist-pypi-testrelease: ## test release on testpypi
	$(NOX) -s dist-pypi -- -p testrelease
dist-pypi-release: ## release to pypi, can pass posargs=...
	$(NOX) -s dist-pypi -- -p release
dist-pypi-command: ## run command with command=...
	$(NOX) -s dist-pypi -- --dist-pypi-run $(command)
dist-pypi-build dist-pypi-testrelease dist-pypi-release dist-pypi-command: requirements/dist-pypi.txt

# ** dist conda
.PHONY: dist-conda-recipe dist-conda-build dist-conda-command
dist-conda-recipe: ## build conda recipe can pass posargs=...
	$(NOX) -s dist-conda -- -c recipe
dist-conda-build: ## build conda recipe can pass posargs=...
	$(NOX) -s dist-conda -- -c build
dist-conda-command: ## run command with command=...
	$(NOX) -s dist-conda -- -dist-conda-run $(command)
dist-conda-build dist-conda-recipe dist-conda-command: requirements/dist-pypi.txt

# ** list all options
.PHONY: nox-list
nox-list:
	$(NOX) --list


################################################################################
# * Installation
################################################################################
.PHONY: install install-dev
install: ## install the package to the active Python's site-packages (run clean?)
	pip install . --no-deps

install-dev: ## install development version (run clean?)
	pip install -e . --no-deps


################################################################################
# * Other tools
################################################################################

# Note that this requires `auto-changelog`, which can be installed with pip(x)
auto-changelog: ## autogenerate changelog and print to stdout
	auto-changelog -u -r usnistgov -v unreleased --tag-prefix v --stdout --template changelog.d/templates/auto-changelog/template.jinja2

commitizen-changelog:
	cz changelog --unreleased-version unreleased --dry-run --incremental

# tuna analyze load time:
.PHONY: tuna-analyze
tuna-import: ## Analyze load time for module
	python -X importtime -c 'import pyproject2conda' 2> tuna-loadtime.log
	tuna tuna-loadtime.log
	rm tuna-loadtime.log

# nbqa-mypy
NOTEBOOKS ?= examples/usage
.PHONY: nbqa-mypy nbqa-pyright nbqa-typing
nbqa-mypy: ## run nbqa mypy
	nbqa --nbqa-shell mypy $(NOTEBOOKS)
nbqa-pyright: ## run nbqa pyright
	nbqa --nbqa-shell pyright $(NOTEBOOKS)
nbqa-typing: nbqa-mypy nbqa-pyright ## run nbqa mypy/pyright

.PHONY: pytest-nbval
pytest-nbval:  ## run pytest --nbval
	pytest --nbval --current-env --sanitize-with=config/nbval.ini $(NOTEBOOKS) -x

.PHONY: cog-readme
cog-readme: ## apply cog to README.md
	cog -rP README.md
	pre-commit run markdownlint --files README.md

# NOTE: Some special stuff for README.pdf
# Can't seem to convert
.PHONY: README.pdf
README.pdf: ## create README.pdf
	P2C_USE_CLICK=false cog -P -o tmp.md README.md
	-pre-commit run markdownlint --files tmp.md
	pandoc -V colorlinks tmp.md -o README.pdf
	rm tmp.md
