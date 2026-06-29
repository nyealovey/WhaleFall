# React 新旧页面功能一致性审计 2026-06-26

## 审计口径

- 旧版页面是功能真源：旧版可见入口、字段、筛选、表单细节、弹窗和批量工作台，新版不得缺失。
- 展示形态可以变化，但业务含义、数据范围、联动规则和可操作能力必须一致。
- 本轮对 24 个 React 路由与对应旧版路由做了线上只读结构采集，并补充代码/模板比对：旧版模板 include、共享标签选择器、实例详情、设置页、调度页和批量标签页面均纳入范围。
- 本地已修复但线上未重建的项单独标注为 `Fixed locally, pending deploy`，避免把线上旧现象误判为未处理。

## 需要修复或复核的差异

| 优先级 | 范围 | 旧版行为 | React 当前问题 | 处置建议 |
| --- | --- | --- | --- | --- |
| P0 | `/console/credentials` 新建/编辑凭据 | 凭据类型包含数据库、API、Veeam、LDAP、SSH，且表单展示中文业务名称；密码输入支持显示/隐藏 | `Fixed locally, pending deploy`：已补 Veeam、中文类型名和密码显隐按钮 | 部署后复核新建/编辑凭据弹窗 |
| P0 | `/console/scheduler` | 页面顶部有“重新初始化任务”；旧版 JS 有删除任务能力，但旧版可见任务卡片未渲染删除按钮 | `Fixed locally, pending deploy`：保留顶部重新初始化，移除卡片可见删除按钮 | 部署后复核任务卡操作入口 |
| P0 | `/console/logs`、`/console/account-change-logs` | 时间范围变化后，统计卡的窗口与每小时指标按当前 hours 计算 | `Fixed locally, pending deploy`：统计卡窗口和每小时指标已按当前筛选 hours 计算；全部口径显示 `-` | 部署后复核 1h/24h/7d/30d/all 切换 |
| P0 | `/console/capacity/instances`、`/console/capacity/databases` | 数据库类型固定包含 MySQL、PostgreSQL、SQL Server、Oracle；实例按类型加载，数据库按实例加载；旧版筛选支持多选数据库类型和实例 | `Fixed locally, pending deploy`：数据库类型和实例恢复多选；实例按所选类型分别加载去重；数据库下拉仅单实例时可选 | 部署后复核多选、Oracle、跨类型实例锁定 |
| P1 | `/console/tags/bulk/assign` | 实例项显示实例名、`host:port`、数据库类型；分配/移除模式在同一独立页面内切换 | `Fixed locally, pending deploy`：实例类型补 `port`，meta 改为 `host:port · 类型`，删除重复类型 badge | 部署后复核批量分配/移除页面实例列表 |
| P1 | `/console/instances/:id` | 账户、容量、审计、备份在同一卡片 Tabs；账户/数据库有显式“显示已删除账户/数据库”开关 | `Fixed locally, pending deploy`：账户、AG 账户、容量信息恢复显式“显示已删除账户/数据库”开关，默认隐藏已删除记录 | 部署后复核三个 Tab 的已删除开关 |
| P1 | `/console/risk-center` | 风险筛选中 `ok` 显示为“正常”，汇总卡中显示“健康” | `Fixed locally, pending deploy`：筛选/卡片等级使用“正常”，汇总卡继续使用“健康” | 部署后复核严重度筛选和汇总卡 |
| P2 | 多数页面 | 旧版没有 React preview/内部说明；迁移期保留“在旧版打开”作为回滚入口 | PageHeader props 中仍传入英文 eyebrow/description，当前大多不渲染；但代码层仍残留迁移期命名 | 不影响功能，但后续清理未渲染 props 和迁移期命名，减少误判 |

## 页面级结论

| React 路由 | 旧版路由 | 本轮结论 |
| --- | --- | --- |
| `/console/dashboard` | `/dashboard/` | 主功能未发现新增缺口；关于/修改密码入口由 Shell 提供。 |
| `/console/risk-center` | `/risk-center/` | 核心筛选、风险墙和跳实例详情存在；`ok` 筛选文案已本地恢复“正常”，汇总卡保留“健康”。 |
| `/console/instances` | `/instances/` | 主列表、导入导出、批量和标签筛选本地代码已覆盖；需部署后复核共享标签选择器。 |
| `/console/instances/:id` | `/instances/{id}` | 详情 Tabs 已恢复；显式“显示已删除账户/数据库”入口已本地补齐。 |
| `/console/database-ledgers` | `/databases/ledgers` | 主功能未发现新增缺口；需部署后复核共享标签选择器。 |
| `/console/account-ledgers` | `/accounts/ledgers` | 权限、变更历史、导出和标签筛选已覆盖；需部署后复核共享标签选择器。 |
| `/console/capacity/instances` | `/capacity/instances` | Oracle、联动和旧版多选筛选能力已本地修复。 |
| `/console/capacity/databases` | `/capacity/databases` | Oracle、多选实例和单实例后数据库选择规则已本地修复。 |
| `/console/instance-statistics` | `/instances/statistics` | 主展示未发现新增缺口。 |
| `/console/account-statistics` | `/accounts/statistics` | 主展示未发现新增缺口。 |
| `/console/database-statistics` | `/databases/statistics` | 主展示未发现新增缺口。 |
| `/console/logs` | `/history/logs/` | 列表、统计和详情动作存在；统计卡窗口/每小时口径已本地按筛选计算。 |
| `/console/account-change-logs` | `/history/account-change-logs/` | 列表、统计和详情动作存在；统计卡窗口/每小时口径已本地按筛选计算。 |
| `/console/clusters` | `/cluster/` | SQL Server/MySQL Tabs、详情和同步动作已覆盖；新增入口拆成两个按钮，功能不缺。 |
| `/console/account-classifications` | `/accounts/classifications/` | 分类、规则、详情和权限选项未发现新增缺口。 |
| `/console/classification-statistics` | `/accounts/statistics/classifications` | 主展示未发现新增缺口。 |
| `/console/scheduler` | `/scheduler/` | 顶部“重新初始化任务”已存在；卡片可见删除任务入口已本地移除。 |
| `/console/sync-sessions` | `/history/sessions/` | 会话列表、详情、错误日志和取消动作未发现新增缺口。 |
| `/console/users` | `/users/` | 新建、编辑、删除和角色/状态筛选未发现新增缺口。 |
| `/console/settings` | `/admin/system-settings` | 完整设置编辑路径存在；需继续线上切 Tab 复核每个模块保存/测试/同步入口。 |
| `/console/credentials` | `/credentials/` | Veeam 类型、中文类型名称和密码显隐已本地补齐。 |
| `/console/tags` | `/tags/` | 标签列表、指标、新建/编辑/删除和批量入口未发现新增缺口。 |
| `/console/tags/bulk/assign` | `/tags/bulk/assign` | 独立页面和两种模式已恢复；实例 `host:port · 类型` 展示已本地补齐。 |
| `/console/partitions` | `/partition/` | 四指标趋势和分区指标已按旧版恢复；本轮未发现新增缺口。 |
| `/console/about` | `/about` | 关于页入口和静态内容已恢复。 |

## 后续执行顺序

1. P0/P1 本地代码侧已修复：凭据表单、调度任务、日志/账户变更统计窗口、容量多选筛选、标签批量实例展示、实例详情删除开关文案、风险中心正常/健康文案。
2. 部署后按页面级结论逐页线上复核，确认后从 `Fixed locally, pending deploy` 收口为 `Closed`。
3. 每修一批同步更新本文档、迁移清单和展示一致性跟踪文档。
4. 每批至少运行 `npm --prefix frontend run test`、`npm --prefix frontend run typecheck`、`npm --prefix frontend run lint`、`npm --prefix frontend run build`。

## 本轮验证

2026-06-29 P0/P1 本地修复验证通过：

```bash
npm --prefix frontend run test -- src/pages/ConsolePages.test.tsx src/pages/AuditPages.test.tsx src/pages/CapacityPages.test.tsx src/api/capacity.test.ts src/pages/RiskCenterPage.test.tsx src/pages/ListPages.test.tsx  # 6 files, 81 tests passed
npm --prefix frontend run test       # 29 files, 164 tests passed
npm --prefix frontend run typecheck  # passed
npm --prefix frontend run lint       # passed
npm --prefix frontend run build      # passed; no Vite chunk-size warning
git diff --check                     # passed
```
