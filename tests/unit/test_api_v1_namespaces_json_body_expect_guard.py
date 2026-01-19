from __future__ import annotations

import ast
from pathlib import Path

import pytest

HTTP_METHOD_NAMES = {"get", "post", "put", "delete", "patch"}


def _uses_request_get_json(fn: ast.FunctionDef) -> bool:
    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get_json":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "request":
                    self.found = True
            self.generic_visit(node)

    visitor = Visitor()
    visitor.visit(fn)
    return visitor.found


def _has_ns_expect(fn: ast.FunctionDef) -> bool:
    for decorator in fn.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if not isinstance(decorator.func, ast.Attribute) or decorator.func.attr != "expect":
            continue
        if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "ns":
            return True
    return False


@pytest.mark.unit
def test_api_v1_json_body_endpoints_declare_ns_expect_model() -> None:
    """OpenAPI: 读取 request.get_json 的端点必须声明 @ns.expect(model)."""
    repo_root = Path(__file__).resolve().parents[2]
    namespaces_root = repo_root / "app" / "api" / "v1" / "namespaces"

    missing: list[str] = []
    for path in sorted(namespaces_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except OSError:
            continue

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name not in HTTP_METHOD_NAMES:
                    continue
                if _uses_request_get_json(item) and not _has_ns_expect(item):
                    rel = path.relative_to(repo_root)
                    missing.append(f"{rel}:{item.lineno}: {node.name}.{item.name} missing @ns.expect")

    assert not missing, "发现缺少 @ns.expect 的 JSON body 端点:\n" + "\n".join(missing)
