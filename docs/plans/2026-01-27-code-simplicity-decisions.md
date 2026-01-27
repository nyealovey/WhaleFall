# 2026-01-27 Code Simplicity Fixes - Decisions (D/E/F)

> 目的：把会改变运行时语义/降级策略/覆盖率策略的点一次性列清，让你统一拍板；我再按你的默认策略批量修复。
>
> 进度追踪仍以 `docs/plans/2026-01-27-code-simplicity-fixes.md` 为准。

---

## 建议的默认策略（推荐）

1) **D（catch-all `except Exception`）**：默认“只捕获可预期异常；其余异常 fail-fast（抛出）”
2) **E（`fallback=True` 降级分支）**：默认只允许出现在“可选能力”（cache / logging / 聚合补偿 / 外部驱动探测）中；凡是影响**数据正确性/权限范围**的，不允许 silent fallback
3) **F（`# pragma: no cover`）**：默认只保留三类：
   - Protocol/typing 抽象方法
   - `__repr__` 等纯调试辅助
   - 明确不可达或环境差异分支（例如某些驱动函数在特定版本不存在）

---

## 决策清单（请按项选择 A/B/C）

### 1) 应用启动：调度器初始化失败是否允许“继续启动”

**涉及：**
- D-001 `app/__init__.py:177`
- E-001 `app/__init__.py:184`

**A. 保持现状（继续启动）**（推荐）
- 继续 `try/except`，记录 `fallback=true`，应用启动不受影响

**B. fail-fast（启动失败）**
- 调度器 init 失败直接抛错，让服务启动失败（更早暴露配置/环境问题）

**C. 可配置开关**
- 增加 setting：`SCHEDULER_STRICT_INIT=true/false`，prod 可 strict，dev 可 continue（需要改 `app/settings.py` + 文档）

---

### 2) 页面降级：统计页面遇到异常时是否返回“空数据页面”

**涉及：**
- D-007 `app/routes/accounts/statistics.py:46`
- D-008 `app/routes/instances/statistics.py:45`

**A. 保持现状（页面降级为 fallback_context/empty_statistics）**（推荐）
- 这类页面属于“可读性/可用性优先”，降级比白屏更友好

**B. fail-fast（异常交给 `safe_route_call` / 全局错误处理）**
- 任何异常都抛出，页面直接报错，不返回“看起来正常但其实是空数据”的 UI

**C. 只对可预期异常降级**
- 仅 `SystemError`（或更具体异常）降级；其他异常抛出

---

### 3) 同步后补偿：容量同步成功后，聚合失败是否允许“忽略”

**涉及：**
- D-026 `app/services/capacity/instance_capacity_sync_actions_service.py:119`
- E-006 `app/services/capacity/instance_capacity_sync_actions_service.py:124`

**A. 保持现状（聚合失败仅记录 fallback 日志）**（推荐）
- 同步与聚合解耦；聚合可由定时任务补跑

**B. fail-fast（聚合失败即视为本次同步失败）**
- 容量同步接口返回失败，避免“同步成功但看不到统计”的弱一致

**C. 允许忽略，但要显式返回 warning**
- API 成功，但 result 内带 `aggregation_failed=true`（需要确认前端/调用方是否接受）

---

### 4) 权限事实（permission_facts）构建失败：是否允许写入“错误占位 facts”

**涉及：**
- D-023 `app/services/accounts_sync/permission_manager.py:452`
- E-005 `app/services/accounts_sync/permission_manager.py:457`
- F-016 `app/services/accounts_sync/permission_manager.py:452`

**A. 保持现状（写入占位 facts，继续同步）**
- 统计/筛选依赖 `permission_facts` 的功能会看到 errors，但同步主流程不断

**B. fail-fast（facts 构建失败即视为该账号同步失败）**（推荐）
- 这是“数据正确性”问题；不应 silent 生成空 capabilities（会误导权限/风险判断）

**C. 降级但隔离：占位写入到单独字段/表，不污染 facts**
- 需要 schema 设计与迁移（成本最高）

---

### 5) Oracle 驱动/权限差异：探测失败是否允许 fallback

**涉及：**
- D-027 `app/services/connection_adapters/adapters/oracle_adapter.py:75`
- E-009 `app/services/connection_adapters/adapters/oracle_adapter.py:81`
- F-031 `app/services/connection_adapters/adapters/oracle_adapter.py:75`
- D-028 `app/services/database_sync/table_size_adapters/oracle_adapter.py:80`
- E-012 `app/services/database_sync/table_size_adapters/oracle_adapter.py:86`

**A. 保持现状（探测失败就按保守路径走）**（推荐）
- 外部驱动/权限差异是真实存在的；fallback 让系统可继续工作

**B. fail-fast（探测失败即视为连接/采集失败）**
- 更严格，但会增加“因环境差异无法工作”的概率

**C. 仅对“可预期异常” fallback**
- 例如仅捕获 `oracledb.Error/TypeError/RuntimeError`，其他异常抛出（更符合“不要吞编程错误”）

---

### 6) 读服务/统计服务：是否继续用 `except Exception -> SystemError` 统一报错

**涉及（同类写法一组拍板，避免逐条争论）：**
- D-012..D-021 `app/services/accounts/account_classifications_read_service.py:*`
- D-033..D-034 `app/services/ledgers/database_ledger_service.py:*`
- D-035..D-037 `app/services/partition/partition_read_service.py:*`
- D-038..D-039 `app/services/scheduler/scheduler_jobs_read_service.py:*`
- D-040..D-044 `app/services/statistics/account_statistics_service.py:*`

**A. 保持现状（任何异常都包成 SystemError）**
- 对外口径稳定，但更容易吞掉编程错误（只在日志里看得到）

**B. 只包“可预期 infra 异常”**（推荐）
- 例如 `SQLAlchemyError/TimeoutError/ConnectionError` 等；编程错误直接抛出交给全局 error handler

**C. 删除这些 try/except，让上层统一处理**
- 代码更短，但需要确认上层（route/api）是否都走 `safe_route_call` / 全局 handler

---

### 7) “记录日志后 re-raise” 的 catch-all：要不要保留

**涉及：**
- D-022 `app/services/accounts_sync/accounts_sync_service.py:322`
- D-029..D-032（diff payload normalize 失败时 log + raise）
- D-031（normalize_sync_details 失败时 log + raise）
- D-045..D-053 `app/services/sync_session_service.py:*`（DB 操作失败时 log + raise）

**A. 保留（仅作为补充上下文日志）**（推荐）
- 不改变异常传播路径，只增加定位维度

**B. 移除（减少 try/except 噪音）**
- 依赖外层日志（`safe_route_call` / 全局 handler / 任务 runner）提供足够信息

**C. 保留，但收窄捕获类型**
- 例如仅捕获 `ValueError/TypeError`（数据形状问题），其余异常直接抛出

---

### 8) F（`# pragma: no cover`）策略：如何处理剩余业务分支的 no cover

**涉及：**
- F-001、F-010、F-012..F-042（Protocol/repr 已在计划里标为 KEEP）

**A. 逐个补测后移除 no cover（最稳）**（推荐）
- 成本高，但能真正证明分支行为

**B. 先移除 no cover，暂不补测（最省事）**
- 如果仓库没有 coverage gate，可以先清噪音；后续再补测试

**C. 保留现状（只在写新测试时顺手清理）**
- 最慢；会长期保留“未证明分支”

---

### 9) cache/adapter fallback 日志：是否需要统一改为 `log_fallback(...)`

**涉及：**
- E-002..E-019（多处直接在 logger 上写 `fallback=True`）

**A. 统一改为 `log_fallback(...)`（字段一致、可检索）**（推荐）
- 行为不变，仅日志口径统一

**B. 保持现状**
- 不改动；但 fallback 字段可能散落在不同 key 结构里

---

## 你给我一个“默认选项”即可

你可以直接回复类似：

```
1A 2C 3A 4B 5C 6B 7A 8A 9A
```

我会按你的选择批量推进，并持续更新 `docs/plans/2026-01-27-code-simplicity-fixes.md`。

