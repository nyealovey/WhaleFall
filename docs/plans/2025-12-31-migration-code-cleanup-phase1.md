# Migration Code Cleanup Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: 权限快照/分类 DSL 迁移清理
> 关联: docs/changes/refactor/020-migration-code-cleanup-plan.md; docs/changes/refactor/020-migration-code-cleanup-progress.md

**Goal:** Remove permission snapshot backfill + legacy classification DSL compatibility, and enforce fail-fast on legacy formats.

**Architecture:** Tighten snapshot validation at service boundaries, remove backfill branches, and make classification DSL v4 the only accepted rule format. Replace silent skips with explicit AppError/ValidationError so callers fail fast.

**Tech Stack:** Python, Flask services, pytest, SQLAlchemy.

### Task 1: Add fail-fast tests for missing snapshots and legacy rules

**Files:**
- Modify: `tests/unit/services/test_permission_snapshot_view.py:1`
- Modify: `tests/unit/services/test_account_permission_manager.py:1`
- Modify: `tests/unit/services/test_account_classification_orchestrator_dsl_guard.py:1`

**Step 1: Write failing tests for snapshot view**

```python
import pytest

from app.errors import AppError
from app.services.accounts_permissions import snapshot_view


def test_permission_snapshot_view_raises_when_missing() -> None:
    class _StubAccount:
        permission_snapshot = None

    with pytest.raises(AppError) as excinfo:
        snapshot_view.build_permission_snapshot_view(_StubAccount())

    assert excinfo.value.message_key == "SNAPSHOT_MISSING"
```

**Step 2: Write failing tests for permission sync when snapshot missing**

```python
import pytest
from types import SimpleNamespace

from app.errors import AppError
from app.services.accounts_sync.permission_manager import AccountPermissionManager, SyncContext


def test_process_existing_permission_raises_when_snapshot_missing() -> None:
    manager = AccountPermissionManager()
    record = SimpleNamespace(
        db_type="mysql",
        is_superuser=False,
        is_locked=False,
        permission_snapshot=None,
        last_sync_time=None,
    )
    remote = {"permissions": {"global_privileges": ["SELECT"]}}
    snapshot = manager._extract_remote_context(remote)
    context = SyncContext(
        instance=SimpleNamespace(id=1, name="test", db_type="mysql"),
        username="demo",
        session_id=None,
    )

    with pytest.raises(AppError) as excinfo:
        manager._process_existing_permission(record, snapshot, context)

    assert excinfo.value.message_key == "SNAPSHOT_MISSING"
```

**Step 3: Write failing test for instance_account_id missing**

```python
import pytest
from types import SimpleNamespace

from app.errors import AppError
from app.models.account_permission import AccountPermission
from app.services.accounts_sync.permission_manager import AccountPermissionManager


def test_find_permission_record_raises_when_instance_account_id_missing(monkeypatch) -> None:
    manager = AccountPermissionManager()
    record = SimpleNamespace(instance_account_id=None)

    class _Query:
        def __init__(self):
            self._last = {}

        def filter_by(self, **kwargs):
            self._last = kwargs
            return self

        def first(self):
            if "instance_account_id" in self._last:
                return None
            return record

    monkeypatch.setattr(AccountPermission, "query", _Query())

    instance = SimpleNamespace(id=1, db_type="mysql")
    account = SimpleNamespace(id=10, username="demo")

    with pytest.raises(AppError) as excinfo:
        manager._find_permission_record(instance, account)

    assert excinfo.value.message_key == "SYNC_DATA_ERROR"
```

**Step 4: Write failing tests for classification DSL strictness**

```python
import pytest

from app.errors import ValidationError
from app.services.account_classification.orchestrator import AccountClassificationService


def test_orchestrator_accepts_dsl_v4_rules() -> None:
    class _StubRule:
        db_type = "mysql"

        @staticmethod
        def get_rule_expression() -> dict:
            return {
                "version": 4,
                "expr": {"fn": "has_capability", "args": {"name": "SUPERUSER"}},
            }

    class _StubAccount:
        permission_facts = {"capabilities": ["SUPERUSER"]}

    assert AccountClassificationService()._evaluate_rule(_StubAccount(), _StubRule()) is True


def test_orchestrator_rejects_legacy_rule_expressions() -> None:
    class _StubRule:
        db_type = "mysql"

        @staticmethod
        def get_rule_expression() -> dict:
            return {"operator": "OR", "global_privileges": ["SELECT"]}

    class _StubAccount:
        permission_facts = {}

    with pytest.raises(ValidationError):
        AccountClassificationService()._evaluate_rule(_StubAccount(), _StubRule())
```

**Step 5: Run tests to verify they fail**

Run:
- `uv run pytest -m unit tests/unit/services/test_permission_snapshot_view.py::test_permission_snapshot_view_raises_when_missing -v`
- `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py::test_process_existing_permission_raises_when_snapshot_missing -v`
- `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py::test_find_permission_record_raises_when_instance_account_id_missing -v`
- `uv run pytest -m unit tests/unit/services/test_account_classification_orchestrator_dsl_guard.py::test_orchestrator_accepts_dsl_v4_rules -v`
- `uv run pytest -m unit tests/unit/services/test_account_classification_orchestrator_dsl_guard.py::test_orchestrator_rejects_legacy_rule_expressions -v`

Expected: FAIL, because production code still accepts legacy formats.

### Task 2: Enforce strict permission snapshot behavior (no backfill)

**Files:**
- Modify: `app/services/accounts_permissions/snapshot_view.py:1`
- Modify: `app/services/accounts_sync/permission_manager.py:300`
- Modify: `app/services/instances/instance_accounts_service.py:50`
- Modify: `app/services/ledgers/accounts_ledger_permissions_service.py:20`

**Step 1: Implement strict snapshot view**

```python
from app.constants import ErrorCategory, ErrorSeverity, HttpStatus
from app.errors import AppError


def build_permission_snapshot_view(account: AccountPermission) -> dict[str, Any]:
    snapshot = getattr(account, "permission_snapshot", None)
    if isinstance(snapshot, dict) and snapshot.get("version") == 4:
        return snapshot

    raise AppError(
        message_key="SNAPSHOT_MISSING",
        status_code=HttpStatus.CONFLICT,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
    )
```

**Step 2: Remove backfill branches in permission manager**

```python
from app.constants import ErrorCategory, ErrorSeverity, HttpStatus
from app.errors import AppError


def _find_permission_record(...):
    existing = AccountPermission.query.filter_by(instance_account_id=account.id).first()
    if existing:
        return existing
    existing = AccountPermission.query.filter_by(
        instance_id=instance.id,
        db_type=instance.db_type,
        username=account.username,
    ).first()
    if existing and not existing.instance_account_id:
        raise AppError(
            message_key="SYNC_DATA_ERROR",
            status_code=HttpStatus.CONFLICT,
            category=ErrorCategory.BUSINESS,
            severity=ErrorSeverity.MEDIUM,
            message="权限记录缺少 instance_account_id, 请先完成数据回填",
        )
    return existing
```

```python
# In _process_existing_permission, remove _needs_snapshot_backfill branch.
if not bool(diff.get("changed")):
    self._mark_synced(record)
    return SyncOutcome(skipped=1)

# Remove _needs_snapshot_backfill method entirely.
```

**Step 3: Remove SNAPSHOT_MISSING checks in services**

```python
# instance_accounts_service.py
snapshot = build_permission_snapshot_view(account)
# remove SNAPSHOT_MISSING conditional; let AppError bubble
```

```python
# accounts_ledger_permissions_service.py
snapshot = build_permission_snapshot_view(account)
# remove SNAPSHOT_MISSING conditional; let AppError bubble
```

**Step 4: Run tests to verify they pass**

Run:
- `uv run pytest -m unit tests/unit/services/test_permission_snapshot_view.py::test_permission_snapshot_view_raises_when_missing -v`
- `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py::test_process_existing_permission_raises_when_snapshot_missing -v`
- `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py::test_find_permission_record_raises_when_instance_account_id_missing -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/services/accounts_permissions/snapshot_view.py \
  app/services/accounts_sync/permission_manager.py \
  app/services/instances/instance_accounts_service.py \
  app/services/ledgers/accounts_ledger_permissions_service.py \
  tests/unit/services/test_permission_snapshot_view.py \
  tests/unit/services/test_account_permission_manager.py

git commit -m "refactor: enforce strict permission snapshot"
```

### Task 3: Remove DSL v4 feature flag and legacy rule compatibility

**Files:**
- Modify: `app/services/account_classification/orchestrator.py:1`
- Modify: `app/settings.py:60`
- Modify: `env.example:60`
- Delete: `app/services/account_classification/flags.py`
- Modify: `tests/unit/services/test_account_classification_orchestrator_dsl_guard.py:1`

**Step 1: Update orchestrator to fail-fast on legacy rules**

```python
from app.errors import ValidationError
from app.services.account_classification.dsl_v4 import (
    DslV4Evaluator,
    collect_dsl_v4_validation_errors,
    is_dsl_v4_expression,
)

rule_expression = rule.get_rule_expression()
if not rule_expression:
    return False

if not is_dsl_v4_expression(rule_expression):
    raise ValidationError("rule_expression 仅支持 DSL v4")

errors = collect_dsl_v4_validation_errors(rule_expression)
if errors:
    raise ValidationError("rule_expression 非法: " + "; ".join(errors))

facts = self._get_permission_facts(account)
return DslV4Evaluator(facts=facts).evaluate(rule_expression).matched
```

**Step 2: Remove settings flag and env example**

```python
# app/settings.py
# delete DEFAULT_ACCOUNT_CLASSIFICATION_DSL_V4
# remove account_classification_dsl_v4 field
# replace _load_account_permission_flags with a mysql-only loader

def _load_account_permission_flags() -> tuple[bool]:
    mysql_enable_role_closure = _parse_bool(
        os.environ.get("MYSQL_ENABLE_ROLE_CLOSURE"),
        default=DEFAULT_MYSQL_ENABLE_ROLE_CLOSURE,
    )
    return (mysql_enable_role_closure,)
```

```python
# Settings.load
(mysql_enable_role_closure,) = _load_account_permission_flags()
# remove account_classification_dsl_v4 from Settings constructor and to_flask_config
```

```bash
# env.example: remove ACCOUNT_CLASSIFICATION_DSL_V4
```

**Step 3: Remove flag helper file**

```bash
rm app/services/account_classification/flags.py
```

**Step 4: Run tests to verify they pass**

Run:
- `uv run pytest -m unit tests/unit/services/test_account_classification_orchestrator_dsl_guard.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/services/account_classification/orchestrator.py \
  app/settings.py env.example \
  tests/unit/services/test_account_classification_orchestrator_dsl_guard.py

git rm app/services/account_classification/flags.py

git commit -m "refactor: drop dsl v4 flag and legacy rules"
```
