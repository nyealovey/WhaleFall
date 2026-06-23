# React Frontend Migration Checklist

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-06-11
> 更新: 2026-06-23
> 范围: `/console` React 新前端迁移进度
> 关联: `frontend/`, `app/api/v1/`, `docs/Obsidian/standards/doc/guide/documentation.md`
> 展示内容跟踪: `docs/plans/2026-06-18-react-display-parity-tracker.md`

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
- 完整替代完成页: 22（代码侧；用户重新构建部署后需按审计报告线上复核）
- 完整替代缺口页: 0
- 当前策略: 导航内页面已按 2026-06-22 线上审计报告完成 P0/P1 修复；后续先做线上复核，再处理明确新增需求或后端新增 API
- API 核查口径: 路由级占位页 0 不代表完整替代完成；旧版本来没有的增强能力不阻塞 `Done - replacement`；只有旧版有入口/动作且 v1 缺路由的能力才作为替代阻塞项
- 旧站点状态: 保持不动，作为回滚入口
- UI 基线: shadcn 风格组件优先，当前已接入 Button、Card、Badge、Input、Textarea、Separator、Table、Tabs、Skeleton、Alert、Dialog、AlertDialog、Progress、Chart、Select、Checkbox、Switch、Label、Tooltip、RadioGroup、Pagination、Sonner、TanStack DataTable

## 完整替代验收口径

- 展示内容与旧版一致：指标、列表字段、筛选项、状态、详情信息和空态不能缺项。
- 展示形态可以调整：优先使用 shadcn 组件、TanStack Table 和 Recharts，避免继续复制旧版 DOM 结构。
- 表格筛选由新版 DataTable 工具栏承载；如果表格自带筛选，不再额外做页面级筛选区。
- 写操作必须在 React 内调用 `/api/v1/` 或新增受控 API，不能只跳回旧版后标记完整替代。
- 高风险动作需要单独记录测试、回滚路径和权限校验。
- API 缺口判定先对照旧版页面和旧版 JS：旧版没有独立交互的功能进入未来增强，不作为 `Done - replacement` 阻塞项。

## UI 组件迁移原则

- 后续迁移优先引入和复用 shadcn/Radix 成熟组件；凡是 shadcn 已覆盖的 Select、Checkbox、Switch、Tooltip、Dialog、AlertDialog、Tabs、Toast/Sonner、Label、Button、Input、Textarea 等基础交互，不再手写同类控件。
- 只有业务强相关组合组件可以在本项目内封装，例如 DataTable、查询框架、指标卡和图表面板；这些封装也应基于 shadcn 原语组合，而不是重新实现基础交互。
- 新增原生 `<select>`、`input[type="checkbox"]`、原生 `title` tooltip 或自制 toast 前，必须先确认 shadcn 是否已有可用组件；确需手写时，需要在本清单记录原因、影响范围和后续替换计划。
- 所有已迁移写操作统一通过 Sonner 展示进行中、成功和失败反馈；新动作不得只静默刷新列表。

## 已完成

| 新前端路径 | 旧页面路径 | 状态 | 接入 API | 备注 |
| --- | --- | --- | --- | --- |
| `/console/dashboard` | `/dashboard/` | Done - replacement | `/api/v1/dashboard/overview`, `/api/v1/dashboard/status`, `/api/v1/dashboard/charts?type=all`, `/api/v1/risk-center/summary` | 已按旧版补齐刷新数据、数据库实例/账户总数/总容量/数据库总数指标、风险告警、错误和告警日志趋势、系统状态、运行时间和分类分布；刷新接入 Sonner 反馈；旧版模板没有活动流展示，新版已删除活动流卡片，完成替代验收 |
| `/console/risk-center` | `/risk-center/` | Done - replacement | `/api/v1/risk-center/summary`, `/api/v1/risk-center/cards?page=...&limit=20&severity=...&db_type=...&status=...&tag=...&search=...` | 已按旧版补齐刷新、总实例/高中低健康指标、搜索/严重度/数据库类型/状态/标签筛选联动、数据库类型分组风险墙和备份/审计/托管/群集/任务核心信号；风险卡默认每页 20 条并接入服务端分页；刷新接入 Sonner 反馈；风险卡沿用旧版跳转实例详情口径，风险处置类动作属于未来增强，不阻塞旧版等价替代 |
| `/console/instances` | `/instances/` | Done - replacement | `/api/v1/instances?page=...&limit=...`, `/api/v1/instances/{id}`, `/api/v1/instances/{id}/connection-status`, `/api/v1/accounts/ledgers?instance_id={id}&owner_type=instance&include_roles=true`, `/api/v1/instances/{id}/ag-accounts`, `/api/v1/databases/sizes?instance_id={id}&latest_only=true&include_inactive=true`, `/api/v1/instances/{id}/audit-info`, `/api/v1/instances/{id}/backup-info`, `/api/v1/credentials?page=...&limit=...`, `POST /api/v1/instances`, `PUT /api/v1/instances/{id}`, `/api/v1/instances/actions/test-connection`, `/api/v1/instances/actions/validate-connection-params`, `/api/v1/instances/actions/batch-test-connections`, `/api/v1/instances/actions/batch-delete`, `/api/v1/instances/actions/batch-create`, `/api/v1/instances/imports/template`, `/api/v1/instances/{id}/actions/sync-accounts`, `/api/v1/instances/{id}/actions/sync-capacity`, `/api/v1/instances/{id}/actions/sync-audit-info`, `/api/v1/integrations/veeam/actions/sync-instance/{id}`, `/api/v1/instances/{id}/actions/restore`, `DELETE /api/v1/instances/{id}`, `/api/v1/instances/exports` | 已按旧版补齐名称、类型、主机/IP、状态、审计、已托管、备份、活跃、版本/同步、标签、操作列；搜索、类型、状态、审计、托管、备份、标签筛选由 DataTable 工具栏承载并接入服务端分页；实例详情补齐实例 ID、数据库版本、标签、编辑、移入回收站、账户/容量四项汇总、查看权限、变更历史、表容量入口、Backup ID、覆盖数量、平台、数据大小、备份大小和压缩率；基础新增/编辑实例表单、凭据下拉选择、单实例连接测试、高级连接参数校验、实例级账户/容量/审计/备份同步、当前可见列表批量测试、批量移入回收站、批量导入 CSV、删除到回收站、恢复、导出 CSV 均已接入 React，完成替代验收 |
| `/console/database-ledgers` | `/databases/ledgers` | Done - replacement | `/api/v1/databases/ledgers?page=...&limit=...`, `/api/v1/databases/ledgers/exports`, `/api/v1/databases/ledgers/actions/sync-all`, `/api/v1/databases/{id}/tables/sizes`, `/api/v1/databases/{id}/tables/sizes/actions/refresh` | 已按旧版补齐数据库/实例、类型、数据库大小、标签、操作列；搜索、类型、标签筛选由 DataTable 工具栏承载并接入服务端分页；同步所有数据库、表容量详情和刷新表容量已接入 React；导出 CSV 链接携带当前筛选条件；容量趋势点位深度钻取归入未来增强，完成替代验收 |
| `/console/account-ledgers` | `/accounts/ledgers` | Done - replacement | `/api/v1/accounts/ledgers?page=...&limit=...`, `/api/v1/accounts/ledgers/exports`, `/api/v1/instances/actions/sync-accounts`, `/api/v1/accounts/ledgers/{id}/permissions`, `/api/v1/accounts/ledgers/{id}/change-history` | 已按旧版补齐账户/实例、是否可用、是否删除、是否超管、AD 状态、分类、类型、标签、操作列；搜索、分类、AD 状态、标签筛选由 DataTable 工具栏承载并接入服务端分页；同步所有账户、权限详情、变更历史和导出 CSV 已接入 React，导出 CSV 链接携带当前筛选条件，完成替代验收 |
| `/console/capacity/instances` | `/capacity/instances` | Done - replacement | `/api/v1/capacity/instances?period_type=...&page=...&limit=...&start_date=...&end_date=...&instance_id=...&db_type=...`, `/api/v1/capacity/instances?period_type=...&start_date=...&end_date=...&get_all=true`, `/api/v1/capacity/instances/summary?period_type=...&start_date=...&end_date=...`, `/api/v1/capacity/aggregations/current` | 已按旧版补齐刷新数据、统计当前周期、开始/结束日期、数据库类型、实例、周期筛选联动、在线实例数/总容量/平均容量/最大容量指标，以及容量统计趋势图、容量变化趋势图、容量变化趋势图(百分比)；趋势图改用旧版同源全量图表数据，容量单位按 MB/GB/TB 自适应；旧版没有的大容量明细列表已删除；刷新和实例当前周期统计已接入 Sonner 反馈，完成替代验收 |
| `/console/capacity/databases` | `/capacity/databases` | Done - replacement | `/api/v1/capacity/databases?period_type=...&page=...&limit=...&start_date=...&end_date=...&instance_id=...&db_type=...&database_name=...`, `/api/v1/capacity/databases?period_type=...&start_date=...&end_date=...&get_all=true`, `/api/v1/capacity/databases/summary?period_type=...&start_date=...&end_date=...`, `/api/v1/capacity/aggregations/current` | 已按旧版补齐刷新数据、统计当前周期、开始/结束日期、数据库类型、实例、数据库、周期筛选联动、总数据库数/总容量/平均容量/最大容量指标，以及容量统计趋势图、容量变化趋势图、容量变化趋势图(百分比)；趋势图改用旧版同源全量图表数据，容量单位按 MB/GB/TB 自适应；旧版没有的大容量明细列表已删除；刷新和数据库当前周期统计已接入 Sonner 反馈，完成替代验收 |
| `/console/instance-statistics` | `/instances/statistics` | Done - replacement | `/api/v1/instances/statistics` | 已按旧版补齐返回实例列表/刷新统计命令、实例总数/审计信息/托管统计/备份统计、备份状态分布、数据库类型分布、端口分布、数据库版本统计和版本分布图；刷新统计已接入 Sonner 反馈；图表点位深度钻取归入未来增强，完成替代验收 |
| `/console/account-statistics` | `/accounts/statistics` | Done - replacement | `/api/v1/accounts/statistics/summary`, `/api/v1/accounts/statistics/db-types`, `/api/v1/accounts/statistics/classifications`, `/api/v1/accounts/statistics/rules` | 已按旧版补齐账户列表/刷新统计命令、总账户数/正常账户/受限账户/统计实例、账户来源分布、AD 账户对比、数据库类型分布、账户分类分布；刷新统计已接入 Sonner 反馈；规则命中作为现有 API 快照保留，图表点位深度钻取归入未来增强，完成替代验收 |
| `/console/database-statistics` | `/databases/statistics` | Done - replacement | `/api/v1/databases/statistics` | 已按旧版补齐数据库台账/刷新统计命令、数据库总数/正常数据库/覆盖实例/总容量、数据库类型分布、实例数据库分布、同步状态分布和最新容量排行；刷新统计已接入 Sonner 反馈；图表点位深度钻取归入未来增强，完成替代验收 |
| `/console/logs` | `/history/logs/` | Done - replacement | `/api/v1/logs?page=...&limit=...`, `/api/v1/logs/modules`, `/api/v1/logs/statistics?hours=...`, `/api/v1/logs/{id}` | 已按旧版补齐总日志数、错误日志、警告日志、信息日志指标，以及时间、级别、模块、消息、操作列；搜索、级别、模块、时间范围筛选由 DataTable 工具栏承载并同时作用于列表和统计；模块选项从 v1 加载，日志详情已迁移到 shadcn Dialog；旧版无写操作和导出入口，完成替代验收 |
| `/console/account-change-logs` | `/history/account-change-logs/` | Done - replacement | `/api/v1/account-change-logs?page=...&limit=...`, `/api/v1/account-change-logs/statistics?hours=...`, `/api/v1/instances/options`, `/api/v1/account-change-logs/{id}` | 已按旧版补齐变更总数、成功率、失败变更、影响账号数指标，以及时间、数据库类型、实例、账号、类型、摘要、操作列；默认使用全部时间口径，时间范围同时传给列表和统计；搜索、实例、数据库类型、变更类型筛选由 DataTable 工具栏承载，实例选项从 v1 加载；账户变更详情已迁移到 shadcn Dialog；旧版无写操作和导出入口，完成替代验收 |
| `/console/clusters` | `/cluster/` | Done - replacement | `GET /api/v1/sqlserver-clusters?page=...&limit=...`, `GET /api/v1/sqlserver-clusters/{id}`, `POST /api/v1/sqlserver-clusters`, `PATCH /api/v1/sqlserver-clusters/{id}`, `PUT /api/v1/sqlserver-clusters/{id}/instances`, `POST /api/v1/sqlserver-clusters/{id}/availability-groups`, `PATCH /api/v1/sqlserver-clusters/{id}/availability-groups/{ag_id}`, `GET /api/v1/sqlserver-clusters/{id}/availability-groups/{ag_id}/dashboard`, `POST /api/v1/sqlserver-clusters/{id}/availability-groups/actions/sync`, `POST /api/v1/sqlserver-clusters/{id}/actions/sync-status`, `POST /api/v1/sqlserver-clusters/{id}/availability-groups/actions/sync-accounts`, `GET /api/v1/mysql-clusters?page=...&limit=...`, `GET /api/v1/mysql-clusters/{id}`, `POST /api/v1/mysql-clusters`, `PATCH /api/v1/mysql-clusters/{id}`, `PUT /api/v1/mysql-clusters/{id}/instances`, `POST /api/v1/mysql-clusters/{id}/actions/sync-topology` | 已按旧版补齐 SQL Server 群集列：群集、域名、状态、绑定实例、AG、最近 AG 同步、数据库同步状态、操作；MySQL 群集列：群集、拓扑、状态、绑定实例、主从状态、异常副本数、操作；SQL Server/MySQL 列表已恢复为 shadcn Tabs 单面板切换，一次只显示一种群集，并接入服务端分页；状态字段使用 `last_status_sync_status/at`、`last_ag_sync_status/at`、`last_topology_sync_status/at` 等业务字段；搜索和状态筛选由 DataTable 工具栏承载；SQL Server/MySQL 群集新建编辑、SQL Server 详情/AG 信息同步/群集状态同步/AG 账户同步、MySQL 主从详情/拓扑同步已迁移到 shadcn Dialog；SQL Server/MySQL 实例绑定/解绑、SQL Server AG 新建/编辑/看板通过群集列表操作入口维护，详情弹窗只保留查看和同步，不再发起子弹窗；群集删除归入未来增强，不阻塞旧版等价替代 |
| `/console/account-classifications` | `/accounts/classifications/` | Done - replacement | `/api/v1/accounts/classifications`, `/api/v1/accounts/classifications/rules`, `/api/v1/accounts/classifications/actions/auto-classify`, `/api/v1/accounts/classifications/{id}`, `/api/v1/accounts/classifications/rules/{id}`, `/api/v1/accounts/classifications/rules/actions/validate-expression`, `/api/v1/accounts/classifications/permissions/{db_type}` | 已按旧版补齐自动分类入口、账户分类面板、规则管理面板、风险等级、系统标记、规则分组、命中数和查看/编辑/删除入口；管理员可执行写操作，非管理员隐藏自动分类、新建、编辑和删除并保留规则查看；删除分类和删除规则使用 shadcn AlertDialog，写操作接入 Sonner；旧版未发现批量分类/批量应用规则入口，不纳入迁移范围，完成替代验收 |
| `/console/classification-statistics` | `/accounts/statistics/classifications` | Done - replacement | `/api/v1/accounts/statistics/classifications`, `/api/v1/accounts/statistics/classifications/trends`, `/api/v1/accounts/statistics/classifications/trend`, `/api/v1/accounts/statistics/rules/overview`, `/api/v1/accounts/statistics/rules/contributions`, `/api/v1/accounts/statistics/rules/trend`, `/api/v1/instances/account-scope-options?db_type=...` | 已按旧版补齐刷新、账户分类/统计周期/数据库类型/实例或 AG 筛选联动、规则列表、分类趋势（去重账号数）、规则贡献（当前周期）、规则趋势钻取和说明文案；实例/AG 选项按数据库类型从 v1 加载，刷新接入 Sonner 反馈，完成替代验收 |
| `/console/scheduler` | `/scheduler/` | Done - replacement | `/api/v1/scheduler/jobs`, `/api/v1/scheduler/jobs/{id}`, `DELETE /api/v1/scheduler/jobs/{id}`, `/api/v1/scheduler/jobs/actions/reload`, `/api/v1/scheduler/jobs/{id}/actions/pause`, `/api/v1/scheduler/jobs/{id}/actions/resume`, `/api/v1/scheduler/jobs/{id}/actions/run` | 已按旧版补齐运行中/已暂停任务分组、任务名称、状态、下次运行、上次运行、任务 ID 和重新初始化/暂停/恢复/立即执行/查看详情/编辑/删除入口；任务详情、重新初始化、暂停、恢复、立即执行、cron 编辑和删除任务已接入 React；列表时间统一本地时间，任务 ID 使用旧版大小写口径，删除旧版没有的卡片 cron 参数正文；删除任务新增 v1 DELETE 路由并补契约测试，完成替代验收 |
| `/console/sync-sessions` | `/history/sessions/` | Done - replacement | `/api/v1/task-runs?page=...&limit=...`, `/api/v1/task-runs/{run_id}`, `/api/v1/task-runs/{run_id}/error-logs`, `/api/v1/task-runs/{run_id}/actions/cancel` | 已按旧版切换到 task-runs 数据源，补齐运行ID、状态、进度、任务、来源、分类、开始时间、耗时、操作列；来源、分类、状态筛选使用固定业务选项并接入服务端分页；会话详情、实例记录、错误日志已迁移到 shadcn Dialog；运行中会话取消已接入 shadcn AlertDialog 确认和 Sonner 反馈，完成替代验收 |
| `/console/users` | `/users/` | Done - replacement | `/api/v1/users?page=...&limit=...`, `/api/v1/users`, `/api/v1/users/{id}` | 已按旧版补齐 ID、用户、角色、状态、创建时间、操作列；搜索、角色、状态筛选由 DataTable 工具栏承载并接入服务端分页；新建、编辑、删除使用 shadcn Dialog/AlertDialog 并接入 v1 action；旧版没有独立详情入口，因此 React 不展示详情按钮；禁用和重置密码沿用旧版编辑用户保存口径；非管理员操作列只读，管理员不可删除当前登录用户，完成替代验收 |
| `/console/settings` | `/admin/system-settings` | Done - replacement | `/api/v1/alerts/email-settings`, `/api/v1/alerts/email-settings/actions/send-test`, `/api/v1/alerts/email-settings/actions/send-feishu-test`, `/api/v1/risk-center/rules`, `/api/v1/integrations/jumpserver/source`, `/api/v1/integrations/jumpserver/actions/sync`, `/api/v1/integrations/veeam/sources`, `/api/v1/integrations/veeam/sources/{id}/actions/enable`, `/api/v1/integrations/veeam/sources/{id}/actions/disable`, `/api/v1/integrations/veeam/actions/sync`, `/api/v1/ad-domain-configs`, `/api/v1/ad-domain-configs/{id}/actions/set-enabled`, `/api/v1/ad-domain-configs/{id}/actions/test-connection`, `/api/v1/ad-domain-configs/actions/sync`, `/api/v1/credentials?page=...&limit=...&credential_type=ldap&status=active` | 已按旧版补齐设置模块导航并改用 shadcn Tabs；告警设置补脱敏 Webhook、清空选项、共享收件人与容量增长百分比/绝对值阈值；风险规则补分类、中文名称、描述、严重级别 RadioGroup 和启用 Switch；JumpServer 补凭据、SSL 状态、最近同步状态/时间；Veeam 补凭据、启用状态、最近同步和 Provider 汇总；AD 默认进入新增模式，列表补域控、凭据、同步状态及 AD/SQL 账户统计；告警测试/保存、风险规则保存、JumpServer 保存/同步/解绑、Veeam 新增/编辑/启停/同步/删除/新增模式/数据源列表编辑、AD 新增/编辑/启停/测试/同步/删除/新增模式/域列表编辑已接入 React；旧版未发现 JumpServer/Veeam 测试连接入口，不纳入迁移范围，完成替代验收 |
| `/console/credentials` | `/credentials/` | Done - replacement | `/api/v1/credentials?page=...&limit=...`, `/api/v1/credentials`, `/api/v1/credentials/{id}` | 已按旧版补齐凭据、类型、数据库类型、状态、绑定实例、创建时间、操作列；搜索、凭据类型、数据库类型、状态筛选由 DataTable 工具栏承载并接入服务端分页；添加、编辑、删除使用 shadcn Dialog/AlertDialog 并接入 v1 action；旧版没有独立详情入口，非管理员操作列只读；旧版只展示绑定实例数量，绑定实例明细和凭据级测试连接归入未来增强，完成替代验收 |
| `/console/tags` | `/tags/` | Done - replacement | `/api/v1/tags?page=...&limit=...`, `/api/v1/tags/categories`, `/api/v1/tags`, `/api/v1/tags/{id}`, `/api/v1/tags/bulk/instances`, `/api/v1/tags/bulk/tags`, `/api/v1/tags/bulk/actions/assign`, `/api/v1/tags/bulk/actions/remove`, `/api/v1/tags/bulk/actions/remove-all` | 已按旧版补齐全部标签、启用率、停用率、标签分类及其辅助指标，以及标签/分类/状态/关联/操作列；搜索、分类、状态筛选由 DataTable 工具栏承载并接入服务端分页；添加、编辑、删除、批量分配、批量移除、批量移除全部使用 shadcn Dialog/AlertDialog 并接入 v1 action；旧版没有独立详情入口，非管理员操作列只读；旧版只展示关联数量，关联资源明细归入未来增强，完成替代验收 |
| `/console/partitions` | `/partition/` | Done - replacement | `/api/v1/partitions/status`, `/api/v1/partitions?page=...&limit=...`, `/api/v1/partitions/core-metrics?period_type=...&days=...`, `/api/v1/partitions`, `/api/v1/partitions/actions/cleanup` | 已按旧版补齐创建分区/清理旧分区入口、历史/当前/未来分区数量、当前分区大小、平均记录数、当前记录数、数据库连接状态、核心指标趋势、日周月季切换参数联动和分区列表；分区列表默认每页 20 条并接入服务端分页；创建分区年份/月份位于 shadcn Dialog，清理保留月数与二次确认位于 shadcn AlertDialog，动作接入 Sonner；分区详情和核心指标点位钻取归入未来增强，完成替代验收 |

## 待迁移

当前导航内没有路由级占位页，22 个页面均达到 `Done - replacement`。后续不再以“迁移缺口”方式追踪旧版没有的增强能力；新增需求需要单独开需求、确认旧版依据或新增后端 API。

## 完整替代缺口矩阵

当前无旧版等价替代阻塞项。

## v1 API 核查与迁移分组

以下分组用于区分“已存在但前端未接入”“旧版有入口但 v1 缺路由”和“旧版本来也没有的未来增强”。后续是否能标记 `Done - replacement`，只受旧版等价能力阻塞，不受未来增强阻塞。

### API 已存在，前端继续接入

| 页面 | 能力 | v1 路口 | 迁移处置 |
| --- | --- | --- | --- |
| `/console/instances` | 高级连接参数校验 | `POST /api/v1/instances/actions/validate-connection-params` | 已接入 React 实例表单 |
| `/console/clusters` | SQL Server/MySQL 实例绑定与解绑 | `PUT /api/v1/sqlserver-clusters/{id}/instances`, `PUT /api/v1/mysql-clusters/{id}/instances` | 已接入群集列表操作入口，通过替换绑定列表实现绑定/解绑；详情弹窗只做查看和同步 |
| `/console/clusters` | SQL Server AG 新建、编辑、看板 | `POST /api/v1/sqlserver-clusters/{id}/availability-groups`, `PATCH /api/v1/sqlserver-clusters/{id}/availability-groups/{ag_id}`, `GET /api/v1/sqlserver-clusters/{id}/availability-groups/{ag_id}/dashboard` | 已接入群集列表操作入口；详情弹窗只做查看和同步，不发起子弹窗 |
| `/console/users` | 用户启停与重置密码 | `PUT /api/v1/users/{id}` | 沿用旧版编辑用户保存口径，不再设计独立动作作为阻塞 |
| `/console/classification-statistics` | 实例/AG 精确范围筛选选项 | `GET /api/v1/instances/account-scope-options?db_type=...` | 已按数据库类型懒加载选项，筛选值随分类统计请求透传 |
| `/console/scheduler` | 删除任务 | `DELETE /api/v1/scheduler/jobs/{id}` | 已补后端 v1 路由、前端确认框和契约测试 |
| `/console/settings` | AD LDAP 凭据下拉 | `GET /api/v1/credentials?page=...&limit=...&credential_type=ldap&status=active` | 已接入系统设置 AD 域表单 |

### 确实缺 v1，且影响旧版等价替代

当前无影响旧版等价替代的 v1 缺口。

### 旧版本来也没有，或属于未来增强

| 页面 | 能力 | 核查结论 | 当前处置 |
| --- | --- | --- | --- |
| `/console/risk-center` | 风险处置/确认/忽略/关闭/批量处置 | 旧版未发现独立处置动作；风险卡身份链接跳实例详情 | 不阻塞旧版替代，进入未来增强 |
| `/console/risk-center` | 风险卡详情、实例风险详情 | 旧版没有独立详情 API；通过实例详情承载 | 按实例详情跳转处理，独立风险详情进入未来增强 |
| `/console/credentials` | 绑定实例明细 | 旧版只展示绑定实例数量 | 数量 parity 即可验收；明细进入未来增强，需要新增 API |
| `/console/tags` | 标签关联资源明细 | 旧版只展示关联数量 | 数量 parity 即可验收；明细进入未来增强，需要新增 API |
| `/console/statistics/*` | 多数图表点位深度钻取 | 旧版以聚合图表和分布表为主 | 不阻塞旧版替代，后续按增强评估 |
| `/console/capacity/*` | 容量图表点位深度钻取 | 旧版聚合与趋势已可由现有 API 覆盖 | 不阻塞旧版替代，后续按增强评估 |
| `/console/clusters` | 群集删除 | 未找到 v1 删除路由，且当前迁移优先覆盖新建/编辑/同步/绑定 | 不阻塞当前等价批次，进入未来增强或后端新功能评估 |

## 后续迁移批次

1. 已完成已有 API 接入：实例高级连接参数校验、群集实例绑定/解绑、SQL Server AG 新建/编辑/看板、用户状态和密码编辑口径收敛到编辑表单。
2. 已完成首批可验收页面收口：日志、账户变更、同步会话、用户、凭据、标签升为 `Done - replacement`；用户/凭据/标签补齐角色感知写入口，非管理员只保留查看入口。
3. 已完成第二批可验收页面收口：数据库台账、账户台账、实例容量、数据库容量、实例统计、账户统计、数据库统计升为 `Done - replacement`；容量页和统计页刷新接入 Sonner 反馈。
4. 已完成第三批可验收页面收口：风险中心、群集管理、分类统计、分区管理升为 `Done - replacement`；风险中心/分类统计刷新接入 Sonner，分类统计实例/AG 选项接入 v1，分区清理补二次确认。
5. 已完成最终收口：仪表盘删除旧版没有的活动流卡片并补刷新反馈；实例表单凭据选择器接入；账户分类删除确认接入；调度任务删除补 v1 路由；系统设置新增模式、多数据源细编辑和 AD LDAP 凭据下拉接入。
6. 已完成 2026-06-22 线上审计修复：DataTable 接入 shadcn Pagination 和服务端分页，日志/账户变更/会话中心切换到旧版同源数据口径，容量/统计/群集/分区/仪表盘补齐旧版展示字段，实例详情和系统设置补齐缺失内容。
7. 后续如需增强能力，按新需求单独评估：凭据绑定实例明细、标签关联资源明细、统计/容量图表点位深度钻取、群集删除等不属于本轮旧版等价迁移阻塞。
8. 持续保留导入导出收敛口径：实例/数据库台账/账户台账三类导出 CSV 链接已接入并携带当前筛选；实例导入上传、实例批量删除、标签批量分配/移除已完成。

## 本次动作迁移与风险

- 已迁移动作与基础能力：shadcn Pagination 服务端分页、固定业务筛选选项、仪表盘刷新、实例基础新增/编辑、实例凭据选择、实例连接测试、高级连接参数校验、实例级账户/容量/审计/备份同步、当前明确选择记录批量测试、实例批量移入回收站、实例批量导入 CSV、实例详情、连接状态、账户信息、SQL Server AG 账户信息、容量信息、数据库表容量详情/刷新、审计详情、备份详情、删除到回收站、恢复、数据库同步、账户同步、账户权限详情/变更历史、容量当前周期统计、容量实例/数据库筛选联动、容量页刷新、统计页刷新、风险中心刷新、分类统计实例/AG筛选和刷新、账户自动分类、分类新建/编辑/删除确认、规则新建/编辑/删除确认、规则表达式校验、规则详情/权限范围详情、SQL Server/MySQL 群集新建编辑、SQL Server 群集详情/AG 信息同步/群集状态同步/AG 账户同步、SQL Server/MySQL 群集实例绑定/解绑、SQL Server AG 新建/编辑/看板、MySQL 主从详情/拓扑同步、调度器重新初始化/暂停/恢复/立即执行/查看详情/cron 编辑/删除确认、会话取消确认、用户详情/新建/编辑/删除、凭据详情/新建/编辑/删除、标签详情/新建/编辑/删除/批量分配/批量移除/批量移除全部、告警测试/保存、风险规则保存、JumpServer 保存/同步/解绑、Veeam 新增/编辑/启停/同步/删除/新增模式、AD 新增/编辑/启停/测试/同步/删除/新增模式、分区按日期创建/按保留月份清理、分区清理二次确认、分区核心指标周期切换。
- 权限展示收敛：用户、凭据、标签页面接入当前登录用户角色；非管理员仅显示查看和只读状态，不暴露新增、编辑、删除、批量分配等写入口；管理员删除当前登录用户时禁用删除按钮。
- 权限校验：所有写操作仍走同源 `/api/v1/**`，后端权限与 CSRF 契约不在 React 层放宽；前端只负责触发与刷新。
- 回滚路径：每页保留“在旧版打开”，如新前端动作异常，可直接回到旧版页面执行同一操作；旧站点模板和静态资源未改动。
- 待补风险控制：用户/凭据/标签/实例/会话取消等删除或中止类动作已补 shadcn AlertDialog；已迁移写操作统一接入 Sonner 异步反馈；未来增强类高风险动作需要在新增 API 时同步补确认弹窗和回滚说明。

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
npm --prefix frontend run test       # 24 files, 124 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; Vite chunk-size warning remains
git diff --check                     # passed
```

2026-06-18 当前批次验证通过:

```bash
npm --prefix frontend run test       # 24 files, 137 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; Vite chunk-size warning remains
uv run pytest tests/unit/routes/test_api_v1_scheduler_contract.py -q  # 2 passed
git diff --check                     # passed
```

2026-06-23 线上审计修复批次验证通过:

```bash
npm --prefix frontend run test       # 26 files, 147 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; Vite chunk-size warning remains
uv run pytest tests/unit/routes/test_api_v1_task_runs_contract.py tests/unit/routes/test_api_v1_history_logs_contract.py tests/unit/routes/test_api_v1_account_change_logs_contract.py tests/unit/routes/test_api_v1_accounts_statistics_contract.py tests/unit/routes/test_api_v1_accounts_classifications_contract.py tests/unit/routes/test_api_v1_sqlserver_clusters_contract.py tests/unit/routes/test_api_v1_mysql_clusters_contract.py tests/unit/routes/test_api_v1_partition_contract.py -q  # 36 passed
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
- 2026-06-15: 继续已有 v1 能力迁移：实例详情/删除/恢复/批量测试、数据库表容量详情/刷新、账户权限/变更历史、分类/规则新建编辑、调度 cron 编辑、标签批量分配/移除、系统设置 JumpServer/Veeam/AD 保存与启停测试、分区日期和保留月份参数均接入 React；新增初版 v1 缺口清单。
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
- 2026-06-16: 继续剩余页面迁移：风险中心筛选真正联动 `/api/v1/risk-center/cards`；分类统计接入分类/周期/数据库类型筛选、规则列表、规则贡献和规则趋势钻取，实例/AG 精确范围因缺少 owner scope 选项来源暂保留缺口。
- 2026-06-16: 继续剩余页面迁移：容量实例/数据库页面接入开始/结束日期、数据库类型、实例、数据库和周期筛选联动；调度任务、用户、凭据、标签详情迁移到 shadcn Dialog；分区核心指标日/周/月/季切换联动 `/api/v1/partitions/core-metrics` 参数。
- 2026-06-16: 重规划 v1 API 缺口口径：把 API 已存在但未接入、旧版有入口但 v1 缺路由、旧版本来也没有的未来增强拆分管理；修正实例高级连接参数校验、群集实例绑定/解绑与 SQL Server AG 配置、用户状态/密码编辑不属于缺 API 的误判。
- 2026-06-18: 按重规划继续已有 API 接入：实例表单接入高级连接参数校验；群集管理接入 SQL Server/MySQL 实例绑定/解绑、SQL Server AG 新建/编辑/看板；群集详情弹窗保持查看和同步，不在详情弹窗内发起子弹窗，维护动作从列表操作入口进入。
- 2026-06-18: 首批可验收页面收口：日志、账户变更、同步会话、用户、凭据、标签升为 `Done - replacement`；用户/凭据/标签接入当前登录角色，非管理员只保留查看入口，管理员不可删除当前登录用户。
- 2026-06-18: 第二批可验收页面收口：数据库台账、账户台账、实例容量、数据库容量、实例统计、账户统计、数据库统计升为 `Done - replacement`；容量页和统计页刷新接入统一 Sonner 反馈。
- 2026-06-18: 第三批可验收页面收口：风险中心、群集管理、分类统计、分区管理升为 `Done - replacement`；分类统计接入 `/api/v1/instances/account-scope-options` 实例/AG 筛选，风险中心/分类统计刷新接入 Sonner，分区清理补 shadcn AlertDialog 二次确认。
- 2026-06-18: 最终收口剩余页面：仪表盘删除旧版没有的活动流卡片并补刷新反馈；实例表单接入凭据下拉；账户分类删除补确认；调度任务删除新增 v1 DELETE 路由并接入 React；系统设置补齐旧版可编辑表单、新增模式、多数据源/多 AD 域编辑和 AD LDAP 凭据下拉；22 个导航页面全部升为 `Done - replacement`。
- 2026-06-23: 按 2026-06-22 线上审计报告完成 P0/P1 修复：DataTable 服务端分页、日志/账户变更/会话中心旧版同源数据口径、容量与统计展示内容、群集状态字段、分区指标、实例详情字段和系统设置五模块内容均已收口；代码侧仍需用户重新构建部署后线上复核。
