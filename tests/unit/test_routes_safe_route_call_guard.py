from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ROUTE_CALL_ATTRS = {"route", "add_url_rule"}


def _declares_routes(tree: ast.AST) -> bool:
    """识别模块是否包含 route 定义（decorator 或 add_url_rule 调用）。"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _ROUTE_CALL_ATTRS:
            return True
    return False


def _uses_safe_route_call(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "safe_route_call":
            return True
    return False


@pytest.mark.unit
def test_routes_modules_must_use_safe_route_call() -> None:
    """Routes 层强约束: 含 route 定义的模块必须使用 safe_route_call."""
    repo_root = Path(__file__).resolve().parents[2]
    routes_root = repo_root / "app" / "routes"

    missing: list[str] = []
    for path in routes_root.rglob("*.py"):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            rel = path.relative_to(repo_root)
            pytest.fail(f"routes 模块语法错误，无法执行门禁检查: {rel}: {exc}")

        if not _declares_routes(tree):
            continue
        if _uses_safe_route_call(tree):
            continue
        missing.append(str(path.relative_to(repo_root)))

    assert not missing, "发现未使用 safe_route_call 的 routes 模块:\n" + "\n".join(sorted(missing))
