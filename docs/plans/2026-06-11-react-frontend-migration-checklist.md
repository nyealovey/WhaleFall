# React Frontend Migration Checklist

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-06-11
> 更新: 2026-06-16
> 范围: `/console` React 新前端迁移进度
> 关联: `frontend/`, `app/api/v1/`, `docs/Obsidian/standards/doc/guide/documentation.md`

## 目标

在不影响旧站点的前提下，逐步把后台页面迁移到 `/console` React 新前端。迁移目标已从“只读首屏”升级为“完整替代旧版”：新版页面展示内容必须与旧版一致，展示形态可以调整；旧页面继续保留为回滚入口，直到对应页面的字段、筛选、详情、写操作和高风险动作全部在 React 内完成验收。

## 更新规则

- 每完成一批页面迁移，必须更新本文档。
- 已迁移页面必须记录新路径、旧路径、接入 API、迁移范围和验证命令。
- 只迁移只读首屏时，状态写为 `Done - read-only`，不要标记成完整替换。
- 进入完整替代返工后，状态写为 `Parity - content`、`Parity - actions` 或 `Done - replacement`，并说明剩余缺口。
- 涉及新增、删除、同步、导入、导出、批量操作时，需要单独补充风险与回滚说明。

## 当前摘要

- React 入口: `/console`
- 路由级已接入页面: 22
- 路由级占位页: 0（仅表示导航路径已有 React 页面，不代表完整替代完成）
- 完整替代完成页: 0
- 完整替代缺口页: 22
- 当前策略: 内容 parity 已覆盖全部导航页，继续按表单、详情、批量、导入导出和高风险确认拆分返工
- 旧站点状态: 保持不动，作为回滚入口
- UI 基线: shadcn 风格组件优先，当前已接入 Button、Card、Badge、Input、Textarea、Separator、Table、Tabs、Skeleton、Alert、Dialog、AlertDialog、Progress、Chart、Select、Checkbox、Switch、Label、Tooltip、Sonner、TanStack DataTable

## 完整替代验收口径

- 展示内容与旧版一致：指标、列表字段、筛选项、状态、详情信息和空态不能缺项。
- 展示形态可以调整：优先使用 shadcn 组件、TanStack Table 和 Recharts，避免继续复制旧版 DOM 结构。
- 表格筛选由新版 DataTable 工具栏承载；如果表格自带筛选，不再额外做页面级筛选区。
- 写操作必须在 React 内调用 `/api/v1/` 或新增受控 API，不能只跳回旧版后标记完整替代。
- 高风险动作需要单独记录测试、回滚路径和权限校验。

## UI 组件迁移原则

- 后续迁移优先引入和复用 shadcn/Radix 成熟组件；凡是 shadcn 已覆盖的 Select、Checkbox、Switch、Tooltip、Dialog、AlertDialog、Tabs、Toast/Sonner、Label、Button、Input、Textarea 等基础交互，不再手写同类控件。
- 只有业务强相关组合组件可以在本项目内封装，例如 DataTable、查询框架、指标卡和图表面板；这些封装也应基于 shadcn 原语组合，而不是重新实现基础交互。
- 新增原生 `<select>`、`input[type="checkbox"]`、原生 `title` tooltip 或自制 toast 前，必须先确认 shadcn 是否已有可用组件；确需手写时，需要在本清单记录原因、影响范围和后续替换计划。
- 所有已迁移写操作统一通过 Sonner 展示进行中、成功和失败反馈；新动作不得只静默刷新列表。

## 已完成

| 新前端路径 | 旧页面路径 | 状态 | 接入 API | 备注 |
| --- | --- | --- | --- | --- |
| `/console/dashboard` | `/dashboard/` | Parity - content | `/api/v1/dashboard/overview`, `/api/v1/dashboard/status`, `/api/v1/dashboard/charts?type=all`, `/api/v1/dashboard/activities`, `/api/v1/risk-center/summary` | 已按旧版补齐刷新数据、数据库实例/账户总数/总容量/数据库总数指标、风险告警、错误和告警日志趋势、系统状态与运行时间；活动流和分类分布作为现有 API 快照保留 |
| `/console/risk-center` | `/risk-center/` | Parity - content | `/api/v1/risk-center/summary`, `/api/v1/risk-center/cards?limit=12` | 已按旧版补齐刷新、总实例/高中低健康指标、搜索/严重度/数据库类型/状态/标签筛选外观、数据库类型分组风险墙和备份/审计/托管/群集/任务核心信号；筛选联动与高风险动作 API 待迁移 |
| `/console/instances` | `/instances/` | Parity - actions | `/api/v1/instances?page=1&limit=200`, `/api/v1/instances/{id}`, `/api/v1/instances/{id}/connection-status`, `/api/v1/accounts/ledgers?instance_id={id}&owner_type=instance&include_roles=true`, `/api/v1/instances/{id}/ag-accounts`, `/api/v1/databases/sizes?instance_id={id}&latest_only=true&include_inactive=true`, `/api/v1/instances/{id}/audit-info`, `/api/v1/instances/{id}/backup-info`, `POST /api/v1/instances`, `PUT /api/v1/instances/{id}`, `/api/v1/instances/actions/test-connection`, `/api/v1/instances/actions/batch-test-connections`, `/api/v1/instances/actions/batch-delete`, `/api/v1/instances/actions/batch-create`, `/api/v1/instances/imports/template`, `/api/v1/instances/{id}/actions/sync-accounts`, `/api/v1/instances/{id}/actions/sync-capacity`, `/api/v1/instances/{id}/actions/sync-audit-info`, `/api/v1/integrations/veeam/actions/sync-instance/{id}`, `/api/v1/instances/{id}/actions/restore`, `DELETE /api/v1/instances/{id}`, `/api/v1/instances/exports` | 已按旧版补齐名称、类型、主机/IP、状态、审计、已托管、备份、活跃、版本/同步、标签、操作列；搜索、类型、状态、审计、托管、备份、标签筛选由 DataTable 工具栏承载；实例详情、连接状态、账户信息、SQL Server AG 账户信息、容量信息、审计信息、备份信息已迁移到 shadcn Tabs/DataTable；基础新增/编辑实例表单、单实例连接测试、实例级账户/容量/审计/备份同步、当前可见列表批量测试、批量移入回收站、批量导入 CSV、删除到回收站、恢复已接入 React；高级连接参数、凭据选择器待增强；导出 CSV 链接已接入 |
| `/console/database-ledgers` | `/databases/ledgers` | Parity - actions | `/api/v1/databases/ledgers?page=1&limit=200`, `/api/v1/databases/ledgers/exports`, `/api/v1/databases/ledgers/actions/sync-all`, `/api/v1/databases/{id}/tables/sizes`, `/api/v1/databases/{id}/tables/sizes/actions/refresh` | 已按旧版补齐数据库/实例、类型、数据库大小、标签、操作列；搜索、类型、标签筛选由 DataTable 工具栏承载；同步所有数据库、表容量详情和刷新表容量已接入 React；导出 CSV 链接已接入；容量趋势点位钻取待迁移 |
| `/console/account-ledgers` | `/accounts/ledgers` | Parity - actions | `/api/v1/accounts/ledgers?page=1&limit=200`, `/api/v1/accounts/ledgers/exports`, `/api/v1/instances/actions/sync-accounts`, `/api/v1/accounts/ledgers/{id}/permissions`, `/api/v1/accounts/ledgers/{id}/change-history` | 已按旧版补齐账户/实例、是否可用、是否删除、是否超管、AD 状态、分类、类型、标签、操作列；搜索、分类、AD 状态、标签筛选由 DataTable 工具栏承载；同步所有账户、权限详情和变更历史已接入 React；导出 CSV 链接已接入 |
| `/console/capacity/instances` | `/capacity/instances` | Parity - actions | `/api/v1/capacity/instances?period_type=daily&page=1&limit=200&start_date=...&end_date=...`, `/api/v1/capacity/instances?period_type=daily&page=1&limit=200&start_date=...&end_date=...&get_all=true&chart_mode=instance`, `/api/v1/capacity/instances/summary?period_type=daily&start_date=...&end_date=...`, `/api/v1/capacity/aggregations/current` | 已按旧版补齐刷新数据、统计当前周期、数据库类型/实例/周期筛选、在线实例数/总容量/平均容量/最大容量指标，以及容量统计趋势图、容量变化趋势图、容量变化趋势图(百分比)；趋势图改用旧版同源全量图表数据；刷新和实例当前周期统计已接入 React；筛选联动细节待完整替代验收 |
| `/console/capacity/databases` | `/capacity/databases` | Parity - actions | `/api/v1/capacity/databases?period_type=daily&page=1&limit=200&start_date=...&end_date=...`, `/api/v1/capacity/databases?period_type=daily&page=1&limit=200&start_date=...&end_date=...&get_all=true&chart_mode=database`, `/api/v1/capacity/databases/summary?period_type=daily&start_date=...&end_date=...`, `/api/v1/capacity/aggregations/current` | 已按旧版补齐刷新数据、统计当前周期、数据库类型/实例/数据库/周期筛选、总数据库数/总容量/平均容量/最大容量指标，以及容量统计趋势图、容量变化趋势图、容量变化趋势图(百分比)；趋势图改用旧版同源全量图表数据；刷新和数据库当前周期统计已接入 React；筛选联动细节待完整替代验收 |
| `/console/instance-statistics` | `/instances/statistics` | Parity - content | `/api/v1/instances/statistics` | 已按旧版补齐返回实例列表/刷新统计命令、实例总数/审计信息/托管统计/备份统计、备份状态分布、数据库类型分布、端口分布、数据库版本统计和版本分布图；刷新写侧效果、图表交互细节待完整替代验收 |
| `/console/account-statistics` | `/accounts/statistics` | Parity - content | `/api/v1/accounts/statistics/summary`, `/api/v1/accounts/statistics/db-types`, `/api/v1/accounts/statistics/classifications`, `/api/v1/accounts/statistics/rules` | 已按旧版补齐账户列表/刷新统计命令、总账户数/正常账户/受限账户/统计实例、账户来源分布、AD 账户对比、数据库类型分布、账户分类分布；规则命中作为现有 API 快照保留 |
| `/console/database-statistics` | `/databases/statistics` | Parity - content | `/api/v1/databases/statistics` | 已按旧版补齐数据库台账/刷新统计命令、数据库总数/正常数据库/覆盖实例/总容量、数据库类型分布、实例数据库分布、同步状态分布和最新容量排行 |
| `/console/logs` | `/history/logs/` | Parity - content | `/api/v1/logs?page=1&limit=200`, `/api/v1/logs/statistics?hours=24`, `/api/v1/logs/{id}` | 已按旧版补齐时间、级别、模块、消息、操作列；搜索、级别、模块、时间范围筛选由 DataTable 工具栏承载；日志详情已迁移到 shadcn Dialog |
| `/console/account-change-logs` | `/history/account-change-logs/` | Parity - content | `/api/v1/account-change-logs?page=1&limit=200`, `/api/v1/account-change-logs/statistics?hours=24`, `/api/v1/account-change-logs/{id}` | 已按旧版补齐时间、数据库类型、实例、账号、类型、摘要、操作列；搜索、实例、数据库类型、变更类型、时间范围筛选由 DataTable 工具栏承载；账户变更详情已迁移到 shadcn Dialog |
| `/console/clusters` | `/cluster/` | Parity - actions | `GET /api/v1/sqlserver-clusters?page=1&limit=200`, `GET /api/v1/sqlserver-clusters/{id}`, `POST /api/v1/sqlserver-clusters`, `PATCH /api/v1/sqlserver-clusters/{id}`, `POST /api/v1/sqlserver-clusters/{id}/availability-groups/actions/sync`, `POST /api/v1/sqlserver-clusters/{id}/actions/sync-status`, `POST /api/v1/sqlserver-clusters/{id}/availability-groups/actions/sync-accounts`, `GET /api/v1/mysql-clusters?page=1&limit=200`, `GET /api/v1/mysql-clusters/{id}`, `POST /api/v1/mysql-clusters`, `PATCH /api/v1/mysql-clusters/{id}`, `POST /api/v1/mysql-clusters/{id}/actions/sync-topology` | 已按旧版补齐 SQL Server 群集列：群集、域名、状态、绑定实例、AG、最近 AG 同步、数据库同步状态、操作；MySQL 群集列：群集、拓扑、状态、绑定实例、主从状态、操作；SQL Server/MySQL 列表已恢复为 shadcn Tabs 单面板切换，一次只显示一种群集；搜索和状态筛选由 DataTable 工具栏承载；SQL Server/MySQL 群集新建编辑、SQL Server 详情/AG 信息同步/群集状态同步/AG 账户同步、MySQL 主从详情/拓扑同步已迁移到 shadcn Dialog；实例绑定和 AG 配置表单待迁移 |
| `/console/account-classifications` | `/accounts/classifications/` | Parity - actions | `/api/v1/accounts/classifications`, `/api/v1/accounts/classifications/rules`, `/api/v1/accounts/classifications/actions/auto-classify`, `/api/v1/accounts/classifications/{id}`, `/api/v1/accounts/classifications/rules/{id}`, `/api/v1/accounts/classifications/rules/actions/validate-expression`, `/api/v1/accounts/classifications/permissions/{db_type}` | 已按旧版补齐自动分类入口、账户分类面板、规则管理面板、风险等级、系统标记、规则分组、命中数和查看/编辑/删除入口；自动分类、分类新建/编辑/删除、规则新建/编辑/删除、表达式校验、规则详情和权限范围详情已接入 React；批量分类/应用规则和删除/自动分类结果反馈待迁移 |
| `/console/classification-statistics` | `/accounts/statistics/classifications` | Parity - content | `/api/v1/accounts/statistics/classifications`, `/api/v1/accounts/statistics/classifications/trends?period_type=daily&periods=7` | 已按旧版补齐刷新、账户分类/统计周期/数据库类型/实例范围筛选外观、规则列表空态、分类趋势（去重账号数）、规则贡献（当前周期）和说明文案；筛选联动、规则钻取 API 待迁移 |
| `/console/scheduler` | `/scheduler/` | Parity - actions | `/api/v1/scheduler/jobs`, `/api/v1/scheduler/jobs/{id}`, `/api/v1/scheduler/jobs/actions/reload`, `/api/v1/scheduler/jobs/{id}/actions/pause`, `/api/v1/scheduler/jobs/{id}/actions/resume`, `/api/v1/scheduler/jobs/{id}/actions/run` | 已按旧版补齐运行中/已暂停任务分组、任务名称、状态、下次运行、上次运行、任务 ID、触发器参数和重新初始化/暂停/恢复/立即执行/编辑/删除入口；重新初始化、暂停、恢复、立即执行和 cron 编辑已接入 React；删除任务缺 v1 API，暂不迁移 |
| `/console/sync-sessions` | `/history/sessions/` | Parity - actions | `/api/v1/sync-sessions?page=1&limit=100`, `/api/v1/sync-sessions/{id}`, `/api/v1/sync-sessions/{id}/error-logs`, `/api/v1/sync-sessions/{id}/actions/cancel` | 已按旧版补齐运行ID、状态、进度、任务、来源、分类、开始时间、耗时、操作列；来源、分类、状态筛选由 DataTable 工具栏承载；会话详情、实例记录、错误日志已迁移到 shadcn Dialog；运行中会话取消已接入 shadcn AlertDialog 确认 |
| `/console/users` | `/users/` | Parity - actions | `/api/v1/users?page=1&limit=200`, `/api/v1/users/stats`, `/api/v1/users`, `/api/v1/users/{id}` | 已按旧版补齐 ID、用户、角色、状态、创建时间、操作列；搜索、角色、状态筛选由 DataTable 工具栏承载；新建、编辑、删除已迁移到 shadcn Dialog/AlertDialog 并接入 v1 action；用户详情和禁用类独立反馈待确认 |
| `/console/settings` | `/admin/system-settings` | Parity - actions | `/api/v1/alerts/email-settings`, `/api/v1/alerts/email-settings/actions/send-test`, `/api/v1/alerts/email-settings/actions/send-feishu-test`, `/api/v1/risk-center/rules`, `/api/v1/integrations/jumpserver/source`, `/api/v1/integrations/jumpserver/actions/sync`, `/api/v1/integrations/veeam/sources`, `/api/v1/integrations/veeam/sources/{id}/actions/enable`, `/api/v1/integrations/veeam/sources/{id}/actions/disable`, `/api/v1/integrations/veeam/actions/sync`, `/api/v1/ad-domain-configs`, `/api/v1/ad-domain-configs/{id}/actions/set-enabled`, `/api/v1/ad-domain-configs/{id}/actions/test-connection`, `/api/v1/ad-domain-configs/actions/sync` | 已按旧版补齐设置模块导航、告警发送/规则设置、风险规则、JumpServer、Veeam、AD 设置表单字段和操作入口；告警测试/保存、风险规则保存、JumpServer 保存/同步/解绑、Veeam 保存/启停/同步/删除、AD 保存/启停/测试/同步/删除已接入 React；新增模式、多数据源细编辑和结果反馈待增强 |
| `/console/credentials` | `/credentials/` | Parity - actions | `/api/v1/credentials?page=1&limit=200`, `/api/v1/credentials`, `/api/v1/credentials/{id}` | 已按旧版补齐凭据、类型、数据库类型、状态、绑定实例、创建时间、操作列；搜索、凭据类型、数据库类型、状态筛选由 DataTable 工具栏承载；新建、编辑、删除已迁移到 shadcn Dialog/AlertDialog 并接入 v1 action；测试连接和绑定实例详情待迁移 |
| `/console/tags` | `/tags/` | Parity - actions | `/api/v1/tags?page=1&limit=200`, `/api/v1/tags/categories`, `/api/v1/tags`, `/api/v1/tags/{id}`, `/api/v1/tags/bulk/instances`, `/api/v1/tags/bulk/tags`, `/api/v1/tags/bulk/actions/assign`, `/api/v1/tags/bulk/actions/remove`, `/api/v1/tags/bulk/actions/remove-all` | 已按旧版补齐全部标签、启用率、停用率、标签分类、标签/分类/状态/关联/操作列；搜索、分类、状态筛选由 DataTable 工具栏承载；新建、编辑、删除、批量分配、批量移除、批量移除全部已迁移到 shadcn Dialog/AlertDialog 并接入 v1 action；关联资源详情待迁移 |
| `/console/partitions` | `/partition/` | Parity - actions | `/api/v1/partitions/status`, `/api/v1/partitions?page=1&limit=200`, `/api/v1/partitions/core-metrics?period_type=daily&days=7`, `/api/v1/partitions`, `/api/v1/partitions/actions/cleanup` | 已按旧版补齐创建分区/清理旧分区入口、分区总数/总大小/总记录数/健康状态指标、核心指标趋势、日周月季切换外观和分区列表；创建分区日期、清理保留月份已接入 React；周期联动待迁移 |

## 待迁移

当前导航内没有路由级占位页，但所有页面仍处于 `Parity - content` 或 `Parity - actions`，还没有任何页面达到 `Done - replacement`。后续迁移必须按下方缺口矩阵逐项关闭，避免“占位页 0”被误读为“功能完整替代已完成”。

## 完整替代缺口矩阵

| 新前端路径 | 表单/可编辑配置 | 详情/钻取 | 批量操作 | 导入导出 | 高风险确认与反馈 |
| --- | --- | --- | --- | --- | --- |
| `/console/dashboard` | - | 活动流、风险卡、图表钻取待迁移 | - | - | 刷新仍为查询刷新，写侧反馈无 |
| `/console/risk-center` | 风险处置/规则相关动作表单待迁移 | 风险卡详情、实例风险详情待迁移 | 批量处置待确认旧版能力后迁移 | - | 高风险处置确认、异步结果反馈待补 |
| `/console/instances` | 基础新增/编辑实例表单已迁移；高级连接参数、凭据选择器和连接参数校验待增强；恢复已迁移 | 实例基础详情、连接状态、账户信息、SQL Server AG 账户信息、容量信息、审计信息、备份信息已迁移；数据库表容量钻取入口待迁移 | 当前可见列表批量测试、批量移入回收站已迁移 | 导出 CSV 链接、导入模板、导入上传已接入 | 删除、批量删除、恢复确认已迁移；实例级账户/容量/审计/备份同步已接入 Sonner 反馈 |
| `/console/clusters` | 添加/编辑 SQL Server 群集、MySQL 群集表单已迁移；实例绑定和 SQL Server AG 配置表单待迁移 | SQL Server 群集详情、AG 状态、MySQL 主从状态/拓扑详情已迁移；AG 账户详情页待确认旧版能力后迁移 | - | - | SQL Server AG 信息/群集状态/AG 账户同步、MySQL 拓扑同步已迁移 Sonner 反馈；删除/解绑类确认待补 |
| `/console/database-ledgers` | - | 表容量详情已迁移；容量趋势点位钻取待迁移 | - | 导出 CSV 链接已接入 | 同步和表容量刷新已接入 Sonner 反馈 |
| `/console/account-ledgers` | - | 权限详情、变更历史详情已迁移 | - | 导出 CSV 链接已接入 | 同步已接入 Sonner 反馈 |
| `/console/capacity/instances` | 日期、周期、实例筛选联动待迁移 | 图表点位、实例容量详情钻取待迁移 | - | - | 统计当前周期已接入 Sonner 反馈 |
| `/console/capacity/databases` | 日期、周期、实例/数据库筛选联动待迁移 | 图表点位、数据库容量详情钻取待迁移 | - | - | 统计当前周期已接入 Sonner 反馈 |
| `/console/instance-statistics` | - | 分布图钻取、实例列表跳转待迁移 | - | - | 刷新仍为查询刷新，写侧反馈无 |
| `/console/account-statistics` | - | 分类、规则命中和 AD 对比钻取待迁移 | - | - | 刷新仍为查询刷新，写侧反馈无 |
| `/console/database-statistics` | - | 类型、实例分布、容量排行钻取待迁移 | - | - | 刷新仍为查询刷新，写侧反馈无 |
| `/console/logs` | - | 日志详情弹窗已迁移 | - | - | - |
| `/console/account-change-logs` | - | 变更详情弹窗已迁移 | - | - | - |
| `/console/account-classifications` | 分类/规则新建编辑、表达式校验表单已迁移 | 规则详情、权限范围详情已迁移 | 批量分类/批量应用规则待确认旧版能力后迁移 | - | 删除分类、删除规则、自动分类和表达式校验已接入 Sonner 反馈；批量类确认待补 |
| `/console/classification-statistics` | 分类、周期、数据库类型、实例范围筛选联动待迁移 | 规则列表、规则趋势、规则贡献钻取待迁移 | - | - | 刷新仍为查询刷新，写侧反馈无 |
| `/console/scheduler` | 编辑任务 cron 表单已迁移 | 任务详情、最近运行记录待迁移 | - | - | 暂停/恢复/立即执行/cron 保存已接入 Sonner 反馈；删除任务缺 v1 API |
| `/console/sync-sessions` | - | 会话详情、实例记录、错误日志已迁移；时间线可视化待增强 | - | - | 取消会话确认已迁移并接入 Sonner 反馈 |
| `/console/users` | 新建/编辑用户、角色/状态表单已迁移；禁用/重置密码独立动作待确认旧版能力后迁移 | 用户详情待确认旧版能力后迁移 | - | - | 删除用户确认已迁移，新建/编辑/删除已接入 Sonner 反馈；禁用用户确认待补 |
| `/console/settings` | JumpServer 绑定、Veeam 首个数据源、AD 首个域配置保存已迁移；告警阈值、新增模式和多数据源细编辑待增强 | 集成源连接/同步详情待迁移；AD 测试连接已迁移 | - | - | 告警、风险规则、JumpServer、Veeam、AD 已迁移动作均接入 Sonner 反馈；复杂删除/解绑确认待增强 |
| `/console/credentials` | 新建/编辑凭据表单已迁移；测试连接入口待新增/确认后端 API 后迁移 | 凭据绑定实例详情待迁移 | - | - | 删除凭据确认已迁移，新建/编辑/删除已接入 Sonner 反馈 |
| `/console/tags` | 新建/编辑标签表单已迁移 | 标签关联资源详情待迁移 | 批量分配、批量移除、批量移除全部已迁移 | - | 删除标签确认已迁移，新建/编辑/删除/批量操作已接入 Sonner 反馈；批量操作二次确认待增强 |
| `/console/partitions` | 创建分区日期、清理保留月份已迁移；周期切换参数待迁移 | 分区详情、核心指标点位钻取待迁移 | - | - | 创建/清理已接入 Sonner 反馈；清理二次确认待增强 |

## 缺少 v1 API 路口

以下能力未在本批实现，原因是当前没有找到可直接复用的 `/api/v1/**` 路口，或现有路口不足以覆盖旧版交互。缺口关闭前不标记对应页面为 `Done - replacement`。

| 页面 | 缺口 | 当前处置 |
| --- | --- | --- |
| `/console/risk-center` | 风险卡详情、实例风险详情、处置/确认/忽略/关闭/批量处置 API 未找到 | 保留只读内容 parity |
| `/console/dashboard` | 活动流详情、风险卡/图表点位钻取 API 未找到；`/api/v1/dashboard/activities` 当前仍为空数组占位 | 保留快照展示 |
| `/console/scheduler` | 删除任务 API 未找到 | 删除按钮保留为缺口，不接旧路由 |
| `/console/credentials` | 凭据级测试连接 API 未找到；绑定实例详情 API 未确认 | 新建/编辑/删除先完成 |
| `/console/users` | 独立禁用/重置密码 API 未找到；当前通过编辑用户保存状态覆盖基础启停 | 新建/编辑/删除先完成 |
| `/console/statistics/*` | 多数图表点位钻取 API 未找到 | 保留内容 parity |
| `/console/capacity/*` | 容量图表点位钻取 API 未找到 | 保留聚合与趋势展示 |
| `/console/tags` | 关联资源详情 API 待确认 | 批量分配/移除先完成 |
| `/console/instances` | 高级连接参数校验 API 待确认 | 基础新增/编辑、导入上传和批量删除先完成 |
| `/console/clusters` | 删除/解绑群集 API 未找到；实例解绑 API 未确认 | 新建/编辑/详情/同步先完成，实例绑定和 SQL Server AG 配置继续作为复杂表单批次 |
| `/console/settings` | JumpServer/Veeam 测试连接 API 未找到；AD 测试连接已存在并已接入 | 保留同步和保存动作 |

## 后续迁移批次

1. 先补共享交互底座：shadcn `Dialog`、`AlertDialog`、`Toast/Sonner`、表单校验和异步 action 反馈。
2. 再补详情类页面：日志详情、账户变更详情、同步会话时间线、实例详情、实例账户/AG账户/容量详情、账户权限详情、分类规则详情、群集详情已完成；后续补容量和统计钻取详情。
3. 再补 CRUD 表单：实例、群集实例绑定/AG 配置、系统设置新增模式；用户/凭据/标签/分类/规则/调度 cron/群集基础信息已完成基础新增编辑删除或保存，后续补特殊动作。
4. 最后补剩余批量与导入导出：实例/数据库台账/账户台账三类导出 CSV 链接已接入，实例导入上传、实例批量删除、标签批量分配/移除已完成。

## 本次动作迁移与风险

- 已迁移动作：实例基础新增/编辑、实例连接测试、实例级账户/容量/审计/备份同步、当前可见列表批量测试、实例批量移入回收站、实例批量导入 CSV、实例详情、连接状态、账户信息、SQL Server AG 账户信息、容量信息、审计详情、备份详情、删除到回收站、恢复、数据库同步、数据库表容量详情/刷新、账户同步、账户权限详情/变更历史、容量当前周期统计、账户自动分类、分类新建/编辑/删除、规则新建/编辑/删除、规则表达式校验、规则详情/权限范围详情、SQL Server/MySQL 群集新建编辑、SQL Server 群集详情/AG 信息同步/群集状态同步/AG 账户同步、MySQL 主从详情/拓扑同步、调度器重新初始化/暂停/恢复/立即执行/cron 编辑、会话取消确认、用户新建/编辑/删除、凭据新建/编辑/删除、标签新建/编辑/删除/批量分配/批量移除/批量移除全部、告警测试/保存、风险规则保存、JumpServer 保存/同步/解绑、Veeam 保存/启停/同步/删除、AD 保存/启停/测试/同步/删除、分区按日期创建/按保留月份清理。
- 权限校验：所有写操作仍走同源 `/api/v1/**`，后端权限与 CSRF 契约不在 React 层放宽；前端只负责触发与刷新。
- 回滚路径：每页保留“在旧版打开”，如新前端动作异常，可直接回到旧版页面执行同一操作；旧站点模板和静态资源未改动。
- 待补风险控制：用户/凭据/标签/实例/会话取消等删除或中止类动作已补 shadcn AlertDialog；已迁移写操作统一接入 Sonner 异步反馈；其余高风险动作还需补确认弹窗。

## 最近验证

2026-06-11 当前批次验证通过:

```bash
npm --prefix frontend run test          # 19 files, 49 tests passed
npm --prefix frontend run typecheck     # passed
npm --prefix frontend run lint          # passed
npm --prefix frontend run build         # passed; /static/css/fonts.css remains runtime-resolved
uv run pytest tests/unit/routes/test_api_v1_sqlserver_clusters_contract.py tests/unit/routes/test_api_v1_mysql_clusters_contract.py tests/unit/routes/test_api_v1_accounts_classifications_contract.py tests/unit/routes/test_api_v1_accounts_statistics_contract.py tests/unit/routes/test_api_v1_scheduler_contract.py tests/unit/routes/test_api_v1_history_sessions_contract.py tests/unit/routes/test_api_v1_users_contract.py tests/unit/routes/test_api_v1_alerts_contract.py tests/unit/routes/test_api_v1_risk_center_contract.py tests/unit/routes/test_api_v1_jumpserver_source_contract.py tests/unit/routes/test_api_v1_veeam_source_contract.py tests/unit/routes/test_api_v1_ad_domain_configs_contract.py tests/unit/routes/test_api_v1_credentials_contract.py tests/unit/routes/test_api_v1_tags_contract.py tests/unit/routes/test_api_v1_partition_contract.py tests/unit/routes/test_console_frontend_contract.py -q  # 79 passed
git diff --check                        # passed
```

2026-06-12 当前批次验证通过:

```bash
npm --prefix frontend run test       # 22 files, 84 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; /static/css/fonts.css remains runtime-resolved; Vite chunk-size warning remains
git diff --check                     # passed
```

2026-06-15 当前批次验证通过:

```bash
npm --prefix frontend run test       # 23 files, 113 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; Vite chunk-size warning remains
uv run pytest tests/unit/schemas/test_instances_query.py tests/unit/schemas/test_history_sessions_query.py -q  # 11 passed
git diff --check                     # passed
```

2026-06-16 当前批次验证通过:

```bash
npm --prefix frontend run test       # 24 files, 114 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; Vite chunk-size warning remains
git diff --check                     # passed
```

## 变更记录

- 2026-06-11: 建立 React 迁移清单；记录 dashboard、risk-center、instances、database-ledgers、account-ledgers、instance-statistics、account-statistics、database-statistics 的只读迁移状态。
- 2026-06-11: 迁移实例容量、数据库容量只读首屏；使用最近 30 天日粒度列表与汇总 API。
- 2026-06-11: 迁移日志中心、账户变更历史只读首屏；补充 shadcn Table、Skeleton、Alert、Progress、Chart 基础组件，运行信号改为 LineChart/AreaChart。
- 2026-06-11: 一次性迁移剩余只读首屏：群集、账户分类、分类统计、定时任务、同步会话、用户、系统设置、凭据、标签、分区；分类统计和分区核心指标使用 AreaChart。
- 2026-06-12: 建立旧版 parity 清单与测试，补充 ApiClient `PUT`/`DELETE`，引入 TanStack DataTable；凭据管理、标签管理按旧版内容口径返工，筛选收敛到 DataTable 工具栏。
- 2026-06-12: 继续内容 parity：用户管理、定时任务、会话中心补齐旧版字段、筛选、分组和操作入口；用户/会话列表切换到 DataTable，调度任务使用 shadcn Card 分组展示。
- 2026-06-12: 继续内容 parity：日志中心、账户变更历史补齐旧版列表字段、筛选和查看详情入口；筛选统一进入 DataTable 工具栏。
- 2026-06-12: 继续内容 parity：实例管理、数据库台账、账户台账补齐旧版字段、筛选、命令栏和操作入口；移除这组三页旧版没有的临时指标卡。
- 2026-06-12: 继续内容 parity：群集管理、账户分类补齐旧版字段、分组、命令入口和操作入口；群集表切换到 DataTable，分类/规则使用 shadcn Button/Badge 与轻量分组面板。
- 2026-06-12: 继续内容 parity：实例容量、数据库容量补齐旧版命令栏、筛选、指标卡和三组趋势图面板；趋势图使用 Recharts AreaChart，现有明细表作为数据快照保留。
- 2026-06-12: 继续内容 parity：实例统计、账户统计、数据库统计、分类统计补齐旧版命令栏、指标、筛选外观、分布表、AD 对比、趋势图和规则贡献区域；统计分布表切换到 shadcn/TanStack DataTable，图表使用 Recharts。
- 2026-06-12: 继续内容 parity：仪表盘补齐刷新、旧版四指标、风险告警、错误/告警日志趋势和系统状态；风险中心补齐筛选外观、分组风险墙和核心信号；系统设置补齐五个设置模块表单；分区管理补齐命令、指标、周期控制和核心指标趋势。
- 2026-06-12: 继续 action parity：新增 `frontend/src/api/actions.ts`，接入实例连接测试、台账同步、容量当前周期统计、账户自动分类/删除、调度任务、同步会话取消、系统设置保存/测试/同步/删除、分区创建/清理等直接动作；复杂新增/编辑/详情/导入表单继续保留为待迁移缺口。
- 2026-06-15: 补 shadcn `Dialog`/`AlertDialog`，迁移日志详情、账户变更详情、同步会话详情/实例记录/错误日志，以及运行中会话取消确认；同步更新详情与高风险确认缺口矩阵。
- 2026-06-15: 继续 action parity：补 shadcn `Textarea`，迁移用户、凭据、标签的新建/编辑表单和删除确认；接入 `/api/v1/users`、`/api/v1/credentials`、`/api/v1/tags` 写操作并更新表单、详情、批量、导入导出缺口矩阵。
- 2026-06-15: 继续已有 v1 能力迁移：实例详情/删除/恢复/批量测试、数据库表容量详情/刷新、账户权限/变更历史、分类/规则新建编辑、调度 cron 编辑、标签批量分配/移除、系统设置 JumpServer/Veeam/AD 保存与启停测试、分区日期和保留月份参数均接入 React；新增“缺少 v1 API 路口”清单。
- 2026-06-15: 继续账户分类 action/detail parity：接入规则表达式校验、规则详情和权限范围详情，查看规则迁移到 shadcn Dialog，规则表单支持校验后回写规范化表达式。
- 2026-06-15: 继续群集管理 action/detail parity：接入 ApiClient PATCH，迁移 SQL Server/MySQL 群集新建编辑、SQL Server 群集详情与 AG/状态/账户同步、MySQL 主从详情与拓扑同步；实例绑定和 AG 配置保留为复杂表单缺口。
- 2026-06-15: 继续实例管理 action parity：接入 `POST /api/v1/instances`、`PUT /api/v1/instances/{id}`，基础新增/编辑实例迁移到 shadcn Dialog；高级连接参数、批量删除和导入上传保留为后续缺口。
- 2026-06-15: 修复新前端基础问题：列表默认请求提升到 200 条，容量图表改用旧版同源 `get_all` 图表数据并放宽 Y 轴宽度，实例详情页加入 React 路由入口，系统设置风险规则响应兼容对象封装；导出清单收敛为实例管理、数据库台账、账户台账三处。
- 2026-06-15: 继续实例管理批量能力迁移：ApiClient 支持 multipart `FormData`，接入 `/api/v1/instances/actions/batch-create` CSV 上传、`/api/v1/instances/imports/template` 模板下载和 `/api/v1/instances/actions/batch-delete` 批量移入回收站确认。
- 2026-06-15: 对齐实例列表分页契约：后端 `InstanceListFiltersQuery` 上限提升到 200，React 实例管理继续请求 `limit=200`；同步会话列表按现有后端上限单独保留 `limit=100`。
- 2026-06-15: 继续实例详情迁移：接入连接状态、审计信息、备份信息读取接口，并补实例级测试连接、同步账户、同步容量、同步审计、同步备份快捷操作。
- 2026-06-16: 继续实例详情迁移：新增 shadcn `Tabs`，接入实例账户、SQL Server AG 账户和数据库容量最新快照；旧版详情页的账户信息、账户信息（AG）、容量信息已迁移到 Tabs + DataTable。
- 2026-06-16: 修复群集管理展示契约：SQL Server/MySQL 群集恢复为旧版一致的 shadcn Tabs 单面板切换，移除双列同时展示。
- 2026-06-16: 引入 shadcn `Select`、`Checkbox`、`Switch`、`Label`、`Tooltip` 和 `Sonner`，替换原生 select/checkbox/title tooltip，统一已迁移写操作的成功/失败反馈；新增“成熟 shadcn 组件优先，不手写基础交互”的后续迁移原则。
