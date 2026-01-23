from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _is_no_accounts_return(node: ast.Return) -> bool:
    """识别 `return {..., "message": "没有需要分类的账户", ...}`."""
    value = node.value
    if not isinstance(value, ast.Dict):
        return False

    for key, val in zip(value.keys, value.values, strict=False):
        if isinstance(key, ast.Constant) and key.value == "message":
            return isinstance(val, ast.Constant) and val.value == "没有需要分类的账户"
    return False


def _is_if_not_accounts(node: ast.If) -> bool:
    """识别 `if not accounts:`."""
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


@pytest.mark.unit
def test_auto_classify_accounts_no_accounts_return_must_be_guarded_by_accounts_check() -> None:
    """防回归：`没有需要分类的账户` 的提前返回必须只发生在 `if not accounts:` 分支内."""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app" / "tasks" / "account_classification_auto_tasks.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = _find_function(tree, name="auto_classify_accounts")

    matches = _find_no_accounts_returns(fn)
    assert matches, "未找到 `message=没有需要分类的账户` 的 return，请确认任务实现是否变更"

    not_guarded_lines = [
        ret.lineno
        for ret, parents in matches
        if not any(isinstance(parent, ast.If) and _is_if_not_accounts(parent) for parent in parents)
    ]
    assert not not_guarded_lines, (
        "发现 `没有需要分类的账户` 的 return 不在 `if not accounts:` 分支内，"
        f"可能导致误判并跳过分类逻辑：{path.relative_to(repo_root)}:{not_guarded_lines}"
    )

