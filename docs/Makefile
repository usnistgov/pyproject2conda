# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SPHINXAUTOBUILD = sphinx-autobuild
SOURCEDIR     = .
BUILDDIR      = _build

ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(SPHINXOPTS)

ALLSPHINXAUTOOPTS = $(ALLSPHINXOPTS) \
	--ignore "*/$(BUILDDIR)/*" \
	--ignore "*/generated/*" \
	--ignore "*/jupyter_execute/*" \
	--ignore "*/.ipynb_checkpoints/*"



.PHONY: help Makefile clean-all build livehtml showlinks release command
# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(ALLSPHINXOPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(ALLSPHINXOPTS) $(O)

clean-all: clean
	rm -rf $(BUILDDIR)/*
	rm -rf generated/*
	rm -rf reference/generated/*

# Alias to html
build: html

livehtml:
	$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html" $(ALLSPHINXAUTOOPTS) $(O)

showlinks:
	python -m sphinx.ext.intersphinx $(BUILDDIR)/html/objects.inv

command ?= @echo pass "command=..."
command:
	$(command)
