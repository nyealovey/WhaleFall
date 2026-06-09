# WhaleFall 产品源码简化审查报告

生成日期: 2026-06-09

## Simplification Analysis

### Core Purpose

`app/**` 的核心目的很明确: 提供 Flask API、Jinja 页面、静态 JS/CSS、后台任务与数据库同步/告警能力。当前复杂度主要不是框架选择问题, 而是同一类职责在多个文件里重复实现: 定时任务生命周期、`TaskRun` 汇总结构、前端 store 响应校验、按钮 loading、数据库类型分支、兼容字段与外部系统同步采样。

### Scan Scope

- 覆盖: `app/**` 产品源码。
- 未纳入问题清单: 第三方静态资源、图片、字体和缓存产物。
- 文件数: 771。
- 扩展名分布: 504 个 `.py`, 142 个 `.js`, 67 个 `.html`, 49 个 `.css`, 3 个 `.yaml`, 3 个 `.md`, 2 个 `.pyi`, 1 个 `typed` 标记。
- 代码行数: 146074 total。
- 最大文件: `app/static/js/modules/views/instances/detail.js` 3399 行, `app/static/js/modules/views/cluster/list.js` 1646 行, `app/services/veeam/sync_actions_service.py` 1569 行, `app/static/js/modules/views/instances/list.js` 1499 行, `app/services/veeam/provider.py` 1415 行。
- Ruff 复杂度证据: `uv run ruff check app --select C901,PLR0911,PLR0912,PLR0915,SIM,RET,ERA --output-format concise` 产出 19 个 `C901`。
- JS 静态检查证据: `npx eslint app/static/js/modules --format stylish --no-warn-ignored` 无输出。

### Priority Summary

| Priority | Count | Meaning |
| --- | ---: | --- |
| P1 | 8 | 影响多个功能文件或任务链路, 建议优先收敛 |
| P2 | 19 | 单文件/局部函数复杂, 有明确拆分或复用方向 |
| P3 | 9 | 兼容残留、开发 fallback 或大文件边界, 需要策略后再处理 |

### Unnecessary Complexity Found

- 定时任务内置元数据分散在 YAML、Python 常量、任务映射和前端数组中, 已出现 `sync_cluster_status` 后端存在而前端弹窗未识别的差异。
- 多个任务文件重复 `_resolve_run_id`、取消检查、初始化 item、失败终止、成功汇总和 `finalize_run`, 造成每个新任务都要手工复制生命周期细节。
- 多个任务直接写 `TaskRun.summary_json`, 且 `cluster_status` 与 `ad_sync` 存在非标准 summary envelope 写法。
- Veeam 同步链路把 API 解析、匹配、采样、持久化、任务进度、汇总和错误处理混在一个服务簇中。
- 前端 store 重复 `ensureSuccessResponse` / `ensureEmitter`; 多个页面重复按钮 loading fallback。
- DSL、权限快照、facts builder、账户同步 adapter 都在同一个函数里用 `db_type` 分支承载不同数据库差异。
- API namespace 中保留兼容字段和旧参数 fallback, 但缺少集中转换层或退场计划。
- 一些 broad `except Exception` 只做日志后原样抛出, 简化价值高于保护价值。

### Code to Remove

- 任务生命周期重复: 预计可从 `app/tasks/*.py` 与 `app/services/veeam/sync_actions_service.py` 合并/删除 500-900 LOC。
- 前端按钮 loading fallback: 预计可删除 120-220 LOC, 统一走 `UI.setButtonLoading` / `UI.clearButtonLoading` 或 `UI.withButtonLoading`。
- store helper 重复: 预计可删除 80-150 LOC。
- Veeam 同步 summary 与采样重复: 预计可删除 250-450 LOC。
- 兼容参数与 inline API model 若制定退场计划: 中期可删除 150-300 LOC。

### Simplification Recommendations

1. 先建立小型任务运行 helper/facade。
   - Current: 每个任务手写 run 解析、item 初始化、失败 item 收尾、summary 写入、finalize。
   - Proposed: `TaskRunLifecycle` 或 `TaskRunRecorder` 封装 `start_or_resolve_run`、`init_items`、`write_summary`、`fail_pending_items`、`finalize_with_errors`。
   - Impact: 定时任务新增/修改时少碰 5-7 个细节分支, 预计减少 500+ LOC。

2. 让内置任务元数据只有一个源头。
   - Current: `scheduler_tasks.yaml`、`TASK_FUNCTIONS`、`BUILTIN_TASK_IDS`、前端弹窗数组各自维护。
   - Proposed: 后端从同一份 schema 派生内置 ID 与 function 映射, 前端通过 API 读取 `is_builtin` 或内置任务清单。
   - Impact: 消除 `sync_cluster_status` 这类漏同步。

3. 把前端通用工具沉到共享模块。
   - Current: store 与按钮状态散落在多个 view/store 文件。
   - Proposed: `store-utils.js` 和 `UI.withButtonLoading`。
   - Impact: 页面逻辑更短, loading 行为更一致。

4. Veeam 链路按职责拆小。
   - Current: 同步动作服务同时做流程编排、summary、stage、异常与多源结果改写。
   - Proposed: provider 只负责 API 数据归一, repository 只负责持久化/查询, sync action 只编排阶段, summary 走统一 builder。
   - Impact: 降低最重同步链路的维护风险。

5. 数据库类型分支改为 dispatch table。
   - Current: `if db_type == ...` 在 DSL、facts、snapshot、adapter 中重复出现。
   - Proposed: 按数据库类型注册 normalizer/extractor/validator。
   - Impact: 新数据库能力不会继续拉长已有函数。

### YAGNI Violations

- `app/services/veeam/provider.py:_extract_next_link` 支持过多未证实分页形状, 更像“为了兼容未来 API”而非当前需求。
- `app/settings.py` 的非生产 fallback 可能是开发便利, 但应有显式环境策略; 否则会继续把“临时能跑”混入运行时配置。
- API 兼容字段如 `name`、`legacy_instance_id` 缺少退场边界, 导致新旧协议长期共存。
- 多个 `except Exception` 只做日志后 `raise`, 增加缩进与噪音, 没有改变行为。

### Final Assessment

Total potential LOC reduction: 8%-12% of reviewed hot-path code, not 8%-12% of entire repository.

Complexity score: High for scheduled tasks / Veeam / permission DSL; Medium for frontend stores and API compatibility; Low for isolated settings fallback.

Recommended action: Proceed with simplifications in batches. 第一批处理 P1 的定时任务元数据、`TaskRun` 生命周期 helper、summary envelope 和前端共享 helper; 第二批处理 Veeam 与权限 DSL; 第三批处理兼容退场和大文件拆分。

## 功能簇问题

### F01 定时任务内置元数据源头分裂

- Priority: P1
- Affected files:
  - `app/config/scheduler_tasks.yaml:1-70`
  - `app/scheduler.py:64-72`
  - `app/core/constants/scheduler_jobs.py:3-10`
  - `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:221-229`
- Problem: 默认任务 `sync_accounts`、`calculate_account`、`sync_databases`、`calculate_database`、`sync_veeam_backups`、`sync_cluster_status`、`email_alert` 在多个地方重复定义。前端弹窗内置数组遗漏 `sync_cluster_status`, 后端常量和 YAML 已包含。
- Why complex: 每次新增、改名、隐藏内置任务都要同步 4 个位置, 且前端没有类型/测试保障。
- Suggested simplification: 后端输出 `is_builtin`、`task_id`、`task_name`、`editable_fields` 等元数据; 前端只消费 API。短期至少从同一 Python metadata 派生 `BUILTIN_TASK_IDS` 与 `TASK_FUNCTIONS`。
- Estimated LOC reduction: 30-80, 更重要的是减少跨文件漏改。

### F02 定时任务 `TaskRun` 生命周期重复

- Priority: P1
- Affected files:
  - `app/tasks/accounts_sync_tasks.py:70-120`, `441-519`, `656-770`
  - `app/tasks/capacity_collection_tasks.py:25-66`, `118-140`, `250-272`, `294-455`
  - `app/tasks/capacity_aggregation_tasks.py:201-342`, `391-545`
  - `app/tasks/capacity_current_aggregation_tasks.py:41-169`, `283-365`
  - `app/tasks/account_classification_daily_tasks.py:28-120`, `231-369`, `455-565`
  - `app/tasks/account_classification_auto_tasks.py:36-188`, `215-277`, `314-454`
  - `app/tasks/ad_sync_tasks.py:46-67`, `249-272`, `275-337`
  - `app/tasks/cluster_status_sync_tasks.py:59-208`, `211-350`
  - `app/tasks/email_alert_tasks.py:59-220`, `224-265`
  - `app/services/veeam/sync_actions_service.py:160-220`, `828-947`, `1004-1033`
- Problem: 每个任务都重复处理 run 复用/创建、item 初始化、取消、失败 item 收尾、summary 写入、`finalize_run`、`completed_with_errors`。
- Why complex: 行为差异会自然漂移。`sync_cluster_status` 曾经就是这类生命周期问题的高风险区; 当前还有新增任务继续复制相同模式。
- Suggested simplification: 增加轻量内部 helper, 只封装运行记录生命周期, 不改变业务同步逻辑。任务函数保留“取数据/处理数据”的主体。
- Estimated LOC reduction: 500-900。

### F03 `TaskRun.summary_json` envelope 不一致

- Priority: P1
- Affected files:
  - `app/schemas/task_run_summary.py:96-125`
  - `app/tasks/cluster_status_sync_tasks.py:46-56`
  - `app/tasks/ad_sync_tasks.py:85-100`, `249-272`
  - `app/services/veeam/sync_actions_service.py:977-1001`, `1004-1033`
- Problem: 标准结构是 `version/common/ext`, 且 `common.metrics` 为 list。`cluster_status` 在 `TaskRunSummaryFactory.base` 后写顶层 `payload["metrics"]` dict; `ad_sync` 手写 `version/task_key/status/ext`; Veeam 直接手动穿透 `ext.data` 后提交。
- Why complex: 读端需要容忍多种 summary 形状, 后续报表/详情页会被迫 defensive parsing。
- Suggested simplification: 只允许任务通过 summary builder/facade 写入; 旧 summary 展示兼容留在读层, 新写入统一 envelope。
- Estimated LOC reduction: 80-180。

### F04 调度器前端存在本地 fallback 和死入口

- Priority: P2
- Affected files:
  - `app/static/js/modules/views/admin/scheduler/index.js:180-228`
  - `app/static/js/modules/views/admin/scheduler/index.js:657-665`
  - `app/static/js/modules/views/admin/scheduler/index.js:676-770`
- Problem: 重新初始化按钮手工改 `innerHTML`; 日志入口仍是“待实现”; loading helper 在页面内重复实现一套 `UI.setButtonLoading` fallback。
- Why complex: 页面维护者要理解本地 DOM 状态缓存、全局 UI helper 和未完成入口三套行为。
- Suggested simplification: 删除本地 fallback, 统一 `UI.withButtonLoading`; 日志入口要么接真实 `TaskRun` 日志页, 要么移除按钮。
- Estimated LOC reduction: 70-130。

### F05 前端 store helper 重复

- Priority: P2
- Affected files:
  - `app/static/js/modules/stores/auth_store.js:29-46`
  - `app/static/js/modules/stores/credentials_store.js:34-51`
  - `app/static/js/modules/stores/mysql_clusters_store.js:19-26`
  - `app/static/js/modules/stores/sqlserver_clusters_store.js:29-36`
  - `app/static/js/modules/stores/task_runs_store.js:26-43`
  - `app/static/js/modules/stores/users_store.js:28-45`
  - `app/static/js/modules/stores/tag_list_store.js:28-45`
  - `app/static/js/modules/stores/account_change_logs_store.js:26-70`
  - `app/static/js/modules/stores/account_classification_store.js:42`
  - `app/static/js/modules/stores/scheduler_store.js:64`
  - `app/static/js/modules/stores/instance_store.js:115`
- Problem: `ensureEmitter` 和 `ensureSuccessResponse` 在大量 store 中复制。
- Why complex: 错误消息口径、事件接口 fallback 和异常类型容易不一致。
- Suggested simplification: 增加 `app/static/js/modules/stores/store-utils.js`, 导出 `ensureEmitter`、`ensureSuccessResponse`、`unwrapSuccessData`。
- Estimated LOC reduction: 80-150。

### F06 前端按钮 loading 重复实现

- Priority: P2
- Affected files:
  - `app/static/js/modules/views/integrations/ad-domain/configs.js:49-68`
  - `app/static/js/modules/views/integrations/jumpserver/source.js:37-53`
  - `app/static/js/modules/views/integrations/veeam/source.js:41-57`
  - `app/static/js/modules/views/admin/risk-center/rule-settings.js:22-35`
  - `app/static/js/modules/views/instances/detail.js:489-509`
  - `app/static/js/modules/views/instances/list.js:1064-1089`, `1394-1400`
  - `app/static/js/modules/views/cluster/list.js:1616-1630`
- Problem: 多处页面各自保存原始 HTML、塞 spinner、禁用按钮、恢复按钮。
- Why complex: loading UI 的无障碍属性、异常恢复、图标按钮文案容易漂移。
- Suggested simplification: 在 `UI` 层提供 `withButtonLoading(button, action, options)`; 页面只传 action。
- Estimated LOC reduction: 120-220。

### F07 Veeam 同步链路多职责混合

- Priority: P1
- Affected files:
  - `app/services/veeam/provider.py:385-476`, `600-671`, `1091-1118`
  - `app/services/veeam/sync_actions_service.py:760-958`, `977-1033`, `1421-1472`
  - `app/repositories/veeam_repository.py:499-558`
  - `app/tasks/veeam_backup_sync_tasks.py:14-53`
- Problem: Veeam provider 负责 API 分页、匹配、采样; sync action 负责阶段进度、summary、异常、写入策略、多源聚合; repository 又做候选匹配和序列化。
- Why complex: 任一 Veeam 行为变更都容易跨 provider/service/repository/task 四层改动。
- Suggested simplification: 拆出 `VeeamMatchSampler`、`VeeamRunSummaryWriter`、`VeeamBackupFileMetricMerger`; repository 的 `find_best_backup_for_instance_name` 拆成候选构建、查询、payload 序列化。
- Estimated LOC reduction: 250-450。

### F08 权限 DSL / snapshot / facts 的数据库类型分支重复

- Priority: P2
- Affected files:
  - `app/utils/account_classification_dsl_v4.py:50-120`, `294-320`
  - `app/schemas/internal_contracts/permission_snapshot_v4.py:165-209`
  - `app/services/accounts_permissions/facts_builder.py:129-172`
- Problem: DSL 校验、运行时函数、snapshot normalize、facts extract 都直接写数据库类型和 scope 分支。
- Why complex: 新增一个数据库字段时, 需要同步改多个分支函数。
- Suggested simplification: 用 dispatch table 注册每个 `db_type` 的 category normalizer、privilege extractor、DSL scope handler。
- Estimated LOC reduction: 120-250。

### F09 账户同步服务和 adapter 过度内聚

- Priority: P2
- Affected files:
  - `app/services/accounts_sync/accounts_sync_service.py:222-345`
  - `app/services/accounts_sync/adapters/mysql_adapter.py:389-474`
  - `app/services/accounts_sync/adapters/oracle_adapter.py:212-283`
  - `app/services/accounts_sync/adapters/sqlserver_adapter.py` 1394 行
  - `app/services/accounts_sync/permission_manager.py:482`
- Problem: 会话管理、结果校验、失败记录、权限查询、错误 augmentation 混在同一函数或大 adapter 内。
- Why complex: 同步失败路径与权限采集路径互相干扰, 异常处理写法也更难复用。
- Suggested simplification: `accounts_sync_service` 中提取 session result writer; MySQL role 预取抽查询配置; Oracle 权限错误 augmentation 独立 helper; SQL Server adapter 按 inventory/permission/facts 拆模块。
- Estimated LOC reduction: 180-350。

### F10 告警、风险中心、群集状态读写链路耦合

- Priority: P1
- Affected files:
  - `app/services/alerts/email_alert_event_service.py:40-117`
  - `app/tasks/cluster_status_sync_tasks.py:105-149`
  - `app/services/risk_center/risk_center_read_service.py:990-1045`
  - `app/services/mysql_clusters/service.py:328-363`
- Problem: 容量告警事件创建、群集状态任务事件、风险中心 SQL Server issue map、MySQL 拓扑检测都各自内联查询/判断/映射。
- Why complex: 同一“同步异常”概念在任务、告警、风险中心和群集管理里分散表达。
- Suggested simplification: 把“异常检测结果”定义成小 DTO/contract, 任务写入、告警事件、风险中心读取都消费同一 contract。
- Estimated LOC reduction: 150-280。

### F11 API namespace 膨胀和兼容残留

- Priority: P3
- Affected files:
  - `app/api/v1/namespaces/instances.py:82-145`
  - `app/api/v1/namespaces/accounts.py:627`, `752`, `805`, `863`, `919`, `979`
  - `app/api/v1/namespaces/accounts_classifications.py:41-42`, `819`
- Problem: RESTX model 大量内联在 namespace 顶部; `parse_account_scope(... legacy_instance_id=instance_id)` 在多个 endpoint 重复; 分类写入仍保留 `name` 兼容字段。
- Why complex: namespace 文件同时承载 schema、parser、compat 转换、controller 逻辑, 旧协议没有集中退场点。
- Suggested simplification: API model 移到 `schemas/api_models` 或 namespace-local model factory; legacy 参数转换集中到 parser helper; 为 `name` 和 `legacy_instance_id` 写退场计划。
- Estimated LOC reduction: 150-300, 但需要兼容策略。

### F12 broad exception / fallback 策略不清

- Priority: P3
- Affected files:
  - `app/services/sync_session_service.py:104-116`, `373-380`, `394-401`, `415-422`
  - `app/services/veeam/sync_actions_service.py:903-957`
  - `app/services/accounts_sync/permission_manager.py:482`
  - `app/services/connection_adapters/adapters/oracle_adapter.py:72-87`
  - `app/__init__.py:172-184`
  - `app/settings.py:129-135`, `525-550`
- Problem: 有些 `except Exception` 只记录后重抛, 有些 fallback 是开发便利, 有些 fallback 是兼容外部驱动异常。它们没有统一标注“为什么必须 broad”。
- Why complex: 审查者难区分必要保护、开发兜底和可以删除的噪音。
- Suggested simplification: 对纯日志重抛改窄异常或移除 wrapper; 对外部系统 fallback 增加命名异常集合; 对 settings fallback 明确环境策略。
- Estimated LOC reduction: 80-180。

## 逐文件明细

### app/config/scheduler_tasks.yaml

- Issue: 默认任务清单与 `app/scheduler.py`、`app/core/constants/scheduler_jobs.py`、前端弹窗数组重复维护。
- Evidence: `sync_cluster_status` 在 `52-60` 定义, 但前端内置数组缺失。
- Recommended action: 保留 YAML 作为调度默认配置, 但由后端加载后派生 `is_builtin` 和可编辑策略。
- Priority: P1

### app/scheduler.py

- Issue: `TASK_FUNCTIONS` 在 `65-72` 再次维护函数映射。
- Evidence: 与 YAML `function` 字段一一对应, 但没有自动校验。
- Recommended action: 让 YAML 的 `function` 只引用已注册 task key, 或由 Python registry 生成 YAML 校验输入。
- Priority: P1

### app/core/constants/scheduler_jobs.py

- Issue: `BUILTIN_TASK_IDS` 在 `3-10` 是第三份内置任务 ID 清单。
- Evidence: 它包含 `sync_cluster_status`, 前端数组未包含。
- Recommended action: 从统一 registry 导出 set, 不再手写。
- Priority: P1

### app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js

- Issue: `buildPayload` 在 `221-229` 写死内置任务数组, 漏掉 `sync_cluster_status`。
- Recommended action: 使用 job payload 中的 `is_builtin` 或 API 返回的 `editable_fields`; 该文件不应知道全部内置任务 ID。
- Priority: P1

### app/static/js/modules/views/admin/scheduler/index.js

- Issue: `180-228` 手工 loading; `657-665` 日志入口未实现; `676-770` 复制全局 loading helper fallback。
- Recommended action: 将 reload action 包成 `UI.withButtonLoading`; 删除未实现入口或接入真实 `TaskRun` 日志/详情。
- Priority: P2

### app/tasks/accounts_sync_tasks.py

- Issue: `_resolve_run_id`、`_is_cancelled`、`_finalize_no_instances`、`_finalize_success`、`_finalize_failure` 重复 `TaskRun` 生命周期。
- Evidence: `70-120`, `441-519`, `656-770`。
- Recommended action: 任务主体只负责账户同步; run 生命周期交给共享 helper。
- Priority: P1

### app/tasks/capacity_collection_tasks.py

- Issue: `_finalize_task_failed` 同时更新 session、run、pending items、返回 API payload。
- Evidence: `25-66`; no-active 与 success finalize 在 `118-140`, `250-272`。
- Recommended action: 拆出 run failure finalizer; session failure 和 response payload 留在 runner/task 层。
- Priority: P1

### app/tasks/capacity_aggregation_tasks.py

- Issue: `201-342` 包含 run 创建、skip、failure、success 三套 lifecycle, 与容量采集和账户分类重复。
- Recommended action: 统一 `skip_run`、`fail_run`、`complete_run` helper。
- Priority: P1

### app/tasks/capacity_current_aggregation_tasks.py

- Issue: `41-169` 与聚合/分类任务重复 run 解析、取消检查、summary 写入、失败 pending item 收尾。
- Recommended action: 复用通用 task-run helper, 当前文件只保留当前周期聚合参数与业务结果。
- Priority: P2

### app/tasks/account_classification_daily_tasks.py

- Issue: `28-120`、`231-369`、`455-565` 重复 run 解析、无规则/无账户/failure/success finalize。
- Recommended action: 让“无规则/无账户”成为标准 skipped/failed result 类型, 统一写 summary。
- Priority: P1

### app/tasks/account_classification_auto_tasks.py

- Issue: `36-188` 与 daily 分类任务结构高度相似, 但 task key 和输入不同。
- Recommended action: 与 daily 分类共享分类任务 run recorder, 把自动/定时差异变成参数。
- Priority: P2

### app/tasks/ad_sync_tasks.py

- Issue: `_summary` 在 `85-100` 手写非标准 summary; `_finalize_run` 在 `249-272` 手工设置 `COMPLETED_WITH_ERRORS`。
- Recommended action: 改用 `TaskRunSummaryFactory.base` 和统一 `finalize_with_errors`。
- Priority: P2

### app/tasks/cluster_status_sync_tasks.py

- Issue: `_summary` 在 `46-56` 写顶层 `metrics` dict, 与 `TaskRunSummaryFactory` 的 `common.metrics` list 不一致。
- Issue: `_record_result` 在 `105-149` 同时更新 totals、item、alert event 并提交。
- Issue: `_fail_run` 在 `195-208` 手工遍历 pending/running item。
- Recommended action: 统一 summary builder; alert event 从标准 cluster result DTO fan out; failure 收尾交给 task-run helper。
- Priority: P1

### app/tasks/email_alert_tasks.py

- Issue: `59-220` 与其他任务重复 run 解析、item 初始化、summary 写入、unexpected failure。
- Recommended action: 使用共享 task-run helper; 邮件任务只保留 rule/send step 业务明细。
- Priority: P2

### app/tasks/veeam_backup_sync_tasks.py

- Issue: 文件本身是薄 wrapper, 但实际 lifecycle 藏在 `app/services/veeam/sync_actions_service.py`。
- Evidence: `14-53` 只包 `sync_backups_background`。
- Recommended action: 保留 wrapper, 但把 Veeam run lifecycle 拉回统一 task-run helper, 避免服务层绕过统一任务规范。
- Priority: P1

### app/services/veeam/sync_actions_service.py

- Issue: `760-958` 的主同步块同时做校验、写快照、写 stage、写 summary、finalize、日志和异常处理。
- Issue: `903-957` broad exception 里重复构造失败 summary、取消后续 stage、再抛出。
- Issue: `977-1001` 手动穿透 `summary.ext.data` 并提交。
- Issue: `1004-1033` `finalize_run` 后又把 partial success 的 run status 改成字符串 `"completed"`。
- Issue: `1421-1472` 逐字段合并 backup file metrics, C901 复杂度 15。
- Recommended action: 拆 `VeeamRunStageRecorder`、`VeeamRunSummaryWriter`、`merge_backup_file_payload`; partial success 状态交给 `TaskRunsWriteService` 或明确状态常量。
- Priority: P1

### app/services/veeam/provider.py

- Issue: `match_backup_objects` 在 `385-476` 同时做匹配判断、缺失机器名采样、未匹配日志和结果组装, C901 复杂度 16。
- Issue: `fetch_backup_file_records` 在 `600-671` 重复 timeout/failure sample 收集, C901 复杂度 11。
- Issue: `_extract_next_link` 在 `1091-1118` 支持多种分页形状, C901 复杂度 15, 属于过度泛化候选。
- Recommended action: 抽 `_match_backup_object`、`SampleCollector`、分页 path table; 只保留实际 API 需要的分页形状。
- Priority: P1

### app/repositories/veeam_repository.py

- Issue: `find_best_backup_for_instance_name` 在 `499-558` 同时构建候选、查询、比较最新 row、序列化 payload, C901 复杂度 12。
- Recommended action: 拆 `_build_binding_match_candidates`、`_query_latest_snapshot_for_binding`、`_serialize_best_match`。
- Priority: P2

### app/utils/account_classification_dsl_v4.py

- Issue: `collect_dsl_v4_validation_errors` 在 `50-120` 内嵌 `_validate_node`, C901 复杂度 27/23。
- Issue: `_fn_has_privilege` 在 `294-320` 按 scope 分支, C901 复杂度 11。
- Recommended action: validator dispatch: `op` validator、function validator、scope evaluator 分开注册。
- Priority: P1

### app/schemas/internal_contracts/permission_snapshot_v4.py

- Issue: `normalize_permission_snapshot_categories_v4` 在 `165-209` 按 `db_type` 分支 normalize category, C901 复杂度 12。
- Recommended action: `NORMALIZE_CATEGORY_BY_DB_TYPE = {}` dispatch table; 每个数据库一个小函数。
- Priority: P2

### app/services/accounts_permissions/facts_builder.py

- Issue: `_extract_privileges` 在 `129-172` 按 `db_type` 构造 privilege buckets, C901 复杂度 11。
- Recommended action: 与 snapshot normalizer 共用 db-type extraction registry。
- Priority: P2

### app/services/accounts_sync/accounts_sync_service.py

- Issue: `_sync_with_session` 在 `222-345` 嵌套局部 helper, 同时创建 session、record、执行同步、校验 details、写 success/failure、记录异常, C901 复杂度 14。
- Recommended action: 拆 `SyncSessionRunContext` 或 `_write_record_from_sync_result`; 外层只保留流程顺序。
- Priority: P2

### app/services/accounts_sync/adapters/mysql_adapter.py

- Issue: `_prefetch_roles` 在 `389-474` 对 direct/default role 两套 SQL 重复执行、过滤、去重, C901 复杂度 16。
- Recommended action: 抽 `_fetch_role_edges(query, warning_event)` 返回 map; direct/default 只传配置。
- Priority: P2

### app/services/accounts_sync/adapters/oracle_adapter.py

- Issue: `enrich_permissions` 在 `212-283` 同时解析目标用户名、遍历账户、查询权限、给 permissions 添加 errors, C901 复杂度 11。
- Recommended action: 拆 `_resolve_target_usernames` 与 `_append_permission_error`。
- Priority: P2

### app/services/accounts_sync/adapters/sqlserver_adapter.py

- Issue: 文件 1394 行, 是产品源码中第 7 大文件; 即使当前 Ruff 没报 C901, 账户 inventory、权限、角色/facts 转换长期堆在一个 adapter 中。
- Recommended action: 后续按 `inventory_reader`、`permission_reader`、`snapshot_builder` 拆子模块; 优先确保 public adapter API 不变。
- Priority: P3

### app/services/accounts_sync/permission_manager.py

- Issue: `482` 附近存在 broad `except Exception`; 权限路径通常应区分连接错误、查询错误、数据形状错误。
- Recommended action: 收敛为 adapter/repository 异常集合, 或在注释/测试中说明必须 broad 的外部驱动场景。
- Priority: P3

### app/services/alerts/email_alert_event_service.py

- Issue: `record_database_capacity_events` 在 `40-117` 同时做 settings gate、row validation、baseline 查询、阈值判断、payload 构造和事件创建, C901 复杂度 12。
- Recommended action: 拆 `_resolve_capacity_growth_candidate` 和 `_should_create_capacity_event`。
- Priority: P2

### app/services/risk_center/risk_center_read_service.py

- Issue: `_sqlserver_cluster_issue_map` 在 `990-1045` 做表存在检查、绑定 map、replica risk、database risk, C901 复杂度 11。
- Recommended action: 拆 `_load_sqlserver_cluster_bindings`、`_collect_abnormal_replicas`、`_collect_abnormal_databases`。
- Priority: P2

### app/services/mysql_clusters/service.py

- Issue: `_detect_instance_topology` 在 `328-363` 内联 `SHOW REPLICA STATUS` 和 `SHOW SLAVE STATUS` fallback、权限错误判断和 read-only 检测, C901 复杂度 11。
- Recommended action: 抽 `_try_replica_status` 与 `_try_legacy_slave_status`, 返回统一 topology result。
- Priority: P2

### app/services/database_sync/table_size_adapters/oracle_adapter.py

- Issue: `fetch_table_sizes` 在 `129-190` 开始连续处理 tablespace 检查、多视图 fallback、查询执行和 row parse, C901 复杂度 11。
- Recommended action: 抽 `_query_segments_from_visible_view` 与 `_query_user_segments_fallback`。
- Priority: P2

### app/services/connection_adapters/adapters/oracle_adapter.py

- Issue: `connect` 在 `51-120` 同时做凭据解析、DSN、thin/thick 检测、client lib path 探测、连接创建, C901 复杂度 11。
- Issue: `72-87` 对 `oracledb.is_thin()` 使用 broad exception fallback。
- Recommended action: 拆 `_build_dsn`、`_ensure_oracle_client_initialized`; broad fallback 保留需写明驱动版本场景。
- Priority: P2

### app/services/jumpserver/provider.py

- Issue: `_resolve_db_type` 在 `325-361` 内嵌 alias mapper, 同时从 platform 和多个字段收集候选, C901 复杂度 13。
- Recommended action: 复用全局 database type alias registry, 该函数只负责收集候选。
- Priority: P2

### app/services/sync_session_service.py

- Issue: `104-116`, `373-380`, `394-401`, `415-422` 等多处 `except Exception` 只做日志后重抛。
- Recommended action: 捕获 repository/SQLAlchemy 异常集合; 或建立 `_run_repository_action` 包装日志字段, 减少重复 try/except。
- Priority: P3

### app/settings.py

- Issue: `_resolve_sqlite_fallback_url` / `_resolve_sqlite_fallback_path` 在 `129-135`; 非生产缺省 `PASSWORD_ENCRYPTION_KEY` 和 `DATABASE_URL` fallback 在 `525-550`。
- Risk: 这是开发便利, 不建议直接删除; 但需要显式环境策略, 防止测试/本地/演示行为继续影响产品假设。
- Recommended action: 文档化 `development/test/production` 配置策略, 并在 settings 校验中标注 fallback 是否启用。
- Priority: P3

### app/__init__.py

- Issue: `172-184` 捕获所有 scheduler init 异常, 仅记录后重抛。
- Recommended action: 若只为补充结构化日志, 捕获 `SCHEDULER_INIT_EXCEPTIONS`; 若无额外恢复行为, 可让异常自然冒泡并由上层记录。
- Priority: P3

### app/api/v1/namespaces/instances.py

- Issue: 文件 1022 行; `82-145` 等位置大量 RESTX model inline 定义在 namespace 顶部。
- Recommended action: model factory 或 schemas 子模块承载 API model; namespace 保留 route/controller。
- Priority: P3

### app/api/v1/namespaces/accounts.py

- Issue: `parse_account_scope(... legacy_instance_id=instance_id)` 重复出现在 `627`, `752`, `805`, `863`, `919`, `979`。
- Recommended action: 查询 parser helper 一次性产出 `account_scope`; 给 `legacy_instance_id` 设置退场计划。
- Priority: P3

### app/api/v1/namespaces/accounts_classifications.py

- Issue: `41-42` 保留 `name` 兼容字段; `819` 继续用 `legacy_instance_id` 解析 scope。
- Recommended action: 兼容字段集中转换, 并在 API 文档/前端迁移完成后删除。
- Priority: P3

### app/static/js/modules/stores/auth_store.js

- Issue: `29-46` 重复 `ensureEmitter` 和 `ensureSuccessResponse`。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/credentials_store.js

- Issue: `34-51` 重复 store helper。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/mysql_clusters_store.js

- Issue: `19-26` 重复 `ensureSuccessResponse`。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/sqlserver_clusters_store.js

- Issue: `29` 附近重复 `ensureSuccessResponse`。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/task_runs_store.js

- Issue: `26-43` 重复 store helper。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/users_store.js

- Issue: `28-45` 重复 store helper。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/tag_list_store.js

- Issue: `28-45` 重复 store helper。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/account_change_logs_store.js

- Issue: `26-70` 重复 `ensureEmitter` / `ensureSuccessResponse`。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/account_classification_store.js

- Issue: `42` 附近重复 `ensureEmitter`。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/scheduler_store.js

- Issue: `64` 附近重复 `ensureEmitter`。
- Recommended action: 引入共享 `store-utils.js`。
- Priority: P2

### app/static/js/modules/stores/instance_store.js

- Issue: `115` 附近重复 `ensureEmitter`; 文件本身 942 行, store 逻辑偏重。
- Recommended action: 先复用 helper; 后续按 query/cache/mutation 拆分。
- Priority: P2

### app/static/js/modules/views/integrations/ad-domain/configs.js

- Issue: `49-68` 重复按钮 busy fallback。
- Recommended action: 使用 `UI.withButtonLoading`。
- Priority: P2

### app/static/js/modules/views/integrations/jumpserver/source.js

- Issue: `37-53` 重复按钮 busy fallback。
- Recommended action: 使用 `UI.withButtonLoading`。
- Priority: P2

### app/static/js/modules/views/integrations/veeam/source.js

- Issue: `41-57` 重复按钮 busy fallback。
- Recommended action: 使用 `UI.withButtonLoading`。
- Priority: P2

### app/static/js/modules/views/admin/risk-center/rule-settings.js

- Issue: `22-35` 在页面内实现 start/stop loading fallback。
- Recommended action: 使用 `UI.withButtonLoading`, 页面只保留保存规则逻辑。
- Priority: P2

### app/static/js/modules/views/instances/detail.js

- Issue: 文件 3399 行, 是当前最大 JS 文件; `489-509` 手工处理按钮 loading。
- Issue: 同一文件还承载审计信息、备份信息、变更历史 modal 等多个 detail 子域。
- Recommended action: 先替换 loading helper; 后续按 audit/backup/history 子模块拆分, 每次只迁移一个子域。
- Priority: P3

### app/static/js/modules/views/instances/list.js

- Issue: 文件 1499 行; `1064-1089`, `1394-1400` 手工 loading。
- Recommended action: 先统一 loading; 后续把列表 action 与渲染 helper 分离。
- Priority: P3

### app/static/js/modules/views/cluster/list.js

- Issue: 文件 1646 行; `1616-1630` 本地 `withButtonLoading` / `setButtonLoading`; 同时承载 MySQL、SQL Server、AG 账户、AG 状态、拓扑弹窗等多个子域。
- Recommended action: 先统一 loading; 再按 modal/dashboard 子模块拆分, 保留现有页面入口不变。
- Priority: P2

## 建议批次

1. Batch 1 - 定时任务基础收敛:
   - 统一内置任务元数据。
   - 新增 task-run lifecycle helper。
   - 修正 `sync_cluster_status` / `ad_sync` summary envelope 新写入。
   - 补单元测试覆盖 `sync_cluster_status`、账户同步、容量同步、Veeam wrapper。

2. Batch 2 - 前端共享 helper:
   - 新增 store helper。
   - 新增 `UI.withButtonLoading`。
   - 替换 scheduler、integrations、risk-center、cluster/instances 中重复 loading。

3. Batch 3 - Veeam 简化:
   - 拆匹配采样、分页 next link、backup file metrics merge、summary writer。
   - 保持 API 和数据写入结果不变, 以 focused tests 验证。

4. Batch 4 - 权限/账户同步 dispatch:
   - `db_type` normalizer/extractor/evaluator 注册表。
   - MySQL/Oracle adapter 局部拆函数。

5. Batch 5 - 兼容退场:
   - `legacy_instance_id`、分类 `name` 字段、inline API model 的迁移计划。
   - 只在前端和调用方确认后删除兼容入口。
