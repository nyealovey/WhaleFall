# Tasks 任务层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/tasks/` 目录下所有后台任务的编写规范

---

## 核心原则

**Tasks = 定时执行 + 调用 Service + 应用上下文**

```python
# ✅ Tasks 职责
- 定义定时/后台任务
- 确保运行在 Flask 应用上下文中
- 调用 Service 执行业务逻辑
- 记录任务执行日志

# ❌ Tasks 禁止
- 直接查询数据库（应通过 Service）
- 包含复杂业务逻辑
- 依赖 Routes/API 层
```

---

## 目录结构

```
tasks/
├── __init__.py
├── accounts_sync_tasks.py        # 账户同步任务
├── capacity_collection_tasks.py  # 容量采集任务
├── capacity_aggregation_tasks.py # 容量聚合任务
├── partition_management_tasks.py # 分区管理任务
└── log_cleanup_tasks.py          # 日志清理任务
```

---

## 任务编写模板

```python
"""账户同步任务."""

from __future__ import annotations

from flask import current_app

from app.services.accounts_sync.accounts_sync_service import accounts_sync_service
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


def sync_accounts(instance_ids: list[int] | None = None) -> dict:
    """执行账户同步任务.

    Args:
        instance_ids: 要同步的实例 ID 列表，None 表示全部.

    Returns:
        任务执行结果.

    """
    # 确保在应用上下文中运行
    with current_app.app_context():
        logger.info(
            "开始账户同步任务",
            module="tasks",
            task="sync_accounts",
            instance_count=len(instance_ids) if instance_ids else "all",
        )

        try:
            result = accounts_sync_service.sync_batch(instance_ids)

            logger.info(
                "账户同步任务完成",
                module="tasks",
                task="sync_accounts",
                success_count=result.get("success_count", 0),
                failed_count=result.get("failed_count", 0),
            )

            return result

        except Exception as exc:
            logger.exception(
                "账户同步任务失败",
                module="tasks",
                task="sync_accounts",
                error=str(exc),
            )
            raise
```

---

## 调度器注册规范

在 `app/scheduler.py` 中注册任务：

```python
from apscheduler.triggers.cron import CronTrigger

from app.tasks.accounts_sync_tasks import sync_accounts
from app.tasks.capacity_aggregation_tasks import run_aggregation


def register_jobs(scheduler, app):
    """注册定时任务."""

    # 账户同步 - 每天凌晨 2 点
    scheduler.add_job(
        func=sync_accounts,
        trigger=CronTrigger(hour=2, minute=0),
        id="sync_accounts_daily",
        name="每日账户同步",
        replace_existing=True,
    )

    # 容量聚合 - 每天凌晨 3 点
    scheduler.add_job(
        func=run_aggregation,
        trigger=CronTrigger(hour=3, minute=0),
        id="capacity_aggregation_daily",
        name="每日容量聚合",
        replace_existing=True,
    )
```

---

## 应用上下文规范

```python
# ✅ 正确：使用 current_app.app_context()
def my_task():
    with current_app.app_context():
        # 任务逻辑
        result = some_service.do_something()
        return result

# ✅ 正确：装饰器方式（如果有）
@with_app_context
def my_task():
    result = some_service.do_something()
    return result

# ❌ 错误：不使用上下文
def my_task():
    result = some_service.do_something()  # 可能报错！
    return result
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| `app.services.*` | 业务服务 |
| `app.utils.*` | 工具函数 |
| `app.constants.*` | 常量 |
| `flask.current_app` | 应用上下文 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.models.*` | 数据模型（通过 Service） |
| `app.repositories.*` | 仓储（通过 Service） |
| `app.routes.*` | 路由层 |
| `app.api.*` | API 层 |

---

## 命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 文件 | `{action}_tasks.py` | `accounts_sync_tasks.py` |
| 函数 | `{action}` 或 `run_{action}` | `sync_accounts`, `run_aggregation` |
| Job ID | `{action}_{frequency}` | `sync_accounts_daily` |

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 150 行 | 拆分为多个文件 |
| 单任务函数行数 | 50 行 | 逻辑移到 Service |

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
