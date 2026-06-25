---
title: React 新旧页面线上内容一致性审计
status: Remediated pending live verification
owner: team
created: 2026-06-22
updated: 2026-06-23
scope: React `/console/**` 与旧版 Flask 页面展示内容、列表数据、详情及设置模块
related:
  - ../plans/2026-06-11-react-frontend-migration-checklist.md
  - ../plans/2026-06-18-react-display-parity-tracker.md
---

# React 新旧页面线上内容一致性审计

> [!warning] 本报告只记录审计结论
> 本次没有修改前端或后端业务代码，没有提交任何写操作。登录凭据未写入仓库或报告。

> [!info] 2026-06-23 修复状态
> 本报告保留 2026-06-22 的原始线上审计发现。P0/P1 项已按 `refactor: add server paginated data table`、`fix: align audit and task run data`、`fix: paginate console resource lists`、`fix: align console summary content`、`fix: align instance detail and settings` 五个代码批次完成修复；由于线上尚未由用户重新构建部署，最终浏览器复核仍为 Pending。

## 2026-06-23 修复跟踪

| 原始发现 | 修复状态 | 线上复核 |
| --- | --- | --- |
| P0-01 列表没有服务端分页 | 已引入 shadcn Pagination、受控服务端分页和 `useServerTableState`；默认每页 20，可选 20/50/100；筛选、搜索、页大小变化回到第一页 | Pending |
| P0-02 会话中心接错 v1 API | 已切换到 `/api/v1/task-runs` 列表、详情、错误日志和取消接口；来源、分类、状态使用固定业务选项 | Pending |
| P0-03 账户变更统计与列表口径冲突 | 列表和统计共用时间范围；默认全部时间口径；实例选项从 `/api/v1/instances/options` 加载 | Pending |
| P1-01 原始枚举和时间格式没有统一映射 | 已建立共享展示 formatter，统一数据库类型、凭据类型、状态、周期、来源、时间和容量文本 | Pending |
| P1-02 日志和变更时间范围控件是静态控件 | 日志和账户变更时间范围已进入 React Query key，并同时透传给列表和统计 | Pending |
| 仪表盘风险告警截断 | 已移除风险列表 `slice` 截断，展示完整旧版同源风险项 | Pending |
| 风险中心只请求 12 张风险卡 | 默认请求 20 条并接入服务端分页 | Pending |
| 实例详情字段和操作缺失 | 已补实例 ID、数据库版本、标签、编辑、移入回收站、账户/容量汇总、查看权限、变更历史、表容量、备份平台/大小/压缩率等字段 | Pending |
| 容量单位、内部来源名和旧版没有的大列表 | 容量单位按 MB/GB/TB 自适应；删除内部来源名和旧版没有的大容量明细列表；图表继续使用旧版同源全量数据 | Pending |
| 账户分类零值分类和规则命中数 | 六种分类始终展示，规则命中数补调 `/api/v1/accounts/statistics/rules?rule_ids=...` 后按 `rule_id` 合并 | Pending |
| 群集状态字段映射错误 | SQL Server 使用 `last_status_sync_status/at`、`last_ag_sync_status/at`；MySQL 使用 `last_topology_sync_status/at` 与异常副本数 | Pending |
| 分区指标缺字段 | 已补历史/当前/未来分区数量、当前分区大小、平均记录数、当前记录数和数据库连接状态；分区列表默认 20 条 | Pending |
| 系统设置模块字段缺失 | 已改用 shadcn Tabs；补告警 Webhook 脱敏/清空、容量阈值、风险规则分类/名称/描述/严重级别、JumpServer/Veeam/AD 状态字段 | Pending |

本轮代码侧验证已通过：

```bash
npm --prefix frontend run test       # 26 files, 147 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; Vite chunk-size warning remains
uv run pytest tests/unit/routes/test_api_v1_task_runs_contract.py tests/unit/routes/test_api_v1_history_logs_contract.py tests/unit/routes/test_api_v1_account_change_logs_contract.py tests/unit/routes/test_api_v1_accounts_statistics_contract.py tests/unit/routes/test_api_v1_accounts_classifications_contract.py tests/unit/routes/test_api_v1_sqlserver_clusters_contract.py tests/unit/routes/test_api_v1_mysql_clusters_contract.py tests/unit/routes/test_api_v1_partition_contract.py -q  # 36 passed
git diff --check                     # passed
```

线上复核需要用户重新构建部署后再按本文原始发现逐页确认。

## 摘要结论

本次对线上 React 新版和 Flask 旧版进行了同账号、同时间窗口的逐页对照。覆盖 22 个主导航页面、1 个实例详情页、系统设置 5 个模块及 SQL Server/MySQL 两类群集标签。

当前 React 页面不能按现有清单统一认定为 `Done - replacement`。主要原因不是布局形态不同，而是以下内容契约仍未对齐：

1. 多数列表只获取后端第一页，再在浏览器内分页。超过 100/200 条的数据无法继续访问，筛选选项也只来源于首批数据。
2. 会话中心接入了错误的数据源。旧版使用 `/api/v1/task-runs`，React 使用 `/api/v1/sync-sessions`，导致总数、任务类型、状态和最新记录均不一致。
3. 账户变更页列表使用全量口径，统计卡使用 24 小时口径，线上出现“列表 7,622 条、统计全为 0”的直接矛盾。
4. 群集状态、账户分类规则命中数、容量单位、实例备份明细、分区字段和系统设置模块存在明确的内容缺失或错误映射。
5. 多个页面直接展示后端原始枚举、UTC/ISO 时间和内部字段名，旧版对应的是中文业务文本和本地时间。

现有迁移清单和展示一致性跟踪文档中的 `Done` 结论需要在修复后重新验收。本次审计时 Git 工作区为干净状态，因此报告中的问题也存在于当前仓库版本，不是仅由线上未部署造成。

## 范围与方法

### 审计范围

- React：`https://dbinfo.whalefall.local/console/**`
- 旧版：同域名下对应 Flask 页面
- 补充检查：实例 `105` 详情、实例详情四个旧版标签、系统设置全部模块、群集两种数据库类型

### 审计方法

- 在两个独立浏览器标签中使用同一账号登录。
- 每个页面等待异步请求完成后，对照标题、指标、筛选项、按钮、表头、当前行数和主要正文。
- 对标签页和只读详情进行切换；未保存表单、未执行同步、删除、测试连接等写操作。
- 对已确认差异继续读取当前 React、旧版 JavaScript 和 v1 API 源码，区分“前端漏接”“字段映射错误”和“接口数据缺口”。
- 动态日志数、运行时间等实时数据只比较口径和结构，不将几秒内自然增长视为差异。

### 严重级别

| 级别 | 判定口径 |
| --- | --- |
| P0 | 用户无法访问完整数据、页面数据源错误、同页核心数据互相矛盾 |
| P1 | 关键指标、状态、字段或详情内容缺失/错误，阻塞旧版替代 |
| P2 | 业务含义基本保留，但枚举、时间、单位、默认展示数量或辅助信息不一致 |
| P3 | 非关键说明、冗余控件或旧版禁用选项等低风险差异 |

## 全局发现

### P0-01 列表没有服务端分页

`DataTable` 固定使用 TanStack 客户端分页，未设置旧版默认的 20 条，也没有页码、总页数、跳页或服务端翻页参数。当前默认每页显示 10 条。

同时，多数 API 方法固定请求 `page=1&limit=200`，会话中心固定请求 `page=1&limit=100`。因此：

- 数据库台账线上总数 1,392 条，React 实际只有前 200 条可访问。
- 账户台账线上总数 2,768 条，React 实际只有前 200 条可访问。
- 日志中心线上总数约 4,043 条，React 实际只有前 200 条可访问。
- 账户变更线上总数 7,622 条，React 实际只有前 200 条可访问。
- 会话中心 React 只持有前 100 条。
- 实例、群集、标签等页面默认显示 10 条，旧版默认显示 20 条。

筛选项由 `snapshot.items` 动态生成，所以实例、模块、变更类型、会话分类等筛选也只覆盖首批 100/200 条数据。该问题不能通过单纯把 `limit` 调大解决，应使用服务端分页和服务端筛选。

源码证据：

- `frontend/src/components/shared/DataTable.tsx:51-70`
- `frontend/src/api/lists.ts:271-294`
- `frontend/src/api/audit.ts:84-103`
- `frontend/src/api/readOnly.ts:427-428`

### P0-02 会话中心接错已有 v1 API

旧版会话中心使用 `/api/v1/task-runs`，React 使用 `/api/v1/sync-sessions`。两者不是同一数据模型。

线上对照结果：

- React 总数 1,055，旧版总数 1,014。
- React 最新记录停留在 2026-06-21 晚间，旧版已包含 2026-06-22 的邮件告警、群集同步、Veeam、容量、分类和账户任务。
- React 只显示 `scheduled_task`、`aggregation`、`capacity`、`account` 等原始值。
- 旧版显示“定时/手动/API”“告警/群集/其他”等业务文本和任务名称。

旧版所需的列表、详情、错误日志和取消动作均已有 v1 路由，不是后端缺口：

- `GET /api/v1/task-runs`
- `GET /api/v1/task-runs/{run_id}`
- `GET /api/v1/task-runs/{run_id}/error-logs`
- `POST /api/v1/task-runs/{run_id}/actions/cancel`

源码证据：

- `app/static/js/modules/services/task_runs_service.js:4-41`
- `app/api/v1/namespaces/task_runs.py:60-192`
- `frontend/src/api/readOnly.ts:592-609`

### P0-03 账户变更统计与列表口径冲突

React 列表请求不带 `hours`，统计请求固定带 `hours=24`，但页面上的时间范围选择器没有连接任何状态或请求参数。

线上结果：列表显示 7,622 条，四个统计卡分别显示 `0 / 0% / 0 / 0`；旧版统计显示 `7,622 / 100% / 0 / 2,885`。

源码证据：

- `frontend/src/api/audit.ts:84-96`
- `frontend/src/api/audit.ts:115-126`
- `frontend/src/pages/AuditPages.tsx:183-199`
- `frontend/src/pages/AuditPages.tsx:559-615`

### P1-01 原始枚举和时间格式没有统一映射

以下内容在多个页面重复出现：

- `mysql/postgresql/sqlserver` 未转换为旧版 `MYSQL/POSTGRESQL/SQL SERVER`。
- `completed/running/healthy/past/current/future/replication` 未转换为中文业务状态。
- 调度任务和会话时间直接显示 ISO 字符串或 UTC 时间，旧版显示本地时间。
- 容量卡显示内部来源名 `instance_size_stats`，旧版显示“采集”等业务文本。
- 凭据类型直接显示 `database/api/veeam/ldap`，旧版显示“数据库凭据/API 凭据/Veeam 凭据/LDAP 凭据”。

应建立共享的业务术语、状态和时间格式映射，不应在各页面分别拼接原始值。

### P1-02 日志和变更时间范围控件是静态控件

两个页面都显示“最近 1 小时/24 小时/7 天/30 天/全部”，但 `TimeRangeFilter` 没有 `onValueChange`，也没有参与 query key 或 API 参数。用户切换后不会改变列表和统计数据。

源码证据：`frontend/src/pages/AuditPages.tsx:183-199`。

## 逐页发现

### 1. 仪表盘 `/console/dashboard`

**结论：P1，阻塞替代。**

- 旧版风险告警展示 15 项，React 标题也显示 15 项，但正文被 `slice(0, 5)` 截断为 5 项。
- 其余核心指标、日志曲线、系统状态和分类分布本次未发现明确结构缺失。

源码证据：`frontend/src/pages/DashboardPage.tsx:250-275`。

### 2. 风险中心 `/console/risk-center`

**结论：P1，阻塞替代。**

- 旧版显示 14 个风险实例卡，React 汇总也是 14，但只请求并显示 12 个。
- React 没有卡片服务端分页或“加载更多”入口。
- 默认限制来自 `filters.limit ?? 12`。

源码证据：`frontend/src/api/riskCenter.ts:73-95`。

### 3. 实例管理 `/console/instances`

**结论：P1，列表基础能力阻塞替代。**

- React 默认显示 10 条，旧版默认 20 条；React 只加载第一页 200 条。
- 部分单元格缩短了旧版业务文本，例如“当前类型暂不支持审计采集”缩为“不支持”，“已备份（24小时内有备份）”缩为“已备份”。
- 实例名称已能进入 `/console/instances/{id}`，不存在“没有详情入口”的问题。

### 4. 实例详情 `/console/instances/105`

**结论：P1，阻塞实例管理替代。**

- React 基本信息缺少实例 ID、数据库版本、标签；旧版均展示。
- React 缺少“编辑实例”和“移入回收站”入口，旧版详情页有这两个操作。
- React 连接状态直接显示 `poor`，旧版使用业务状态文本。
- 账户标签缺少“当前账户/活跃账户/已删除账户/超管账户”四项汇总。
- 账户表缺少旧版“查看权限”和“变更历史”操作列。
- 容量标签缺少当前数据库、在线数据库、已删除数据库、总容量四项汇总，以及“表容量”入口。
- 备份摘要缺少 Backup ID 和“已覆盖恢复点/总恢复点”信息。
- 恢复点明细缺少平台、数据大小、压缩率；React 只保留恢复点、备份方式、备份大小和创建时间。
- React 将审计、备份卡固定放在账户/容量标签上方；旧版使用四个标签切换。形态可不同，但修复时必须保留旧版全部字段。

上述备份字段已经存在于当前 v1 响应类型，不是后端缺口：`frontend/src/api/lists.ts:77-105`。

### 5. 数据库台账 `/console/database-ledgers`

**结论：P0，完整数据不可访问。**

- 线上总数 1,392 条，React 只加载前 200 条。
- React 默认显示 10 条，旧版默认显示 20 条。
- 当前可见列的主要业务字段与旧版基本一致。

### 6. 账户台账 `/console/account-ledgers`

**结论：P0，完整数据不可访问。**

- 线上总数 2,768 条，React 只加载前 200 条。
- React 默认显示 10 条，旧版默认显示 20 条。
- 当前可见列的主要业务字段与旧版基本一致。

### 7. 实例容量 `/console/capacity/instances`

**结论：P1，阻塞替代。**

- React 容量格式最多转换到 GB，旧版会继续转换到 TB。线上同类总量显示为 `96279.83 GB` 与 `103.38 TB`，除单位外数值也存在差异，需要复核默认日期范围和汇总请求。
- React 显示内部元数据 `daily · instance_size_stats`，旧版显示“日/采集”。
- React 在三个旧版图表之外增加了约 2,508 条容量明细列表；旧版页面没有该列表，应删除或另行确认产品需求。
- 图表坐标轴本次线上已能显示，但图表序列值仍需在修复容量查询后重新逐点验收。

源码证据：`frontend/src/pages/CapacityPages.tsx:38-44`。

### 8. 数据库容量 `/console/capacity/databases`

**结论：P1，阻塞替代。**

- 与实例容量相同，存在 GB/TB 格式、内部来源名和额外大列表问题。
- 线上 React 与旧版汇总值存在差异，需要与旧版相同筛选条件重新核对 summary 和三组 chart 请求。

### 9. 实例统计 `/console/instance-statistics`

**结论：P2，主要内容接近一致。**

- 指标和主要分布内容基本一致。
- React 将 4/5/10 行静态分布也放入带搜索和分页的 DataTable，增加了旧版没有的交互和分页文案。
- 数据库类型等枚举使用小写原始值，旧版使用大写业务文本。

### 10. 账户统计 `/console/account-statistics`

**结论：P1，阻塞替代。**

- 旧版账户分类分布始终展示 `SUPER/HIGHLY/SENSITIVE/MEDIUM/LOW/PUBLIC` 六类，包括数量为 0 的分类。
- React 只展示有数据的 `super/highly/medium` 三类，缺少三项零值分类。
- 数据库类型和分类编码使用小写原始值。

### 11. 数据库统计 `/console/database-statistics`

**结论：P2，主要内容接近一致。**

- 指标、数据库类型分布、实例分布、同步状态和容量排行基本齐全。
- 同步状态单元格同时显示原始值 `running` 和中文“待刷新”，旧版只显示业务文本。
- 小型静态表增加了搜索和分页控件；数据库类型使用小写原始值。

### 12. 日志中心 `/console/logs`

**结论：P0，完整数据和筛选不可用。**

- React 只加载前 200 条，旧版服务端分页可访问全部约 4,043 条。
- React 默认显示 10 条，旧版默认 20 条。
- 模块筛选项只从前 200 条生成，无法覆盖全部模块。
- 时间范围选择器不触发请求，属于无效控件。
- 模块等枚举大小写与旧版不一致。

### 13. 账户变更 `/console/account-change-logs`

**结论：P0，同页核心数据互相矛盾。**

- 统计卡全为 0，但列表显示 7,622 条；旧版统计与列表均采用全量口径。
- React 只加载前 200 条，默认显示 10 条；旧版默认 20 条并支持服务端分页。
- 实例、数据库类型和变更类型筛选只从前 200 条生成。
- 时间范围选择器不触发请求。

### 14. 群集管理 `/console/clusters`

**结论：P1，核心状态错误。**

SQL Server：

- 旧版“数据库同步状态”显示“正常/异常 + 检测时间”。
- React 错误复用了 `last_ag_sync_status`，大多数行显示“未同步”，且不显示检测时间。
- “最近 AG 同步”缺少 `last_ag_sync_at` 时间，状态直接显示小写 `completed`。

MySQL：

- 旧版“主从状态”显示“正常/检测失败 + 检测时间”。
- React 显示拓扑类型 `replication`，不是主从健康状态。
- 当前 v1 列表已有 `last_topology_sync_status` 和 `last_topology_sync_at`，前端没有使用。

共同问题：

- 两类群集已按标签单面板切换，符合旧版交互。
- React 默认只显示 10 条。SQL Server 共 11 条，MySQL 共 23 条；旧版默认 20 条。
- React 类型定义漏掉了服务端已有的同步状态和时间字段。

源码证据：

- `frontend/src/pages/ClustersPage.tsx`
- `frontend/src/pages/ConsolePageScaffold.tsx`
- `app/models/sqlserver_cluster.py:50-61`
- `app/models/mysql_cluster.py:31-43`

### 15. 账户分类 `/console/account-classifications`

**结论：P1，规则命中数错误。**

- React 九条规则的命中数全部显示 0。
- 旧版对应命中数为 4、230、347、3、4、5、569、338、8。
- 旧版在加载规则后继续调用 `GET /api/v1/accounts/statistics/rules?rule_ids=...` 并合并 `matched_accounts_count`。
- React 只请求分类和规则列表，没有调用已有的规则统计接口。

这不是后端 API 缺口，是 React 漏接已有接口。

源码证据：

- `app/static/js/modules/stores/account_classification_store.js:226-265`
- `app/static/js/modules/services/account_classification_service.js:117-123`
- `frontend/src/api/readOnly.ts:475-486`

### 16. 分类统计 `/console/classification-statistics`

**结论：P3，未发现明确的核心内容缺失。**

- 筛选、规则列表、分类趋势、规则贡献和说明均存在。
- 旧版显示禁用的“年统计（即将支持）”，React 没有该禁用项。
- React 增加“刷新”按钮。
- 旧版图表使用 Canvas，React 使用 SVG；本次仅核对结构、日期轴和系列标题，没有逐点导出 Canvas 数据，修复其他数据问题后需补一次数值验收。

### 17. 定时任务 `/console/scheduler`

**结论：P2，内容格式和展示范围不一致。**

- 任务数量和七个任务名称一致。
- React 直接显示 ISO 时间，旧版显示本地时间。
- React 任务 ID 为小写，旧版为大写。
- React 在每张卡上永久展示 cron 触发器参数，旧版任务卡没有这段正文。
- React 上次运行时间按 UTC 字符串直接展示，导致与旧版本地时间看起来相差 8 小时。

### 18. 会话中心 `/console/sync-sessions`

**结论：P0，数据源错误。**

详见“P0-02 会话中心接错已有 v1 API”。该页面应整体切换到 `/api/v1/task-runs` 契约后重新验收，不能在当前 `/sync-sessions` 数据上继续补样式。

### 19. 用户管理 `/console/users`

**结论：主要展示内容一致。**

- 三个用户的 ID、用户名、角色、状态和创建时间一致。
- React 使用表格内即时筛选，旧版使用“筛选/清除”，属于允许的展示形态差异。
- 当前数据少于 10 条，未触发全局分页缺陷；仍应统一接入服务端分页组件。

### 20. 系统设置 `/console/settings`

**结论：P1，多个模块缺少旧版信息。**

告警设置：

- React 不显示已配置飞书 Webhook 的脱敏值，也没有“清空飞书机器人 URL”选项。
- React 缺少容量异常增长的“增幅阈值 (%)”和“增量阈值 (GB)”字段。

风险规则：

- React 只显示 `rule_key`、严重级别和启用状态。
- 旧版还显示分类、中文规则名、规则描述，并可分别选择高/中/低严重级别。

JumpServer：

- React 运行状态只保留 Provider、简化后的绑定主机和最近同步字段。
- 旧版展示完整绑定（凭据、URL、org、SSL 状态）以及同步状态和时间。

Veeam：

- React 数据源列表只显示名称、地址、编辑和停用。
- 旧版还显示凭据、启用状态、最近同步状态/时间和 Provider 汇总。

AD 设置：

- React 默认选中并填充第一个域，旧版默认处于新增模式。
- React 域列表只显示域名、NetBIOS、状态和编辑入口。
- 旧版还显示域控、凭据、最近同步、AD 对象/用户/组数量、SQL 账户及正常/停用/孤账户/更新数量和全局汇总。

### 21. 凭据管理 `/console/credentials`

**结论：P2，字段齐全但业务文本未对齐。**

- 八条凭据及其绑定实例数量与旧版一致。
- React 显示原始类型 `ldap/veeam/api/database` 和原始数据库类型；旧版显示中文凭据类型及规范化数据库类型。
- 当前数据少于 10 条，未触发全局分页缺陷。

### 22. 标签管理 `/console/tags`

**结论：P2，内容基本齐全但列表和格式不一致。**

- 总数 22、启用/停用数量、分类数和关联数量一致。
- React 默认显示 10 条，旧版默认显示 20 条。
- React 显示分类原始值 `architecture/deployment/environment`，旧版使用大写规范值。
- React 均值显示 `3.143`，旧版显示 `3.1`；启用率显示 `100.0%`，旧版显示 `100%`。

### 23. 分区管理 `/console/partitions`

**结论：P1，关键辅助指标和字段缺失。**

- React 四张指标卡只显示主值。
- 旧版“分区总数”还显示历史/当前/未来数量；“总大小”显示当前分区大小；“总记录数”显示平均每分区和当前分区记录数；“健康状态”显示数据库连接状态。
- React 表格缺少“分区月份”字段。
- React 将 `display_name/table/table_type` 拆成“分区/表/类型”三列，并直接显示 `aggregations/stats` 等内部值；旧版显示“分区名称/表类型”的业务文本。
- React 状态直接显示 `past/current/future`，旧版显示“历史/当前/未来”。
- React 一次渲染全部 71 行，旧版每页 20 条。

旧版辅助指标均由当前分区列表计算，不需要新增 API。源码证据：

- `app/static/js/modules/views/admin/partitions/index.js:212-270`
- `app/static/js/modules/views/admin/partitions/partition-list.js:118-155`

## 已确认的接口与实现归类

| 问题 | 归类 | 结论 |
| --- | --- | --- |
| 会话中心数据不一致 | 前端接错接口 | 改用已有 `/api/v1/task-runs` 全套接口 |
| 账户分类命中数为 0 | 前端漏接接口 | 补调已有 `/api/v1/accounts/statistics/rules` |
| SQL Server 群集状态错误 | 前端字段映射错误 | 使用 `last_status_sync_status/at`，AG 使用 `last_ag_sync_status/at` |
| MySQL 主从状态显示 `replication` | 前端字段映射错误 | 使用 `last_topology_sync_status/at` 和异常副本数量 |
| 账户变更统计为 0 | 前端查询口径错误 | 列表、统计和时间范围必须使用同一 `hours` 参数 |
| 日志/变更时间范围无效 | 前端控件未接状态 | 选择值进入 query key、列表和统计请求 |
| 大列表只能看前 100/200 条 | 前端分页架构错误 | DataTable 支持服务端页码、页大小、总数和服务端筛选 |
| 风险中心只显示 12 条 | 前端固定限制 | 增加服务端分页或按旧版完整加载 |
| 仪表盘只显示 5 条风险 | 前端主动截断 | 移除 `slice(0, 5)` 或提供可访问全部内容的入口 |
| 容量只格式化到 GB | 前端格式函数缺陷 | 统一使用旧版 MB/GB/TB 自适应格式 |
| 实例备份字段缺失 | 前端未展示已有字段 | v1 已返回 Backup ID、覆盖率、数据大小和压缩率等 |
| 分区辅助指标缺失 | 前端未复用列表数据 | 旧版为前端计算，无需新增 API |

## 建议修复顺序

1. **列表基础设施**：DataTable 改为服务端分页，默认 20 条；页码、总页数、页大小、搜索和筛选全部进入 API 请求。
2. **纠正数据源和查询口径**：会话中心改用 task-runs；账户变更和日志接通时间范围；账户分类补规则统计接口。
3. **修正核心状态**：SQL Server/MySQL 群集状态与时间、账户变更统计、容量汇总单位和风险卡完整性。
4. **补详情内容**：实例基本信息、账户/容量汇总、账户操作、备份完整字段。
5. **补设置与分区内容**：按旧版恢复设置模块状态摘要、阈值、规则文案、Veeam/AD 同步统计和分区辅助指标。
6. **统一展示词典**：数据库类型、凭据类型、状态、时间、容量、同步来源和周期全部走共享 formatter。
7. **逐页回归**：修复后重新打开本报告中的全部页面，记录实际行数、总数、关键指标和详情字段，再更新迁移清单状态。

## 验收口径

- 新旧页面在相同筛选条件下，指标值、总数、状态、字段集合和详情内容一致。
- 展示形态可以不同，但不能删减旧版业务信息，也不能增加旧版不存在且未确认的正文或列表。
- 所有列表默认每页 20 条，并能通过服务端分页访问全部记录。
- 筛选必须作用于全量数据，不得只筛选首批 100/200 条。
- 所有可见筛选控件必须真正改变请求和结果。
- 后端原始枚举、内部来源名和 UTC/ISO 时间不得直接作为最终业务文本展示。
- 只有通过线上逐页复核的页面，才能在迁移清单中标记为 `Done - replacement`。

## 证据与数据来源

- 线上 React 与旧版页面 DOM、可访问性树、表头、指标和可见正文，审计日期：2026-06-22。
- 当前仓库 React 源码：`frontend/src/**`。
- 旧版页面与 JavaScript：`app/templates/**`、`app/static/js/**`。
- v1 路由和服务：`app/api/v1/**`、`app/services/**`。

本报告未保存页面截图和登录状态文件。线上实时数据会继续变化，文中的数量用于定位本次审计时的口径差异，不作为长期固定业务基线。
