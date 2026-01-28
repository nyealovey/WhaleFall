#!/usr/bin/env bash
# db.session.rollback 门禁：services/repositories 禁止 rollback；infra 仅允许 entrypoints
#
# 参考：
# - docs/Obsidian/standards/backend/standard/write-operation-boundary.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/db-session-rollback-allowlist-guard.sh

Checks:
  - app/services/**/*.py 禁止调用 db.session.rollback（含 `session = db.session` alias）
  - app/repositories/**/*.py 禁止调用 db.session.rollback（含 alias）
  - app/infra/**/*.py 仅允许：
    - app/infra/route_safety.py
    - app/infra/logging/queue_worker.py
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
  echo "未检测到 python3，无法执行 rollback allowlist 门禁检查。" >&2
  exit 1
fi

"${PY_BIN}" - <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path


ALLOWED_INFRA_ROLLBACK_FILES = {
    Path("app/infra/route_safety.py"),
    Path("app/infra/logging/queue_worker.py"),
}


def _extract_app_db_names(tree: ast.AST) -> set[str]:
    """提取本模块中可能表示 `app.db` 的名字集合（支持 `from app import db as xxx`）。"""
    names = {"db"}
    if not isinstance(tree, ast.Module):
        return names
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "app":
            continue
        for alias in node.names:
            if alias.name == "db":
                names.add(alias.asname or alias.name)
    return names


def _is_db_session(node: ast.AST, *, db_names: set[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "session"
        and isinstance(node.value, ast.Name)
        and node.value.id in db_names
    )


def _collect_db_session_aliases(body: list[ast.stmt], *, db_names: set[str]) -> set[str]:
    """收集 `session = db.session` 这类别名（不做复杂数据流分析）。"""

    def iter_child_bodies(stmt: ast.stmt) -> list[list[ast.stmt]]:
        if isinstance(stmt, ast.If):
            return [stmt.body, stmt.orelse]
        if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            return [stmt.body, stmt.orelse]
        if isinstance(stmt, ast.With):
            return [stmt.body]
        if isinstance(stmt, ast.AsyncWith):
            return [stmt.body]
        if isinstance(stmt, ast.Try):
            bodies: list[list[ast.stmt]] = [stmt.body, stmt.orelse, stmt.finalbody]
            bodies.extend(handler.body for handler in stmt.handlers)
            return bodies
        if isinstance(stmt, ast.Match):
            return [case.body for case in stmt.cases]
        return []

    aliases: set[str] = set()
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        value: ast.AST | None = None
        targets: list[ast.AST] = []
        if isinstance(stmt, ast.Assign):
            value = stmt.value
            targets = list(stmt.targets)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            value = stmt.value
            targets = [stmt.target]

        if value is not None and _is_db_session(value, db_names=db_names):
            for target in targets:
                if isinstance(target, ast.Name):
                    aliases.add(target.id)

        for child_body in iter_child_bodies(stmt):
            aliases.update(_collect_db_session_aliases(child_body, db_names=db_names))
    return aliases


def _find_db_session_rollback_calls(path: Path, *, display_path: Path) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return [f"{display_path}: SYNTAX_ERROR {exc}"]

    db_names = _extract_app_db_names(tree)
    module_aliases = _collect_db_session_aliases(getattr(tree, "body", []), db_names=db_names)

    matches: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.alias_stack: list[set[str]] = [set(module_aliases)]

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            local_aliases = _collect_db_session_aliases(node.body, db_names=db_names)
            self.alias_stack.append(set(module_aliases) | local_aliases)
            self.generic_visit(node)
            self.alias_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            local_aliases = _collect_db_session_aliases(node.body, db_names=db_names)
            self.alias_stack.append(set(module_aliases) | local_aliases)
            self.generic_visit(node)
            self.alias_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "rollback":
                aliases = self.alias_stack[-1]
                if _is_db_session(func.value, db_names=db_names):
                    matches.append(f"{display_path}:{node.lineno}: db.session.rollback()")
                elif isinstance(func.value, ast.Name) and func.value.id in aliases:
                    matches.append(f"{display_path}:{node.lineno}: {func.value.id}.rollback()")
            self.generic_visit(node)

    Visitor().visit(tree)
    return matches


def _scan_tree(root: Path, *, repo_root: Path) -> list[str]:
    return [
        match
        for path in sorted(root.rglob("*.py"))
        for match in _find_db_session_rollback_calls(path, display_path=path.relative_to(repo_root))
    ]


def main() -> int:
    repo_root = Path.cwd()

    # 1) services/repositories: strict deny
    deny_hits: list[str] = []
    for rel_root in (Path("app/services"), Path("app/repositories")):
        abs_root = repo_root / rel_root
        if not abs_root.exists():
            continue
        deny_hits.extend(_scan_tree(abs_root, repo_root=repo_root))

    if deny_hits:
        sys.stderr.write("检测到 services/repositories 调用 db.session.rollback（禁止）：\n")
        sys.stderr.write("\n".join(f"- {item}" for item in deny_hits[:80]) + "\n")
        return 1

    # 2) infra: allowlist only
    infra_root = repo_root / "app/infra"
    if infra_root.exists():
        infra_hits: list[str] = []
        for path in sorted(infra_root.rglob("*.py")):
            rel = path.relative_to(repo_root)
            if rel in ALLOWED_INFRA_ROLLBACK_FILES:
                continue
            infra_hits.extend(_find_db_session_rollback_calls(path, display_path=rel))

        if infra_hits:
            sys.stderr.write("检测到 infra 非允许位置调用 db.session.rollback（禁止）：\n")
            sys.stderr.write("\n".join(f"- {item}" for item in infra_hits[:80]) + "\n")
            sys.stderr.write("\n允许位置：\n")
            sys.stderr.write("\n".join(f"- {item}" for item in sorted(ALLOWED_INFRA_ROLLBACK_FILES)) + "\n")
            return 1

    sys.stdout.write("✅ rollback allowlist 门禁通过。\n")
    return 0


raise SystemExit(main())
PY
