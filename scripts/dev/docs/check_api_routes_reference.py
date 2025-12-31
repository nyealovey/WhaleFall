#!/usr/bin/env python3
"""校验 API 路由索引文档是否与代码一致.

用法:
  python3 scripts/dev/docs/check_api_routes_reference.py

规则:
  - 从 `app/__init__.py` 的 `configure_blueprints()` 提取蓝图注册信息
  - 静态扫描 `app/routes/**/*.py` 中对这些蓝图的 `.route(...)` / `.add_url_rule(...)`
  - 与 `docs/reference/api/api-routes-documentation.md` 表格中的 (path, methods) 对比

说明:
  - Phase 4 起, legacy `*/api/*` JSON API 已迁移到 `/api/v1/**`,
    且旧路径由 `app/api/__init__.py::_register_legacy_api_shutdown` 统一返回 410.
  - 因此本脚本仅校验 **页面路由(HTML)** 与文档是否一致, 自动忽略路径包含 `/api` 的条目.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
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
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "blueprint_specs"
        ):
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


def _route_from_decorator(
    decorator: ast.AST,
    prefix_map: dict[str, tuple[str | None, str | None]],
) -> tuple[str, tuple[str, ...]] | None:
    if (
        not isinstance(decorator, ast.Call)
        or not isinstance(decorator.func, ast.Attribute)
        or not isinstance(decorator.func.value, ast.Name)
    ):
        return None

    blueprint_name = decorator.func.value.id
    prefixes = prefix_map.get(blueprint_name)
    if prefixes is None:
        return None

    method_attr = decorator.func.attr
    if method_attr not in {"route", "get", "post", "put", "delete", "patch"}:
        return None

    rule = _get_str(decorator.args[0]) if decorator.args else None
    if not rule:
        return None

    if method_attr != "route":
        methods: tuple[str, ...] = (method_attr.upper(),)
    else:
        methods_raw = _get_str_list(_get_kw(decorator, "methods"))
        methods = tuple(m.upper() for m in methods_raw) if methods_raw else ("GET",)

    app_prefix, blueprint_prefix = prefixes
    full_path = _join_prefix(app_prefix, blueprint_prefix, rule)
    return (full_path, methods)


def _route_from_add_url_rule_call(
    node: ast.AST,
    prefix_map: dict[str, tuple[str | None, str | None]],
) -> tuple[str, tuple[str, ...]] | None:
    if (
        not isinstance(node, ast.Call)
        or not isinstance(node.func, ast.Attribute)
        or not isinstance(node.func.value, ast.Name)
        or node.func.attr != "add_url_rule"
    ):
        return None

    blueprint_name = node.func.value.id
    prefixes = prefix_map.get(blueprint_name)
    if prefixes is None:
        return None

    rule = _get_str(node.args[0]) if node.args else None
    if not rule:
        return None

    methods_raw = _get_str_list(_get_kw(node, "methods"))
    methods = tuple(m.upper() for m in methods_raw) if methods_raw else ("GET",)

    app_prefix, blueprint_prefix = prefixes
    full_path = _join_prefix(app_prefix, blueprint_prefix, rule)
    return (full_path, methods)


def _extract_code_routes(prefix_map: dict[str, tuple[str | None, str | None]]) -> set[tuple[str, tuple[str, ...]]]:
    routes: set[tuple[str, tuple[str, ...]]] = set()
    for py_file in ROUTES_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    route = _route_from_decorator(decorator, prefix_map)
                    if route is not None:
                        routes.add(route)

            route = _route_from_add_url_rule_call(node, prefix_map)
            if route is not None:
                routes.add(route)
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
        sys.stderr.write(f"目标文档不存在: {DOC_PATH}\n")
        return 2

    prefix_map = _build_blueprint_prefix_map()
    code_routes = _extract_code_routes(prefix_map)
    doc_routes = _extract_doc_routes()

    def _is_page_route(path: str) -> bool:
        return "/api" not in path

    code_routes = {(path, methods) for path, methods in code_routes if _is_page_route(path)}
    doc_routes = {(path, methods) for path, methods in doc_routes if _is_page_route(path)}

    missing = sorted(code_routes - doc_routes)
    extra = sorted(doc_routes - code_routes)

    sys.stdout.write(f"code_routes: {len(code_routes)}\n")
    sys.stdout.write(f"doc_routes : {len(doc_routes)}\n")
    sys.stdout.write(f"missing    : {len(missing)}\n")
    sys.stdout.write(f"extra      : {len(extra)}\n")

    if missing:
        sys.stdout.write("\nMissing routes in docs (path, methods):\n")
        for path, methods in missing[:50]:
            sys.stdout.write(f"- {path} {', '.join(methods)}\n")
        if len(missing) > 50:
            sys.stdout.write(f"... ({len(missing) - 50} more)\n")

    if extra:
        sys.stdout.write("\nExtra routes in docs (path, methods):\n")
        for path, methods in extra[:50]:
            sys.stdout.write(f"- {path} {', '.join(methods)}\n")
        if len(extra) > 50:
            sys.stdout.write(f"... ({len(extra) - 50} more)\n")

    return 1 if (missing or extra) else 0


if __name__ == "__main__":
    raise SystemExit(main())
