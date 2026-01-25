#!/usr/bin/env bash
# API v1(OpenAPI) 门禁：读取 request.get_json 的端点必须声明 @ns.expect(model)
#
# 参考：
# - docs/Obsidian/standards/backend/gate/layer/api-layer.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/api-v1-ns-expect-guard.sh

Checks:
  - app/api/v1/namespaces/**/*.py：
    对 Class-based Resource 的 HTTP method（get/post/put/delete/patch）
    如调用 request.get_json(...) 则必须具备 decorator: @ns.expect(...)
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

PY_BIN="${PY_BIN:-python3}"
if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
  echo "未检测到 python3，无法执行 api v1 ns.expect 门禁检查。" >&2
  exit 1
fi

"${PY_BIN}" - <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path


HTTP_METHOD_NAMES = {"get", "post", "put", "delete", "patch"}


def _uses_request_get_json(fn: ast.FunctionDef) -> bool:
    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
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


def main() -> int:
    repo_root = Path.cwd()
    namespaces_root = repo_root / "app" / "api" / "v1" / "namespaces"
    if not namespaces_root.exists():
        sys.stdout.write("未找到 app/api/v1/namespaces，跳过检查。\n")
        return 0

    missing: list[str] = []
    parse_errors: list[str] = []

    for path in sorted(namespaces_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        except SyntaxError as exc:
            rel = path.relative_to(repo_root)
            parse_errors.append(f"{rel}: {exc}")
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

    if parse_errors:
        sys.stderr.write("API namespaces 解析失败，无法执行门禁检查：\n")
        sys.stderr.write("\n".join(f"- {item}" for item in parse_errors[:20]) + "\n")
        return 1

    if missing:
        sys.stderr.write("发现缺少 @ns.expect 的 JSON body 端点（禁止）：\n")
        sys.stderr.write("\n".join(f"- {item}" for item in missing[:200]) + "\n")
        return 1

    sys.stdout.write("✅ api v1 ns.expect 门禁通过。\n")
    return 0


raise SystemExit(main())
PY

