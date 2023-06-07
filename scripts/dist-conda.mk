
project_name?=pyproject2conda
sdist_path?=$(project_name)

.PHONY: help clean-recipe clean-build grayskull recipe-append recipe build command

help:
	@echo Makefile for building conda dist
clean-recipe:
	rm -rf dist-conda/$(project_name)

clean-build:
	rm -rf build

# by default, only use a few sections
grayskull_args ?= --maintainers wpk-nist-gov --sections package source build requirements
grayskull: clean-recipe
	grayskull pypi $(sdist_path) $(grayskull_args) -o dist-conda

# append the rest
recipe_base_path ?= dist-conda/$(project_name)/meta.yaml
recipe_append_path ?= .recipe-append.yaml
recipe-append:
	bash scripts/recipe-append.sh $(recipe_base_path) $(recipe_append_path)

recipe: grayskull recipe-append

build: clean-build
	conda mambabuild --output-folder=dist-conda/build --no-anaconda-upload dist-conda

command:
	$(command)
