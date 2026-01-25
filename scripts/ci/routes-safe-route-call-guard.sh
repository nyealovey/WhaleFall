#!/usr/bin/env bash
# Routes 门禁：含 route 定义的模块必须使用 safe_route_call（统一事务边界/错误封套）
#
# 参考：
# - docs/Obsidian/standards/backend/standard/write-operation-boundary.md
# - docs/Obsidian/standards/backend/gate/layer/routes-layer.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/routes-safe-route-call-guard.sh

Checks:
  - app/routes/**/*.py：凡包含 `.route(...)` / `.add_url_rule(...)` 的模块，必须调用 `safe_route_call(...)`
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/routes"

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

PY_BIN="${PY_BIN:-python3}"
if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
  echo "未检测到 python3，无法执行 routes safe_route_call 门禁检查。" >&2
  exit 1
fi

cd "${ROOT_DIR}"

"${PY_BIN}" - <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path


ROUTE_CALL_ATTRS = {"route", "add_url_rule"}


def _declares_routes(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in ROUTE_CALL_ATTRS:
            return True
    return False


def _uses_safe_route_call(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "safe_route_call":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "safe_route_call":
            return True
    return False


def main() -> int:
    repo_root = Path.cwd()
    routes_root = repo_root / "app" / "routes"
    missing: list[str] = []
    parse_errors: list[str] = []

    for path in sorted(routes_root.rglob("*.py")):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            rel = path.relative_to(repo_root)
            parse_errors.append(f"{rel}: {exc}")
            continue

        if not _declares_routes(tree):
            continue
        if _uses_safe_route_call(tree):
            continue
        missing.append(str(path.relative_to(repo_root)))

    if parse_errors:
        sys.stderr.write("routes 模块语法错误，无法执行门禁检查：\n")
        sys.stderr.write("\n".join(f"- {item}" for item in parse_errors[:20]) + "\n")
        return 1

    if missing:
        sys.stderr.write("发现未使用 safe_route_call 的 routes 模块（禁止）：\n")
        sys.stderr.write("\n".join(f"- {item}" for item in sorted(missing)) + "\n")
        return 1

    sys.stdout.write("✅ routes safe_route_call 门禁通过。\n")
    return 0


raise SystemExit(main())
PY
