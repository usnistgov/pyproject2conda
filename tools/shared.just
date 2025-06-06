# * Variables ------------------------------------------------------------------

PACKAGE_NAME := "pyproject2conda"
IMPORT_NAME := "pyproject2conda"
CONSTRAINTS_MIN := "requirements/uvx-tools.txt"
CONSTRAINTS_LOCK := "requirements/lock/uvx-tools.txt"
PYLINT_OPTS := "--enable-all-extensions"
UVX := "uvx"
UVX_OPTS := "--constraints=" + CONSTRAINTS_LOCK
UVX_WITH_OPTS := UVX + " " + UVX_OPTS
UVRUN_OPTS := ""
UVRUN := trim("uv run " + UVRUN_OPTS)
TYPECHECK := "tools/typecheck.py -v"

# * Functions ------------------------------------------------------------------

# run nox
[group("tools")]
nox *options:
    {{ UVX_WITH_OPTS }} nox {{ options }}

# run pre-commit
[group("lint")]
[group("tools")]
pre-commit *commands:
    @[[ ! -f {{ CONSTRAINTS_MIN }} ]] && touch {{ CONSTRAINTS_MIN }} || true
    {{ UVX }} --constraints={{ CONSTRAINTS_MIN }} --with=pre-commit-uv pre-commit {{ commands }}
