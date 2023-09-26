# Installation

## Stable release

To install `pyproject2conda`, run this command in your terminal:

```bash
pip install pyproject2conda
```

or

```bash
conda install -c wpk-nist pyproject2conda
```

If using pip, to install with [rich] and [shellingham] support, either install
them your self, or use:

```bash
pip install pyproject2conda[all]
```

The conda-forge distribution of [typer] (which `pyproject2conda` uses) installs
[rich] and [shellingham] by default.

[rich]: https://github.com/Textualize/rich
[shellingham]: https://github.com/sarugaku/shellingham

This is the preferred method to install pyproject2conda, as it will always
install the most recent stable release.

## From sources

See [](./contributing) for details on installing from source.
