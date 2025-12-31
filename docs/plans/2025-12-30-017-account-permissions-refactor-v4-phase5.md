# Account Permissions Refactor V4 - Phase 5 Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 删除 legacy account classification 分类器代码，并确保分类规则评估仅支持 DSL v4（Fail-closed）。

**Architecture:** `AccountClassificationService._evaluate_rule()` 仅评估 DSL v4 表达式；非 v4 表达式统一视为“不支持/不匹配”(返回 `False`) 并记录日志。删除 legacy 分类器包与其单测/文档引用，避免误用与维护成本。

**Tech Stack:** Python (Flask), SQLAlchemy, pytest.

---

### Task 1: 为“legacy 表达式不再支持”增加单测门禁

**Files:**
- Modify: `tests/unit/services/test_account_classification_orchestrator_dsl_guard.py`

**Step 1: Write the failing test**

在同文件增加一个 legacy 表达式用例（version != 4 / 不含 `expr` 结构），并构造一个会被旧分类器命中的账户权限，断言 `_evaluate_rule()` 返回 `False`：

```python
@pytest.mark.unit
def test_orchestrator_skips_legacy_rule_expressions() -> None:
    class _StubRule:
        db_type = "mysql"

        @staticmethod
        def get_rule_expression() -> dict:
            return {"operator": "OR", "global_privileges": ["SELECT"]}

    class _StubAccount:
        def get_permissions_by_db_type(self) -> dict[str, object]:
            return {"global_privileges": ["SELECT"]}

    assert AccountClassificationService()._evaluate_rule(_StubAccount(), _StubRule()) is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_orchestrator_dsl_guard.py -q`
Expected: FAIL（当前仍会走 legacy classifier 路径，返回 True 或触发 legacy 评估）

---

### Task 2: 移除 orchestrator 对 legacy classifier 的依赖

**Files:**
- Modify: `app/services/account_classification/orchestrator.py`

**Step 1: Write minimal implementation**

- 删除 `from .classifiers import ClassifierFactory` 与构造参数/属性 `classifier_factory`
- `_evaluate_rule()` 在非 DSL v4 时直接返回 `False`（并记录 “跳过 legacy 规则评估/不支持” 日志）

**Step 2: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_orchestrator_dsl_guard.py -q`
Expected: PASS

---

### Task 3: 删除 legacy classifiers 包与对应单测/文档引用

**Files:**
- Delete: `app/services/account_classification/classifiers/`（全部 python 源文件）
- Delete: `tests/unit/services/test_rule_classifiers_operator_semantics.py`
- Modify: `docs/reference/api/services-utils-documentation.md`

**Step 1: Delete code and update docs**

- 移除 `services-utils-documentation.md` 中关于 `app/services/account_classification/classifiers/*` 的条目章节

**Step 2: Quick sanity search**

Run: `rg "ClassifierFactory|account_classification\\.classifiers" -n`
Expected: 无结果（或仅剩历史 plan/变更文档中的文字描述）

---

### Task 4: 更新进度文档勾选 Phase 5

**Files:**
- Modify: `docs/changes/refactor/017-account-permissions-refactor-v4-progress.md`

**Step 1: Mark checklist**

- 勾选 Phase 5 两项：
  - 删除 legacy 分类器代码
  - 删除 `PERMISSION_FIELDS` 在分类器侧的引用（若存在；本阶段通过搜索确认不存在）

---

### Task 5: 回归验证

**Step 1: Run unit tests**

Run: `uv run pytest -m unit`
Expected: PASS

