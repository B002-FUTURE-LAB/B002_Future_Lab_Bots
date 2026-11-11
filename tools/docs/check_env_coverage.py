#!/usr/bin/env python3
"""Check that every variable in future_lab_control_center/.env.example is documented in docs/reference/configuration.md."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / "future_lab_control_center" / ".env.example"
CONFIG_DOC = ROOT / "docs" / "reference" / "configuration.md"


def parse_env_keys(path: Path) -> list[str]:
    keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if match:
            keys.append(match.group(1))
    return keys


def main() -> int:
    if not ENV_EXAMPLE.exists():
        print(f"ERROR: {ENV_EXAMPLE} not found", file=sys.stderr)
        return 1
    if not CONFIG_DOC.exists():
        print(f"ERROR: {CONFIG_DOC} not found", file=sys.stderr)
        return 1

    keys = parse_env_keys(ENV_EXAMPLE)
    doc_text = CONFIG_DOC.read_text(encoding="utf-8")
    missing = [key for key in keys if f"`{key}`" not in doc_text and key not in doc_text]

    if missing:
        print(
            f"ERROR: {len(missing)} variable(s) from .env.example missing in {CONFIG_DOC.relative_to(ROOT)}:",
            file=sys.stderr,
        )
        for key in missing:
            print(f"  - {key}", file=sys.stderr)
        return 1

    print(f"OK: all {len(keys)} variable(s) from .env.example are documented in {CONFIG_DOC.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
