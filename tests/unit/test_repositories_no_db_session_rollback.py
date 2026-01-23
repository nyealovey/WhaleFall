from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _extract_app_db_names(tree: ast.AST) -> set[str]:
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
        pytest.fail(f"无法解析 Python 文件，rollback 门禁无法执行: {display_path}: {exc}")

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


@pytest.mark.unit
def test_repositories_do_not_call_db_session_rollback() -> None:
    """Write boundary: repositories 层不得回滚整个 session(应由边界入口处理)."""
    repo_root = Path(__file__).resolve().parents[2]
    repositories_root = repo_root / "app" / "repositories"

    matches: list[str] = []
    for path in repositories_root.rglob("*.py"):
        matches.extend(_find_db_session_rollback_calls(path, display_path=path.relative_to(repo_root)))

    assert not matches, "Repositories 层发现 db.session.rollback 漂移:\n" + "\n".join(matches[:50])
