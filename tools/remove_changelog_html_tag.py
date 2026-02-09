"""Remove html tag scriv adds to changelog"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


def _remove_html_tag(path: Path) -> Iterator[str]:
    import re

    pattern = re.compile(r"^<a.*\ id=.*></a>$")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not pattern.match(line):
                yield line


def _main() -> int:
    parser = ArgumentParser()
    _ = parser.add_argument("changelog", type=Path)

    options = parser.parse_args()

    path = options.changelog

    out: list[str] = list(_remove_html_tag(path))

    with path.open("w") as f:
        f.writelines(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
