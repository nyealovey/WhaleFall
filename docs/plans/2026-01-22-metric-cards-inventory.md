# Metric Cards Inventory & Recommendations

> status: draft
> owner: WhaleFall Team
> created: 2026-01-22
> updated: 2026-01-22
> scope: UI metric/stat cards usage in `app/templates/**`, related CSS/JS.
> related:
> - docs/plans/2026-01-22-metric-card-standardization-implementation-plan.md

## 1. 目标

本清单用于在重构前先把"哪些页面需要指标卡"以及"每张卡显示什么"确定下来, 便于逐页审计.

本文件只讨论"指标/统计类卡片"(label + number + optional meta), 不覆盖普通内容卡片(表格容器 card, panel card, modal card 等).

## 2. 判定标准(建议)

### 2.1 什么时候应该使用指标卡

- SHOULD: 页面本质是"概览/监控/统计"(dashboard, statistics, health), 指标卡用于回答"现在是什么状态".
- SHOULD: 指标与页面主要决策强相关, 例如错误量, 容量总量, 健康状态.
- SHOULD: 指标不是从列表里一眼就能看到, 或者列表很长, 指标卡能显著减少用户扫描成本.
- SHOULD: 指标可稳定定义(含不含已删除, 统计口径一致, 单位明确).

### 2.2 什么时候不应该使用指标卡

- SHOULD NOT: 页面是"CRUD 列表"且数据量小/信息可直接从列表获得(例如只有 4 条任务), 指标卡只会占用纵向空间.
- SHOULD NOT: 指标卡的统计口径不完整或误导(例如只统计当前分页 items, 但看起来像全量).
- SHOULD NOT: 指标与页面目标弱相关, 或仅重复展示已存在信息(例如列表右上角已经有"共 N 条").

### 2.3 替代方案(当不使用指标卡)

- Prefer: 在列表 header/toolbar 显示"共 N 条" + 关键筛选条件摘要.
- Prefer: 用 `chip-outline`/`status-pill` 做轻量摘要, 避免整行卡片.

### 2.4 已确认口径(第 1 轮)

以下口径来自逐项确认(以本文件为 SSOT, 后续如需变更继续追加新轮次).

- 术语(A1=A1-3):
  - `deleted_at != None` => "已删除"
  - `is_active == false` => "停用/下线"
  - 例外: 系统仪表板的"数据库总数"卡片, 允许将 `InstanceDatabase.is_active == false` 口径展示为"已删除"(B4-term=A1-2).
- 在线/活跃定义(A2=不改):
  - 实例在线/活跃: `Instance.deleted_at is None && Instance.is_active == true`
  - 数据库在线: `InstanceDatabase.is_active == true` 且所属实例在线
  - 账户活跃: `InstanceAccount.is_active == true` 且所属实例在线
  - 标签启用: `Tag.is_active == true`
- 统计页默认范围(A3=A3-1): 所有"统计/概览"类页面的总数默认只覆盖"在线实例"范围, 不混入停用/已删除实例的数据.

### 2.5 已确认口径(第 2 轮)

以下口径来自逐项确认(1=1-1, 2=2-1, 3=3-1, 4=4-1).

1) 系统仪表板 - 账户卡 meta 文案(1=1-1)
- "非活跃账户"在文案上使用"停用/下线账户"(与 A1=A1-3 保持一致), 其口径为 `total - active`.

2) 容量统计页 - 顶部汇总卡时间窗(2=2-1)
- 顶部 4 卡的统计口径跟随页面选择的统计周期(7/14/30), 即按 `start_date/end_date` 窗口计算/聚合.

3) 容量统计(数据库) - "总数据库数"是否包含停用/下线数据库(3=3-1)
- "总数据库数"仅统计 `InstanceDatabase.is_active == true` 的在线数据库(不包含停用/下线数据库).

4) 容量统计(实例) - "活跃实例数"命名(4=4-1)
- 将卡片标题从"活跃实例数"调整为"在线实例数"(口径不变, 仍为 A2 定义的在线实例).

### 2.6 已确认口径(第 3 轮)

以下口径来自逐项确认(5=5-1, 6=6-1, 7=7-1, 8=8-2).

5) 实例统计页(InstanceStatisticsPage)顶部 4 卡内容(5=5-1)
- 在线实例 + 停用/下线实例 + 已删除实例 + 数据库类型(覆盖)

6) 账户统计页(AccountsStatisticsPage)卡片"关联实例"文案(6=6-1)
- 改为"在线实例"(与 A2/A3 口径一致)

7) 实例详情页(InstanceDetailPage)tab 内文案(7=7-1)
- "已删除数据库/已删除账户"改为"停用/下线数据库/停用/下线账户"(严格按 A1=A1-3)

8) 系统仪表板(DashboardOverviewPage)卡片标题"账户总数(含已删除)"文案(8=8-2)
- 改为"账户总数"(不写括号)

## 3. 项目内现有"指标卡"实现分叉(扫描结果)

当前存在以下 10 套命名/结构(仅列出模板中出现的 class):

- `dashboard-stat-card` (dashboard)
- `stats_card` macro -> `stats-card` (capacity)
- `tags-stat-card` (tags)
- `log-stats-card` (history logs)
- `session-stats-card` (history task runs)
- `scheduler-stat-card` (admin scheduler)
- `change-log-stats-card` (account change logs)
- `instance-stat-card` (instances statistics + instances detail tabs)
- `account-stat-card` (accounts statistics)
- `partition-stat-card` (admin partitions)

这也是你截图里"看起来都不一样"的根因: 同类组件在页面 CSS 内各自定义 border/shadow/padding/typography.

## 4. 全量页面清单(以 `extends base.html` 为准)

说明:
- "现状"列只记录当前是否存在指标卡.
- "建议"列按 4 类: keep / remove / add / none.
- "理由(简)"只写最主要的一条, 详细理由见第 5 节.

| Page(title) | Template | page_id | 现状 | 建议 | 理由(简) |
| --- | --- | --- | --- | --- | --- |
| 系统仪表板 | `app/templates/dashboard/overview.html` | `DashboardOverviewPage` | 4 cards | keep | 全局概览第一屏摘要 |
| 容量统计(数据库) | `app/templates/capacity/databases.html` | `CapacityDatabasesPage` | 4 cards | keep | 容量分析汇总 |
| 容量统计(实例) | `app/templates/capacity/instances.html` | `InstanceAggregationsPage` | 4 cards | keep | 容量分析汇总 |
| 标签管理 | `app/templates/tags/index.html` | `TagsIndexPage` | 4 cards | keep | 配置资产概览 |
| 日志中心 | `app/templates/history/logs/logs.html` | `LogsPage` | 4 cards | keep | 风险监控摘要 |
| 运行中心 | `app/templates/history/sessions/sync-sessions.html` | `SyncSessionsPage` | 4 cards | remove (per request) | 列表页, 指标增益低且易误导 |
| 定时任务管理 | `app/templates/admin/scheduler/index.html` | `SchedulerPage` | 4 cards | remove (per request) | 数据量小, 信息重复 |
| 账户变更历史 | `app/templates/history/account_change_logs/account-change-logs.html` | `AccountChangeLogsPage` | 4 cards | keep | 审计/回溯摘要 |
| 分区管理 | `app/templates/admin/partitions/index.html` | `AdminPartitionsPage` | 4 cards | keep | 健康监控入口 |
| 实例统计 | `app/templates/instances/statistics.html` | `InstanceStatisticsPage` | 4 cards | keep | 概览统计页 |
| 账户统计 | `app/templates/accounts/statistics.html` | `AccountsStatisticsPage` | 4 cards | keep | 概览统计页 |
| 实例详情 | `app/templates/instances/detail.html` | `InstanceDetailPage` | 2x3 cards | keep (but consider compact) | 单实例画像 |
| 标签批量分配 | `app/templates/tags/bulk/assign.html` | `TagsBatchAssignPage` | 1 summary card (non-metric) | keep | workflow 摘要, 降低误操作 |
| 账户分类统计 | `app/templates/accounts/classification_statistics.html` | `AccountClassificationStatisticsPage` | none | none (use panel meta) | 已有 panel meta 摘要 |
| 账户台账 | `app/templates/accounts/ledgers.html` | `AccountsListPage` | none | none | CRUD list |
| 数据库台账 | `app/templates/databases/ledgers.html` | `DatabaseLedgerPage` | none | none | CRUD list |
| 实例管理(列表) | `app/templates/instances/list.html` | `InstancesListPage` | none | none | CRUD list |
| 实例表单 | `app/templates/instances/form.html` | `InstanceFormPage` | none | none | 表单页 |
| 凭据管理 | `app/templates/credentials/list.html` | `CredentialsListPage` | none | none | CRUD list |
| 用户管理 | `app/templates/auth/list.html` | `AuthListPage` | none | none | CRUD list |
| 用户表单 | `app/templates/users/form.html` | `UserFormPage` | none | none | 表单页 |
| 登录 | `app/templates/auth/login.html` | `LoginPage` | none | none | 登录页 |
| 修改密码 | `app/templates/auth/change_password.html` | `ChangePasswordPage` | none | none | 表单页 |
| 关于 | `app/templates/about.html` | `AboutPage` | none | none | 信息页 |
| 错误页 | `app/templates/errors/error.html` | `ErrorPage` | none | none | 错误页 |
| 账户分类管理 | `app/templates/accounts/account-classification/index.html` | `AccountClassificationPage` | none | add (optional) | 规则资产概览(可选) |
| 账户分类表单 | `app/templates/accounts/account-classification/classifications_form.html` | `AccountClassificationFormPage` | none | none | 表单页 |
| 分类规则表单 | `app/templates/accounts/account-classification/rules_form.html` | `ClassificationRuleFormPage` | none | none | 表单页 |

备注:
- "账户分类管理"是否需要新增指标卡, 取决于你是否希望在进入页面第一屏就看到"分类数/规则数/启用规则"等全局概览. 本清单先标为 optional.

## 5. 逐页卡片内容定义与建议

### 5.1 系统仪表板

Template: `app/templates/dashboard/overview.html`

现有 4 张卡(需按本节口径调整展示):

1) 数据库实例
- value(B1=B1-2): 总实例数(含已删除实例)
- meta(B1=B1-2): 在线实例 + 停用实例 + 已删除实例(三段拆分展示)
  - 在线: `deleted_at is None && is_active == true`
  - 停用: `deleted_at is None && is_active == false`
  - 已删除: `deleted_at is not None`
  - 备注: 该卡片口径是"全量实例"(包含已删除), 属于 A3 的例外.

2) 账户总数
- scope(B2-scope=A3-1): 仅统计在线实例范围内的账户, 不混入停用/已删除实例的数据
- value: 账户总数(在线实例范围内, 包含停用/下线账户)
- meta(B2-meta=B2-meta-1): 活跃账户 + 受限账户 + 停用/下线账户
  - 受限账户为活跃账户子集(`locked <= active`)
  - 停用/下线账户 = total - active

3) 总容量
- scope(B3=B3-1): 仅统计在线实例范围内的容量
- value(B3=B3-1): 各在线实例"最新采样值"(latest sample)的总和
- meta(B3-u=B3-u-1): 不展示"使用率"(删除该 meta, 避免口径不清)

4) 数据库总数(含已删除)
- scope(B4-scope=B4-scope-1): 仅统计在线实例范围内的数据库, 不纳入已删除实例下的数据库
- value: 数据库总数(包含 `InstanceDatabase.is_active == false` 的数据库)
- meta(B4-term=A1-2):
  - 在线: `InstanceDatabase.is_active == true`
  - 已删除: `InstanceDatabase.is_active == false` (此处允许用"已删除"命名)

建议: keep
- 理由: 仪表板是"全局概览"页面, 顶部 4 卡是第一屏关键摘要.
- 审计点:
  - 明确每张卡是否"含已删除".
  - 总容量使用 latest sample 口径后, 需明确与容量统计页(时间窗/周期)的差异并避免用户误解.

### 5.2 容量统计(数据库)

Template: `app/templates/capacity/databases.html`

现有 4 张卡(通过 `stats_card` macro):

- 总数据库数
  - dom id: `totalDatabases`
  - API: `/api/v1/capacity/databases/summary` -> `total_databases`
  - 口径: 仅 active instances + active databases.

- 总容量
  - dom id: `totalCapacity`
  - API field: `total_size_mb` (前端用 `formatBytesFromMB`, 自动选择单位)

- 平均容量
  - dom id: `averageSize`
  - API field: `avg_size_mb`

- 最大容量
  - dom id: `maxSize`
  - API field: `max_size_mb`

建议: keep
- 理由: 本页目标是容量分析, 卡片是"当前筛选条件下"的汇总.
- 审计点:
  - 顶部汇总卡跟随统计周期(7/14/30)时间窗, 避免用户将其误解为"全量 latest".
  - 文案可选: "总数据库数"可改名为"在线数据库数"(避免误读为包含停用/下线数据库).

### 5.3 容量统计(实例)

Template: `app/templates/capacity/instances.html`

现有 4 张卡(通过 `stats_card` macro):

- 在线实例数
  - dom id: `totalInstances`
  - API: `/api/v1/capacity/instances/summary` -> `total_instances`
  - 口径: 仓库层过滤 `Instance.is_active=true` 且未删除.

- 总容量
  - dom id: `totalDatabases` (命名误导, 实际展示 total size)
  - API field: `total_size_mb`

- 平均容量
  - dom id: `averageSize`
  - API field: `avg_size_mb`

- 最大容量
  - dom id: `maxSize`
  - API field: `max_size_mb`

建议: keep
- 理由: 与数据库容量页同类, 需要"当前筛选条件下"的汇总.
- 审计点:
  - 顶部汇总卡跟随统计周期(7/14/30)时间窗, 避免用户将其误解为"全量 latest".
  - dom id 命名与含义不一致(不影响功能, 但影响可读性与后续重构).

### 5.4 标签管理

Template: `app/templates/tags/index.html`

现有 4 张卡(服务端渲染, JS 可增量更新):

- 全部标签: `tag_stats.total`
- 启用标签: `tag_stats.active`
- 停用标签: `tag_stats.inactive`
- 标签分类: `tag_stats.category_count`

建议: keep
- 理由: 标签是"配置资产", 顶部摘要帮助快速判断规模与健康度(是否存在大量停用).

### 5.5 日志中心

Template: `app/templates/history/logs/logs.html`

现有 4 张卡(由 JS 调用 stats API 刷新):

- 总日志数: `#totalLogs`
- 错误日志: `#errorLogs`
- 警告日志: `#warningLogs`
- 模块数量: `#modulesCount`

建议: keep
- 理由: 日志中心是"风险监控"入口, 第一屏应回答"错误量是否异常".
- 审计点:
  - 明确统计维度是否随筛选变化(当前实现会随筛选刷新).

### 5.6 运行中心(任务运行)

Template: `app/templates/history/sessions/sync-sessions.html`

现有 4 张卡:

- 总会话数: `#totalSessions`
- 运行中: `#runningSessions`
- 已完成: `#completedSessions`
- 失败/取消: `#failedSessions`

关键问题(强烈影响是否保留):
- JS 里 `total` 使用 `payload.total`(全量), 但 running/completed/failed 仅从 `payload.items`(当前分页)统计.
- 当 total > page size 时, 卡片看起来像全量统计, 实际是"本页统计", 存在误导.

建议: remove
- 理由(按你的反馈): 页面主要目标是查看列表与详情, 顶部 4 卡在空间和信息增益上不划算.
- 替代: 列表 header 显示"共 N 条"即可.

### 5.7 定时任务管理

Template: `app/templates/admin/scheduler/index.html`

现有 4 张卡:

- 任务总数
- 运行中
- 已暂停
- 内置任务

建议: remove
- 理由(按你的反馈): 任务数量非常少(当前仅 4 个), 指标卡与列表信息高度重复.
- 替代: 在"运行中的任务"与"已暂停的任务"分组标题处显示数量即可(当前已有 `0 项`).

### 5.8 账户变更历史

Template: `app/templates/history/account_change_logs/account-change-logs.html`

现有 4 张卡(由 stats API 刷新):

- 变更总数: `#totalChanges`
- 成功变更: `#successChanges`
- 失败变更: `#failedChanges`
- 影响账号数: `#affectedAccounts`

建议: keep
- 理由: 该页是"审计/故障回溯"入口, 顶部摘要能快速判断近期变更压力与失败率.
- 审计点:
  - 明确时间窗口(由筛选 hours/time_range 控制).

### 5.9 分区管理

Template: `app/templates/admin/partitions/index.html`

现有 4 张卡(由 PartitionStore + health API 更新):

- 分区总数: `data-stat=total_partitions`
- 总大小: `data-stat=total_size`
- 总记录数: `data-stat=total_records`
- 健康状态: `data-stat=health` (tone + meta badge)

建议: keep
- 理由: 这是典型"管理中心 + 健康监控"页面, 指标卡与页面目标强相关.

### 5.10 实例统计

Template: `app/templates/instances/statistics.html`

目标 4 张卡(可通过 refresh API 更新, 5=5-1):

- 在线实例: `stats.active_instances` (未删除且 `is_active == true`)
- 停用/下线实例: `stats.inactive_instances` (未删除且 `is_active == false`)
- 已删除实例: `stats.deleted_instances` (`deleted_at is not None`)
- 数据库类型: `stats.db_types_count` (db_type 的 distinct 计数)

建议: keep
- 理由: 统计页本身就是"概览".
- 审计点:
  - 不再展示"总实例数", 避免把已删除实例混入第一张卡导致口径歧义.

### 5.11 账户统计

Template: `app/templates/accounts/statistics.html`

现有 4 张卡(可通过 refresh API 更新, scope 已符合 A3=A3-1: 仅在线实例):

- 总账户数: `stats.total_accounts` (包含非活跃账户, 但仅统计在线实例)
- 活跃账户: `stats.active_accounts`
- 锁定账户: `stats.locked_accounts`
- 在线实例: `stats.total_instances` (当前实现等于在线实例数)

建议: keep
- 理由: 统计页本身就是"概览".

### 5.12 实例详情(卡片在 tab 内)

Template: `app/templates/instances/detail.html`

现有 2 组(每组 3 张):

A) 数据库容量信息 tab
- 在线数据库: `#databaseOnlineCount` (JS 写入)
  - API: `/api/v1/databases/sizes?instance_id=<id>&latest_only=true&include_inactive=true&limit=1&page=1`
  - field: `active_count` (含义: `InstanceDatabase.is_active == true` 的数量)
- 停用/下线数据库: `#databaseDeletedCount` (JS 写入)
  - field: `filtered_count` (含义: `InstanceDatabase.is_active == false` 的数量, 并非 `deleted_at`)
- 总容量: `#databaseTotalCapacity` (JS 写入)
  - field: `total_size_mb` (含义: 仅对在线数据库(active)的 size 求和, 不包含停用/下线数据库)

B) 数据库账户信息 tab
- 活跃账户: `account_summary.active` (服务端渲染)
- 停用/下线账户: `account_summary.deleted` (服务端渲染)
  - 口径: `InstanceAccount.is_active == false` 的数量
- 超级管理员: `account_summary.superuser` (服务端渲染)

建议: keep (but consider compact)
- 理由: 这是"单实例画像"页面, tab 内的 3 指标用于快速理解该实例的数据库/账户规模.
- 可选优化(不在本次实现范围): 如果你希望减少卡片, 可改为一行 chips(3-6 个)放在 tab header 下方.
- 审计点:
  - 本页字段/统计口径已明确为 `is_active == false`, 文案统一使用"停用/下线"(7=7-1), 不再使用"已删除".

### 5.13 标签批量分配(非指标类 summary card)

Template: `app/templates/tags/bulk/assign.html`

- `batch-summary-card` 是"操作概览"(选中实例数, 已选标签等), 属于 workflow 辅助, 不算指标卡.

建议: keep
- 理由: 该卡片是交互流程的一部分, 用于降低批量操作的误操作风险.

### 5.14 账户分类统计

Template: `app/templates/accounts/classification_statistics.html`

现状: 无指标卡.

建议: none
- 理由: 页面已经使用 panel header meta(chip)表达"覆盖/窗口"等摘要, 再加 4 卡会加重信息密度.
- 如果你后续希望增加, 建议优先做"2-3 个 chips"而不是 4 张大卡.

### 5.15 账户分类管理(可选新增)

Template: `app/templates/accounts/account-classification/index.html`

现状: 无指标卡.

建议: add (optional)
- 理由: 该页是"规则资产"管理页, 若分类/规则规模增长, 第一屏摘要会有价值.

建议的 3-4 项指标(仅提案, 待你审计):
- 分类数
- 规则总数
- 启用规则
- 已归档规则

备注: 这些值可以从页面现有数据源(分类列表/规则列表 API)聚合得到, 但需要确认口径(例如是否包含停用分类).
