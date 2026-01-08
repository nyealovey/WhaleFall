# Accounts Sync Actions Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `POST /api/v1/instances/*/actions/sync-accounts` 的“动作编排逻辑”下沉到 `app/services/accounts_sync`，让路由层只负责鉴权/封套，业务逻辑由 service 层承载。

**Architecture:** 新增 `AccountsSyncActionsService`（无状态编排服务），负责：
- 校验“是否存在活跃实例”
- 触发后台全量同步（返回 `session_id`）
- 触发单实例同步并标准化返回结构（`status/message/success`）

路由层 `app/api/v1/namespaces/instances_accounts_sync.py` 仅保留：参数解析、`safe_call`、封套返回与权限/CSRF 装饰器。

**Tech Stack:** Flask-RESTX、SQLAlchemy、pytest（unit）。

---

### Task 1: 定义 Actions Service 的公共接口

**Files:**
- Create: `app/services/accounts_sync/accounts_sync_actions_service.py`

**Step 1: 写一个最小的 service 骨架**

```python
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True, slots=True)
class AccountsSyncActionResult:
    success: bool
    message: str
    result: dict[str, Any]

class AccountsSyncActionsService:
    def trigger_background_full_sync(...): ...
    def sync_instance_accounts(...): ...
```

**Step 2: 约束返回结构**

确保 `sync_instance_accounts()` 返回 `AccountsSyncActionResult.result` 至少包含：
- `status`: `"completed"` 或 `"failed"`
- `message`: string
- `success`: boolean

---

### Task 2: 下沉“全量同步触发”逻辑

**Files:**
- Modify: `app/api/v1/namespaces/instances_accounts_sync.py`
- Create: `app/services/accounts_sync/accounts_sync_actions_service.py`
- Test: `tests/unit/routes/test_api_v1_accounts_sync_contract.py`

**Step 1: 在 service 中实现 active instances 校验 + 启动线程**

```python
def trigger_background_full_sync(self, *, created_by: int | None) -> str:
    active_count = Instance.query.filter_by(is_active=True).count()
    if active_count == 0:
        raise ValidationError("没有找到活跃的数据库实例")
    session_id = str(uuid4())
    threading.Thread(target=..., args=(created_by, session_id), daemon=True).start()
    return session_id
```

**Step 2: 路由改为调用 service**

路由 `POST /api/v1/instances/actions/sync-accounts`：
- 调用 `AccountsSyncActionsService().trigger_background_full_sync(created_by=...)`
- 返回 `data.session_id`

**Step 3: 更新单测 monkeypatch 点**

单测不再 patch 路由模块的 `_launch_background_sync`，改 patch service 内部启动线程的实现点（例如注入启动函数/或 patch service 方法本身）。

---

### Task 3: 下沉“单实例同步”逻辑并标准化 result

**Files:**
- Modify: `app/api/v1/namespaces/instances_accounts_sync.py`
- Create: `app/services/accounts_sync/accounts_sync_actions_service.py`
- Test: `tests/unit/routes/test_api_v1_accounts_sync_contract.py`

**Step 1: 在 service 中实现 instance 获取 + 调用 `accounts_sync_service.sync_accounts`**

```python
def sync_instance_accounts(self, *, instance_id: int, sync_service: Any) -> AccountsSyncActionResult:
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        raise NotFoundError("实例不存在")
    raw = sync_service.sync_accounts(instance, sync_type=SyncOperationType.MANUAL_SINGLE.value)
    # normalize -> status/message/success
    ...
```

**Step 2: 路由改为只做封套与状态码选择**

- success: 200 + `data.result`
- failure: 400 + `error_message(..., extra={"result": normalized, "instance_id": ...})`

---

### Task 4: 运行并验证单测

**Step 1: 只跑相关测试**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_sync_contract.py -q`

Expected: PASS

