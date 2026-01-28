#!/usr/bin/env bash
# Task 回归门禁：auto_classify_accounts 的 “没有需要分类的账户” 提前返回必须由 `if not accounts:` 分支守护
#
# 参考：
# - docs/Obsidian/standards/backend/gate/layer/tasks-layer.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/account-classification-auto-tasks-guard.sh

Checks:
  - app/tasks/account_classification_auto_tasks.py::auto_classify_accounts
    - 返回 message="没有需要分类的账户" 的 return 只能出现在 `if not accounts:` 分支内
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

DEFAULT_PY_BIN="python3"
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  # CI 默认会通过 uv 创建 .venv；优先使用项目虚拟环境，避免本机 python 版本不一致。
  DEFAULT_PY_BIN="${ROOT_DIR}/.venv/bin/python"
fi
PY_BIN="${PY_BIN:-${DEFAULT_PY_BIN}}"
if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
  echo "未检测到 python3，无法执行 account classification task 门禁检查。" >&2
  exit 1
fi

"${PY_BIN}" - <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path


def _is_no_accounts_return(node: ast.Return) -> bool:
    value = node.value
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "_finalize_run_no_accounts":
        return True
    if not isinstance(value, ast.Dict):
        return False
    for key, val in zip(value.keys, value.values):
        if isinstance(key, ast.Constant) and key.value == "message":
            return isinstance(val, ast.Constant) and val.value == "没有需要分类的账户"
    return False


def _is_if_not_accounts(node: ast.If) -> bool:
    test = node.test
    return (
        isinstance(test, ast.UnaryOp)
        and isinstance(test.op, ast.Not)
        and isinstance(test.operand, ast.Name)
        and test.operand.id == "accounts"
    )


def _find_function(tree: ast.Module, *, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"未找到函数: {name}")


def _find_no_accounts_returns(fn: ast.FunctionDef) -> list[tuple[ast.Return, list[ast.AST]]]:
    found: list[tuple[ast.Return, list[ast.AST]]] = []

    def walk(node: ast.AST, parents: list[ast.AST]) -> None:
        if isinstance(node, ast.Return) and _is_no_accounts_return(node):
            found.append((node, parents))
        for child in ast.iter_child_nodes(node):
            walk(child, [*parents, node])

    walk(fn, [])
    return found


def main() -> int:
    path = Path("app/tasks/account_classification_auto_tasks.py")
    if not path.exists():
        sys.stdout.write("未找到 app/tasks/account_classification_auto_tasks.py，跳过检查。\n")
        return 0

    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    fn = _find_function(tree, name="auto_classify_accounts")

    matches = _find_no_accounts_returns(fn)
    if not matches:
        raise AssertionError("未找到 `message=没有需要分类的账户` 的 return，请确认任务实现是否变更")

    not_guarded_lines = [
        ret.lineno
        for ret, parents in matches
        if not any(isinstance(parent, ast.If) and _is_if_not_accounts(parent) for parent in parents)
    ]
    if not_guarded_lines:
        raise AssertionError(
            "发现 `没有需要分类的账户` 的 return 不在 `if not accounts:` 分支内，"
            f"可能导致误判并跳过分类逻辑：{path}:{not_guarded_lines}"
        )

    sys.stdout.write("✅ account classification task 门禁通过。\n")
    return 0


try:
    raise SystemExit(main())
except AssertionError as exc:
    sys.stderr.write(f"{exc}\n")
    raise SystemExit(1)
PY
