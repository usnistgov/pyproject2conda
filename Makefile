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
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache




################################################################################
# utilities
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
# my convenience functions
################################################################################
.PHONY: user-venv user-autoenv-zsh user-all
user-venv: ## create .venv file with name of conda env
	echo $${PWD}/.tox/dev > .venv

user-autoenv-zsh: ## create .autoenv.zsh files
	echo conda activate $$(cat .venv) > .autoenv.zsh
	echo conda deactivate > .autoenv_leave.zsh

user-all: user-venv user-autoenv-zsh ## runs user scripts


################################################################################
# Testing
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
# versioning
################################################################################
.PHONY: version-scm version-import version
version-scm: ## check version of package
	python -m setuptools_scm

version-import: ## check version from python import
	python -c 'import pyproject2conda; print(pyproject2conda.__version__)'

version: version-scm version-import

################################################################################
# Environment files
################################################################################
ENVIRONMENTS = $(addsuffix .yaml,$(addprefix environment/, dev docs test))
PRETTIER = bash scripts/run-prettier.sh

environment/%.yaml: environment.yaml environment/%-extras.yaml ## create combined environment/{dev,docs,test}.yaml
	conda-merge $^ > $@
	$(PRETTIER) $@

environment/dev.yaml: ## development environment yaml file
environment/test.yaml: ## testing environment yaml file
enviornment/docs.yaml: ## docs environment yaml file


# special for linters
environment/lint.yaml: environment.yaml $(addsuffix .yaml, $(addprefix environment/, test-extras lint-extras)) ## mypy environment
	echo $^
	conda-merge $^ > $@
	$(PRETTIER) $@

ENVIRONMENTS += environment/lint.yaml

.PHONY: environment-files-clean
environment-files-clean: ## clean all created environment/{dev,docs,test}.yaml
	-rm $(ENVIRONMENTS) 2> /dev/null || true

.PHONY: environment-files-build
environment-files-build: $(ENVIRONMENTS) ## rebuild all environment files

################################################################################
# virtual env
################################################################################
.PHONY: mamba-env mamba-dev mamba-env-update mamba-dev-update

mamba-env: environment.yaml ## create base environment
	mamba env create -f $<

mamba-env-update: environment.yaml ## update base environment
	mamba env update -f $<

mamba-dev: environment/dev.yaml ## create development environment
	mamba env create -f $<

mamba-dev-update: environment/dev.yaml ## update development environment
	mamba env update -f $<

################################################################################
# TOX
###############################################################################
tox_args?=-v
version?=
TOX=CONDA_EXE=mamba SETUPTOOLS_SCM_PRETEND_VERSION=$(version) tox $(tox_args)

.PHONY: tox-ipykernel-display-name
tox-ipykernel-display-name: ## Update display-name for any tox env with ipykernel
	bash ./scripts/tox-ipykernel-display-name.sh pyproject2conda

## dev env
.PHONY: dev-env
dev-env: environment/dev.yaml ## create development environment using tox
	tox -e dev

## testing
.PHONY: test-all
test-all: environment/test.yaml ## run tests on every Python version with tox.  can pass posargs=...
	$(TOX) -- $(posargs)

## docs
.PHONY: docs-examples-symlink
docs-examples-symlink: ## create symlinks to notebooks from /examples/ to /docs/examples.
	bash ./scripts/docs-examples-symlinks.sh


.PHONY: docs-build docs-release docs-clean docs-command
docs-build: ## build docs in isolation
	$(TOX) -e docs -- build
docs-clean: ## clean docs
	rm -rf docs/_build/*
	rm -rf docs/generated/*
	rm -rf docs/reference/generated/*
docs-clean-build: docs-clean docs-build ## clean and build
docs-release: ## release docs.  use release_args=... to override stuff
	$(TOX) -e docs -- release
docs-command: ## run command with command=...
	$(TOX) -e docs -- command

.PHONY: .docs-spelling docs-nist-pages docs-open docs-livehtml docs-clean-build docs-linkcheck
docs-spelling: ## run spell check with sphinx
	$(TOX) -e docs -- spelling
docs-livehtml: ## use autobuild for docs
	$(TOX) -e docs -- livehtml
docs-open: ## open the build
	$(BROWSER) docs/_build/html/index.html
docs-linkcheck: ## check links
	$(TOX) -e docs -- linkcheck

docs-build docs-release docs-command docs-clean docs-livehtml docs-linkcheck: environment/docs.yaml

## linting
.PHONY: lint-mypy lint-pyright lint-pytype lint-all lint-command
lint-mypy: ## run mypy mypy_args=...
	$(TOX) -e lint -- mypy
lint-pyright: ## run pyright pyright_args=...
	$(TOX) -e lint -- pyright
lint-pytype: ## run pytype pytype_args=...
	$(TOX) -e lint -- pytype
lint-all:
	$(TOX) -e lint -- all
lint-command:
	$(TOX) -e lint -- command

lint-mypy lint-pyright lint-pytype lint-all lint-command: environment/lint.yaml

## distribution
.PHONY: dist-pypi-build dist-pypi-testrelease dist-pypi-release dist-pypi-command

dist-pypi-build: ## build dist
	$(TOX) -e dist-pypi -- build
dist-pypi-testrelease: ## test release on testpypi
	$(TOX) -e dist-pypi -- testrelease
dist-pypi-release: ## release to pypi, can pass posargs=...
	$(TOX) -e dist-pypi -- release
dist-pypi-command: ## run command with command=...
	$(TOX) -e dist-pypi -- command
dist-pypi-build dist-pypi-testrelease dist-pypi-release dist-pypi-command: environment/dist-pypi.yaml

.PHONY: dist-conda-recipe dist-conda-build dist-conda-command
dist-conda-recipe: ## build conda recipe can pass posargs=...
	$(TOX) -e dist-conda -- recipe
dist-conda-build: ## build conda recipe can pass posargs=...
	$(TOX) -e dist-conda -- build
dist-conda-command: ## run command with command=...
	$(TOX) -e dist-conda -- command
dist-conda-build dist-conda-recipe dist-conda-command: environment/dist-conda.yaml


## test distribution
.PHONY: testdist-pypi-remote testdist-conda-remote testdist-pypi-local testdist-conda-local

py?=310
testdist-pypi-remote: ## testdist-pypi-remote: ## test pypi install, can run as `make test-dist-pypi-remote py=39` to run test-dist-pypi-local-py39.  Can specify version setting, eg,  TEST_VERSION='==0.1.0'.  Note that the the format should be '=={version}'.
	$(TOX) -e $@-py$(py) -- $(posargs)
testdist-conda-remote: ## test conda install, can run as `make test-dist-conda-remote py=39` to run test-dist-conda-local-py39
	$(TOX) -e $@-py$(py) -- $(poasargs)
testdist-pypi-local: ## test pypi install, can run as `make test-dist-pypi-local py=39` to run test-dist-pypi-local-py39
	$(TOX) -e $@-py$(py) -- $(posargs)
testdist-conda-local: ## test conda install, can run as `make test-dist-conda-local py=39` to run test-dist-conda-local-py39
	$(TOX) -e $@-py$(py) -- $(poasargs)

testdist-pypi-remote testdist-conda-remote testdist-pypi-local testdist-conda-local: environment/test.yaml

## list all options
.PHONY: tox-list
tox-list:
	$(TOX) -a


################################################################################
# installation
################################################################################
.PHONY: install install-dev
install: ## install the package to the active Python's site-packages (run clean?)
	pip install . --no-deps

install-dev: ## install development version (run clean?)
	pip install -e . --no-deps


################################################################################
# other tools
################################################################################

# Note that this requires `auto-changelog`, which can be installed with pip(x)
auto-changelog: ## autogenerate changelog and print to stdout
	auto-changelog -u -r usnistgov -v unreleased --tag-prefix v --stdout --template changelog.d/templates/auto-changelog/template.jinja2

commitizen-changelog:
	cz changelog --unreleased-version unreleased --dry-run --incremental

# --- cog output -- --------------------------------------------------------------------

.PHONY: cog-readme
cog-readme: ## apply cog to README.md
	cog -rP README.md
