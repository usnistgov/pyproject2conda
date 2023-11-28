---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3
  name: python3
---

# Usage

An example for using ipython directives or jupytext

## jupytext

```{code-cell} ipython3

import pyproject2conda

a = 1
```

```{code-cell} ipython3

print(a)
```

## ipython directive

To use Python Boilerplate in a project:

```python
import pyproject2conda
```

see, e.g., {py:meth}`~pyproject2conda.core.another_func`

ipython example...

```{eval-rst}
.. ipython:: python

    import pyproject2conda
```
