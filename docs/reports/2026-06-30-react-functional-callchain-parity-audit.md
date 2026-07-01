# React 新旧页面功能调用链一致性审计（2026-06-30）

状态：`Active - call-chain audit`

本文件替代“只看页面静态展示”的复核方式。后续每次验收按同一口径逐项核对：

`操作入口 -> 旧版调用接口/参数 -> 新版调用接口/参数 -> 展示结果`

## 审计口径

- 旧版真源包括 Flask 模板、旧版共享 JS、旧版弹窗和二级异步请求。
- 新版真源包括 React 页面、`frontend/src/api/*.ts`、React Query key、表格/弹窗展示和相关测试。
- 写操作不在生产环境直接点击最终确认；以源码参数、单元测试和必要的线上只读 Network 复核为准。
- 对旧版没有的增强入口，不纳入替代验收；新版已出现的旧版无入口能力要删除或移出主流程。

## 状态定义

| 状态 | 含义 |
| --- | --- |
| `Closed` | 源码调用链一致，参数一致或等价，已有测试或低风险只读复核。 |
| `Fixed locally` | 本地代码已修复并通过测试，等待部署后线上复核。 |
| `Needs live verification` | 源码口径基本一致，但必须部署后用浏览器逐项点击/看 Network 验证。 |
| `Open` | 新版仍缺入口、缺接口参数、缺展示结果或展示明显不等价。 |
| `Out of scope` | 旧版没有该入口或只是未来增强，不阻塞本次替代。 |

## 本轮结论

- 已修复一个此前静态审计漏掉的功能链：SQL Server 群集 `AG 账户` 弹窗现在会按选中 AG 调用账户台账接口，并展示真实 AG 账户列表。
- 旧版 `AG 账户` 不是只展示 AG 看板；它还会发起二级请求：`/api/v1/accounts/ledgers?owner_type=sqlserver_ag&owner_id=...&include_roles=true&sort=username&order=asc&limit=100`。
- 新版已补齐同一二级请求，并在测试中断言 `owner_type`、`owner_id`、`include_roles`、排序和展示字段。
- 这份文档仍是源码级审计结果；部署后需要按“后续线上复核清单”逐项点页面和弹窗确认。

## 全局入口

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 全局页头 | 修改密码 | 旧版 `base.html` 触发 `data-action="open-change-password"`，提交认证相关接口 | React 全局弹窗沿用认证接口提交密码变更 | 弹窗表单、成功/失败反馈 | `Needs live verification` |
| 全局页头 | 退出 | 旧版登出入口 | React `apiClient.post("/api/v1/auth/logout", {})` | 清理会话并跳转登录 | `Needs live verification` |
| 页尾 | 关于 | 旧版 `/old/about` | React `/about` | 关于页版本、功能说明、版本历史 | `Closed` |
| 页尾 | 新版/旧版入口 | 旧版挂 `/old/` | React `/dashboard`、旧版 `/old/` | 页尾统一入口，不再每页放“在旧版打开” | `Closed` |

## 仪表盘与风险中心

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/dashboard` | 页面加载/刷新 | 旧版 `dashboard/overview.js` 读取 dashboard 总览、状态、图表、风险摘要 | `fetchDashboardSnapshot()` 并行调用 `/api/v1/dashboard/overview`、`/api/v1/dashboard/status`、`/api/v1/dashboard/charts?type=all`、`/api/v1/dashboard/activities`、`/api/v1/risk-center/summary` | 总览卡片、运行信号图、风险摘要 | `Needs live verification` |
| `/dashboard` | 风险卡跳转 | 旧版风险摘要卡进入风险/实例详情 | React 风险摘要链接到风险中心或实例详情 | 不做旧版没有的活动流详情 | `Needs live verification` |
| `/risk-center` | 风险列表筛选/分页 | 旧版风险中心筛选后刷新风险卡 | React `/api/v1/risk-center/summary` + `/api/v1/risk-center/cards?page=&limit=&severity=&db_type=&status=&tag=&search=` | 风险卡分页列表、摘要 | `Closed` |
| `/risk-center` | 清空筛选/刷新 | 旧版 `data-action="clear-risk-filters"`、`refresh-risk-center` | React 重置本地筛选并重新请求同一路口 | 筛选恢复默认、Toast 反馈 | `Needs live verification` |

## 实例管理与实例详情

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/instances` | 列表搜索/筛选/分页 | 旧版实例 grid 调 `/api/v1/instances`，带 `page/limit/search/db_type/status/audit_status/managed_status/backup_status/tags/include_deleted` | `fetchInstances()` 同参数，默认 `limit=20`，标签多值透传 | 20/50/100 服务端分页，筛选结果列表 | `Needs live verification` |
| `/instances` | 导出 CSV | 旧版 `data-export-url="/api/v1/instances/exports"`，带当前筛选 | `buildInstancesExportPath()` 带当前筛选参数 | 下载 CSV | `Closed` |
| `/instances` | 新增/编辑实例 | 旧版实例表单保存 `/api/v1/instances` 或 `/api/v1/instances/{id}` | `createInstance()`、`updateInstance()`；保存前可调用 `validateInstanceConnectionParams()` | 表单字段、凭据、标签、连接参数 | `Needs live verification` |
| `/instances` | 高级连接参数校验 | 旧版同 v1 校验路由 | `POST /api/v1/instances/actions/validate-connection-params` | 参数校验反馈 | `Closed` |
| `/instances` | 测试连接 | 旧版行按钮 `test-connection` | `POST /api/v1/instances/actions/test-connection`，body `{ instance_id }` | 行操作反馈 | `Closed` |
| `/instances` | 批量测试连接 | 旧版批量测试选中实例 | `POST /api/v1/instances/actions/batch-test-connections`，body `{ instance_ids }` | 批量结果反馈 | `Needs live verification` |
| `/instances` | 批量移入回收站 | 旧版批量删除选中实例 | `POST /api/v1/instances/actions/batch-delete`，body `{ instance_ids, deletion_mode }` | 只作用于当前明确选中记录 | `Needs live verification` |
| `/instances` | 批量导入 | 旧版模板下载 `/api/v1/instances/imports/template`，上传批量创建 | React 模板链接同旧版；上传 `POST /api/v1/instances/actions/batch-create` form-data `file` | 导入结果反馈 | `Closed` |
| `/instances` | 恢复已删除实例 | 旧版行操作 `restore-instance` | `POST /api/v1/instances/{id}/actions/restore` | 恢复后刷新列表 | `Closed` |
| `/instances/{id}` | 详情基础信息 | 旧版详情页读取实例详情、连接状态 | `GET /api/v1/instances/{id}`、`GET /api/v1/instances/{id}/connection-status` | 实例 ID、名称、类型、主机、版本、状态、标签、最后同步 | `Needs live verification` |
| `/instances/{id}` | 详情编辑/删除 | 旧版 `edit-instance`、`delete-instance` | React 跳编辑表单，删除 `DELETE /api/v1/instances/{id}` | 编辑入口、移入回收站入口 | `Needs live verification` |
| `/instances/{id}` | 同步账户 | 旧版 `POST /api/v1/instances/{id}/actions/sync-accounts` | `syncInstanceAccounts(instanceId)` | 刷新账户区 | `Closed` |
| `/instances/{id}` | 同步容量 | 旧版 `POST /api/v1/instances/{id}/actions/sync-capacity` | `syncInstanceCapacity(instanceId)` | 刷新容量区 | `Closed` |
| `/instances/{id}` | 同步审计 | 旧版 `POST /api/v1/instances/{id}/actions/sync-audit-info` | `syncInstanceAuditInfo(instanceId)` | 刷新审计区 | `Closed` |
| `/instances/{id}` | 同步备份 | 旧版 Veeam 单实例同步 | `POST /api/v1/integrations/veeam/actions/sync-instance/{instanceId}` | 刷新备份区 | `Closed` |
| `/instances/{id}` | 账户信息 Tab | 旧版 `/api/v1/accounts/ledgers?instance_id={id}&sort=username&order=asc&include_roles=true&owner_type=instance` | `fetchInstanceAccounts()` 同参数 | 账户汇总、账户列表、权限/变更历史入口 | `Closed` |
| `/instances/{id}` | AG 账户 Tab | 旧版 `/api/v1/instances/{id}/ag-accounts` | `fetchInstanceAgAccounts()` | AG 账户列表、状态和最近同步 | `Closed` |
| `/instances/{id}` | 容量信息 Tab | 旧版 `/api/v1/databases/sizes?instance_id={id}` | `/api/v1/databases/sizes?instance_id={id}&latest_only=true&include_inactive=true&page=1&limit=100` | 数据库总数、当前/删除、容量总量、表容量入口 | `Needs live verification` |
| `/instances/{id}` | 审计信息 Tab | 旧版 `/api/v1/instances/{id}/audit-info` | `fetchInstanceAuditInfo()` | 审计状态、策略、时间、明细 | `Needs live verification` |
| `/instances/{id}` | 备份信息 Tab | 旧版 `/api/v1/instances/{id}/backup-info` | `fetchInstanceBackupInfo()` | Backup ID、平台、覆盖数量、备份大小、压缩率 | `Needs live verification` |
| `/instances/{id}` | 账户权限详情 | 旧版账户行 `view-permissions` 调 `/api/v1/accounts/ledgers/{accountId}/permissions` | `fetchAccountPermissions(accountId)`，展示共享 `PermissionSnapshotView` | 按旧版分组展示角色、权限、数据库权限，不再展示原始 JSON | `Fixed locally` |
| `/instances/{id}` | 账户变更历史 | 旧版账户行 `view-history` 调 `/api/v1/accounts/ledgers/{accountId}/change-history` | `fetchAccountChangeHistory(accountId)` | 账户变更列表/详情 | `Needs live verification` |
| `/instances/{id}` | 表容量 | 旧版数据库行 `open-table-sizes` 调 `/api/v1/databases/{databaseId}/tables/sizes` | `fetchDatabaseTableSizes(databaseId)`，刷新表容量 `POST /api/v1/databases/{id}/tables/sizes/actions/refresh?page=1&limit=20` | 表容量弹窗 | `Closed` |

## 数据库台账与账户台账

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/databases` | 列表搜索/筛选/分页 | 旧版 `/api/v1/databases/ledgers`，带 `page/limit/search/db_type/instance_id/tags` | `fetchDatabaseLedgers()` 同参数 | 数据库列表、分页、标签筛选 | `Needs live verification` |
| `/databases` | 同步全部数据库 | 旧版 `POST /api/v1/databases/ledgers/actions/sync-all` | `syncDatabases()` | 同步反馈并刷新 | `Closed` |
| `/databases` | 导出 CSV | 旧版 `/api/v1/databases/ledgers/exports` 带筛选 | `buildDatabaseLedgersExportPath()` | 下载 CSV | `Closed` |
| `/databases` | 表容量 | 旧版数据库行表容量弹窗 | 新版按钮文案为“表容量”，调 `/api/v1/databases/{id}/tables/sizes` | 展示表容量明细 | `Fixed locally` |
| `/databases` | 趋势 | 旧版跳转数据库容量并带实例/数据库筛选 | 新版新增“趋势”链接到 `/capacity/databases?instance_id=&db_type=&database_name=` | 容量页面自动带入筛选 | `Fixed locally` |
| `/accounts` | 列表搜索/筛选/分页 | 旧版 `/api/v1/accounts/ledgers`，带 `page/limit/search/instance_id/tags/classification/db_type/ad_status` | `fetchAccountLedgers()` 同参数，默认追加 `sort=username&order=asc` | 账户台账列表、分类/AD/标签筛选 | `Needs live verification` |
| `/accounts` | 同步全部账户 | 旧版 `POST /api/v1/instances/actions/sync-accounts` | `syncAccounts()` | 同步反馈并刷新 | `Closed` |
| `/accounts` | 导出 CSV | 旧版 `/api/v1/accounts/ledgers/exports` 带筛选 | `buildAccountLedgersExportPath()` | 下载 CSV | `Closed` |
| `/accounts` | 权限详情 | 旧版 `/api/v1/accounts/ledgers/{id}/permissions` | `fetchAccountPermissions()` + `PermissionSnapshotView` | 与实例详情入口共用展示 | `Fixed locally` |
| `/accounts` | 变更历史 | 旧版 `/api/v1/accounts/ledgers/{id}/change-history` | `fetchAccountChangeHistory()` | 变更历史弹窗/详情 | `Needs live verification` |

## 群集管理

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/clusters` | SQL Server/MySQL 标签切换 | 旧版同一页按标签展示一种群集 | React 使用 Tabs，同屏只展示当前类型 | SQL Server 和 MySQL 不再双列同时显示 | `Closed` |
| `/clusters` | SQL Server 列表 | 旧版 SQL Server 群集 grid | `GET /api/v1/sqlserver-clusters?page=&limit=&search=&status=` | 群集列表、状态字段、操作入口 | `Needs live verification` |
| `/clusters` | MySQL 列表 | 旧版 MySQL 群集 grid | `GET /api/v1/mysql-clusters?page=&limit=&search=&status=` | 群集列表、拓扑状态 | `Needs live verification` |
| `/clusters` | 新建/编辑 SQL Server 群集 | 旧版群集管理弹窗保存 | `POST /api/v1/sqlserver-clusters`、`PATCH /api/v1/sqlserver-clusters/{id}` | 表单、保存反馈 | `Needs live verification` |
| `/clusters` | 新建/编辑 MySQL 群集 | 旧版 MySQL 群集管理弹窗保存 | `POST /api/v1/mysql-clusters`、`PATCH /api/v1/mysql-clusters/{id}` | 表单、保存反馈 | `Needs live verification` |
| `/clusters` | 绑定/解绑实例 | 旧版群集管理中调整实例列表 | `PUT /api/v1/sqlserver-clusters/{id}/instances`、`PUT /api/v1/mysql-clusters/{id}/instances`，body `{ instance_ids }` | 替换绑定实例列表 | `Closed` |
| `/clusters` | SQL Server AG 新建/编辑 | 旧版 AG 配置表单 | `POST /api/v1/sqlserver-clusters/{id}/availability-groups`、`PATCH /api/v1/sqlserver-clusters/{id}/availability-groups/{agId}` | AG 配置保存 | `Closed` |
| `/clusters` | 同步 AG | 旧版 `sync-ag` 调 AG 同步 | `POST /api/v1/sqlserver-clusters/{id}/availability-groups/actions/sync`，body `{ connection_database }` | AG 列表刷新 | `Closed` |
| `/clusters` | 同步 SQL Server 状态 | 旧版 `sync-sqlserver-status` | `POST /api/v1/sqlserver-clusters/{id}/actions/sync-status` | 群集状态刷新 | `Closed` |
| `/clusters` | AG 状态看板 | 旧版打开 AG 状态弹窗并按 AG 切换 | `GET /api/v1/sqlserver-clusters/{clusterId}/availability-groups/{agId}/dashboard` | 副本/数据库同步状态明细 | `Needs live verification` |
| `/clusters` | AG 账户看板 | 旧版先取群集详情，再按选中 AG 调 `/api/v1/accounts/ledgers?owner_type=sqlserver_ag&owner_id={agId}&include_roles=true&sort=username&order=asc&limit=100` | 新版已按同一参数调用 `fetchAccountLedgers({ ownerType:"sqlserver_ag", ownerId:agId, includeRoles:true, limit:100 })` | AG KPI、AG Tabs、真实账户列表、分类、标签、AD 状态、最近变更 | `Fixed locally` |
| `/clusters` | 同步 AG 账户 | 旧版 `sync-ag-accounts-dashboard` | `POST /api/v1/sqlserver-clusters/{id}/availability-groups/actions/sync-accounts` | 同步后刷新 AG 账户列表 | `Fixed locally` |
| `/clusters` | MySQL 拓扑看板/同步 | 旧版打开主从状态并 `sync-mysql-topology-dashboard` | `GET /api/v1/mysql-clusters/{id}`、`POST /api/v1/mysql-clusters/{id}/actions/sync-topology` | 拓扑、异常副本、最近同步 | `Needs live verification` |

## 标签、用户、凭据

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/tags` | 标签列表筛选/分页 | 旧版 `/api/v1/tags` + `/api/v1/tags/categories` | React 同路口，服务端分页 | 标签名称、分类、状态、关联数量 | `Needs live verification` |
| `/tags` | 新建/编辑标签 | 旧版标签表单含分类下拉 | `POST /api/v1/tags`、`PUT /api/v1/tags/{id}`，分类来自 categories/options | 分类下拉、名称/代码/颜色/状态 | `Fixed locally` |
| `/tags` | 删除标签 | 旧版 `DELETE /api/v1/tags/{id}` | `deleteTag(tagId)` | 删除确认和刷新 | `Closed` |
| `/tags` | 批量分配标签 | 旧版一个页面内含分配/移除模式，实例按数据库类型折叠，标签按分类折叠；提交 `POST /api/v1/tags/bulk/actions/assign` | 新版批量页已还原分配/移除模式，数据源 `GET /api/v1/tags/bulk/instances`、`GET /api/v1/tags/bulk/tags`，提交 `{ instance_ids, tag_ids }` | 折叠分组、选择汇总、确认结果 | `Needs live verification` |
| `/tags` | 批量移除标签 | 旧版同批量页切换移除模式；提交 remove/remove-all | `POST /api/v1/tags/bulk/actions/remove` 或 `remove-all` | 移除模式清晰展示 | `Needs live verification` |
| `/users` | 用户列表 | 旧版 `/api/v1/users` | `GET /api/v1/users?page=&limit=&search=&role=&status=` + `/api/v1/users/stats` | 用户列表、角色、状态 | `Closed` |
| `/users` | 新建/编辑/删除用户 | 旧版 `POST/PUT/DELETE /api/v1/users` | React 同路口；启停和重置密码收敛在编辑保存口径 | 表单、状态、角色、密码字段 | `Needs live verification` |
| `/credentials` | 凭据列表 | 旧版 `/api/v1/credentials` | `GET /api/v1/credentials?page=&limit=&search=&credential_type=&db_type=&status=` | 凭据类型、数据库类型、绑定数量、状态 | `Closed` |
| `/credentials` | 新建/编辑/删除凭据 | 旧版 `POST/PUT/DELETE /api/v1/credentials` | React 同路口 | 数据库类型条件字段、状态、保存反馈 | `Needs live verification` |

## 账户分类与分类统计

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/account-classifications` | 分类列表 | 旧版 `/api/v1/accounts/classifications` | `GET /api/v1/accounts/classifications` | 六种分类、零值分类也展示 | `Closed` |
| `/account-classifications` | 新建/编辑/删除分类 | 旧版分类表单和删除 | `POST /api/v1/accounts/classifications`、`PUT /api/v1/accounts/classifications/{id}`、`DELETE /api/v1/accounts/classifications/{id}` | 分类基础信息、删除确认 | `Needs live verification` |
| `/account-classifications` | 规则列表 | 旧版 `/api/v1/accounts/classifications/rules` + `/api/v1/accounts/statistics/rules?rule_ids=...` | `fetchAccountClassificationsSnapshot()` 同路口合并命中数 | 按数据库类型显示规则、命中数 | `Closed` |
| `/account-classifications` | 查看规则详情 | 旧版查看规则展示权限勾选结果，不展示原始 JSON | `GET /api/v1/accounts/classifications/rules/{id}`；新版已统一解析规则表达式为权限分组展示 | 规则详情、权限选项、分类/类型/版本 | `Fixed locally` |
| `/account-classifications` | 新建/编辑规则 | 旧版选择数据库类型后显示可勾选权限复选框，保存规则表达式 | React 读取 `GET /api/v1/accounts/classifications/permissions/{dbType}`，表单用复选框生成统一规则表达式，保存 `POST/PUT /api/v1/accounts/classifications/rules` | 复选框权限配置，不再让用户手写表达式 | `Fixed locally` |
| `/account-classifications` | 校验规则表达式 | 旧版保存前/调试可校验表达式 | `POST /api/v1/accounts/classifications/rules/actions/validate-expression` | 校验反馈 | `Needs live verification` |
| `/account-classifications` | 自动分类 | 旧版 `auto-classify-all` | `POST /api/v1/accounts/classifications/actions/auto-classify` | 自动分类结果反馈 | `Needs live verification` |
| `/classification-statistics` | 默认全分类趋势 | 旧版默认展示所有分类曲线 | 新版 `GET /api/v1/accounts/statistics/classifications/trends?period_type=&periods=&db_type=&account_scope=`，默认全部分类 | 图例显示全部分类，不要求先选分类 | `Fixed locally` |
| `/classification-statistics` | 规则列表和规则贡献 | 旧版选中分类后展示规则列表、规则趋势、贡献 | 新版 `trend`、`rules/overview`、`rules/contributions`、`rules/trend` 同 v1 统计路口 | 分类趋势、规则贡献、覆盖天数 | `Needs live verification` |

## 容量、统计、分区

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/capacity/instances` | 筛选/趋势 | 旧版实例容量按 db_type、实例、周期、日期窗口查询 | `/api/v1/capacity/instances`、`/summary`，参数 `period_type/page/limit/start_date/end_date/instance_id/db_type/get_all` | 四张汇总卡、趋势图、TopN | `Needs live verification` |
| `/capacity/databases` | 筛选/趋势 | 旧版数据库容量按 db_type、实例、数据库、周期查询 | `/api/v1/capacity/databases`、`/summary`，参数 `period_type/page/limit/start_date/end_date/instance_id/db_type/database_name/get_all` | 汇总卡、趋势图、TopN | `Needs live verification` |
| `/capacity/*` | 统计当前周期 | 旧版统计当前周期按钮 | `POST /api/v1/capacity/aggregations/current`，body `{ scope }` | 统计反馈 | `Closed` |
| `/statistics/instances` | 实例统计 | 旧版 `/api/v1/instances/statistics` | React 同路口 | 分布、同步状态、静态统计表 | `Closed` |
| `/statistics/accounts` | 账户统计 | 旧版账户统计三路口 | `/api/v1/accounts/statistics/summary`、`/db-types`、`/classifications`、`/rules` | 六种分类、数据库类型和规则统计 | `Closed` |
| `/statistics/databases` | 数据库统计 | 旧版 `/api/v1/databases/statistics` | React 同路口 | 数据库分布、统计表 | `Closed` |
| `/partitions` | 分区状态/列表 | 旧版分区页显示状态、历史/当前/未来和列表 | `GET /api/v1/partitions/status`、`GET /api/v1/partitions?page=&limit=&search=&table_type=&status=` | 4 张卡片、列表状态颜色图标 | `Fixed locally` |
| `/partitions` | 核心指标趋势 | 旧版按日/周/月/季展示多条核心指标曲线 | `GET /api/v1/partitions/core-metrics?period_type=&days=` | 区分实例平均/实例统计量/数据库平均/数据库统计量，颜色和图标对齐旧版 | `Fixed locally` |
| `/partitions` | 创建分区/清理分区 | 旧版分区创建、清理 | `POST /api/v1/partitions`、`POST /api/v1/partitions/actions/cleanup` | 创建/清理反馈、二次确认 | `Needs live verification` |

## 日志、变更历史、会话中心、定时任务

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/logs` | 日志列表筛选 | 旧版日志页按时间范围、级别、模块筛选 | `/api/v1/logs?page=&limit=&search=&level=&module=&hours=` + `/api/v1/logs/statistics?hours=` + `/api/v1/logs/modules` | 列表和统计同时间范围 | `Closed` |
| `/logs` | 日志详情 | 旧版 `/api/v1/logs/{id}`，支持复制消息/JSON/堆栈 | `fetchHistoryLogDetail()` 同路口；复制为前端行为 | 详情弹窗、上下文、复制按钮 | `Needs live verification` |
| `/account-changes` | 变更列表筛选 | 旧版 `/api/v1/account-change-logs`，默认全部时间；实例选项来自实例 options | 新版同路口，统计 `/statistics`，选项 `/api/v1/instances/options` | 无 4 张多余卡片、实例显示正确 | `Fixed locally` |
| `/account-changes` | 变更详情 | 旧版 `/api/v1/account-change-logs/{id}` | `fetchAccountChangeLogDetail()` 同路口 | 账户、实例、类型、差异明细 | `Fixed locally` |
| `/sessions` | 会话/任务运行列表 | 旧版任务运行页 | `GET /api/v1/task-runs?page=&limit=&task_category=&status=&sort=started_at&order=desc` | 任务运行列表、来源/分类/状态固定选项 | `Closed` |
| `/sessions` | 任务详情/错误日志 | 旧版 task-run 详情和错误日志 | `GET /api/v1/task-runs/{runId}`、`GET /api/v1/task-runs/{runId}/error-logs` | 详情、错误日志、复制 run id/堆栈 | `Closed` |
| `/sessions` | 取消任务 | 旧版取消运行中任务 | `POST /api/v1/task-runs/{runId}/actions/cancel` | 取消反馈 | `Needs live verification` |
| `/scheduler` | 任务列表/详情 | 旧版 scheduler jobs | `GET /api/v1/scheduler/jobs`、`GET /api/v1/scheduler/jobs/{id}` | 任务 ID、触发器拆字段、本地时间 | `Closed` |
| `/scheduler` | 重载/暂停/恢复/运行/编辑/删除 | 旧版 scheduler 动作 | `POST reload`、`POST pause/resume/run`、`PUT /jobs/{id}`、`DELETE /jobs/{id}` | 按钮反馈、刷新列表 | `Needs live verification` |

## 系统设置

| 页面/区域 | 操作入口 | 旧版调用接口/参数 | 新版调用接口/参数 | 展示结果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `/settings` | 告警设置加载/保存 | 旧版 `_email-alert-settings-section.html` 使用 `/api/v1/alerts/email-settings` | `GET /api/v1/alerts/email-settings`、`PUT /api/v1/alerts/email-settings` | 收件人、容量异常增长子设置、飞书 webhook 脱敏 | `Needs live verification` |
| `/settings` | 邮件测试 | 旧版 `send-test` | `POST /api/v1/alerts/email-settings/actions/send-test`，body `{ recipients }` | 测试反馈 | `Needs live verification` |
| `/settings` | 飞书测试 | 旧版 `send-feishu-test` | `POST /api/v1/alerts/email-settings/actions/send-feishu-test`，body `{ feishu_webhook_url }` | 测试反馈 | `Needs live verification` |
| `/settings` | 风险规则保存 | 旧版 `/api/v1/risk-center/rules` | `GET /api/v1/risk-center/rules`、`PUT /api/v1/risk-center/rules` | 分类、中文名、描述、严重级别、启用开关 | `Needs live verification` |
| `/settings` | JumpServer 来源 | 旧版 `/api/v1/integrations/jumpserver/source`、同步 `/actions/sync` | React 同路口，支持保存/解绑/同步 | 绑定信息、SSL 状态、最近同步 | `Needs live verification` |
| `/settings` | Veeam 数据源 | 旧版 source/sources/sync | `GET /sources`、`POST /sources`、`PUT /sources/{id}`、`POST enable/disable`、`DELETE /sources/{id}`、`POST /actions/sync` | 多数据源列表、启用状态、最近同步 | `Needs live verification` |
| `/settings` | AD 域配置 | 旧版 `/api/v1/ad-domain-configs` + LDAP 凭据下拉 `/api/v1/credentials?credential_type=ldap&status=active` | React 同路口；新增/编辑/启停/测试/删除/同步 | 域控、凭据、同步状态、AD/SQL 统计 | `Needs live verification` |

## 本轮已补的测试证据

| 范围 | 验证 |
| --- | --- |
| AG 账户调用链 | `npm --prefix frontend run test -- src/api/lists.test.ts`，断言账户台账带 `owner_type=sqlserver_ag&owner_id=21&include_roles=true`。 |
| AG 账户展示 | `npm --prefix frontend run test -- src/pages/ConsolePages.test.tsx`，断言弹窗展示 AG 账户、分类、标签和最近变更。 |
| 实例详情布局稳定 | `npm --prefix frontend run test -- src/pages/ListPages.test.tsx`，断言详情 Tab 内容区固定最小高度，避免切 Tab 页面跳动。 |
| 全量前端静态验证 | 最近本地已通过 `npm --prefix frontend run lint`、`npm --prefix frontend run typecheck`、`npm --prefix frontend run build`。 |

## 后续线上复核清单

部署本地修复后，按以下顺序逐项复核。只读入口可直接点击；写操作到确认前停止，或在测试数据上执行。

1. `/clusters`：打开 SQL Server 群集的 `AG 账户`，切换 AG 标签，确认 Network 出现 `/api/v1/accounts/ledgers?owner_type=sqlserver_ag&owner_id=...&include_roles=true...`，列表出现真实账户。
2. `/databases`：点击同一行 `表容量` 与 `趋势`，确认前者打开表容量弹窗，后者跳 `/capacity/databases` 并带 `instance_id/db_type/database_name`。
3. `/accounts` 和 `/instances/{id}`：分别打开权限详情，确认不再展示原始 JSON，显示角色、服务器权限、数据库权限分组。
4. `/account-classifications`：新建/编辑规则时切换数据库类型，确认权限复选框立即按数据库类型加载；查看规则详情也展示复选框式结果。
5. `/classification-statistics`：默认不选分类时确认所有分类曲线都可见。
6. `/account-changes`：确认列表实例名称/IP 正确显示，详情中的权限差异清晰分组，页面顶部不再有无必要的 4 张统计卡片。
7. `/partitions`：确认只保留 4 张卡片；核心指标趋势包含旧版 4 条指标线；列表历史/当前/未来状态有颜色和图标。
8. `/tags/bulk`：确认分配/移除模式在同一页；数据库类型和标签分类可展开/合拢；提交参数为选中实例和标签。
9. `/settings`：确认菜单英文一致；飞书 webhook 已按已配置状态展示；容量增长设置隶属于容量异常增长开关；飞书配置以数据源列表方式编辑。

## 以后避免漏检的规则

- 对每个弹窗至少核三层：打开弹窗请求、切换 Tab/行选择请求、列表/详情渲染结果。
- 对每个 React Query key 核参数完整性，尤其是实体 ID、owner scope、筛选项和时间范围。
- 对每个“数量卡片”核是否还有对应“明细列表”二级请求；旧版有明细，新版必须有明细。
- 对每个筛选器核选项来源：固定业务枚举或 options API，不允许从当前页数据临时推导。
- 对每个导出链接核当前筛选参数是否完整透传。
