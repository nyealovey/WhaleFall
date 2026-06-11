# WhaleFall 产品源码简化复扫报告

> 状态: Active  
> 负责人: team  
> 创建: 2026-06-11  
> 更新: 2026-06-11  
> 范围: `app/**` 产品源码, 重点复扫 `docs/reports/code-simplicity-review-2026-06-09.md` 中的问题项  
> 关联: `docs/reports/code-simplicity-review-2026-06-09.md`

## Simplification Analysis

### Core Purpose

`app/**` 的核心目的仍然清晰: 提供 Flask API、Jinja 页面、静态 JS/CSS、后台任务、数据库同步、权限分类、容量统计、告警和外部系统同步能力。相较 2026-06-09 报告, 当前代码已经把一部分“职责源头分裂”收敛到明确门面, 例如调度器内置元数据、`TaskRun.summary_json` envelope、Veeam summary writer、备份指标合并器。

本次复扫发现的主要复杂度已经从“缺少公共能力”转为“调用侧继续复制编排细节”: `TaskRun` 生命周期、前端 store helper、按钮 loading fallback、权限 DSL 分支、事务提交点和 broad exception 仍然散落在多个文件中。

### Scan Scope

- 覆盖: `app/**` 产品源码。
- 排除: `tests/**`、`scripts/**`、第三方 vendor、缓存产物。
- 产品文件数: 795。
- 产品行数: 约 146799 行。
- 扩展名分布: 511 个 `.py`, 157 个 `.js`, 67 个 `.html`, 52 个 `.css`, 3 个 `.yaml`, 3 个 `.md`, 2 个 `.pyi`。
- 最大文件:
  - `app/static/js/modules/views/instances/detail.js`: 3399 行
  - `app/static/js/modules/views/cluster/list.js`: 1646 行
  - `app/static/js/modules/views/instances/list.js`: 1499 行
  - `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`: 1429 行
  - `app/services/accounts_sync/adapters/sqlserver_adapter.py`: 1394 行
  - `app/services/veeam/sync_actions_service.py`: 1326 行
  - `app/services/veeam/provider.py`: 1164 行
- 静态复杂度证据: `uv run ruff check app --select C901,PLR0911,PLR0912,PLR0915,SIM,RET,ERA --output-format concise` 返回 14 个 `C901`。
- 重复模式证据:
  - `ensureEmitter`: 18 个 store 文件定义。
  - `ensureSuccessResponse`: 9 个 store 文件定义。
  - `setButtonLoading/clearButtonLoading/withButtonLoading`: 12 个 view 文件命中。
  - `except Exception`: 48 个真实捕获点。
  - `db.session.commit()`: 114 处。
  - `begin_nested()`: 30 处。
  - `legacy_instance_id` / `COMPAT`: 本次目标路径未命中, 属于已整改项。

### 2026-06-09 报告整改对照

| 旧编号 | 旧问题 | 当前状态 | 复扫结论 |
| --- | --- | --- | --- |
| F01 | 定时任务内置元数据源头分裂 | 部分完成 | `BUILTIN_SCHEDULER_TASKS` 已作为 Python registry, `TASK_FUNCTIONS` 由 registry 派生, 前端编辑弹窗消费 `editable_fields`。`scheduler_tasks.yaml` 现在只保留默认 trigger, 可降为 P2 跟踪。 |
| F02 | `TaskRun` 生命周期重复 | 部分完成 | 已有 `TaskRunsWriteService`, 但 9 个任务/服务仍直接编排 `resolve_or_start_run`, 10 个文件直接构造 `TaskRunItemInit`, 11 个文件直接 finalize。问题从 P1 保留。 |
| F03 | `TaskRun.summary_json` envelope 不一致 | 基本完成 | 已新增 `app/services/task_runs/task_run_summary_builders.py`; `cluster_status`, `ad_sync`, `veeam` 均有 v1 envelope 测试覆盖。降为观察项。 |
| F04 | 调度器前端 fallback 和死入口 | 部分完成 | 已接入 `UI.withButtonLoading`, 但 `showLoadingState` / `hideLoadingState` wrapper 仍保留。P2。 |
| F05 | 前端 store helper 重复 | 未完成 | `ensureEmitter` 和 `ensureSuccessResponse` 仍在多个 store 复制。P1。 |
| F06 | 前端按钮 loading 重复实现 | 未完成 | `button-loading.js` 已存在, 但多个 view 仍写本地 fallback。P1。 |
| F07 | Veeam 同步链路多职责混合 | 部分完成 | 已拆出 `run_summary_writer.py`, `backup_file_metric_merger.py`, `match_sampler.py`, 但 provider 分页、timeout sample、sync action stage failure 仍复杂。P2。 |
| F08 | 权限 DSL / snapshot / facts 的数据库类型分支重复 | 未完成 | `collect_dsl_v4_validation_errors`, `_fn_has_privilege`, `normalize_permission_snapshot_categories_v4`, `_extract_privileges` 仍触发 C901。P1。 |
| F09 | 账户同步服务和 adapter 过度内聚 | 未完成 | `_sync_with_session`, MySQL `_prefetch_roles`, Oracle `enrich_permissions` 仍触发 C901。P2。 |
| F10 | 告警、风险中心、群集状态读写链路耦合 | 部分完成 | 群集状态已有 `ClusterStatusDetectionResult` contract, 风险中心 SQL Server issue map 仍复杂。P2。 |
| F11 | API namespace 膨胀和兼容残留 | 部分完成 | `legacy_instance_id` 和分类 `name` 兼容已清理, 但 `accounts.py` 中 `parse_account_scope` 仍重复 6 处, RESTX model inline 仍偏重。P3。 |
| F12 | broad exception / fallback 策略不清 | 未完成 | 真实 `except Exception` 仍有 48 处, `sync_session_service.py` 单文件 9 处。P2。 |

### Unnecessary Complexity Found

- `app/tasks/*.py` 与 `app/services/veeam/sync_actions_service.py` 已经共享 `TaskRunsWriteService`, 但每个任务仍手工处理 run 创建、item 初始化、取消检查、summary 写入、partial success、commit 和异常收尾。
- `app/static/js/modules/stores/*.js` 仍重复 `ensureEmitter` / `ensureSuccessResponse`, 错误对象、事件接口和 fallback message 口径容易漂移。
- `app/static/js/modules/ui/button-loading.js` 已提供 `UI.withButtonLoading`, 但多个 view 继续保留本地 `setButtonBusy`、`startButtonLoading`、`showLoadingState` / `hideLoadingState`。
- 权限分类 DSL 验证、DSL 运行、permission snapshot normalize、facts builder 都继续按 `fn` / `scope` / `db_type` 写长分支。
- Veeam provider 仍支持多种未确认分页形状, `fetch_backup_file_records` 还同时做去重、请求、timeout sample、failed sample、record normalize 和聚合统计。
- `sync_session_service.py` 仍有多处 broad exception 只做日志封装或失败标记, 可以用窄异常集合或小包装函数减少重复。
- 事务提交点分散在 service/task/repository 边界, 114 处 `db.session.commit()` 让“谁拥有事务”不够直观。

### Code to Remove

- `TaskRun` 调用侧生命周期重复: 预计删除 250-450 LOC。
  - 重点文件: `app/tasks/accounts_sync_tasks.py`, `app/tasks/capacity_collection_tasks.py`, `app/tasks/capacity_aggregation_tasks.py`, `app/tasks/account_classification_daily_tasks.py`, `app/tasks/account_classification_auto_tasks.py`, `app/tasks/ad_sync_tasks.py`, `app/tasks/cluster_status_sync_tasks.py`, `app/tasks/email_alert_tasks.py`, `app/services/veeam/sync_actions_service.py`。
- 前端 store helper 重复: 预计删除 90-160 LOC。
  - 重点文件: `app/static/js/modules/stores/auth_store.js`, `credentials_store.js`, `users_store.js`, `task_runs_store.js`, `tag_list_store.js`, `account_change_logs_store.js`, `instance_crud_store.js`, `mysql_clusters_store.js`, `sqlserver_clusters_store.js`。
- 前端按钮 loading fallback: 预计删除 120-220 LOC。
  - 重点文件: `app/static/js/modules/views/integrations/veeam/source.js:42`, `app/static/js/modules/views/integrations/jumpserver/source.js:38`, `app/static/js/modules/views/integrations/ad-domain/configs.js:53`, `app/static/js/modules/views/admin/risk-center/rule-settings.js:23`, `app/static/js/modules/views/cluster/list.js:1616`, `app/static/js/modules/views/admin/scheduler/index.js:654`。
- 权限 DSL / facts / snapshot 分支: 预计删除 120-220 LOC, 同时把 4 个 `C901` 降到阈值内。
- broad exception 日志样板: 预计删除 80-160 LOC。
- Veeam provider 和 sync action 剩余阶段逻辑: 预计删除 180-320 LOC, 但需要按测试分批推进。

### Simplification Recommendations

1. 先收敛前端 store helper。
   - Current: 18 个 store 自己实现 `ensureEmitter`, 9 个 store 自己实现 `ensureSuccessResponse`。
   - Proposed: 新增 `app/static/js/modules/stores/store-utils.js`, 提供 `ensureEmitter`, `ensureSuccessResponse`, `handleStoreError` 或 `createStoreHelpers`。
   - Impact: 低风险, 预计删除 90-160 LOC, 后续 store 行为更一致。

2. 用 `UI.withButtonLoading` 替换 view 本地 fallback。
   - Current: 页面先探测 `setButtonLoading/clearButtonLoading`, 缺失时再手工改 `innerHTML`。
   - Proposed: 页面直接调用 `UI.withButtonLoading(button, action, { loadingText, fallbackText })`; 缺少全局 UI 时 fail fast, 不再复制 spinner HTML。
   - Impact: 预计删除 120-220 LOC, 同时减少按钮 disabled 恢复和无障碍状态漂移。

3. 给 `TaskRunsWriteService` 增加更高层的小型生命周期 helper。
   - Current: 调用侧仍要手写 `resolve_or_start_run`, `init_items`, `write_summary`, `finalize_run_with_summary`, partial success status override 和 `db.session.commit()`。
   - Proposed: 保持现有 service, 增加小函数或小对象封装常见模式: `start_builtin_run`, `init_items_from`, `complete_with_summary`, `fail_run_and_pending_items`, `complete_with_partial_success`。
   - Impact: 预计删除 250-450 LOC, 新任务少复制 5-7 个生命周期细节。

4. 权限 DSL 使用 dispatch table, 不再把所有函数塞进一个验证器。
   - Current: `collect_dsl_v4_validation_errors` 内嵌 `_validate_node`; `_fn_has_privilege` 按 scope 分支; snapshot/facts 按 db_type 分支。
   - Proposed: `FN_ARG_VALIDATORS`, `SCOPE_PRIVILEGE_CHECKERS`, `CATEGORY_NORMALIZERS_BY_DB_TYPE`, `PRIVILEGE_EXTRACTORS_BY_DB_TYPE`。
   - Impact: 预计删除 120-220 LOC, `C901` 从 4 个点移除, 新 db type 只加注册项。

5. 将 `sync_session_service.py` 的重复 try/except 收敛为 repository action wrapper。
   - Current: `app/services/sync_session_service.py:108`, `175`, `212`, `271`, `322`, `373`, `394`, `415`, `450` 多处 broad exception。
   - Proposed: `_run_session_write(action, *, operation, record_id, failure_message)` 或窄异常集合, 统一日志字段。
   - Impact: 预计删除 60-120 LOC, 同时让真正需要 broad 的外部边界更醒目。

6. Veeam 继续只做职责切片, 不做大重写。
   - Current: `fetch_backup_file_records` 和 `_extract_next_link` 仍复杂; `sync_actions_service.py:910` 的异常块重复写 binding、fail item、cancel stages、summary。
   - Proposed: 先抽 `BackupFileFetchAccumulator` 与 `NextLinkResolver`, 再抽 `fail_current_stage_and_finalize`。
   - Impact: 预计删除 180-320 LOC, 但建议每次只改一个 stage 并保留现有契约测试。

### YAGNI Violations

- 前端 view 的本地按钮 fallback 已不再必要。仓库已经有 `app/static/js/modules/ui/button-loading.js`, 页面继续保留手工 spinner 和 `innerHTML` 恢复逻辑属于“以防全局 UI 不存在”的重复实现。
- `app/services/veeam/provider.py:_extract_next_link` 支持顶层、`data`、`paging`、`pagination`、`links`、`meta` 以及 list/dict 多种 next 形状。若当前 Veeam API 只需要其中 1-2 种, 其余属于面向未知未来 API 的泛化。
- 多处 `except Exception` 只为补日志或失败标记, 没有恢复行为。这里更适合窄异常集合加统一 wrapper, 否则每个调用点都背负一段维护成本。
- API namespace 中 inline RESTX model 不是当前最大风险, 但继续把 schema、parser、controller、compat 校验放在同一文件, 会让 namespace 文件越来越难删减。

### Final Assessment

Total potential LOC reduction: 900-1530 LOC, 约占当前 `app/**` 总行数 0.6%-1.0%; 若只看本次复扫 hot-path, 预计可减少 5%-8%。

Complexity score: Medium-High。相较 2026-06-09, 最危险的 summary envelope 与调度器漏同步已经明显缓解; 但任务生命周期、前端重复 helper、权限 DSL、broad exception 仍是高收益简化区。

Recommended action: Proceed with simplifications in batches。第一批做前端 store helper 和按钮 loading, 风险最低且 LOC 收益明确; 第二批做权限 DSL dispatch 与 `TaskRun` lifecycle helper; 第三批再处理 Veeam、事务边界和大文件拆分。

## 当前 P1 清单

### P1-001 前端 store helper 统一

- Affected files:
  - `app/static/js/modules/stores/auth_store.js:29`
  - `app/static/js/modules/stores/credentials_store.js:34`
  - `app/static/js/modules/stores/users_store.js:28`
  - `app/static/js/modules/stores/task_runs_store.js:26`
  - `app/static/js/modules/stores/tag_list_store.js:28`
  - `app/static/js/modules/stores/account_change_logs_store.js:26`
  - `app/static/js/modules/stores/instance_crud_store.js:34`
  - `app/static/js/modules/stores/mysql_clusters_store.js:19`
  - `app/static/js/modules/stores/sqlserver_clusters_store.js:29`
- Problem: `ensureEmitter` / `ensureSuccessResponse` 重复定义。
- Suggested simplification: `store-utils.js` 统一导出 helper, 由各 store 引入。
- Estimated LOC reduction: 90-160。

### P1-002 前端按钮 loading 统一

- Affected files:
  - `app/static/js/modules/views/integrations/veeam/source.js:42`
  - `app/static/js/modules/views/integrations/jumpserver/source.js:38`
  - `app/static/js/modules/views/integrations/ad-domain/configs.js:53`
  - `app/static/js/modules/views/admin/risk-center/rule-settings.js:23`
  - `app/static/js/modules/views/cluster/list.js:1616`
  - `app/static/js/modules/views/admin/scheduler/index.js:654`
- Problem: 已有 `UI.withButtonLoading`, 但页面继续复制 fallback。
- Suggested simplification: 页面只保留业务 action, loading 行为统一由 UI 模块提供。
- Estimated LOC reduction: 120-220。

### P1-003 `TaskRun` 生命周期调用侧去重

- Affected files:
  - `app/tasks/accounts_sync_tasks.py:76`
  - `app/tasks/capacity_collection_tasks.py:294`
  - `app/tasks/capacity_aggregation_tasks.py:207`
  - `app/tasks/capacity_current_aggregation_tasks.py:45`
  - `app/tasks/account_classification_daily_tasks.py:33`
  - `app/tasks/account_classification_auto_tasks.py:41`
  - `app/tasks/ad_sync_tasks.py:53`
  - `app/tasks/cluster_status_sync_tasks.py:66`
  - `app/tasks/email_alert_tasks.py:65`
  - `app/services/veeam/sync_actions_service.py:836`
- Problem: 底层写入服务已存在, 但任务侧仍重复生命周期流程。
- Suggested simplification: 在 `TaskRunsWriteService` 之上增加更高层 helper, 只封装任务运行记录生命周期, 不碰业务同步逻辑。
- Estimated LOC reduction: 250-450。

### P1-004 权限 DSL / permission facts 分支收敛

- Affected files:
  - `app/utils/account_classification_dsl_v4.py:50`
  - `app/utils/account_classification_dsl_v4.py:66`
  - `app/utils/account_classification_dsl_v4.py:294`
  - `app/schemas/internal_contracts/permission_snapshot_v4.py:165`
  - `app/services/accounts_permissions/facts_builder.py:129`
- Problem: 验证、运行、normalize、facts extract 分别维护分支。
- Suggested simplification: dispatch table 注册函数校验器、scope evaluator、db type normalizer/extractor。
- Estimated LOC reduction: 120-220。

## 当前 P2 清单

### P2-001 Veeam 剩余复杂度继续切片

- Affected files:
  - `app/services/veeam/provider.py:385`
  - `app/services/veeam/provider.py:876`
  - `app/services/veeam/sync_actions_service.py:910`
- Problem: 已拆出 summary writer、metric merger、sampler, 但 provider 和 stage failure 收尾仍复杂。
- Suggested simplification: 先抽 backup file fetch accumulator 和 next link resolver, 再抽 stage failure finalizer。
- Estimated LOC reduction: 180-320。

### P2-002 账户同步 session 结果写入收敛

- Affected files:
  - `app/services/accounts_sync/accounts_sync_service.py:222`
  - `app/services/sync_session_service.py:108`
  - `app/services/sync_session_service.py:175`
  - `app/services/sync_session_service.py:212`
  - `app/services/sync_session_service.py:271`
  - `app/services/sync_session_service.py:322`
  - `app/services/sync_session_service.py:373`
  - `app/services/sync_session_service.py:394`
  - `app/services/sync_session_service.py:415`
  - `app/services/sync_session_service.py:450`
- Problem: session 创建、record 写入、失败标记、异常日志重复交织。
- Suggested simplification: session write wrapper + failure result writer。
- Estimated LOC reduction: 100-180。

### P2-003 调度器默认任务源头继续收窄

- Affected files:
  - `app/core/constants/scheduler_jobs.py:19`
  - `app/scheduler.py:66`
  - `app/config/scheduler_tasks.yaml:1`
  - `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:137`
- Problem: 前端硬编码已清理, 但默认任务 ID 仍同时出现在 Python registry 与 YAML trigger 配置中。
- Suggested simplification: 当前可保留。若后续继续收敛, 让 YAML 只按 registry key 覆盖 trigger, 并用测试保证所有 YAML id 都存在于 registry。
- Estimated LOC reduction: 低, 主要是防漏改。

### P2-004 事务边界梳理

- Affected files: `app/**`
- Problem: `db.session.commit()` 114 处, `begin_nested()` 30 处。service/task/repository 边界的事务所有权不够统一。
- Suggested simplification: 先按功能簇盘点 owner, 不建议一次性全改。优先处理 task run lifecycle 与 sync session 两条链路。
- Estimated LOC reduction: 80-160, 主要收益是降低语义漂移。

## 当前 P3 清单

### P3-001 API namespace 继续减重

- Affected files:
  - `app/api/v1/namespaces/accounts.py:619`
  - `app/api/v1/namespaces/accounts.py:742`
  - `app/api/v1/namespaces/accounts.py:792`
  - `app/api/v1/namespaces/accounts.py:847`
  - `app/api/v1/namespaces/accounts.py:900`
  - `app/api/v1/namespaces/accounts.py:957`
  - `app/api/v1/namespaces/instances.py:82`
  - `app/api/v1/namespaces/accounts_classifications.py:25`
- Problem: 旧兼容字段已清理, 但 parser/controller/model 仍混在 namespace 中。
- Suggested simplification: 先抽 account statistics query parser helper, 再考虑 RESTX model factory。
- Estimated LOC reduction: 60-140。

### P3-002 大文件分域拆分

- Affected files:
  - `app/static/js/modules/views/instances/detail.js`
  - `app/static/js/modules/views/cluster/list.js`
  - `app/static/js/modules/views/instances/list.js`
  - `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`
  - `app/services/accounts_sync/adapters/sqlserver_adapter.py`
- Problem: 大文件本身不是 bug, 但多个子域共处一页/一个 adapter, 后续简化会被文件体积拖慢。
- Suggested simplification: 只在做功能改动时顺手迁移一个子域, 不做单独“大拆分 PR”。
- Estimated LOC reduction: 不以删除行数为目标, 以降低变更冲突为目标。

## 建议推进顺序

1. 前端 `store-utils.js`。
2. 前端 `UI.withButtonLoading` 调用侧替换。
3. 权限 DSL dispatch table。
4. `TaskRun` lifecycle helper。
5. `sync_session_service.py` broad exception 与写入 wrapper。
6. Veeam provider / sync action 剩余复杂度切片。
