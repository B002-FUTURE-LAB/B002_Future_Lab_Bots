#!/usr/bin/env python3
"""Fail if a published documentation page contains Portuguese-only letters.

This is a deliberately simple heuristic (accented letters used in Portuguese
but not in English). It catches accidental Portuguese text, not every
possible mistake. Pages excluded from the site in ``mkdocs.yml`` are skipped.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
PORTUGUESE_LETTERS = re.compile("[áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]")


def excluded_files() -> set:
    """Read the ``exclude_docs`` block of mkdocs.yml (one filename per line)."""
    names, inside = set(), False
    for line in (ROOT / "mkdocs.yml").read_text(encoding="utf-8").splitlines():
        if line.startswith("exclude_docs:"):
            inside = True
            continue
        if inside:
            if line.startswith("  ") and line.strip():
                names.add(line.strip())
            else:
                inside = False
    return names


def main() -> int:
    skipped = excluded_files()
    failures = 0
    for page in sorted(DOCS.rglob("*.md")):
        if page.name in skipped:
            continue
        for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            if PORTUGUESE_LETTERS.search(line):
                print(f"{page.relative_to(ROOT)}:{number}: non-English letters: {line.strip()[:100]}")
                failures += 1
    if failures:
        print(f"\n{failures} line(s) look like Portuguese. The documentation must be English.")
        return 1
    print("OK: no Portuguese-specific letters found in published pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
