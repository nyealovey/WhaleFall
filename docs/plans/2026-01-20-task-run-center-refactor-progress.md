# TaskRun Center Refactor Progress

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 将 `/history/sessions` 从“同步会话中心”升级为“通用任务运行中心”，以 `TaskRun/TaskRunItem` 统一承载后台任务观测面，并将关键任务入口统一改为异步返回 `run_id`。

**Spec:** `docs/plans/2026-01-19-task-run-center-refactor-design.md`

**Tech Stack:** Flask / Flask-RESTX / SQLAlchemy / Alembic / Grid.js / Vanilla JS

## 进度表（按执行顺序）

| 阶段 | 任务 | 关键输出 | 验证方式 | 状态 |
| --- | --- | --- | --- | --- |
| P0 | 对齐范围与清单（含必须覆盖的 4 个按钮 + scheduler 4 个 job） | 变更清单 & 风险点 | `rg -n "session_id" app` 命中收敛 | TODO |
| P1 | 新增数据模型与迁移：`task_runs/task_run_items` | 2 张表 + index/unique/check | `uv run pytest -m unit` | TODO |
| P2 | Write Service：`TaskRunsWriteService`（run/items 状态流转、聚合、cancel） | service + 单测 | `uv run pytest -m unit` | TODO |
| P3 | Read Service + Repository：list/detail/error-logs | service + 单测 | `uv run pytest -m unit` | TODO |
| P4 | API：`/api/v1/task-runs`（list/detail/error-logs/cancel） | namespace + contract tests | `uv run pytest -m unit` | TODO |
| P5 | Web UI：`/history/sessions` 改为运行中心（列表 + 详情 modal） | template/js/service 更新 | 手工：打开页面检查列表/详情/取消 | TODO |
| P6 | Scheduler jobs 接入 TaskRun（4 个 builtin） | task 侧写入 run/items | 手工：触发任务后在运行中心可见 | TODO |
| P7 | 页面按钮接入 TaskRun（必须覆盖 4 项） | action endpoint 返回 `run_id` | 手工：触发按钮 -> toast -> 运行中心可见 | TODO |
| P8 | 清理与兼容：移除 UI 轮询逻辑、统一文案“运行中心”、收敛 `session_id` 对外契约 | 文案/接口一致 | `rg -n "sync-sessions|session_id" app/static/js app/api` 重点检查 | TODO |
| P9 | 全量验证：format/typecheck/unit | CI 本地可过 | `make format && make typecheck && uv run pytest -m unit` | TODO |

## 验收标准（DoD）

- 运行中心能展示：账户同步/容量同步/聚合/账户分类统计（覆盖 builtin jobs）。
- 任意异步任务触发成功统一返回 `data.run_id`；结果入口指向 `/history/sessions`。
- 账户分类统计 run 里能看到按规则的 item 列表；失败可定位到具体 rule。
- cancel action 能把 run 标记 cancelled，并在任务循环边界尽力提前退出。
- 单测覆盖：API contract（list/detail/error-logs/cancel）+ write service 状态流转。

