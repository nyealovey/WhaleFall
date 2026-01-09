---
title: Tasks 任务层编写规范
aliases:
  - tasks-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: "`app/tasks/**` 下所有后台任务函数"
related:
  - "[[standards/backend/task-and-scheduler]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/layer/services-layer-standards]]"
---

# Tasks 任务层编写规范

> [!note] 说明
> Tasks 层承载 APScheduler job 或后台线程触发的任务函数. 任务函数必须确保运行在 Flask `app.app_context()` 内, 业务逻辑调用 Service, 禁止直接查库.

## 目的

- 固化后台任务执行边界(应用上下文, 日志, 失败处理), 避免 "Working outside of application context".
- 保持任务函数 "薄", 让任务本质只是调度入口, 核心逻辑集中在 Service.
- 统一任务的命名, 注册, 可观测性字段, 便于排障与审计.

## 适用范围

- `app/tasks/**` 下所有任务函数, 包括定时任务与手动触发的后台执行.

## 规则(MUST/SHOULD/MAY)

### 1) 应用上下文(强约束)

- MUST: 任何在请求上下文之外运行的任务必须在 `app.app_context()` 内执行.
- MUST: 处理无上下文场景时遵循 [[standards/backend/task-and-scheduler|任务与调度(APScheduler)]] 的做法(必要时创建 app).

### 2) 职责边界

- MUST: 任务函数只负责调度入口, 参数规整, 调用 `app.services.*`, 记录任务日志.
- MUST NOT: 直接访问数据库, 包括 `Model.query`, `db.session`, 原生 SQL.
- MUST NOT: 在任务函数内堆叠复杂业务逻辑(应下沉到 Service).

### 3) 可观测性与敏感数据

- MUST: 使用结构化日志(例如 `get_system_logger()`), 禁止 `print`.
- SHOULD: 日志包含 `task`/`job_id`/`instance_id` 等维度.
- MUST: 遵循 [[standards/backend/sensitive-data-handling|敏感数据处理]] 约束, 禁止把敏感字段写入日志.

### 4) 任务注册

- MUST: 任务注册与调度配置遵循 [[standards/backend/task-and-scheduler]].
- SHOULD: 任务函数保持稳定导入路径, 避免重构导致 scheduler 找不到 callable.

### 5) 命名规范

| 类型 | 命名规则 | 示例 |
|---|---|---|
| 文件 | `{action}_tasks.py` | `accounts_sync_tasks.py` |
| 函数 | `{action}`/`run_{action}` | `sync_accounts`, `run_aggregation` |
| Job ID | `{action}_{frequency}` | `sync_accounts_daily` |

### 6) 代码规模限制

- SHOULD: 单文件 <= 150 行.
- SHOULD: 单任务函数 <= 50 行, 超出则把逻辑下沉到 Service.

## 正反例

### 正例: 兼容有无 app context 的任务模板

```python
from __future__ import annotations

from flask import has_app_context

from app import create_app
from app.services.accounts_sync.accounts_sync_service import accounts_sync_service
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


def sync_accounts(instance_ids: list[int] | None = None) -> dict:
    def _execute() -> dict:
        logger.info(
            "开始账户同步任务",
            module="tasks",
            task="sync_accounts",
            instance_count=len(instance_ids) if instance_ids else "all",
        )
        return accounts_sync_service.sync_batch(instance_ids)

    if has_app_context():
        return _execute()

    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        return _execute()
```

### 反例: 任务里直接查库且无 app context

```python
def bad_task():
    # 反例: 直接 Model.query 且没有 app.app_context
    return Instance.query.count()
```

## 门禁/检查方式

- 评审检查:
  - 任务是否确保在 `app.app_context()` 内执行?
  - 是否存在直接查库或把业务逻辑写在 task 里?
  - 是否使用结构化日志且避免敏感数据?
- 自查命令(示例):

```bash
rg -n "Model\\.query|db\\.session" app/tasks
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
