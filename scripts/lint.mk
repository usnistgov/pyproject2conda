.PHONY: help mypy pyright pytype all

help:
	@echo Makefile for linting

mypy:
	-mypy --color-output $(mypy_args)

pyright:
	-pyright $(pyright_args)

pytype:
	-pytype $(pytype_args)

all: mypy pyright pytype

command?= @echo 'pass command=...'
command:
	$(command)
