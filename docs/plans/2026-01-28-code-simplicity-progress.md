# Code Simplicity Progress (Codex / Minimalism / YAGNI)

更新时间：2026-01-28  
参考文档：`docs/reports/2026-01-28-code-simplicity-review-codex.md`  
范围：仅跟踪“最小化/YAGNI”简化项；**不包含「单文件过大」类治理项**。

---

## 目标（Goal）

在不改变对外行为（Web/UI/API/任务调度语义）的前提下，优先消除：

- 未使用/重复的抽象入口（减少并行机制与口径漂移）
- 过宽异常捕获与“吞错回退值”（避免把 bug 当成无数据）
- 前端 services 重复样板（降低复制粘贴维护成本）
- `COMPAT` 兼容分支的永久化风险（补齐退出机制）

---

## 进度概览（Summary）

| 维度 | 基线（2026-01-28） | 当前 | 目标（阶段性） | 备注 |
|---|---:|---:|---:|---|
| ruff | pass | pass | pass | `uv run ruff check app` |
| pyright | 0 errors | 0 errors | 0 errors | `uv run pyright` |
| eslint | 0 errors | 0 errors | 0 errors | `npx eslint app/static/js --ext .js` |
| `except Exception` 数量 | 32 | 31 | ≤ 20 | 优先收紧“可恢复异常集合” |
| `log_fallback` 调用点 | 21 | 21 | 保留必要点，删重复实现 | 先解决双实现问题 |
| `COMPAT` 标记数 | 14 | 0 | 0 | 已改为严格校验，并移除历史数据形状兼容 |
| `pragma: no cover` | 9 | 9 | 9 | protocol/`__repr__` 允许保留 |
| except 内 `return []` | 4 | 2 | 0-2 | 仅允许“明确业务语义的空结果” |
| except 内 `return {}` | 1 | 0 | 0 | 适配器失败建议 fail-fast |
| except 内 `return None` | 23 | 23 | 仅保留“可选能力/解析失败” | 需要逐点判定 |
| JS `ensureHttpClient` 复制点 | 18 | 1 | 1 | 抽 shared helper |
| JS `toQueryString` 复制点 | 6 | 1 | 1 | 抽 shared helper |

> 注：基线统计来自本次扫描与关键模式检索（见参考文档）。

---

## 工作项（Work Items）

状态约定：
- `TODO`：未开始
- `DOING`：进行中
- `DONE`：已完成（建议附 commit + 验证命令）
- `KEEP`：确认保留（写明原因 + 退出条件/不退出原因）
- `SKIP`：不做（写明原因）

### P0（必须先做：删未用入口 / 合并重复实现）

| ID | 状态 | Location | 说明 | 验证 | 备注/Commit |
|---|---|---|---|---|---|
| P0-001 | DONE | `app/utils/structlog_config.py` | 删除确认未使用的 `error_handler()` 装饰器，并从 `__all__` 移除导出，避免与全局 errorhandler/`safe_route_call` 职责重叠。 | `uv run ruff check app/utils/structlog_config.py && uv run pyright` | 2026-01-28：已验证通过 |
| P0-002 | DONE | `app/infra/route_safety.py:78` / `app/utils/structlog_config.py:349` | `log_fallback` 双实现合并为单一 SSOT（`structlog_config.log_fallback` 为唯一实现；`route_safety.log_fallback` 保留签名但委托到 SSOT）。 | `uv run ruff check app && uv run pyright` | 2026-01-28：已验证通过 |

### P1（高收益：收紧吞错/异常边界 + 去重前端样板）

| ID | 状态 | Location | 说明 | 验证 | 备注/Commit |
|---|---|---|---|---|---|
| P1-001 | DONE | `app/services/accounts_sync/adapters/sqlserver_adapter.py:740` | 避免适配器捕获后直接 `return {}`；改为 fail-fast（上抛），避免把失败伪装成“无权限数据”。 | `uv run ruff check app/services/accounts_sync/adapters/sqlserver_adapter.py && uv run pyright` | 2026-01-28：已验证通过 |
| P1-002 | DONE | `app/services/accounts_sync/adapters/oracle_adapter.py:83` | except 内不再 `return []`；改为 fail-fast（上抛），避免上游误判为“远端 0 账号”从而清空清单。 | `uv run ruff check app/services/accounts_sync/adapters/oracle_adapter.py && uv run pyright` | 2026-01-28：已验证通过 |
| P1-003 | DONE | `app/services/accounts_sync/adapters/postgresql_adapter.py:109` | except 内不再 `return []`；改为 fail-fast（上抛），避免上游误判为“远端 0 账号”从而清空清单。 | `uv run ruff check app/services/accounts_sync/adapters/postgresql_adapter.py && uv run pyright` | 2026-01-28：已验证通过 |
| P1-004 | KEEP | `app/services/statistics/log_statistics_service.py:81` / `app/services/statistics/log_statistics_service.py:107` | Dashboard 图表为非关键展示：查询失败时返回空列表可避免页面整体失败；同时已 `log_error`，便于排障与监控。 | `(manual) review usage in dashboard_charts_service` | 2026-01-28：确认保留回退语义 |
| P1-005 | DONE | `app/static/js/modules/services/**` / `app/templates/base.html` | 抽共享 helper：新增 `ServiceUtils`（`ensureHttpClient/toQueryString`）并在所有 service 中引用；`base.html` 统一引入，避免页面各自复制样板。 | `./scripts/ci/eslint-report.sh quick` | 2026-01-28：eslint quick 通过 |

### P2（长期债务治理：COMPAT 退出机制 + 事务边界收敛）

| ID | 状态 | Location | 说明 | 验证 | 备注/Commit |
|---|---|---|---|---|---|
| P2-001 | DONE | `app/schemas/**`（12 处 `COMPAT`） | 改为严格校验：非法分页/排序/日期直接抛错，不再做默认降级；移除 schema 内 `COMPAT` 分支。 | `uv run ruff check app tests/unit/schemas && uv run pyright` | 2026-01-28：完成并通过单测 |
| P2-002 | DONE | `app/services/history_sessions/history_sessions_read_service.py` / `app/schemas/internal_contracts/sync_details_v1.py` | 移除历史 sync_details 兼容：要求 `version=1`，缺失直接报错，不再注入默认值。 | `uv run pytest -m unit` | 2026-01-28：全量单测通过 |
| P2-003 | DONE | `app/services/ledgers/accounts_ledger_change_history_service.py` / `app/schemas/internal_contracts/account_change_log_diff_v1.py` | 移除 legacy list diff 兼容：只接受 v1 dict 形状，list 直接报错。 | `uv run pytest -m unit` | 2026-01-28：全量单测通过 |
| P2-004 | TODO | `app/**` | 事务边界收敛：评估 `db.session.commit()`（69 处）与 `begin_nested()`（29 处）是否可集中到少数入口（例如 `safe_route_call` / task runner），减少散落样板与语义漂移。 | `uv run pyright` |  |

---

## 进度日志（Changelog）

- 2026-01-28
  - 生成审查报告：`docs/reports/2026-01-28-code-simplicity-review-codex.md`
  - 新增进度跟踪：`docs/plans/2026-01-28-code-simplicity-progress.md`
  - 完成 P0-001：删除未使用的 `error_handler()`（`app/utils/structlog_config.py`）
  - 完成 P0-002：合并 `log_fallback` 双实现（`app/infra/route_safety.py:78` / `app/utils/structlog_config.py:349`）
  - 完成 P1-001：SQLServer DB 权限批量采集失败不再 `return {}`（`app/services/accounts_sync/adapters/sqlserver_adapter.py:740`）
  - 完成 P1-002：Oracle 账号采集失败不再 `return []`（`app/services/accounts_sync/adapters/oracle_adapter.py:83`）
  - 完成 P1-003：PostgreSQL 账号采集失败不再 `return []`（`app/services/accounts_sync/adapters/postgresql_adapter.py:109`）
  - 完成 P1-005：前端 services 抽 `ServiceUtils`（`app/static/js/modules/services/service_utils.js` + 全量 service 改造；`./scripts/ci/eslint-report.sh quick` 通过）
  - 完成 P2-001：schema 层去除 `COMPAT` 降级逻辑，非法参数改为直接报错（更新相关单测）
  - 完成 P2-002：sync_details v1 仅允许 `version=1`，移除缺失版本兼容（更新相关单测）
  - 完成 P2-003：账户变更 diff 仅接受 v1 dict，移除 legacy list 兼容（更新相关单测）

---

## 风险与注意事项（Risks）

- 适配器层（accounts_sync / connection_adapters）对失败语义非常敏感：把失败改为 fail-fast 可能影响“同步会话”的状态口径与 UI 展示，需要先确认上游是否会把空列表当作“清空远端清单”。
- JS services 抽 shared helper 的改动面较广：应以“等价重构”为约束，并以 eslint + 页面冒烟（手动）做最小验证。
- `COMPAT` 分支删除需要配合数据迁移/观测窗口：进度应记录“命中次数”或日志查询方式，避免拍脑袋删兼容。
