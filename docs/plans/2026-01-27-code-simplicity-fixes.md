# Code Simplicity Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `docs/reports/2026-01-27-code-simplicity-review.md` 的清单逐项修复/确认保留，降低复杂度与维护成本，同时保持功能不变。

**Architecture:** 将问题按“lint 可自动修复 / 大文件拆分 / 前端兜底与全局注入 / 异常边界与回退 / 文档漂移 / 指标复测”分桶；每条问题对应一个可追踪条目（ID），修复后记录 commit 与验证命令。

**Tech Stack:** Flask, SQLAlchemy, APScheduler, structlog, uv/ruff/pyright, ESLint, Grid.js

---

## Reference
- Review report: `docs/reports/2026-01-27-code-simplicity-review.md`
- Decisions: `docs/plans/2026-01-27-code-simplicity-decisions.md`

## Status Convention
- `TODO`：未开始
- `DOING`：进行中
- `DONE`：已完成（建议填写 commit + 验证命令）
- `SKIP`：不修（例如确认是合理设计/历史兼容，需写明原因）
- `KEEP`：保留（与 `SKIP` 类似，但强调保留为长期策略）

---

## Summary
| Category | Count |
|---|---:|
| A1 | 33 |
| A2 | 2 |
| B1 | 20 |
| B2 | 20 |
| C1 | 5 |
| C2 | 2 |
| C3 | 1 |
| C4 | 7 |
| C5 | 18 |
| C6 | 16 |
| C7 | 2 |
| C8 | 22 |
| C9 | 4 |
| D | 60 |
| E | 19 |
| F | 42 |
| G | 2 |
| H | 2 |
| I | 2 |
| J | 3 |
| K | 2 |
| L | 3 |

---

## A1 (33)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| A1-001 | DONE | `app/repositories/account_classification_daily_stats_repository.py:45:29` | `B009`：不要用 `getattr(x, "__table__")` 访问常量属性名；直接 `x.__table__` 更简单。 | `uv run ruff check app/repositories/account_classification_daily_stats_repository.py` | `getattr(..., "__table__")` 改为 `Model.__table__` |
| A1-002 | DONE | `app/repositories/account_classification_daily_stats_repository.py:71:29` | `B009`：同上。 | `uv run ruff check app/repositories/account_classification_daily_stats_repository.py` | 同上 |
| A1-003 | DONE | `app/routes/accounts/__init__.py:21:11` | `RUF022`：`__all__` 未排序（会制造 diff 噪音）。 | `uv run ruff check app/routes/accounts/__init__.py` | 调整 `__all__` 顺序，减少 diff 噪音 |
| A1-004 | DONE | `app/services/account_classification/cache.py:58:33` | `UP037`：类型注解不需要引号。 | `uv run ruff check app/services/account_classification/cache.py && uv run pyright` | 去掉 `list["JsonDict"]` 的引号（文件已启用 `from __future__ import annotations`） |
| A1-005 | DONE | `app/services/account_classification/cache.py:81:37` | `UP037`：同上。 | `uv run ruff check app/services/account_classification/cache.py && uv run pyright` | 去掉 `Iterable[Mapping[str, JsonValue]]` 的引号 |
| A1-006 | DONE | `app/services/accounts/account_classifications_write_service.py:239:9` | `PLR0915`：语句过多（51 > 50），函数体过长。 | `uv run ruff check app/services/accounts/account_classifications_write_service.py && uv run pyright` | 抽取 `_normalize_expression/_permission_config_changed`，减少 `update_rule` 语句数量并保持行为不变 |
| A1-007 | DONE | `app/services/accounts_sync/accounts_sync_service.py:224:9` | `PLR0912`：分支过多（17 > 12），流程编排/错误处理混杂。 | `uv run ruff check app/services/accounts_sync/accounts_sync_service.py && uv run pyright` | 抽取 `_get_summary_dict/_get_error_payload` 降低分支数量，保持行为不变 |
| A1-008 | DONE | `app/services/accounts_sync/accounts_sync_service.py:45:44` | `UP037`：类型注解不需要引号。 | `uv run ruff check app/services/accounts_sync/accounts_sync_service.py && uv run pyright` | 移除 `SyncOperationResult` 注解引号（配合 `from __future__ import annotations`） |
| A1-009 | DONE | `app/services/cache/cache_actions_service.py:256:42` | `C420`：不必要的 dict comprehension；可用 `dict.fromkeys(...)`。 | `uv run ruff check app/services/cache/cache_actions_service.py` | 已使用 `dict.fromkeys(CLASSIFICATION_DB_TYPES, 0)` 初始化计数 |
| A1-010 | DONE | `app/services/common/options_cache.py:165:53` | `UP037`：类型注解不需要引号。 | `uv run ruff check app/services/common/options_cache.py && uv run pyright` | 去掉 `CommonDatabasesOptionsFilters` 注解引号 |
| A1-011 | DONE | `app/services/common/options_cache.py:172:53` | `UP037`：同上。 | `uv run ruff check app/services/common/options_cache.py && uv run pyright` | 去掉 `CommonDatabasesOptionsFilters` 注解引号 |
| A1-012 | DONE | `app/services/common/options_cache.py:83:48` | `UP037`：同上。 | `uv run ruff check app/services/common/options_cache.py && uv run pyright` | 去掉 `CommonDatabasesOptionsFilters` 注解引号 |
| A1-013 | DONE | `app/tasks/account_classification_auto_tasks.py:110:33` | `RUF046`：对已经是整数的值重复 `int(...)`。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 抽取 `_duration_ms` 统一计算耗时，移除重复 `int(round(...))` |
| A1-014 | DONE | `app/tasks/account_classification_auto_tasks.py:145:33` | `RUF046`：同上。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 同上 |
| A1-015 | DONE | `app/tasks/account_classification_auto_tasks.py:196:21` | `TRY301`：建议把 `raise` 抽到内部函数以减少主流程噪音。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | DSL v4 校验与 permission_facts 校验抽到 helper，主流程不直接 `raise` |
| A1-016 | DONE | `app/tasks/account_classification_auto_tasks.py:199:21` | `TRY301`：同上。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 同上 |
| A1-017 | DONE | `app/tasks/account_classification_auto_tasks.py:205:25` | `TRY301`：同上。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 同上 |
| A1-018 | DONE | `app/tasks/account_classification_auto_tasks.py:223:31` | `RUF046`：重复 `int(...)`。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 同 A1-013（统一用 `_duration_ms`） |
| A1-019 | DONE | `app/tasks/account_classification_auto_tasks.py:284:29` | `RUF046`：重复 `int(...)`。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 同 A1-013（统一用 `_duration_ms`） |
| A1-020 | DONE | `app/tasks/account_classification_auto_tasks.py:31:5` | `PLR0912`：分支过多（25 > 12）。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 抽取 run_id 解析/无规则/无账号/单规则处理/失败 finalize 等 helper，降低分支数量 |
| A1-021 | DONE | `app/tasks/account_classification_auto_tasks.py:31:5` | `PLR0915`：语句过多（108 > 50）。 | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 同上（主函数改为编排+早返回） |
| A1-022 | DONE | `app/tasks/account_classification_daily_tasks.py:230:35` | `RUF046`：重复 `int(...)`。 | `uv run ruff check app/tasks/account_classification_daily_tasks.py && uv run pyright` | 用 `_duration_ms` 替换 `int(round(...))` |
| A1-023 | DONE | `app/tasks/account_classification_daily_tasks.py:24:5` | `PLR0912`：分支过多（33 > 12）。 | `uv run ruff check app/tasks/account_classification_daily_tasks.py && uv run pyright` | 抽取 run_id 解析/无规则/无账号/单规则计算/失败处理等 helper，降低分支 |
| A1-024 | DONE | `app/tasks/account_classification_daily_tasks.py:24:5` | `PLR0915`：语句过多（146 > 50）。 | `uv run ruff check app/tasks/account_classification_daily_tasks.py && uv run pyright` | 同上（主函数改为编排+早返回） |
| A1-025 | DONE | `app/tasks/accounts_sync_tasks.py:166:5` | `PLR0912`：分支过多（21 > 12）。 | `uv run ruff check app/tasks/accounts_sync_tasks.py && uv run pyright app/tasks/accounts_sync_tasks.py` | `sync_accounts` 改为“编排函数”，复用 `_resolve_run_id/_resolve_session/_sync_instances/_finalize_*`，分支下降且行为不变 |
| A1-026 | DONE | `app/tasks/accounts_sync_tasks.py:166:5` | `PLR0915`：语句过多（105 > 50）。 | `uv run ruff check app/tasks/accounts_sync_tasks.py && uv run pyright app/tasks/accounts_sync_tasks.py` | 同 A1-025（主流程缩短为 orchestration） |
| A1-027 | DONE | `app/tasks/accounts_sync_tasks.py:264:13` | `RET505`：`return` 后的 `else` 多余。 | `uv run ruff check app/tasks/accounts_sync_tasks.py` | 移除“无实例 return 后还包一层 else”的结构（早返回） |
| A1-028 | DONE | `app/tasks/capacity_aggregation_tasks.py:201:5` | `PLR0915`：语句过多（75 > 50）。 | `uv run ruff check app/tasks/capacity_aggregation_tasks.py` | 抽取 run_id 解析/skip finalize/异常 finalize 等 helper，降低主函数语句数量并保持行为不变 |
| A1-029 | DONE | `app/tasks/capacity_collection_tasks.py:114:5` | `PLR0912`：分支过多（14 > 12）。 | `uv run ruff check app/tasks/capacity_collection_tasks.py` | 抽取“无活跃实例/循环处理/汇总 finalize/result build” helper，降低分支数量 |
| A1-030 | DONE | `app/tasks/capacity_collection_tasks.py:114:5` | `PLR0915`：语句过多（76 > 50）。 | `uv run ruff check app/tasks/capacity_collection_tasks.py` | 同上（拆分后 ruff 通过） |
| A1-031 | DONE | `app/tasks/capacity_collection_tasks.py:326:13` | `TRY300`：建议把语句移到 `else` 块（减少 try 作用域）。 | `uv run ruff check app/tasks/capacity_collection_tasks.py` | 将最终 `return result` 挪到 `try/except/else` 的 `else` 中，避免把成功返回纳入异常处理作用域 |
| A1-032 | DONE | `app/tasks/capacity_current_aggregation_tasks.py:40:5` | `PLR0912`：分支过多（13 > 12）。 | `uv run ruff check app/tasks/capacity_current_aggregation_tasks.py` | 抽取 run_id 解析/summary 写入/callbacks builder/异常 finalize helper，主函数只做编排 |
| A1-033 | DONE | `app/tasks/capacity_current_aggregation_tasks.py:40:5` | `PLR0915`：语句过多（89 > 50）。 | `uv run ruff check app/tasks/capacity_current_aggregation_tasks.py` | 同上（拆分后 ruff 通过，行为不变） |

---

## A2 (2)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| A2-001 | DONE | `app/static/js/common/grid-table.js:29:25` | `security/detect-object-injection`：动态 key 读 `result[key]`。 | `npx eslint app/static/js/common/grid-table.js` | 改用 `Reflect.get/Reflect.set` 并过滤 `__proto__/prototype/constructor`，eslint 0 warnings |
| A2-002 | DONE | `app/static/js/common/grid-table.js:39:7` | `security/detect-object-injection`：动态 key 写 `result[key] = ...`。 | `npx eslint app/static/js/common/grid-table.js` | 同上 |

---

## B1 (20)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| B1-001 | TODO | `app/__init__.py` | 单文件过大（477 行） | `uv run ruff check app && uv run pyright` |  |
| B1-002 | TODO | `app/api/v1/namespaces/accounts.py` | 单文件过大（966 行） | `uv run ruff check app && uv run pyright` |  |
| B1-003 | TODO | `app/api/v1/namespaces/accounts_classifications.py` | 单文件过大（837 行） | `uv run ruff check app && uv run pyright` |  |
| B1-004 | TODO | `app/api/v1/namespaces/databases.py` | 单文件过大（634 行） | `uv run ruff check app && uv run pyright` |  |
| B1-005 | TODO | `app/api/v1/namespaces/instances.py` | 单文件过大（902 行） | `uv run ruff check app && uv run pyright` |  |
| B1-006 | TODO | `app/api/v1/namespaces/tags.py` | 单文件过大（722 行） | `uv run ruff check app && uv run pyright` |  |
| B1-007 | TODO | `app/scheduler.py` | 单文件过大（583 行） | `uv run ruff check app && uv run pyright` |  |
| B1-008 | TODO | `app/schemas/account_classifications.py` | 单文件过大（476 行） | `uv run ruff check app && uv run pyright` |  |
| B1-009 | TODO | `app/services/accounts/account_classifications_write_service.py` | 单文件过大（513 行） | `uv run ruff check app && uv run pyright` |  |
| B1-010 | TODO | `app/services/accounts_sync/accounts_sync_service.py` | 单文件过大（503 行） | `uv run ruff check app && uv run pyright` |  |
| B1-011 | TODO | `app/services/accounts_sync/adapters/mysql_adapter.py` | 单文件过大（891 行） | `uv run ruff check app && uv run pyright` |  |
| B1-012 | TODO | `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 单文件过大（1375 行） | `uv run ruff check app && uv run pyright` |  |
| B1-013 | TODO | `app/services/accounts_sync/permission_manager.py` | 单文件过大（1102 行） | `uv run ruff check app && uv run pyright` |  |
| B1-014 | TODO | `app/services/aggregation/aggregation_service.py` | 单文件过大（841 行） | `uv run ruff check app && uv run pyright` |  |
| B1-015 | TODO | `app/services/aggregation/database_aggregation_runner.py` | 单文件过大（560 行） | `uv run ruff check app && uv run pyright` |  |
| B1-016 | TODO | `app/services/aggregation/instance_aggregation_runner.py` | 单文件过大（565 行） | `uv run ruff check app && uv run pyright` |  |
| B1-017 | TODO | `app/services/partition/partition_read_service.py` | 单文件过大（473 行） | `uv run ruff check app && uv run pyright` |  |
| B1-018 | TODO | `app/services/partition_management_service.py` | 单文件过大（635 行） | `uv run ruff check app && uv run pyright` |  |
| B1-019 | TODO | `app/settings.py` | 单文件过大（558 行） | `uv run ruff check app && uv run pyright` |  |
| B1-020 | TODO | `app/utils/structlog_config.py` | 单文件过大（618 行） | `uv run ruff check app && uv run pyright` |  |

---

## B2 (20)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| B2-001 | TODO | `app/static/js/modules/stores/instance_store.js` | 单文件过大（846 行） | `uv run ruff check app && uv run pyright` |  |
| B2-002 | TODO | `app/static/js/modules/stores/tag_management_store.js` | 单文件过大（622 行） | `uv run ruff check app && uv run pyright` |  |
| B2-003 | TODO | `app/static/js/modules/views/accounts/account-classification/index.js` | 单文件过大（778 行） | `uv run ruff check app && uv run pyright` |  |
| B2-004 | TODO | `app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js` | 单文件过大（727 行） | `uv run ruff check app && uv run pyright` |  |
| B2-005 | TODO | `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js` | 单文件过大（1429 行） | `uv run ruff check app && uv run pyright` |  |
| B2-006 | TODO | `app/static/js/modules/views/accounts/classification_statistics.js` | 单文件过大（1055 行） | `uv run ruff check app && uv run pyright` |  |
| B2-007 | TODO | `app/static/js/modules/views/accounts/ledgers.js` | 单文件过大（776 行） | `uv run ruff check app && uv run pyright` |  |
| B2-008 | TODO | `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js` | 单文件过大（669 行） | `uv run ruff check app && uv run pyright` |  |
| B2-009 | TODO | `app/static/js/modules/views/admin/scheduler/index.js` | 单文件过大（908 行） | `uv run ruff check app && uv run pyright` |  |
| B2-010 | TODO | `app/static/js/modules/views/components/charts/manager.js` | 单文件过大（982 行） | `uv run ruff check app && uv run pyright` |  |
| B2-011 | TODO | `app/static/js/modules/views/components/permissions/permission-modal.js` | 单文件过大（602 行） | `uv run ruff check app && uv run pyright` |  |
| B2-012 | TODO | `app/static/js/modules/views/components/tags/tag-selector-controller.js` | 单文件过大（805 行） | `uv run ruff check app && uv run pyright` |  |
| B2-013 | TODO | `app/static/js/modules/views/history/logs/logs.js` | 单文件过大（660 行） | `uv run ruff check app && uv run pyright` |  |
| B2-014 | TODO | `app/static/js/modules/views/history/sessions/session-detail.js` | 单文件过大（651 行） | `uv run ruff check app && uv run pyright` |  |
| B2-015 | TODO | `app/static/js/modules/views/history/sessions/sync-sessions.js` | 单文件过大（914 行） | `uv run ruff check app && uv run pyright` |  |
| B2-016 | TODO | `app/static/js/modules/views/instances/detail.js` | 单文件过大（2123 行） | `uv run ruff check app && uv run pyright` |  |
| B2-017 | TODO | `app/static/js/modules/views/instances/list.js` | 单文件过大（1348 行） | `uv run ruff check app && uv run pyright` |  |
| B2-018 | TODO | `app/static/js/modules/views/instances/statistics.js` | 单文件过大（605 行） | `uv run ruff check app && uv run pyright` |  |
| B2-019 | TODO | `app/static/js/modules/views/tags/batch-assign.js` | 单文件过大（707 行） | `uv run ruff check app && uv run pyright` |  |
| B2-020 | TODO | `app/static/js/modules/views/tags/index.js` | 单文件过大（567 行） | `uv run ruff check app && uv run pyright` |  |

---

## C1 (5)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C1-001 | DONE | `app/static/js/modules/views/accounts/account-classification/index.js:91` | C.1  默认实现 | `npx eslint app/static/js --ext .js` | 移除 `toast` console.* fallback；改为依赖 `window.toast`，缺失时直接 return；eslint 0 errors |
| C1-002 | DONE | `app/static/js/modules/views/admin/scheduler/index.js:11` | C.1  默认实现 | `npx eslint app/static/js --ext .js` | 移除 `toast` console.* fallback；改为强依赖 `window.toast` 并 fail-fast；eslint 0 errors |
| C1-003 | DONE | `app/static/js/modules/views/instances/detail.js:11` | C.1  默认实现 | `npx eslint app/static/js --ext .js` | 移除 `toast` console.* fallback；改为强依赖 `window.toast` 并 fail-fast；eslint 0 errors |
| C1-004 | DONE | `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:9` | C.1  默认实现 | `npx eslint app/static/js --ext .js` | 移除 `toast` console.* fallback；缺失时 throw；eslint 0 errors |
| C1-005 | DONE | `app/static/js/modules/views/tags/batch-assign.js:42` | C.1  默认实现 | `npx eslint app/static/js --ext .js` | 移除 `toast` console.* fallback；缺失时直接 return；eslint 0 errors |

---

## C2 (2)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C2-001 | DONE | `app/static/js/modules/views/instances/detail.js:21` | C.2 DOM helpers 兜底 stub | `npx eslint app/static/js --ext .js` | 移除 `helpersFallback` stub；改为强依赖 `DOMHelpers` 并 fail-fast；eslint 0 errors |
| C2-002 | DONE | `app/static/js/modules/views/instances/detail.js:28` | C.2 DOM helpers 兜底 stub | `npx eslint app/static/js --ext .js` | 移除 `DOMHelpers || helpersFallback` 解构回退；eslint 0 errors |

---

## C3 (1)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C3-001 | DONE | `app/static/js/modules/views/accounts/account-classification/index.js:99` | C.3  默认实现 | `npx eslint app/static/js --ext .js` | 删除 `logErrorWithContext`/fallbackLogger 抽象，直接 `console.error`；eslint 0 errors |

---

## C4 (7)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C4-001 | DONE | `app/static/js/modules/views/components/change-history/change-history-renderer.js:4` | C.4 其它 fallback 函数/空函数兜底 | `npx eslint app/static/js --ext .js` | 移除不安全的 `escapeHtml` fallback，改为强依赖 `UI.escapeHtml` 并 fail-fast；eslint 0 errors |
| C4-002 | DONE | `app/static/js/modules/views/components/tags/tag-selector-modal-adapter.js:51` | C.4 其它 fallback 函数/空函数兜底 | `npx eslint app/static/js --ext .js` | 移除 open/close/setLoading 的 no-op fallback；modal 未就绪时返回 null 并打印错误；eslint 0 errors |
| C4-003 | DONE | `app/static/js/modules/views/components/tags/tag-selector-modal-adapter.js:52` | C.4 其它 fallback 函数/空函数兜底 | `npx eslint app/static/js --ext .js` | 移除 open/close/setLoading 的 no-op fallback；modal 未就绪时返回 null 并打印错误；eslint 0 errors |
| C4-004 | DONE | `app/static/js/modules/views/components/tags/tag-selector-modal-adapter.js:53` | C.4 其它 fallback 函数/空函数兜底 | `npx eslint app/static/js --ext .js` | 移除 open/close/setLoading 的 no-op fallback；modal 未就绪时返回 null 并打印错误；eslint 0 errors |
| C4-005 | DONE | `app/static/js/modules/views/components/tags/tag-selector-view.js:121` | C.4 其它 fallback 函数/空函数兜底 | `npx eslint app/static/js --ext .js` | 移除 handlers 的 no-op fallback，改为必传函数并 fail-fast；eslint 0 errors |
| C4-006 | DONE | `app/static/js/modules/views/components/tags/tag-selector-view.js:122` | C.4 其它 fallback 函数/空函数兜底 | `npx eslint app/static/js --ext .js` | 移除 handlers 的 no-op fallback，改为必传函数并 fail-fast；eslint 0 errors |
| C4-007 | DONE | `app/static/js/modules/views/components/tags/tag-selector-view.js:123` | C.4 其它 fallback 函数/空函数兜底 | `npx eslint app/static/js --ext .js` | 移除 handlers 的 no-op fallback，改为必传函数并 fail-fast；eslint 0 errors |

---

## C5 (18)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C5-001 | DONE | `app/static/js/modules/services/account_change_logs_service.js:7` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-002 | DONE | `app/static/js/modules/services/account_classification_service.js:15` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-003 | DONE | `app/static/js/modules/services/account_classification_statistics_service.js:7` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-004 | DONE | `app/static/js/modules/services/accounts_statistics_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-005 | DONE | `app/static/js/modules/services/auth_service.js:17` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-006 | DONE | `app/static/js/modules/services/capacity_stats_service.js:22` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-007 | DONE | `app/static/js/modules/services/connection_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-008 | DONE | `app/static/js/modules/services/credentials_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-009 | DONE | `app/static/js/modules/services/dashboard_service.js:12` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-010 | DONE | `app/static/js/modules/services/instance_management_service.js:12` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-011 | DONE | `app/static/js/modules/services/instance_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-012 | DONE | `app/static/js/modules/services/logs_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-013 | DONE | `app/static/js/modules/services/partition_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-014 | DONE | `app/static/js/modules/services/permission_service.js:12` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-015 | DONE | `app/static/js/modules/services/scheduler_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-016 | DONE | `app/static/js/modules/services/tag_management_service.js:23` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-017 | DONE | `app/static/js/modules/services/task_runs_service.js:7` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |
| C5-018 | DONE | `app/static/js/modules/services/user_service.js:14` | C.5 HTTP client 解析回退链 | `npx eslint app/static/js --ext .js` | 移除 `global.http` 兜底，仅保留 `client || global.httpU`；eslint 0 errors |

---

## C6 (16)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C6-001 | DONE | `app/static/js/modules/stores/tag_batch_store.js:41` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（保持原有 fail-fast 校验）；eslint 0 errors |
| C6-002 | DONE | `app/static/js/modules/views/accounts/classification_statistics.js:1000` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（保持可选链行为不变）；eslint 0 errors |
| C6-003 | DONE | `app/static/js/modules/views/components/charts/manager.js:17` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（后续仍用可选链判断）；eslint 0 errors |
| C6-004 | DONE | `app/static/js/modules/views/components/charts/manager.js:18` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（后续仍用显式判断）；eslint 0 errors |
| C6-005 | DONE | `app/static/js/modules/views/grid-page.js:110` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（ctx 字段保留可空语义）；eslint 0 errors |
| C6-006 | DONE | `app/static/js/modules/views/grid-page.js:111` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（ctx 字段保留可空语义）；eslint 0 errors |
| C6-007 | DONE | `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:32` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-008 | DONE | `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:33` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-009 | DONE | `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:38` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-010 | DONE | `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:39` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-011 | DONE | `app/static/js/modules/views/history/logs/logs.js:48` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-012 | DONE | `app/static/js/modules/views/history/logs/logs.js:49` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-013 | DONE | `app/static/js/modules/views/history/logs/logs.js:54` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-014 | DONE | `app/static/js/modules/views/history/logs/logs.js:55` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会按原逻辑报错并 return）；eslint 0 errors |
| C6-015 | DONE | `app/static/js/modules/views/instances/detail.js:10` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（未注入时保持可空）；eslint 0 errors |
| C6-016 | DONE | `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:4` | C.6 依赖回退到 | `npx eslint app/static/js --ext .js` | 移除显式 `|| null`（依赖缺失仍会 throw）；eslint 0 errors |

---

## C7 (2)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C7-001 | DONE | `app/static/js/modules/views/admin/partitions/index.js:347` | C.7 UI 行为回退 | `npx eslint app/static/js --ext .js` | toast 存在时只 toast，不再因为 `||` 触发永远 alert；eslint 0 errors |
| C7-002 | DONE | `app/static/js/modules/views/admin/partitions/index.js:359` | C.7 UI 行为回退 | `npx eslint app/static/js --ext .js` | toast 存在时只 toast，不再因为 `||` 触发永远 alert；eslint 0 errors |

---

## C8 (22)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C8-001 | DONE | `app/static/js/common/grid-row-meta.js:11` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 改为一次性 `Object.freeze({ get })` 赋值，不再 `global.X = global.X || {}` |
| C8-002 | DONE | `app/static/js/common/table-query-params.js:103` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 改为一次性 `Object.freeze({ ... })` 赋值，不再 `global.X = global.X || {}` |
| C8-003 | DONE | `app/static/js/modules/ui/async-action-feedback.js:132` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 新增 `js/common/namespaces.js` 统一初始化 `UI/Views`，模块只挂载方法不再自建 namespace |
| C8-004 | DONE | `app/static/js/modules/ui/button-loading.js:149` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上（UI 统一初始化，模块不再 `global.UI = global.UI || {}`） |
| C8-005 | DONE | `app/static/js/modules/ui/danger-confirm.js:223` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-006 | DONE | `app/static/js/modules/ui/filter-card.js:352` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-007 | DONE | `app/static/js/modules/ui/modal.js:204` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-008 | DONE | `app/static/js/modules/ui/terms.js:91` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | `UI.Terms` 改为一次性 `Object.freeze({ ... })` 赋值，不再 `|| {}` |
| C8-009 | DONE | `app/static/js/modules/ui/terms.js:92` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-010 | DONE | `app/static/js/modules/ui/ui-helpers.js:92` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同 C8-003（UI 统一初始化） |
| C8-011 | DONE | `app/static/js/modules/views/components/charts/manager.js:980` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 改为一次性 `window.CapacityStats = { Manager: ... }` 赋值，不再 `|| {}` |
| C8-012 | DONE | `app/static/js/modules/views/grid-page.js:286` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 新增 `js/common/namespaces.js` 统一初始化 `Views`，模块只挂载 `Views.GridPage.mount` |
| C8-013 | DONE | `app/static/js/modules/views/grid-page.js:287` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-014 | DONE | `app/static/js/modules/views/grid-plugins/action-delegation.js:46` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | `Views.GridPlugins` 由 `namespaces.js` 初始化，插件不再自建 namespace |
| C8-015 | DONE | `app/static/js/modules/views/grid-plugins/action-delegation.js:47` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-016 | DONE | `app/static/js/modules/views/grid-plugins/export-button.js:55` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-017 | DONE | `app/static/js/modules/views/grid-plugins/export-button.js:56` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-018 | DONE | `app/static/js/modules/views/grid-plugins/filter-card.js:47` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-019 | DONE | `app/static/js/modules/views/grid-plugins/filter-card.js:48` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-020 | DONE | `app/static/js/modules/views/grid-plugins/url-sync.js:30` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-021 | DONE | `app/static/js/modules/views/grid-plugins/url-sync.js:31` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 同上 |
| C8-022 | DONE | `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:290` | C.8 全局命名空间注入 | `npx eslint app/static/js --ext .js` | 改为一次性 `Object.freeze({ createController })` 赋值，不再 `|| {}` |

---

## C9 (4)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| C9-001 | DONE | `app/static/js/modules/views/accounts/ledgers.js` | C.9 存在 Tab 缩进/格式噪音的文件（按文件列出，共 4 个） | `npx eslint app/static/js --ext .js` | 将实际 Tab 字符替换为 4 spaces（符合 `.editorconfig`）；eslint 0 errors |
| C9-002 | DONE | `app/static/js/modules/views/components/connection-manager.js` | C.9 存在 Tab 缩进/格式噪音的文件（按文件列出，共 4 个） | `npx eslint app/static/js --ext .js` | 将实际 Tab 字符替换为 4 spaces（符合 `.editorconfig`）；eslint 0 errors |
| C9-003 | DONE | `app/static/js/modules/views/instances/detail.js` | C.9 存在 Tab 缩进/格式噪音的文件（按文件列出，共 4 个） | `npx eslint app/static/js --ext .js` | 将实际 Tab 字符替换为 4 spaces（符合 `.editorconfig`）；eslint 0 errors |
| C9-004 | DONE | `app/static/js/modules/views/instances/list.js` | C.9 存在 Tab 缩进/格式噪音的文件（按文件列出，共 4 个） | `npx eslint app/static/js --ext .js` | 将实际 Tab 字符替换为 4 spaces（符合 `.editorconfig`）；eslint 0 errors |

---

## D (60)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| D-001 | DONE | `app/__init__.py:177` | catch-all except Exception | `uv run ruff check app/__init__.py && uv run pyright` | 1B：调度器 init 失败改为 fail-fast（记录 error 后 re-raise），不再吞异常继续启动 |
| D-002 | DONE | `app/api/v1/namespaces/instances.py:408` | catch-all except Exception | `uv run ruff check app/api/v1/namespaces/instances.py && uv run pyright` | 收窄为 `UnicodeDecodeError/csv.Error`；仅将“CSV/编码问题”转为 `ValidationError`，其他异常上抛避免吞真实 bug |
| D-003 | KEEP | `app/infra/logging/queue_worker.py:185` | catch-all except Exception | `uv run ruff check app/infra/logging/queue_worker.py` | 日志写库属于“辅助能力”；失败时不应让 worker 崩溃（已记录 fallback 日志并尝试 rollback） |
| D-004 | KEEP | `app/infra/route_safety.py:165` | catch-all except Exception | `uv run ruff check app/infra/route_safety.py` | `safe_route_call` 作为视图层统一异常封装点，保留 catch-all 将未知异常转为 `SystemError(public_error)` |
| D-005 | KEEP | `app/infra/route_safety.py:180` | catch-all except Exception | `uv run ruff check app/infra/route_safety.py` | 同上（commit 失败属于不可恢复的 infra 异常，按统一口径抛 `SystemError`） |
| D-006 | DONE | `app/models/account_permission.py:104` | catch-all except Exception | `uv run ruff check app/models/account_permission.py && uv run pyright` | 异常收窄为 `(RuntimeError, UnboundExecutionError)`（session 未绑定/无 app context），避免 catch-all 吞掉编程错误 |
| D-007 | DONE | `app/routes/accounts/statistics.py:46` | catch-all except Exception | `uv run ruff check app/routes/accounts/statistics.py && uv run pyright` | 2B：移除统计页降级逻辑；异常直接交给 `safe_route_call`/全局错误处理 |
| D-008 | DONE | `app/routes/instances/statistics.py:45` | catch-all except Exception | `uv run ruff check app/routes/instances/statistics.py && uv run pyright` | 2B：移除统计页降级逻辑；异常直接交给 `safe_route_call`/全局错误处理 |
| D-009 | DONE | `app/schemas/capacity_query.py:38` | catch-all except Exception | `uv run ruff check app && uv run pyright` | `time_utils.to_china` 本身不抛异常(返回 None)，移除无效 try/except；解析失败返回一致的字段格式错误 |
| D-010 | DONE | `app/schemas/databases_query.py:59` | catch-all except Exception | `uv run ruff check app && uv run pyright` | `time_utils.to_china` 返回 None 即视为不可解析；移除无效 try/except；删除未使用的 `field` 参数避免噪音 |
| D-011 | DONE | `app/schemas/partitions.py:45` | catch-all except Exception | `uv run ruff check app && uv run pyright` | `time_utils.to_china` 返回 None 即视为格式错误；移除无效 try/except，避免吞掉真实 bug |
| D-012 | DONE | `app/services/accounts/account_classifications_read_service.py:108` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 6B：read service 仅捕获 `SQLAlchemyError` 并转 `SystemError`；其余异常上抛 |
| D-013 | DONE | `app/services/accounts/account_classifications_read_service.py:132` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-014 | DONE | `app/services/accounts/account_classifications_read_service.py:168` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-015 | DONE | `app/services/accounts/account_classifications_read_service.py:198` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-016 | DONE | `app/services/accounts/account_classifications_read_service.py:220` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-017 | DONE | `app/services/accounts/account_classifications_read_service.py:232` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-018 | DONE | `app/services/accounts/account_classifications_read_service.py:42` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-019 | DONE | `app/services/accounts/account_classifications_read_service.py:49` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-020 | DONE | `app/services/accounts/account_classifications_read_service.py:72` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-021 | DONE | `app/services/accounts/account_classifications_read_service.py:80` | catch-all except Exception | `uv run ruff check app/services/accounts/account_classifications_read_service.py && uv run pyright` | 同上 |
| D-022 | KEEP | `app/services/accounts_sync/accounts_sync_service.py:322` | catch-all except Exception | `uv run ruff check app/services/accounts_sync/accounts_sync_service.py && uv run pyright` | 7A：保留 best-effort 标记失败的 catch-all（仅补充日志，避免 `fail_instance_sync` 异常覆盖原始同步异常） |
| D-023 | DONE | `app/services/accounts_sync/permission_manager.py:452` | catch-all except Exception | `uv run ruff check app/services/accounts_sync/permission_manager.py && uv run pyright` | 4B：facts 构建失败不再写占位数据；记录异常后抛 `SystemError`（fail-fast） |
| D-024 | KEEP | `app/services/cache/cache_actions_service.py:179` | catch-all except Exception | `uv run ruff check app/services/cache/cache_actions_service.py && uv run pyright` | 缓存属于可选能力：单实例清缓存异常不阻断其它实例；catch-all + `log_fallback` 后继续（unit test 已覆盖） |
| D-025 | DONE | `app/services/cache/cache_actions_service.py:245` | catch-all except Exception | `uv run ruff check app/services/cache/cache_actions_service.py && uv run pyright` | `CacheManager.get/_extract_rules_from_cache` 不抛异常；移除冗余 try/except，让异常按真实链路暴露 |
| D-026 | KEEP | `app/services/capacity/instance_capacity_sync_actions_service.py:119` | catch-all except Exception | `uv run ruff check app/services/capacity/instance_capacity_sync_actions_service.py && uv run pyright` | 3A：聚合属于同步后的补偿步骤；失败仅记录 fallback，不影响主流程；保留 catch-all 避免同步失败 |
| D-027 | KEEP | `app/services/connection_adapters/adapters/oracle_adapter.py:75` | catch-all except Exception | `uv run ruff check app/services/connection_adapters/adapters/oracle_adapter.py && uv run pyright` | 5A：Oracle 驱动/权限差异探测失败按保守路径继续；保留 catch-all（日志已统一 `log_fallback`） |
| D-028 | KEEP | `app/services/database_sync/table_size_adapters/oracle_adapter.py:80` | catch-all except Exception | `uv run ruff check app/services/database_sync/table_size_adapters/oracle_adapter.py && uv run pyright` | 5A：Oracle schema 探测失败按保守路径继续；保留 catch-all（日志已统一 `log_fallback`） |
| D-029 | KEEP | `app/services/history_account_change_logs/history_account_change_logs_read_service.py:129` | catch-all except Exception | `uv run ruff check app/services/history_account_change_logs/history_account_change_logs_read_service.py && uv run pyright` | 7A：diff payload 解析失败仅补充上下文日志后 re-raise（不改变异常传播） |
| D-030 | KEEP | `app/services/history_account_change_logs/history_account_change_logs_read_service.py:73` | catch-all except Exception | `uv run ruff check app/services/history_account_change_logs/history_account_change_logs_read_service.py && uv run pyright` | 同上 |
| D-031 | KEEP | `app/services/history_sessions/history_sessions_read_service.py:124` | catch-all except Exception | `uv run ruff check app/services/history_sessions/history_sessions_read_service.py && uv run pyright` | 7A：sync_details 解析失败记录 session/record 上下文后 re-raise（数据一致性问题 fail-fast） |
| D-032 | KEEP | `app/services/ledgers/accounts_ledger_change_history_service.py:78` | catch-all except Exception | `uv run ruff check app/services/ledgers/accounts_ledger_change_history_service.py && uv run pyright` | 7A：diff payload 解析失败仅补充上下文日志后 re-raise（不改变异常传播） |
| D-033 | DONE | `app/services/ledgers/database_ledger_service.py:141` | catch-all except Exception | `uv run ruff check app/services/ledgers/database_ledger_service.py && uv run pyright` | 6B：仅捕获 `SQLAlchemyError` 并转 `SystemError`；其余异常上抛 |
| D-034 | DONE | `app/services/ledgers/database_ledger_service.py:90` | catch-all except Exception | `uv run ruff check app/services/ledgers/database_ledger_service.py && uv run pyright` | 同上 |
| D-035 | DONE | `app/services/partition/partition_read_service.py:155` | catch-all except Exception | `uv run ruff check app/services/partition/partition_read_service.py && uv run pyright` | 6B：仅捕获 `SQLAlchemyError` 并转 `SystemError`；其余异常上抛 |
| D-036 | DONE | `app/services/partition/partition_read_service.py:50` | catch-all except Exception | `uv run ruff check app/services/partition/partition_read_service.py && uv run pyright` | 同上 |
| D-037 | DONE | `app/services/partition/partition_read_service.py:74` | catch-all except Exception | `uv run ruff check app/services/partition/partition_read_service.py && uv run pyright` | 同上 |
| D-038 | DONE | `app/services/scheduler/scheduler_jobs_read_service.py:45` | catch-all except Exception | `uv run ruff check app/services/scheduler/scheduler_jobs_read_service.py && uv run pyright` | 6B：仅捕获 `SQLAlchemyError` 并转 `SystemError`；其余异常上抛 |
| D-039 | DONE | `app/services/scheduler/scheduler_jobs_read_service.py:58` | catch-all except Exception | `uv run ruff check app/services/scheduler/scheduler_jobs_read_service.py && uv run pyright` | 同上 |
| D-040 | DONE | `app/services/statistics/account_statistics_service.py:103` | catch-all except Exception | `uv run ruff check app/services/statistics/account_statistics_service.py && uv run pyright` | 6B：仅捕获 `SQLAlchemyError` 并转 `SystemError`；其余异常上抛 |
| D-041 | DONE | `app/services/statistics/account_statistics_service.py:126` | catch-all except Exception | `uv run ruff check app/services/statistics/account_statistics_service.py && uv run pyright` | 同上 |
| D-042 | DONE | `app/services/statistics/account_statistics_service.py:152` | catch-all except Exception | `uv run ruff check app/services/statistics/account_statistics_service.py && uv run pyright` | 同上 |
| D-043 | DONE | `app/services/statistics/account_statistics_service.py:47` | catch-all except Exception | `uv run ruff check app/services/statistics/account_statistics_service.py && uv run pyright` | 同上 |
| D-044 | DONE | `app/services/statistics/account_statistics_service.py:76` | catch-all except Exception | `uv run ruff check app/services/statistics/account_statistics_service.py && uv run pyright` | 同上 |
| D-045 | KEEP | `app/services/sync_session_service.py:108` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 7A：DB 写入失败仅补充上下文日志后 re-raise（不改变异常传播） |
| D-046 | KEEP | `app/services/sync_session_service.py:175` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-047 | KEEP | `app/services/sync_session_service.py:212` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-048 | KEEP | `app/services/sync_session_service.py:271` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-049 | KEEP | `app/services/sync_session_service.py:322` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-050 | KEEP | `app/services/sync_session_service.py:373` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-051 | KEEP | `app/services/sync_session_service.py:394` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-052 | KEEP | `app/services/sync_session_service.py:415` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-053 | KEEP | `app/services/sync_session_service.py:450` | catch-all except Exception | `uv run ruff check app/services/sync_session_service.py && uv run pyright` | 同上 |
| D-054 | KEEP | `app/tasks/account_classification_auto_tasks.py:246` | catch-all except Exception | `uv run ruff check app/tasks/account_classification_auto_tasks.py && uv run pyright` | 任务 run/item 需要对任意异常做失败落库；捕获后更新状态并 re-raise（不吞异常） |
| D-055 | KEEP | `app/tasks/account_classification_daily_tasks.py:249` | catch-all except Exception | `uv run ruff check app/tasks/account_classification_daily_tasks.py && uv run pyright` | 同上（规则级别失败需要落库并 re-raise） |
| D-056 | KEEP | `app/tasks/account_classification_daily_tasks.py:330` | catch-all except Exception | `uv run ruff check app/tasks/account_classification_daily_tasks.py && uv run pyright` | 任务入口失败需统一 finalize + 返回失败结果；保留 catch-all（避免 run 卡死） |
| D-057 | KEEP | `app/tasks/capacity_collection_tasks.py:339` | catch-all except Exception | `uv run ruff check app/tasks/capacity_collection_tasks.py && uv run pyright` | 容量任务兜底失败分支：确保会话/run 不“卡死”，并返回失败结果 |
| D-058 | KEEP | `app/tasks/capacity_collection_tasks.py:83` | catch-all except Exception | `uv run ruff check app/tasks/capacity_collection_tasks.py && uv run pyright` | 单实例处理兜底：保证单个实例异常不会阻断整批任务，且记录 fallback 日志 |
| D-059 | KEEP | `app/tasks/capacity_current_aggregation_tasks.py:200` | catch-all except Exception | `uv run ruff check app/tasks/capacity_current_aggregation_tasks.py && uv run pyright` | 任务入口兜底失败分支：确保 run 可 finalize 并返回失败结果（避免任务卡死） |
| D-060 | KEEP | `app/utils/structlog_config.py:591` | catch-all except Exception | `uv run ruff check app/utils/structlog_config.py` | `error_handler` 装饰器的职责就是“统一捕获异常并封套响应”；保留 catch-all 属于设计本意 |

---

## E (19)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| E-001 | DONE | `app/__init__.py:184` | fallback=True 日志/降级分支 | `uv run ruff check app/__init__.py && uv run pyright` | 1B：删除启动继续跑的 fallback 日志；改为启动中止 |
| E-002 | DONE | `app/models/account_permission.py:25` | fallback=True 日志/降级分支 | `uv run ruff check app/models/account_permission.py && uv run pyright` | 9A：改用 `app.utils.structlog_config.log_fallback` 统一口径（避免手写 fallback 字段） |
| E-003 | DONE | `app/services/accounts_sync/adapters/mysql_adapter.py:252` | fallback=True 日志/降级分支 | `uv run ruff check app/services/accounts_sync/adapters/mysql_adapter.py && uv run pyright` | 9A：改用 `log_fallback`（缺少版本信息 -> 角色支持探测降级） |
| E-004 | DONE | `app/services/accounts_sync/adapters/mysql_adapter.py:80` | fallback=True 日志/降级分支 | `uv run ruff check app/services/accounts_sync/adapters/mysql_adapter.py && uv run pyright` | 9A：改用 `log_fallback`（mysql.user 列探测失败 -> 按不存在列降级） |
| E-005 | DONE | `app/services/accounts_sync/permission_manager.py:457` | fallback=True 日志/降级分支 | `uv run ruff check app/services/accounts_sync/permission_manager.py && uv run pyright` | 4B：移除 facts 构建失败的 fallback 字段与“空 capabilities”占位；改为 fail-fast |
| E-006 | DONE | `app/services/capacity/instance_capacity_sync_actions_service.py:124` | fallback=True 日志/降级分支 | `uv run ruff check app/services/capacity/instance_capacity_sync_actions_service.py && uv run pyright` | 3A+9A：聚合失败仍忽略（只记 fallback）；改用 `log_fallback` 统一口径 |
| E-007 | DONE | `app/services/connection_adapters/adapters/mysql_adapter.py:192` | fallback=True 日志/降级分支 | `uv run ruff check app/services/connection_adapters/adapters/mysql_adapter.py && uv run pyright` | 9A：改用 `log_fallback`（版本查询失败 -> 返回 None） |
| E-008 | DONE | `app/services/connection_adapters/adapters/oracle_adapter.py:240` | fallback=True 日志/降级分支 | `uv run ruff check app/services/connection_adapters/adapters/oracle_adapter.py && uv run pyright` | 9A：改用 `log_fallback`（版本查询失败 -> 返回 None） |
| E-009 | DONE | `app/services/connection_adapters/adapters/oracle_adapter.py:81` | fallback=True 日志/降级分支 | `uv run ruff check app/services/connection_adapters/adapters/oracle_adapter.py && uv run pyright` | 9A：改用 `log_fallback`（`oracledb.is_thin()` 探测失败 -> 保守按 thick） |
| E-010 | DONE | `app/services/connection_adapters/adapters/postgresql_adapter.py:179` | fallback=True 日志/降级分支 | `uv run ruff check app/services/connection_adapters/adapters/postgresql_adapter.py && uv run pyright` | 9A：改用 `log_fallback`（版本查询失败 -> 返回 None） |
| E-011 | DONE | `app/services/connection_adapters/adapters/sqlserver_adapter.py:231` | fallback=True 日志/降级分支 | `uv run ruff check app/services/connection_adapters/adapters/sqlserver_adapter.py && uv run pyright` | 9A：改用 `log_fallback`（版本查询失败 -> 返回 None） |
| E-012 | DONE | `app/services/database_sync/table_size_adapters/oracle_adapter.py:86` | fallback=True 日志/降级分支 | `uv run ruff check app/services/database_sync/table_size_adapters/oracle_adapter.py && uv run pyright` | 5A+9A：Oracle current_schema 探测失败保持降级；改用 `log_fallback` 统一口径 |
| E-013 | DONE | `app/services/history_sessions/history_sessions_read_service.py:115` | fallback=True 日志/降级分支 | `uv run ruff check app/services/history_sessions/history_sessions_read_service.py && uv run pyright` | 9A：COMPAT 命中日志统一改用 `log_fallback` |
| E-014 | DONE | `app/services/ledgers/accounts_ledger_change_history_service.py:69` | fallback=True 日志/降级分支 | `uv run ruff check app/services/ledgers/accounts_ledger_change_history_service.py && uv run pyright` | 9A：COMPAT 命中日志统一改用 `log_fallback` |
| E-015 | DONE | `app/tasks/capacity_collection_tasks.py:94` | fallback=True 日志/降级分支 | `uv run ruff check app/tasks/capacity_collection_tasks.py && uv run pyright` | 9A：任务兜底日志改用 `log_fallback`（仍避免会话卡死） |
| E-016 | DONE | `app/utils/cache_utils.py:120` | fallback=True 日志/降级分支 | `uv run ruff check app/utils/cache_utils.py && uv run pyright` | 9A：缓存操作失败日志改用 `log_fallback` 统一口径 |
| E-017 | DONE | `app/utils/cache_utils.py:146` | fallback=True 日志/降级分支 | `uv run ruff check app/utils/cache_utils.py && uv run pyright` | 同上 |
| E-018 | DONE | `app/utils/cache_utils.py:164` | fallback=True 日志/降级分支 | `uv run ruff check app/utils/cache_utils.py && uv run pyright` | 同上 |
| E-019 | DONE | `app/utils/cache_utils.py:91` | fallback=True 日志/降级分支 | `uv run ruff check app/utils/cache_utils.py && uv run pyright` | 同上 |

---

## F (42)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| F-001 | DONE | `app/api/v1/namespaces/instances_connections.py:222` | pragma: no cover | `uv run pytest -m unit tests/unit/api/test_instances_connections_batch_tests.py` | 已补单测覆盖批量连接测试单实例异常分支，并移除 `pragma: no cover` |
| F-002 | KEEP | `app/core/types/credentials.py:24` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-003 | KEEP | `app/core/types/dbapi.py:11` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-004 | KEEP | `app/core/types/dbapi.py:15` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-005 | KEEP | `app/core/types/dbapi.py:19` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-006 | KEEP | `app/core/types/dbapi.py:27` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-007 | KEEP | `app/core/types/dbapi.py:31` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-008 | KEEP | `app/core/types/sync.py:15` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-009 | KEEP | `app/core/types/sync.py:19` | pragma: no cover | `uv run ruff check app` | Protocol 抽象方法（仅类型约束）；保留 `pragma: no cover - protocol` |
| F-010 | DONE | `app/models/account_permission.py:104` | pragma: no cover | `uv run pytest -m unit tests/unit/models/test_account_permission.py -k bind_unavailable` | 已补单测覆盖 dialect 探测 fallback 分支，并移除 `pragma: no cover` |
| F-011 | KEEP | `app/models/permission_config.py:68` | pragma: no cover | `uv run ruff check app/models/permission_config.py` | `__repr__` 属于调试辅助且不影响业务；保留 `pragma: no cover` 以避免覆盖率噪音 |
| F-012 | DONE | `app/repositories/ledgers/accounts_ledger_repository.py:189` | pragma: no cover | `uv run pytest -m unit tests/unit/repositories/test_accounts_ledger_repository_tag_filter.py` | 已补单测覆盖标签过滤 SQLAlchemyError 分支，并移除 `pragma: no cover` |
| F-013 | DONE | `app/services/account_classification/auto_classify_actions_service.py:68` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_auto_classify_actions_service_background.py` | 已补单测覆盖后台线程异常分支，并移除 `pragma: no cover` |
| F-014 | DONE | `app/services/accounts_sync/accounts_sync_actions_service.py:94` | pragma: no cover | `uv run pytest -m unit tests/unit/services/accounts_sync/test_accounts_sync_actions_service_background.py` | 已补单测覆盖后台线程异常分支，并移除 `pragma: no cover` |
| F-015 | DONE | `app/services/accounts_sync/accounts_sync_service.py:322` | pragma: no cover | `uv run pytest -m unit tests/unit/services/accounts_sync/test_accounts_sync_service_fail_instance_sync_logging.py` | 已补单测覆盖“标记失败再次失败”的日志分支，并移除 `pragma: no cover` |
| F-016 | DONE | `app/services/accounts_sync/permission_manager.py:452` | pragma: no cover | `uv run pytest -m unit -k test_apply_permissions_raises_when_facts_builder_fails` | 已补单测覆盖失败分支：`tests/unit/services/test_account_permission_manager.py` |
| F-017 | DONE | `app/services/aggregation/aggregation_service.py:157` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_aggregation_service_no_cover_branches.py -k commit_with_partition_retry` | 已补单测覆盖 commit flush 异常分支，并移除 `pragma: no cover` |
| F-018 | DONE | `app/services/aggregation/aggregation_service.py:417` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_aggregation_service_no_cover_branches.py -k execute_instance_period` | 已补单测覆盖 executor 异常分支，并移除 `pragma: no cover` |
| F-019 | DONE | `app/services/aggregation/aggregation_service.py:484` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_aggregation_service_no_cover_branches.py -k aggregate_database_periods` | 已补单测覆盖数据库级聚合异常分支，并移除 `pragma: no cover` |
| F-020 | DONE | `app/services/aggregation/capacity_aggregation_task_runner.py:311` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_capacity_aggregation_task_runner_no_cover_branches.py` | 已补单测覆盖单实例聚合异常分支，并移除 `pragma: no cover` |
| F-021 | DONE | `app/services/aggregation/database_aggregation_runner.py:105` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_database_aggregation_runner_no_cover_branches.py -k invoke_callback` | 已补单测覆盖回调异常分支，并移除 `pragma: no cover` |
| F-022 | DONE | `app/services/aggregation/database_aggregation_runner.py:205` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_database_aggregation_runner_no_cover_branches.py -k aggregate_period` | 已补单测覆盖实例聚合异常分支，并移除 `pragma: no cover` |
| F-023 | DONE | `app/services/aggregation/database_aggregation_runner.py:512` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_database_aggregation_runner_no_cover_branches.py -k apply_change_statistics` | 已补单测覆盖增量统计 fallback 分支，并移除 `pragma: no cover` |
| F-024 | DONE | `app/services/aggregation/instance_aggregation_runner.py:108` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_instance_aggregation_runner_no_cover_branches.py -k invoke_callback` | 已补单测覆盖回调异常分支，并移除 `pragma: no cover` |
| F-025 | DONE | `app/services/aggregation/instance_aggregation_runner.py:212` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_instance_aggregation_runner_no_cover_branches.py -k aggregate_period` | 已补单测覆盖实例聚合异常分支，并移除 `pragma: no cover` |
| F-026 | DONE | `app/services/aggregation/instance_aggregation_runner.py:422` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_instance_aggregation_runner_no_cover_branches.py -k wraps_sqlalchemy_error` | 已补单测覆盖 SQLAlchemyError 分支，并移除 `pragma: no cover` |
| F-027 | DONE | `app/services/aggregation/instance_aggregation_runner.py:440` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_instance_aggregation_runner_no_cover_branches.py -k wraps_unknown_commit_error` | 已补单测覆盖未知异常分支，并移除 `pragma: no cover` |
| F-028 | DONE | `app/services/aggregation/instance_aggregation_runner.py:532` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_instance_aggregation_runner_no_cover_branches.py -k apply_change_statistics` | 已补单测覆盖增量统计 fallback 分支，并移除 `pragma: no cover` |
| F-029 | DONE | `app/services/capacity/capacity_collection_actions_service.py:64` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_capacity_collection_actions_service_background.py` | 已补单测覆盖后台线程异常分支，并移除 `pragma: no cover` |
| F-030 | DONE | `app/services/capacity/capacity_current_aggregation_actions_service.py:78` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_capacity_current_aggregation_actions_service_background.py` | 已补单测覆盖后台线程异常分支，并移除 `pragma: no cover` |
| F-031 | DONE | `app/services/connection_adapters/adapters/oracle_adapter.py:75` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_oracle_connection_adapter_is_thin_fallback.py` | 已补单测覆盖 is_thin 探测异常 fallback 分支，并移除 `pragma: no cover` |
| F-032 | DONE | `app/services/database_sync/adapters/mysql_adapter.py:124` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_mysql_capacity_adapter_exception_logging.py` | 已补单测覆盖异常日志分支，并移除 `pragma: no cover` |
| F-033 | DONE | `app/services/database_sync/database_filters.py:69` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_yaml_config_validation_filters.py -k invalid_syntax` | 已补单测覆盖 YAML 语法错误分支，并移除 `pragma: no cover` |
| F-034 | DONE | `app/services/partition_management_service.py:194` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_partition_management_service_no_cover_branches.py -k create_partition` | 已补单测覆盖创建分区“未捕获异常”分支，并移除 `pragma: no cover` |
| F-035 | DONE | `app/services/partition_management_service.py:326` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_partition_management_service_no_cover_branches.py -k cleanup_old_partitions` | 已补单测覆盖清理分区“未捕获异常”分支，并移除 `pragma: no cover` |
| F-036 | DONE | `app/services/partition_management_service.py:447` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_partition_management_service_no_cover_branches.py -k get_table_partitions` | 已补单测覆盖单条分区信息失败分支，并移除 `pragma: no cover` |
| F-037 | DONE | `app/services/scheduler/scheduler_actions_service.py:128` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_scheduler_actions_service_background_error_logging.py` | 已补单测覆盖后台执行任务异常日志分支，并移除 `pragma: no cover` |
| F-038 | DONE | `app/services/scheduler/scheduler_job_write_service.py:27` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_scheduler_job_write_service_type_checking_guard.py` | 已补单测覆盖 TYPE_CHECKING guard 分支，并移除 `pragma: no cover` |
| F-039 | DONE | `app/services/tags/tag_write_service.py:166` | pragma: no cover | `uv run pytest -m unit tests/unit/services/test_tag_write_service_batch_delete_error_logging.py` | 已补单测覆盖批量删除 SQLAlchemyError 分支，并移除 `pragma: no cover` |
| F-040 | DONE | `app/tasks/capacity_aggregation_tasks.py:181` | pragma: no cover | `uv run pytest -m unit tests/unit/tasks/test_capacity_aggregation_tasks_no_cover_branches.py` | 已补单测覆盖 rollback 抑制异常分支，并移除 `pragma: no cover` |
| F-041 | DONE | `app/tasks/capacity_collection_tasks.py:339` | pragma: no cover | `uv run pytest -m unit tests/unit/tasks/test_capacity_collection_tasks_no_cover_branches.py -k unclassified_exception` | 已补单测覆盖“未分类异常”兜底分支，并移除 `pragma: no cover` |
| F-042 | DONE | `app/tasks/capacity_collection_tasks.py:83` | pragma: no cover | `uv run pytest -m unit tests/unit/tasks/test_capacity_collection_tasks_no_cover_branches.py -k process_instance_with_fallback` | 已补单测覆盖单实例同步异常兜底分支，并移除 `pragma: no cover` |

---

## G (2)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| G-001 | DONE | `app/services/accounts_sync/adapters/mysql_adapter.py:53` | `MYSQL_ADAPTER_EXCEPTIONS` 含 `KeyError/AttributeError`；`_has_mysql_user_column` 捕获后当“不存在列”继续（可能把真实错误当成“兼容差异”）。 | `uv run ruff check app` | 移除/收窄 `MYSQL_ADAPTER_EXCEPTIONS`（不再吞 `KeyError/AttributeError`）；探测仅对 `ConnectionAdapterError` 降级；`uv run ruff check <touched>` + `uv run pyright` |
| G-002 | DONE | `app/services/accounts_sync/adapters/sqlserver_adapter.py:31` | `SQLSERVER_ADAPTER_EXCEPTIONS` 含 `KeyError/AttributeError` 等编程错误；并在 `_fetch_raw_accounts` 捕获后直接 `return []`（隐藏真实问题）。 | `uv run ruff check app` | 移除 `LookupError/KeyError/AttributeError`；`_fetch_raw_accounts` 捕获后改为 raise（不再 `return []`）；`uv run ruff check <touched>` + `uv run pyright` |

---

## H (2)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| H-001 | DONE | `app/core/constants/status_types.py` | `SyncStatus` 与 `TaskRunStatus` 基本重复（维护两个来源会漂移）。 | `uv run ruff check app` | `TaskRunStatus` 复用 `SyncStatus` 常量，避免双份字符串；`uv run ruff check <touched>` + `uv run pyright` |
| H-002 | DONE | `app/models/task_run.py:32` | `TaskRun.status` 默认值直接写 `"running"`，未复用常量（与 `TaskRunItem` 使用 `TaskRunStatus` 不一致）。 | `uv run ruff check app` | `TaskRun.status` 默认值改用 `TaskRunStatus.RUNNING`；`uv run ruff check <touched>` + `uv run pyright` |

---

## I (2)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| I-001 | DONE | `app/repositories/account_statistics_repository.py:104` | `total_instances = active_instances`（看起来像口径错误/字段冗余）。 | `uv run ruff check app` | `total_instances = active + disabled`，`normal_instances = active_instances`；`uv run ruff check <touched>` + `uv run pyright` |
| I-002 | DONE | `app/repositories/account_statistics_repository.py:124` | `fetch_db_type_stats()` 逐 db_type `.all()` 拉全量再 Python 计数；可用 SQL 聚合一次拿齐，代码更短更快。 | `uv run ruff check app` | 改为单次 SQL `GROUP BY db_type` 聚合；移除 `.all()` + Python loop；`uv run ruff check <touched>` + `uv run pyright` |

---

## J (3)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| J-001 | DONE | `README.md:148` | 写 `http://localhost:5000`，但本地启动默认端口是 `5001`（`app.py`）。 | `(manual) review docs` | 修正本地访问端口为 `5001`（与 `app.py` 一致） |
| J-002 | DONE | `docs/reports/clean-code-analysis.md:161` | 引用不存在的 `services/cache_service.py`（当前仓库无该文件），说明报告已过期。 | `(manual) review docs` | 替换为现有路径 `services/cache/cache_actions_service.py` |
| J-003 | DONE | `docs/reports/clean-code-analysis.md:52` | 提到 Celery，但仓库内未发现 `celery`/`Celery` 实际使用（需确认是否历史遗留/文档误导）。 | `(manual) review docs` | 更新描述：任务由 APScheduler 驱动，未引入 Celery |

---

## K (2)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| K-001 | DONE | `app/infra/route_safety.py:115` | `safe_route_call` 的 `func_args/func_kwargs`（仓库内未发现调用方传入，属于“预留扩展点”）。 | `uv run ruff check app` | 删除 `func_args/func_kwargs` 预留扩展点，直接 `func()`；`uv run ruff check <touched>` + `uv run pyright` |
| K-002 | DONE | `app/static/js/modules/views/errors` | 空目录（纯噪音）。 | `uv run ruff check app` | 该目录为空且不受 git 跟踪；本地已删除（无 repo 变更） |

---

## L (3)

| ID | Status | Location | Issue | Verify | Commit/Notes |
|---|---|---|---|---|---|
| L-001 | DONE | `TaskRun.query.filter_by(run_id=...)` | 约出现 35 次（同一套 run 生命周期逻辑在多处复制粘贴的信号）。 | `rg \"TaskRun\\.query\\.filter_by\\(run_id=\" app` | 复测：`34` 次（app/ 内），仍建议后续抽 `task_run_repo`/helper 收敛 |
| L-002 | DONE | `db.session.commit()` | 在  约出现 69 次（事务边界分散，容易出现“到处 commit”的维护成本）。 | `rg \"db\\.session\\.commit\\(\" app` | 复测：`69` 次（app/ 内），属于长期收敛项（建议按模块逐步合并事务边界） |
| L-003 | DONE | `getattr(..., "literal")` | 类模式在 Python 侧出现约 297 次（排除 ），其中部分属于“过度防御性/动态结构”使用；建议按模块逐步收敛到明确类型与字段访问。 | `rg \"getattr\\([^\\n]+,\\s*['\\\"]\" app --type py` | 复测：`301` 次（app/ 内，仅统计 string literal），属于长期收敛项 |
