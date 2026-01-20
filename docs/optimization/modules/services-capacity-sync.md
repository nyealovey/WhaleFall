# capacity-sync（services/capacity + tasks/capacity_*）

## Core Purpose

- 提供容量采集与聚合相关能力：
  - 容量采集（collection）：采集各实例数据库容量并落库
  - 统计聚合（aggregation）：对采集结果按周期汇总（日/周/月等）
  - 对外提供 API/任务可调用的读写服务与任务入口

## Unnecessary Complexity Found

- （已落地）`app/tasks/capacity_collection_tasks.py:1`：
  - `sync_databases` 中 `except CAPACITY_TASK_EXCEPTIONS` 与 `except Exception` 两段逻辑完全重复 (仅日志 message 不同), 包含:
    - 标记 session failed
    - 统一返回失败结构
  - 重复样板增加了修改点与出错概率。

## Code to Remove

- `app/tasks/capacity_collection_tasks.py:1`：抽取 `_finalize_task_failed` 去除重复失败处理样板（可删/可减复杂度 LOC 估算：~20-40）。

## Simplification Recommendations

1. 失败处理只保留一个“事实来源”
   - Current: 多段 except 分支复制相同的 session 失败收尾与返回结构。
   - Proposed: `_finalize_task_failed(...)` 作为唯一收口点，分支只负责决定日志 message。

## YAGNI Violations

- 重复的异常分支样板（没有提供额外语义/差异化收益）。

## Final Assessment

- 可删/可减复杂度估算：~20-40（已落地，以去重样板为主）
- Complexity: Medium -> Lower
- Recommended action: Proceed（本轮仅做等价去重，不改采集/聚合业务行为）
