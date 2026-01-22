---
title: TaskRun summary_json 口径（v1）
aliases:
  - task-run-summary-json
tags:
  - operations
  - operations/task-runs
status: draft
created: 2026-01-22
updated: 2026-01-22
owner: WhaleFall Team
scope: TaskRun Center 的 summary_json 写入结构约定、容量控制与数据清理操作
related:
  - "[[operations/README|operations]]"
  - "[[standards/backend/task-and-scheduler]]"
---

# TaskRun summary_json 口径（v1）

## 1. 适用场景

- 需要在“任务运行中心/历史会话”列表页快速展示任务概览（不打开明细也能读懂结果）。
- 需要统一各任务 `task_runs.summary_json` 的结构，便于前端按 `ext.type` 渲染。
- 需要收敛大明细到 `TaskRunItem.metrics_json/details_json`，避免 `task_runs` 行过大。

## 2. Summary Envelope 结构（强约束）

`task_runs.summary_json` 顶层只能是：

```json
{
  "version": 1,
  "common": { "inputs": {}, "scope": { "time": null, "target": {} }, "metrics": [], "highlights": [], "flags": { "skipped": false, "skip_reason": null } },
  "ext": { "type": "sync_accounts", "version": 1, "data": {} }
}
```

约束点：

- 顶层只允许 `version/common/ext`，禁止出现散落字段（例如 `skipped/records/periods_executed` 等）。
- `ext.type` 必须等于 `TaskRun.task_key`（用于前端/registry 自动识别任务类型）。
- `ext.data` 仅用于“聚合后的小字段”；大明细必须落到 `TaskRunItem.metrics_json/details_json`。

实现参考：

- schema: `app/schemas/task_run_summary.py`
- builders: `app/services/task_runs/task_run_summary_builders.py`

## 3. 写入原则（代码侧约定）

- 创建 run 时：`TaskRunsWriteService.start_run(...)` 会写入基础 envelope（即使调用方传 `summary_json=None`）。
- 任务完成前：任务应写入最终 summary（通用 metrics + ext.data），并在必要时写入 `common.flags.skipped/skip_reason`。
- 子项明细：按实例/规则维度等写入 `TaskRunItem.metrics_json/details_json`，避免把每条明细塞进 `summary_json`。

## 4. 安全与容量约束

- 禁止在 `summary_json` 放入敏感信息（账号口令、token、连接串、个人信息等）。
- 禁止在 `summary_json` 放入大数组/大对象；需要详情请放到 `TaskRunItem.details_json`，并控制字段规模。

## 5. 旧数据清理（本次不做兼容）

> [!danger]
> 本操作会**永久删除**历史任务运行记录与子项明细。仅在确认不需要历史数据时执行。

```sql
BEGIN;
DELETE FROM task_run_items;
DELETE FROM task_runs;
COMMIT;
```

## 6. 验证建议

- 确认各内置任务执行后，`task_runs.summary_json` 顶层仅包含 `version/common/ext`。
- 任意任务应满足：`summary_json.ext.type == task_runs.task_key`。
- 需要更详细的执行细节时，优先查看 `task_run_items.metrics_json/details_json`。

