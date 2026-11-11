#!/usr/bin/env python3
"""Fail if a REST route in the backend is missing from docs/reference/rest-api.md.

Routes are discovered with ``ast`` (no imports), so this runs without ROS 2,
FastAPI or any backend dependency.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "future_lab_control_center" / "backend" / "api"
PAGE = ROOT / "docs" / "reference" / "rest-api.md"
METHODS = {"get", "post", "put", "delete", "patch"}


def literal(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def routes_in(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prefix = ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "APIRouter":
            for kw in node.keywords:
                if kw.arg == "prefix":
                    prefix = literal(kw.value) or ""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                    and deco.func.attr in METHODS and deco.args):
                sub = literal(deco.args[0])
                if sub is not None:
                    yield deco.func.attr.upper(), prefix + (sub if sub != "/" else "/")


def main() -> int:
    page = PAGE.read_text(encoding="utf-8")
    found, missing = 0, []
    for file in sorted(API_DIR.glob("*_routes.py")):
        for method, path in routes_in(file):
            found += 1
            if f"`{method} {path}`" not in page:
                missing.append(f"{method} {path}  ({file.name})")
    print(f"Routes found in code: {found}")
    if missing:
        print("Missing from docs/reference/rest-api.md:")
        for item in missing:
            print(f"  - {item}")
        return 1
    print("OK: every route is documented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
