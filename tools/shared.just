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
TYPECHECK := "-m typecheck_runner -v"

# * Functions ------------------------------------------------------------------

# run nox
[group("tools")]
nox *options:
    uv run --script noxfile.py {{ options }}

# run pre-commit
[group("lint")]
[group("tools")]
pre-commit *commands:
    @[[ ! -f {{ CONSTRAINTS_LOCK }} ]] && touch {{ CONSTRAINTS_LOCK }} || true
    {{ UVX }} --constraints={{ CONSTRAINTS_LOCK }} prek {{ commands }} # using prek

[group("lint")]
[group("tools")]
prek *commands: (pre-commit commands)
