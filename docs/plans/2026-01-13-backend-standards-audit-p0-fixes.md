# Backend Standards Audit P0 Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 `docs/reports/2026-01-13-backend-standards-audit-report.md` 中 P0 违规项，避免 internal payload 形状兼容链散落在 Service，以及连接测试结果缺失 `message` 导致口径漂移。

**Architecture:** 新增 internal contract adapter/normalizer（schema 层单入口）对 `permission_snapshot(v4)` 做一次 canonicalization（重点收敛 roles 形状兼容），并让 `facts_builder` 只消费 canonical 形状；同时统一 `connection_adapters/*_adapter.py` 的 `test_connection()` 失败返回结构，保证始终包含 `message` 字段。

**Tech Stack:** Python, pytest(`-m unit`), Ruff, Pyright, Pydantic(v2).

---

### Task 1: 新增 `permission_snapshot(v4)` 的 adapter/normalizer（单入口）

**Files:**
- Create: `app/schemas/internal_contracts/__init__.py`
- Create: `app/schemas/internal_contracts/permission_snapshot_v4.py`
- Modify: `app/services/accounts_permissions/facts_builder.py:140`
- Test: `tests/unit/schemas/test_permission_snapshot_v4_internal_contract.py`

**Step 1: 写 failing test（覆盖 canonical + 历史形状）**

```python
import pytest

from app.schemas.internal_contracts.permission_snapshot_v4 import normalize_permission_snapshot_categories_v4


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ([{"name": "sysadmin"}], ["sysadmin"]),
        (["sysadmin"], ["sysadmin"]),
    ],
)
def test_normalize_permission_snapshot_categories_v4_sqlserver_server_roles(raw, expected):
    categories = {"server_roles": raw}
    normalized = normalize_permission_snapshot_categories_v4("sqlserver", categories)
    assert normalized["server_roles"] == expected
```

**Step 2: 运行测试，确认失败**

Run: `uv run pytest -m unit tests/unit/schemas/test_permission_snapshot_v4_internal_contract.py -v`
Expected: FAIL（module/function not found）

**Step 3: 实现 normalizer（只做一次 canonicalization）**

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

JsonDict = dict[str, Any]


def _normalize_str_list(value: object, *, dict_key: str | None = None) -> list[str]:
    ...


def normalize_permission_snapshot_categories_v4(db_type: str, categories: Mapping[str, object]) -> JsonDict:
    # 只在这里做形状兼容与类型规整；业务层消费 canonical 形状
    ...
```

**Step 4: 运行测试，确认通过**

Run: `uv run pytest -m unit tests/unit/schemas/test_permission_snapshot_v4_internal_contract.py -v`
Expected: PASS

---

### Task 2: `facts_builder` 仅消费 canonical 形状（移除 Service 内兼容链）

**Files:**
- Modify: `app/services/accounts_permissions/facts_builder.py:140`
- Test: `tests/unit/services/test_permission_facts_builder.py`

**Step 1: 将 roles 相关兼容逻辑替换为 normalizer 调用**

目标：删除 `facts_builder.py:148/153/161/163/170` 的 `or` 兜底链，让 `_extract_roles(...)` 只读取已规范化的 list[str]。

伪代码：

```python
from app.schemas.internal_contracts.permission_snapshot_v4 import normalize_permission_snapshot_categories_v4


def build_permission_facts(...):
    ...
    categories = _resolve_categories(snapshot, errors)
    categories = normalize_permission_snapshot_categories_v4(db_type, categories)
    roles = _extract_roles(db_type, categories)
    ...
```

**Step 2: 运行既有单测确保行为不回归**

Run: `uv run pytest -m unit tests/unit/services/test_permission_facts_builder.py -v`
Expected: PASS

---

### Task 3: 修复 connection adapters 的 `test_connection` 失败结果缺失 `message`

**Files:**
- Modify: `app/services/connection_adapters/adapters/mysql_adapter.py:98`
- Modify: `app/services/connection_adapters/adapters/postgresql_adapter.py:94`
- Modify: `app/services/connection_adapters/adapters/sqlserver_adapter.py:151`
- Modify: `app/services/connection_adapters/adapters/oracle_adapter.py:146`
- Test: `tests/unit/services/test_connection_factory_test_connection_contract.py`

**Step 1: 写 failing test（失败分支必须包含 message）**

```python
import pytest

from app.services.connection_adapters.adapters.mysql_adapter import MySQLConnection


class _StubInstance:
    id = 1
    host = "127.0.0.1"
    port = 3306
    database_name = None
    credential = None


@pytest.mark.unit
def test_mysql_adapter_test_connection_failure_includes_message(monkeypatch):
    conn = MySQLConnection(_StubInstance())
    monkeypatch.setattr(conn, "connect", lambda: False)
    monkeypatch.setattr(conn, "disconnect", lambda: None)
    result = conn.test_connection()
    assert result["success"] is False
    assert isinstance(result.get("message"), str) and result["message"]
```

**Step 2: 运行测试，确认失败**

Run: `uv run pytest -m unit tests/unit/services/test_connection_factory_test_connection_contract.py -v`
Expected: FAIL（message missing）

**Step 3: 实现：统一失败结果最小结构**

实现目标：
- 失败：`{"success": False, "message": "...", "error": "...(optional)"}`（`error` 保留诊断信息）
- 成功：维持原有 `message/database_version` 字段

**Step 4: 运行测试，确认通过**

Run: `uv run pytest -m unit tests/unit/services/test_connection_factory_test_connection_contract.py -v`
Expected: PASS

---

### Task 4: 回归验证（unit + ruff/typecheck）

**Files:**
- (none)

**Step 1: 跑 unit**

Run: `uv run pytest -m unit`
Expected: PASS

**Step 2: 跑 ruff / pyright（若仓库门禁要求）**

Run:
- `./scripts/ci/ruff-report.sh style`
- `./scripts/ci/pyright-report.sh`
Expected: PASS（若 `pyright` 仅命中 `tests/unit/**`，按报告说明另行处理 baseline）

