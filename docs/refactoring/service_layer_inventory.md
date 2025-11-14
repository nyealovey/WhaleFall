# 前端服务层抽离清单

> 目标：为“服务层优先”策略提供现状盘点，明确哪些接口可最先抽离到 `app/static/js/modules/services/`，并标记涉及的页面/组件，便于并行改造。

## 扫描方法
- 使用 `rg "/[a-z_]+/api"` 与 `rg "httpClient|httpU"` 检索 `app/static/js/**/*.js`。
- 按接口前缀归类，并记录消费者文件与主要操作（GET/POST/DELETE 等）。
- 过滤仅与底层 `http-u.js`（transport）有关的调用，聚焦业务 API。

## 服务候选列表

| 优先级 | 领域服务 | 代表接口 | 当前消费者 | 备注 |
| --- | --- | --- | --- | --- |
| S0-1 | **SyncSessionsService** | `GET /sync_sessions/api/sessions`, `GET /sync_sessions/api/sessions/:id`, `GET /sync_sessions/api/sessions/:id/error-logs`, `POST /sync_sessions/api/sessions/:id/cancel` | `pages/history/sync_sessions.js` | ✅ 服务层已实现（`modules/services/sync_sessions_service.js`）并在会话页面接入，后续可继续拆分 store/视图。 |
| S0-2 | **TagManagementService** | `GET /tags/api/tags`, `GET /tags/api/categories`, `GET /tags/api/instances`, `GET /tags/api/all_tags`, `POST /tags/api/batch_assign_tags`, `POST /tags/api/batch_remove_all_tags`, `POST /tags/api/batch_delete`, `POST /tags/api/delete/:id` | `components/tag_selector.js`, `pages/tags/batch_assign.js`, `pages/tags/index.js`, `pages/accounts/list.js`(通过 TagSelector) | ✅ 已抽离为 `modules/services/tag_management_service.js`，并在标签组件/页面接入。 |
| S0-3 | **AccountClassificationService**（已部分存在于 `app/static/js/api/accountClassification.js`） | `/account_classification/api/**`（分类 CRUD、规则 CRUD、stats、auto-classify、permissions） | `pages/accounts/account_classification.js`, `common/permission_policy_center.js` | ✅ 已替换为 `modules/services/account_classification_service.js`，并删除旧 API 脚本。 |
| S0-4 | **SchedulerService** | `/scheduler/api/jobs`, `/scheduler/api/jobs/:id/(resume|pause|run)`, `/scheduler/api/jobs/reload`, `/scheduler/api/jobs/by-func` | `pages/admin/scheduler.js` | ✅ 已由 `modules/services/scheduler_service.js` 承担，页面抛弃 `$.ajax`。 |
| S0-5 | **InstanceManagementService** | `/account_sync/api/instances/:id/sync`, `/capacity/api/instances/:id/sync-capacity`, `/instances/api/...`（账户历史、数据库容量、批量操作、统计） | `pages/instances/detail.js`, `pages/instances/list.js`, `pages/instances/statistics.js`, `pages/accounts/list.js` | ✅ `modules/services/instance_management_service.js` 接管实例/容量/批量/API，账户列表同步 `syncAllAccounts` 复用该服务。 |
| S0-6 | **AccountSyncService** | `POST /account_sync/api/sync-all` | `pages/accounts/list.js` | ✅ 已并入 InstanceManagementService（`syncAllAccounts()`）。 |
| S0-7 | **ConnectionService** | `/connections/api/test`, `/connections/api/validate-params`, `/connections/api/batch-test`, `/connections/api/status/:id` | `components/connection-manager.js`, `pages/instances/detail.js`, `pages/instances/list.js`, `pages/instances/form.js` | ✅ `modules/services/connection_service.js` 在 `base.html` 全局注入。 |
| S0-8 | **CredentialsService** | `POST /credentials/api/credentials/:id/delete` | `pages/credentials/list.js` | ✅ `modules/services/credentials_service.js`。 |
| S0-9 | **LogsService** | `GET /logs/api/modules`, `/logs/api/stats`, `/logs/api/search`, `/logs/api/detail/:id` | `pages/history/logs.js` | ✅ `modules/services/logs_service.js`。 |
| S0-10 | **DashboardService** | `GET /dashboard/api/charts?type=logs` | `pages/dashboard/overview.js` | ✅ `modules/services/dashboard_service.js`。 |
| S0-11 | **CapacityStatsService** | 配置化调用 `/instance_aggr/api/...`, `/database_aggr/api/...`, `/aggregations/api/...` | `pages/capacity_stats/*.js`, `common/capacity_stats/data_source.js` | ✅ `modules/services/capacity_stats_service.js` ＋ data_source 重写。 |
| S0-12 | **PartitionService** | `/partition/api/info`, `/partition/api/create`, `/partition/api/cleanup`, `/partition/api/aggregations/core-metrics` | `pages/admin/partitions.js`, `pages/admin/aggregations_chart.js` | ✅ `modules/services/partition_service.js`。 |
| S0-13 | **PermissionService** | `/account/api/:id/permissions`, `/instances/api/:instanceId/accounts/:accountId/permissions`, `/account_classification/api/permissions/:dbType` | `common/permission-viewer.js`, `components/permission-button.js`, `pages/instances/detail.js`, `common/permission_policy_center.js` | ✅ `modules/services/permission_service.js`，`base.html` 全局加载。 |

> 说明：编号仅表示建议顺序，可按实际迭代安排调整。S0-1～S0-4 推荐作为首批试点，覆盖会话中心、标签体系、账户分类和调度任务四类典型场景，完成后即可验证服务层的可复用性。

## 建议的落地动作
1. **创建 `modules/services/README.md`**：记录命名规则（snake_case 文件名 + CapWords 类或工厂函数）、依赖注入方式（传入 `httpClient`）、错误结构等。
2. **按表中顺序实现服务**：每引入一个新服务，即回到对应页面，将直接的 `httpClient` 调用替换为服务方法，保持页面逻辑不变。
3. **集中测试**：每个服务覆盖的页面需在迁移后执行 `make quality`、相关页面自测，并在 PR 模板里添加“服务层抽离”检查项。
4. **同步文档**：迁移完成的领域在本清单中标记状态（例如 ✅ 完成 / 🔄 进行中），并补充到 `docs/refactoring/frontend_script_refactor_plan.md` 的 S0 进度中。

借此清单，可快速指派子任务（例如“实现 SyncSessionsService 并替换会话页面”、“封装 TagManagementService 并复用在 TagSelector 与批量操作”），推动前端分层重构的第一阶段。
