"""
Script to cleanup installed ipykernels that no longer exist.

This script must be run from the environment with the notebook server.
For example, if you have a conda environment `notebook` with your
jupyter server, run the following:

$ conda run -n notebook python path/to/clean_kernelspec.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from subprocess import CalledProcessError

FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("clean_kernelspec")


def get_kernelspec_data() -> None:
    """Main function."""
    from subprocess import check_output

    s = check_output(
        ["jupyter", "kernelspec", "list", "--json", "--log-level", "ERROR"],
    )

    to_remove: list[str] = []
    for name, data in json.loads(s)["kernelspecs"].items():
        p = Path(data["spec"]["argv"][0])

        if not p.exists():
            logger.debug("%s does not exist.", name)
            to_remove.append(name)

        else:
            logger.debug("%s exists.", name)

    if to_remove:
        logger.info("removing kernels %s", to_remove)
        check_output(["jupyter", "kernelspec", "remove", "-f", *to_remove])
    else:
        logger.info("nothing to do")


if __name__ == "__main__":
    try:
        get_kernelspec_data()
    except CalledProcessError:
        logger.exception("Most likely you didn't run from notebook server environment")
        raise
