#!/usr/bin/env python3
"""校验 API 路由索引文档是否与代码一致.

用法:
  python3 scripts/docs/check_api_routes_reference.py

规则:
  - 从 `app/__init__.py` 的 `configure_blueprints()` 提取蓝图注册信息
  - 静态扫描 `app/routes/**/*.py` 中对这些蓝图的 `.route(...)` / `.add_url_rule(...)`
  - 与 `docs/reference/api/api-routes-documentation.md` 表格中的 (path, methods) 对比
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs/reference/api/api-routes-documentation.md"
APP_INIT_PATH = REPO_ROOT / "app/__init__.py"
ROUTES_ROOT = REPO_ROOT / "app/routes"


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def _get_kw(call: ast.Call, name: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _get_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _get_str_list(node: ast.AST | None) -> list[str] | None:
    if node is None:
        return None
    value = _literal(node)
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return [str(item) for item in value]
    return None


def _join_prefix(app_prefix: str | None, blueprint_prefix: str | None, rule: str) -> str:
    parts: list[str] = []
    for prefix in (app_prefix, blueprint_prefix):
        if not prefix:
            continue
        normalized = prefix if prefix.startswith("/") else f"/{prefix}"
        parts.append(normalized.rstrip("/"))

    normalized_rule = rule if rule.startswith("/") else f"/{rule}"

    if not parts:
        return normalized_rule
    if normalized_rule == "/":
        return "".join(parts) + "/"
    return "".join(parts) + normalized_rule


def _load_blueprint_specs() -> list[tuple[str, str, str | None]]:
    tree = ast.parse(APP_INIT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "blueprint_specs":
            value = _literal(node.value) if node.value is not None else None
            if isinstance(value, list):
                return [(a, b, c) for a, b, c in value]
    raise RuntimeError("无法在 app/__init__.py 中定位 blueprint_specs")


def _resolve_blueprint_prefix(module_path: str, blueprint_name: str) -> str | None:
    module_file = REPO_ROOT / (module_path.replace(".", "/") + ".py")
    tree = ast.parse(module_file.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets: list[ast.AST]
        value: ast.AST | None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        else:
            targets = [node.target]
            value = node.value

        if not any(isinstance(target, ast.Name) and target.id == blueprint_name for target in targets):
            continue
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "Blueprint":
            return _get_str(_get_kw(value, "url_prefix"))
    return None


def _build_blueprint_prefix_map() -> dict[str, tuple[str | None, str | None]]:
    prefix_map: dict[str, tuple[str | None, str | None]] = {}
    for module_path, blueprint_name, app_prefix in _load_blueprint_specs():
        blueprint_prefix = _resolve_blueprint_prefix(module_path, blueprint_name)
        prefix_map[blueprint_name] = (app_prefix, blueprint_prefix)
    return prefix_map


def _extract_code_routes(prefix_map: dict[str, tuple[str | None, str | None]]) -> set[tuple[str, tuple[str, ...]]]:
    routes: set[tuple[str, tuple[str, ...]]] = set()
    for py_file in ROUTES_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if (
                        not isinstance(decorator, ast.Call)
                        or not isinstance(decorator.func, ast.Attribute)
                        or not isinstance(decorator.func.value, ast.Name)
                    ):
                        continue
                    blueprint_name = decorator.func.value.id
                    if blueprint_name not in prefix_map:
                        continue
                    method_attr = decorator.func.attr
                    if method_attr not in {"route", "get", "post", "put", "delete", "patch"}:
                        continue
                    rule = _get_str(decorator.args[0]) if decorator.args else None
                    if not rule:
                        continue

                    if method_attr != "route":
                        methods = (method_attr.upper(),)
                    else:
                        methods_raw = _get_str_list(_get_kw(decorator, "methods"))
                        methods = tuple((m.upper() for m in methods_raw)) if methods_raw else ("GET",)

                    app_prefix, blueprint_prefix = prefix_map[blueprint_name]
                    full_path = _join_prefix(app_prefix, blueprint_prefix, rule)
                    routes.add((full_path, methods))

            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.attr == "add_url_rule"
            ):
                blueprint_name = node.func.value.id
                if blueprint_name not in prefix_map:
                    continue
                rule = _get_str(node.args[0]) if node.args else None
                if not rule:
                    continue
                methods_raw = _get_str_list(_get_kw(node, "methods"))
                methods = tuple((m.upper() for m in methods_raw)) if methods_raw else ("GET",)
                app_prefix, blueprint_prefix = prefix_map[blueprint_name]
                full_path = _join_prefix(app_prefix, blueprint_prefix, rule)
                routes.add((full_path, methods))
    return routes


def _extract_doc_routes() -> set[tuple[str, tuple[str, ...]]]:
    text = DOC_PATH.read_text(encoding="utf-8")
    row_re = re.compile(
        r"^[|]\s*(?:`(?P<path_bt>[^`]+)`|(?P<path>/[^|]+?))\s*[|]\s*(?P<methods>[^|]+?)\s*[|]",
        re.M,
    )

    routes: set[tuple[str, tuple[str, ...]]] = set()
    for match in row_re.finditer(text):
        path = (match.group("path_bt") or match.group("path") or "").strip()
        if not path.startswith("/"):
            continue
        methods_raw = match.group("methods").strip()
        methods = tuple(method.strip().upper() for method in methods_raw.split(",") if method.strip())
        if not methods:
            continue
        if not all(re.fullmatch(r"[A-Z]+", method) for method in methods):
            continue
        routes.add((path, methods))
    return routes


def main() -> int:
    if not DOC_PATH.exists():
        print(f"目标文档不存在: {DOC_PATH}")
        return 2

    prefix_map = _build_blueprint_prefix_map()
    code_routes = _extract_code_routes(prefix_map)
    doc_routes = _extract_doc_routes()

    missing = sorted(code_routes - doc_routes)
    extra = sorted(doc_routes - code_routes)

    print(f"code_routes: {len(code_routes)}")
    print(f"doc_routes : {len(doc_routes)}")
    print(f"missing    : {len(missing)}")
    print(f"extra      : {len(extra)}")

    if missing:
        print("\nMissing routes in docs (path, methods):")
        for path, methods in missing[:50]:
            print(f"- {path} {', '.join(methods)}")
        if len(missing) > 50:
            print(f"... ({len(missing) - 50} more)")

    if extra:
        print("\nExtra routes in docs (path, methods):")
        for path, methods in extra[:50]:
            print(f"- {path} {', '.join(methods)}")
        if len(extra) > 50:
            print(f"... ({len(extra) - 50} more)")

    return 1 if (missing or extra) else 0


if __name__ == "__main__":
    raise SystemExit(main())
