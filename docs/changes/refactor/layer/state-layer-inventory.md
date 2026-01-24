# 前端状态层(Store)迁移清单（SSOT）

> 状态: Active
> 范围: `app/static/js/modules/{views,stores,services}/**` + `app/templates/**`
> 目标: 全站严格遵循 `Page Entry -> Views -> Stores -> Services`

## 判定口径（硬约束）

- Page Entry：只做 wiring（读取 dataset/全局依赖，组装 service/store/view，订阅 store 事件，触发首屏 actions）。
- Views：只做 DOM/交互；不得直连 `window.httpU`；不得自行 `new *Service()`；不得自维护业务 state（接口响应形成的状态应下沉 store）。
- Stores：维护业务状态 + actions；内部调用 services；不得依赖 views/ui；不得直连 `window.httpU`。
- Services：只做 API client 封装（path/query/payload/错误规整）；不得操作 DOM/toast/EventBus。

## 页面清单（page_id）

说明：
- `DONE`：已按分层落到 store/actions（或无需 store 的纯展示页），且无 P0/P1/P2 违例。
- `PARTIAL`：已有 store 或基本分层已成形，但仍存在组件直连 service/兜底降级/自维护业务 state 等遗留。
- `TODO`：缺 store，或页面仍直连 service/httpU，需要迁移。

| page_id | 模板 | 入口脚本 | Store | 状态 | 主要问题 |
|---|---|---|---|---|---|
| AboutPage | `app/templates/about.html` | `app/static/js/modules/views/about/index.js` | - | DONE | 无业务逻辑 |
| ErrorPage | `app/templates/errors/error.html` | `app/static/js/modules/views/errors/error.js` | - | DONE | 无业务逻辑 |
| LoginPage | `app/templates/auth/login.html` | `app/static/js/modules/views/auth/login.js` | - | DONE | 无 service/store 需求 |
| AccountClassificationPage | `app/templates/accounts/account-classification/index.html` | `app/static/js/modules/views/accounts/account-classification/index.js` | `account_classification_store.js` | DONE | - |
| TagsBatchAssignPage | `app/templates/tags/bulk/assign.html` | `app/static/js/modules/views/tags/batch-assign.js` | `tag_batch_store.js` | DONE | - |
| CredentialsListPage | `app/templates/credentials/list.html` | `app/static/js/modules/views/credentials/list.js` | `credentials_store.js` | DONE | CredentialModals 改为注入 store/actions；列表页移除迁移期兜底并统一由 store 提供 gridUrl |
| InstancesListPage | `app/templates/instances/list.html` | `app/static/js/modules/views/instances/list.js` | `instance_store.js` / `instance_crud_store.js` | PARTIAL | 页面内仍维护 selection 等状态（需继续下沉/移除 `selectedInstanceIds`） |
| InstanceDetailPage | `app/templates/instances/detail.html` | `app/static/js/modules/views/instances/detail.js` | `instance_store.js` / `instance_crud_store.js` | PARTIAL | 页面体量大，存在 service 直连与迁移期兜底（后续拆分）；已收口 InstanceModals 注入 |
| InstanceStatisticsPage | `app/templates/instances/statistics.html` | `app/static/js/modules/views/instances/statistics.js` | `instance_store.js` | PARTIAL | 存在迁移期兜底（后续收敛） |
| AccountsListPage | `app/templates/accounts/ledgers.html` | `app/static/js/modules/views/accounts/ledgers.js` | `instance_store.js` | DONE | - |
| DatabaseLedgerPage | `app/templates/databases/ledgers.html` | `app/static/js/modules/views/databases/ledgers.js` | `tag_management_store.js`(组件) | DONE | - |
| AdminPartitionsPage | `app/templates/admin/partitions/index.html` | `app/static/js/modules/views/admin/partitions/index.js` | `partition_store.js` | DONE | - |
| SchedulerPage | `app/templates/admin/scheduler/index.html` | `app/static/js/modules/views/admin/scheduler/index.js` | `scheduler_store.js` | PARTIAL | 基本 OK，后续按“禁兜底/统一注入”收敛 |
| CapacityDatabasesPage | `app/templates/capacity/databases.html` | `app/static/js/modules/views/capacity/databases.js` | - | DONE | - |
| InstanceAggregationsPage | `app/templates/capacity/instances.html` | `app/static/js/modules/views/capacity/instances.js` | - | DONE | - |
| DashboardOverviewPage | `app/templates/dashboard/overview.html` | `app/static/js/modules/views/dashboard/overview.js` | `dashboard_store.js` | DONE | 图表数据下沉 store，入口脚本不再直连 service 方法 |
| AccountsStatisticsPage | `app/templates/accounts/statistics.html` | `app/static/js/modules/views/accounts/statistics.js` | `accounts_statistics_store.js` | DONE | 刷新动作下沉 store，入口脚本不再直连 service 方法 |
| AccountClassificationStatisticsPage | `app/templates/accounts/classification_statistics.html` | `app/static/js/modules/views/accounts/classification_statistics.js` | `account_classification_statistics_store.js` | DONE | 已迁移到 store/actions，views 不再直连 `httpU` |
| TagsIndexPage | `app/templates/tags/index.html` | `app/static/js/modules/views/tags/index.js` | `tag_list_store.js` | DONE | 标签 CRUD + stats 下沉 store；TagModals 改为注入 store/actions |
| AuthListPage | `app/templates/auth/list.html` | `app/static/js/modules/views/auth/list.js` | `users_store.js` | DONE | 用户 CRUD 下沉 store；UserModals 改为注入 store/actions |
| SyncSessionsPage | `app/templates/history/sessions/sync-sessions.html` | `app/static/js/modules/views/history/sessions/sync-sessions.js` | `task_runs_store.js` | DONE | 总数/详情/取消下沉 store，入口脚本不再直连 service 方法 |
| LogsPage | `app/templates/history/logs/logs.html` | `app/static/js/modules/views/history/logs/logs.js` | `logs_store.js` | DONE | 统计/详情/缓存下沉 store，入口脚本不再直连 service 方法 |
| AccountChangeLogsPage | `app/templates/history/account_change_logs/account-change-logs.html` | `app/static/js/modules/views/history/account-change-logs/account-change-logs.js` | `account_change_logs_store.js` | DONE | 统计/详情/缓存下沉 store，入口脚本不再直连 service 方法 |

## 全局/共享脚本清单（非 page_id，但同样必须分层）

| 模块 | 引用点 | 状态 | 主要问题 | 目标改造 |
|---|---|---|---|---|
| `app/static/js/modules/views/auth/modals/change-password-modals.js` | `app/templates/base.html:310` | DONE | - | 已改为 `auth_service.js` + `auth_store.js`，views 不再直连 `httpU` |
| `app/static/js/modules/views/components/permissions/permission-viewer.js` | `accounts/ledgers.html` / `instances/detail.html` | DONE | - | 已改为 `PermissionViewer.configure({ fetchPermissions, showPermissionsModal, toast })` 注入依赖 |
| `app/static/js/modules/views/admin/partitions/partition-list.js` | `admin/partitions/index.html` | DONE | - | 已改为注入 `gridUrl`（由 Page Entry 提供），组件内不再 new Service |
| `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js` | `admin/partitions/index.html` | DONE | - | 已移除 direct request fallback，强制依赖 `PartitionStoreInstance` |
| `app/static/js/modules/views/components/charts/data-source.js` | capacity 两个页面 | DONE | - | 已改为 `createCapacityStatsDataSource({ service })` 并由 Page Entry 注入 `CapacityStats.Manager({ dataSource })` |
| `app/static/js/modules/views/components/tags/tag-selector-controller.js` | 多页面 include | DONE | - | 已改为注入 `TagManagementStore`；组件内不再 `new TagManagementService()`/`createTagManagementStore()` |
| `app/static/js/modules/views/instances/modals/instance-modals.js` | instances list/detail | DONE | - | 已改为注入 `InstanceCrudStore`；组件内不再 `new InstanceService()`/`window.location.reload()` |

## Store Backlog（待新增）
