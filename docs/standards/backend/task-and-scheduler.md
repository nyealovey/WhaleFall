# 任务与调度（APScheduler）

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：`app/scheduler.py`、`app/tasks/**`、调度器管理路由与后台线程

## 目的

- 统一后台任务的执行边界（应用上下文、日志、失败隔离），避免出现 `Working outside of application context`。
- 确保调度器在多进程环境下保持单实例执行，避免重复跑任务造成数据破坏。

## 适用范围

- APScheduler 定时任务（job）与其绑定的任务函数（`app/tasks/**`）。
- 通过路由触发的“后台执行”（批量、采集、聚合等）。
- 后台线程（例如日志队列 worker）需要使用 Flask `app.app_context()` 的场景。

## 规则（MUST/SHOULD/MAY）

### 1) 应用上下文（强约束）

- MUST：任何在请求上下文之外运行的任务函数必须在 `app.app_context()` 中执行。
- MUST：若复用 `current_app`，必须先判断 `has_app_context()`；否则创建新应用并包裹上下文：
  - `create_app(init_scheduler_on_start=False)`
  - `with app.app_context(): ...`

### 2) 调度器单实例（强约束）

- MUST：调度器必须通过文件锁保持单实例运行（当前实现位于 `app/scheduler.py`）。
- MUST：当环境变量 `ENABLE_SCHEDULER` 明确禁用时不得启动调度器。
- SHOULD：在 gunicorn 或 Flask reloader 场景中，遵循现有实现的“子进程/单实例”策略，避免重复初始化。

### 3) 任务注册与配置（强约束）

- MUST：新增任务需同时更新：
  - `app/scheduler.py` 的 `TASK_FUNCTIONS`（注册任务名到可导入的函数路径）
  - `app/config/scheduler_tasks.yaml`（新增/调整默认 job 配置）
- SHOULD：任务函数保持稳定的导入路径，避免重构导致调度器找不到 callable。

### 4) 可观测性与失败处理

- MUST：任务必须使用结构化日志（`get_system_logger()` 或模块 logger），禁止 `print`。
- SHOULD：任务日志包含 `job_id/task_name` 等维度，便于在日志中心过滤。
- SHOULD：任务失败时只记录必要诊断信息，避免把敏感数据写入日志（详见 [敏感数据处理](./sensitive-data-handling.md)）。

## 正反例

### 正例：无上下文时创建应用并包裹执行

```python
from flask import has_app_context

from app import create_app


def run_task() -> None:
    if has_app_context():
        _execute()
        return

    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        _execute()
```

### 反例：在后台线程直接访问数据库

- 后台线程/任务直接调用 `Model.query...`，但未进入 `app.app_context()`，会触发上下文错误或拿到错误配置。

## 门禁/检查方式

- 评审检查：
  - 新增任务是否同时更新 `TASK_FUNCTIONS` 与 `scheduler_tasks.yaml`？
  - 是否在无 app context 场景里安全地创建 app 并包裹？
- 运行期观察：通过调度器页面/日志中心确认任务未重复执行（同一时间窗口只有一个进程持锁）。

## 变更历史

- 2025-12-25：新增标准文档，固化 app context、单实例锁与任务注册配置要求。
