"""Utilities for tools."""
from __future__ import annotations


def get_conda_environment_map(simplify: bool = True) -> dict[str, str]:
    """Contruct mapping from environment env_name to path"""
    import subprocess
    from pathlib import Path

    result = subprocess.check_output(["conda", "env", "list"])

    env_map = {}
    for line in result.decode().split("\n"):
        if not line.startswith("#"):
            x = line.replace("*", "").split()
            n = len(x)
            if n == 1:
                # this is path environment
                pass
            elif n == 2:
                env_map[x[0]] = x[1]
    if simplify:
        home = str(Path.home())
        env_map = {k: v.replace(home, "~") for k, v in env_map.items()}
    return env_map
