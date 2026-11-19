"""DB-06 / DB-07: architecture rules, checked on the source."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
READ_ONLY_PACKAGES = ["agents", "sql", "viz", "guardrails", "rbac"]


def python_files(package: str):
    root = APP / package
    return sorted(root.rglob("*.py")) if root.exists() else []


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_db_06_ai_and_query_code_never_touch_the_write_engine():
    offenders = [
        str(path.relative_to(APP)) for package in READ_ONLY_PACKAGES
        for path in python_files(package) if "write_engine" in path.read_text()
    ]
    assert offenders == []


def test_db_07_po_module_never_imports_sql_generation():
    offenders = [
        str(path.relative_to(APP)) for path in python_files("po")
        if any(m.startswith(("app.agents", "app.sql.validator", "app.llm.openai"))
               for m in imported_modules(path))
    ]
    assert offenders == []


def test_nodes_never_import_vendor_llm_sdks_directly():
    offenders = [
        str(path.relative_to(APP)) for path in python_files("agents")
        if any(m.startswith(("openai", "langchain_openai")) for m in imported_modules(path))
    ]
    assert offenders == []
