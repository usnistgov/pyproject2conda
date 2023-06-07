.PHONY: help clean build release testrelease command
help:
	@echo Makefile for building pypi dist
clean:
	-rm -rf dist/*

build: clean
	python -m build --outdir dist/

testrelease:
	twine upload --repository testpypi dist/*

release:
	twine upload dist/*

command?= @echo "pass command=..."
command:
	$(command)
