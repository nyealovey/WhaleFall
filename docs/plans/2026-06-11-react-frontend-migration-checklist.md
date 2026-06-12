# React Frontend Migration Checklist

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-06-11
> 更新: 2026-06-12
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
- 已接入页面: 22
- 仍为占位页: 0
- 当前策略: 内容 parity 已覆盖全部导航页，继续按直接动作、详情弹窗和复杂表单拆分返工
- 旧站点状态: 保持不动，作为回滚入口
- UI 基线: shadcn 风格组件优先，当前已接入 Button、Card、Badge、Input、Separator、Table、Skeleton、Alert、Progress、Chart、TanStack DataTable

## 完整替代验收口径

- 展示内容与旧版一致：指标、列表字段、筛选项、状态、详情信息和空态不能缺项。
- 展示形态可以调整：优先使用 shadcn 组件、TanStack Table 和 Recharts，避免继续复制旧版 DOM 结构。
- 表格筛选由新版 DataTable 工具栏承载；如果表格自带筛选，不再额外做页面级筛选区。
- 写操作必须在 React 内调用 `/api/v1/` 或新增受控 API，不能只跳回旧版后标记完整替代。
- 高风险动作需要单独记录测试、回滚路径和权限校验。

## 已完成

| 新前端路径 | 旧页面路径 | 状态 | 接入 API | 备注 |
| --- | --- | --- | --- | --- |
| `/console/dashboard` | `/dashboard/` | Parity - content | `/api/v1/dashboard/overview`, `/api/v1/dashboard/status`, `/api/v1/dashboard/charts?type=all`, `/api/v1/dashboard/activities`, `/api/v1/risk-center/summary` | 已按旧版补齐刷新数据、数据库实例/账户总数/总容量/数据库总数指标、风险告警、错误和告警日志趋势、系统状态与运行时间；活动流和分类分布作为现有 API 快照保留 |
| `/console/risk-center` | `/risk-center/` | Parity - content | `/api/v1/risk-center/summary`, `/api/v1/risk-center/cards?limit=12` | 已按旧版补齐刷新、总实例/高中低健康指标、搜索/严重度/数据库类型/状态/标签筛选外观、数据库类型分组风险墙和备份/审计/托管/群集/任务核心信号；筛选联动与高风险动作 API 待迁移 |
| `/console/instances` | `/instances/` | Parity - actions | `/api/v1/instances?page=1&limit=20`, `/api/v1/instances/actions/test-connection` | 已按旧版补齐名称、类型、主机/IP、状态、审计、已托管、备份、活跃、版本/同步、标签、操作列；搜索、类型、状态、审计、托管、备份、标签筛选由 DataTable 工具栏承载；单实例连接测试已接入 v1 action；新增、批量删除、批量测试、批量导入和详情待迁移 |
| `/console/database-ledgers` | `/databases/ledgers` | Parity - actions | `/api/v1/databases/ledgers?page=1&limit=20`, `/api/v1/databases/ledgers/actions/sync-all` | 已按旧版补齐数据库/实例、类型、数据库大小、标签、操作列；搜索、类型、标签筛选由 DataTable 工具栏承载；同步所有数据库已接入 v1 action；导出、容量趋势跳转待迁移 |
| `/console/account-ledgers` | `/accounts/ledgers` | Parity - actions | `/api/v1/accounts/ledgers?page=1&limit=20`, `/api/v1/instances/actions/sync-accounts` | 已按旧版补齐账户/实例、是否可用、是否删除、是否超管、AD 状态、分类、类型、标签、操作列；搜索、分类、AD 状态、标签筛选由 DataTable 工具栏承载；同步所有账户已接入 v1 action；导出、权限详情待迁移 |
| `/console/capacity/instances` | `/capacity/instances` | Parity - actions | `/api/v1/capacity/instances?period_type=daily&page=1&limit=20&start_date=...&end_date=...`, `/api/v1/capacity/instances/summary?period_type=daily&start_date=...&end_date=...`, `/api/v1/capacity/aggregations/current` | 已按旧版补齐刷新数据、统计当前周期、数据库类型/实例/周期筛选、在线实例数/总容量/平均容量/最大容量指标，以及容量统计趋势图、容量变化趋势图、容量变化趋势图(百分比)；刷新和实例当前周期统计已接入 React；筛选联动细节待完整替代验收 |
| `/console/capacity/databases` | `/capacity/databases` | Parity - actions | `/api/v1/capacity/databases?period_type=daily&page=1&limit=20&start_date=...&end_date=...`, `/api/v1/capacity/databases/summary?period_type=daily&start_date=...&end_date=...`, `/api/v1/capacity/aggregations/current` | 已按旧版补齐刷新数据、统计当前周期、数据库类型/实例/数据库/周期筛选、总数据库数/总容量/平均容量/最大容量指标，以及容量统计趋势图、容量变化趋势图、容量变化趋势图(百分比)；刷新和数据库当前周期统计已接入 React；筛选联动细节待完整替代验收 |
| `/console/instance-statistics` | `/instances/statistics` | Parity - content | `/api/v1/instances/statistics` | 已按旧版补齐返回实例列表/刷新统计命令、实例总数/审计信息/托管统计/备份统计、备份状态分布、数据库类型分布、端口分布、数据库版本统计和版本分布图；刷新写侧效果、图表交互细节待完整替代验收 |
| `/console/account-statistics` | `/accounts/statistics` | Parity - content | `/api/v1/accounts/statistics/summary`, `/api/v1/accounts/statistics/db-types`, `/api/v1/accounts/statistics/classifications`, `/api/v1/accounts/statistics/rules` | 已按旧版补齐账户列表/刷新统计命令、总账户数/正常账户/受限账户/统计实例、账户来源分布、AD 账户对比、数据库类型分布、账户分类分布；规则命中作为现有 API 快照保留 |
| `/console/database-statistics` | `/databases/statistics` | Parity - content | `/api/v1/databases/statistics` | 已按旧版补齐数据库台账/刷新统计命令、数据库总数/正常数据库/覆盖实例/总容量、数据库类型分布、实例数据库分布、同步状态分布和最新容量排行 |
| `/console/logs` | `/history/logs/` | Parity - content | `/api/v1/logs?page=1&limit=20`, `/api/v1/logs/statistics?hours=24` | 已按旧版补齐时间、级别、模块、消息、操作列；搜索、级别、模块、时间范围筛选由 DataTable 工具栏承载；详情 API/弹窗待迁移 |
| `/console/account-change-logs` | `/history/account-change-logs/` | Parity - content | `/api/v1/account-change-logs?page=1&limit=20`, `/api/v1/account-change-logs/statistics?hours=24` | 已按旧版补齐时间、数据库类型、实例、账号、类型、摘要、操作列；搜索、实例、数据库类型、变更类型、时间范围筛选由 DataTable 工具栏承载；详情 API/弹窗待迁移 |
| `/console/clusters` | `/cluster/` | Parity - content | `/api/v1/sqlserver-clusters?page=1&limit=20`, `/api/v1/mysql-clusters?page=1&limit=20` | 已按旧版补齐 SQL Server 群集列：群集、域名、状态、绑定实例、AG、最近 AG 同步、数据库同步状态、操作；MySQL 群集列：群集、拓扑、状态、绑定实例、主从状态、操作；搜索和状态筛选由 DataTable 工具栏承载；添加、管理、AG 账户、AG 状态、主从状态 API 待迁移 |
| `/console/account-classifications` | `/accounts/classifications/` | Parity - actions | `/api/v1/accounts/classifications`, `/api/v1/accounts/classifications/rules`, `/api/v1/accounts/classifications/actions/auto-classify`, `/api/v1/accounts/classifications/{id}`, `/api/v1/accounts/classifications/rules/{id}` | 已按旧版补齐自动分类入口、账户分类面板、规则管理面板、风险等级、系统标记、规则分组、命中数和查看/编辑/删除入口；自动分类、自定义分类删除和规则删除已接入 v1 action；新建/编辑分类和规则表单待迁移 |
| `/console/classification-statistics` | `/accounts/statistics/classifications` | Parity - content | `/api/v1/accounts/statistics/classifications`, `/api/v1/accounts/statistics/classifications/trends?period_type=daily&periods=7` | 已按旧版补齐刷新、账户分类/统计周期/数据库类型/实例范围筛选外观、规则列表空态、分类趋势（去重账号数）、规则贡献（当前周期）和说明文案；筛选联动、规则钻取 API 待迁移 |
| `/console/scheduler` | `/scheduler/` | Parity - actions | `/api/v1/scheduler/jobs`, `/api/v1/scheduler/jobs/actions/reload`, `/api/v1/scheduler/jobs/{id}/actions/pause`, `/api/v1/scheduler/jobs/{id}/actions/resume`, `/api/v1/scheduler/jobs/{id}/actions/run` | 已按旧版补齐运行中/已暂停任务分组、任务名称、状态、下次运行、上次运行、任务 ID、触发器参数和重新初始化/暂停/恢复/立即执行/编辑/删除入口；重新初始化、暂停、恢复、立即执行已接入 v1 action；编辑/删除任务待迁移 |
| `/console/sync-sessions` | `/history/sessions/` | Parity - actions | `/api/v1/sync-sessions?page=1&limit=20`, `/api/v1/sync-sessions/{id}/actions/cancel` | 已按旧版补齐运行ID、状态、进度、任务、来源、分类、开始时间、耗时、操作列；来源、分类、状态筛选由 DataTable 工具栏承载；运行中会话取消已接入 v1 action；详情时间线待迁移 |
| `/console/users` | `/users/` | Parity - content | `/api/v1/users?page=1&limit=10`, `/api/v1/users/stats` | 已按旧版补齐 ID、用户、角色、状态、创建时间、操作列；搜索、角色、状态筛选由 DataTable 工具栏承载；新建、编辑、删除 API 待迁移 |
| `/console/settings` | `/admin/system-settings` | Parity - actions | `/api/v1/alerts/email-settings`, `/api/v1/alerts/email-settings/actions/send-test`, `/api/v1/alerts/email-settings/actions/send-feishu-test`, `/api/v1/risk-center/rules`, `/api/v1/integrations/jumpserver/source`, `/api/v1/integrations/jumpserver/actions/sync`, `/api/v1/integrations/veeam/sources`, `/api/v1/integrations/veeam/actions/sync`, `/api/v1/ad-domain-configs`, `/api/v1/ad-domain-configs/actions/sync` | 已按旧版补齐设置模块导航、告警发送/规则设置、风险规则、JumpServer、Veeam、AD 设置表单字段和操作入口；告警测试/保存、风险规则保存、JumpServer 同步/解绑、Veeam 同步/删除、AD 同步/删除已接入 v1 action；绑定、数据源、AD 域编辑表单待迁移 |
| `/console/credentials` | `/credentials/` | Parity - content | `/api/v1/credentials?page=1&limit=20` | 已按旧版补齐凭据、类型、数据库类型、状态、绑定实例、创建时间、操作列；搜索、凭据类型、数据库类型、状态筛选由 DataTable 工具栏承载；新增、编辑、删除、测试连接 API 待迁移 |
| `/console/tags` | `/tags/` | Parity - content | `/api/v1/tags?page=1&limit=20`, `/api/v1/tags/categories` | 已按旧版补齐全部标签、启用率、停用率、标签分类、标签/分类/状态/关联/操作列；搜索、分类、状态筛选由 DataTable 工具栏承载；新增、删除、批量分配 API 待迁移 |
| `/console/partitions` | `/partition/` | Parity - actions | `/api/v1/partitions/status`, `/api/v1/partitions?page=1&limit=20`, `/api/v1/partitions/core-metrics?period_type=daily&days=7`, `/api/v1/partitions`, `/api/v1/partitions/actions/cleanup` | 已按旧版补齐创建分区/清理旧分区入口、分区总数/总大小/总记录数/健康状态指标、核心指标趋势、日周月季切换外观和分区列表；创建分区和按 12 个月保留清理已接入 v1 action；周期联动和保留月份输入待迁移 |

## 待迁移

当前导航内剩余页面的只读首屏已全部迁移到 React；同步、刷新、取消、删除、统计当前周期等已有 v1 直接动作已迁移一批。接下来按完整替代口径迁移新增、编辑、导入、导出、详情弹窗、批量绑定、批量删除、可配置参数表单等复杂交互。

## 本次动作迁移与风险

- 已迁移动作：实例连接测试、数据库同步、账户同步、容量当前周期统计、账户自动分类、自定义分类删除、规则删除、调度器重新初始化/暂停/恢复/立即执行、会话取消、告警测试/保存、风险规则保存、JumpServer 同步/解绑、Veeam 同步/删除、AD 同步/删除、分区创建/清理。
- 权限校验：所有写操作仍走同源 `/api/v1/**`，后端权限与 CSRF 契约不在 React 层放宽；前端只负责触发与刷新。
- 回滚路径：每页保留“在旧版打开”，如新前端动作异常，可直接回到旧版页面执行同一操作；旧站点模板和静态资源未改动。
- 待补风险控制：高风险删除动作后续应补 shadcn AlertDialog/确认弹窗和用户可见的异步结果反馈；当前批次先完成 API 接线与测试覆盖。

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
- 2026-06-12: 继续 action parity：新增 `frontend/src/api/actions.ts`，接入实例连接测试、台账同步、容量当前周期统计、账户自动分类/删除、调度任务、同步会话取消、系统设置保存/测试/同步/删除、分区创建/清理等直接动作；复杂新增/编辑/详情/导入/导出表单继续保留为待迁移缺口。
