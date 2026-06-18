# React Display Parity Tracker

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-06-18
> 更新: 2026-06-18
> 范围: `/console` React 新前端与旧版页面展示内容对齐
> 关联: `docs/plans/2026-06-11-react-frontend-migration-checklist.md`, `frontend/`, `app/templates/`, `app/static/js/modules/views/`

## 目标

本文档只跟踪“页面展示内容”的新旧差异，不跟踪 API 缺口、写操作缺口和部署问题。

React 新前端的迁移目标是旧版功能等价替代：展示形态可以换成 shadcn、TanStack Table、Recharts 等成熟组件，但页面展示的信息口径要和旧版一致。旧版模板没有的展示内容，不因为新版 API 能拿到数据就默认新增。

## 处理口径

- 旧版有的指标、字段、筛选项、详情块、状态说明和空态，新版必须保留。
- 旧版没有的卡片、图表、说明段落和统计信息，默认删除；如果确实有业务价值，先标记为未来增强，不混进替代验收。
- 表格自带筛选可以替代旧版独立筛选区，但筛选字段必须等价。
- shadcn 组件优先：Select、Checkbox、Switch、Tooltip、Tabs、Dialog、AlertDialog、Sonner 等不要手写。
- `在旧版打开` 属于迁移期回滚入口，不按旧版内容差异处理；等 React 完全验收后再评估是否移除。
- 英文 eyebrow、页面描述、指标解释这类“新版说明文字”按页面逐项核对；旧版没有且不影响操作的，优先删减。

## 状态说明

| 状态 | 含义 |
| --- | --- |
| `Open` | 已确认展示差异，待处理 |
| `In progress` | 正在处理 |
| `Done` | 已按旧版展示内容完成调整 |
| `Keep - migration` | 与旧版不同，但属于迁移期必要能力，例如旧版入口 |
| `Future enhancement` | 旧版没有，后续如需保留需要单独立需求 |

## 优先级

1. 先处理用户已经明确感知的问题：仪表盘额外图表、系统设置空白/展示形态、群集页展示形态。
2. 再处理全局额外说明文字和非旧版指标卡。
3. 最后逐页复核列表字段、详情块、筛选项和图表标题。

## 全局差异跟踪

| 范围 | 差异 | 处理方式 | 状态 |
| --- | --- | --- | --- |
| 所有 React 页面 | 新版 PageHeader 通常包含英文 eyebrow 和页面说明，旧版多数页面没有 | 已集中移除 PageHeader 英文 eyebrow 和说明；Dashboard 自定义头部同步移除 `React console` | Done |
| 所有 React 页面 | `在旧版打开` 入口旧版没有 | 作为迁移期回滚入口保留 | Keep - migration |
| 所有列表页 | 旧版独立筛选区被新版 DataTable 工具栏吸收 | 保留这种形态，但逐页核对筛选字段是否与旧版一致 | Open |
| 多数页面 | 新版新增顶部指标卡、`每页 X 条`、描述性副标题 | 旧版没有的删掉；旧版有对应指标的保留 | Open |
| 所有写操作页面 | 新版 Sonner toast 反馈旧版没有 | 保留，属于交互反馈，不改变展示数据口径 | Keep - migration |

## 页面差异跟踪

| 页面 | 旧版展示口径 | 新版确认差异 | 处理方式 | 状态 |
| --- | --- | --- | --- | --- |
| `/console/dashboard` | 4 个核心指标、风险告警、错误和告警日志趋势、系统状态、运行时间 | 新版额外展示账户分类、日志等级图、同步趋势图、容量利用率标记和说明文字 | 已删除旧版没有的账户分类、日志等级图、同步趋势图和容量利用率标记；页面保留旧版驾驶舱核心内容 | Done |
| `/console/risk-center` | 风险看板、风险卡、严重度/类型/状态等筛选 | 新版分组为风险墙、高优先级风险、核心信号，展示分组与旧版不同 | 对照旧版模板和 JS 复核风险卡字段；旧版没有的“高优先级风险”独立区先降级或删除 | Open |
| `/console/instances` | 独立筛选区、实例列表、批量操作、实例详情入口 | 新版有详情弹窗和详情页两个入口，并有额外说明/每页条数 | 保留一个主详情入口；另一个如需保留改成轻量操作入口或隐藏；删除非旧版说明文字 | Open |
| `/console/instances/:id` | 实例基础信息、账户信息、AG 账户、容量、审计、备份等详情块 | 新版增加汇总卡片和更强分区说明 | 保留旧版详情块；额外汇总卡片逐项核对，旧版无对应内容则删除 | Open |
| `/console/database-ledgers` | 数据库台账列表、筛选、同步、导出、表容量详情 | 新版主要差异为筛选位置和说明文字 | 核对字段和筛选项；删除非旧版说明文字 | Open |
| `/console/account-ledgers` | 账户台账列表、筛选、同步、导出、权限/变更历史 | 新版主要差异为筛选位置和说明文字 | 核对字段和筛选项；删除非旧版说明文字 | Open |
| `/console/capacity/instances` | 容量筛选、核心指标、三类容量趋势图、容量列表 | 新版额外解释每页条数、增长率/占比等说明 | 保留旧版图表和指标；删除旧版没有的辅助说明 | Open |
| `/console/capacity/databases` | 容量筛选、核心指标、三类容量趋势图、容量列表 | 新版额外解释每页条数、增长率/占比等说明 | 保留旧版图表和指标；删除旧版没有的辅助说明 | Open |
| `/console/instance-statistics` | 刷新统计、实例指标、类型/端口/版本/备份等分布 | 新版有额外 PageHeader 和说明卡片 | 核对图表标题和分布项；删减非旧版说明 | Open |
| `/console/account-statistics` | 刷新统计、账户指标、来源/AD/类型/分类分布 | 新版保留规则命中快照，可能超出旧版展示 | 如果旧版没有规则命中独立展示，移入未来增强或删除 | Open |
| `/console/database-statistics` | 刷新统计、数据库指标、类型/实例/同步状态/容量排行 | 新版有额外说明和卡片化布局 | 核对图表标题和排行字段；删减非旧版说明 | Open |
| `/console/logs` | 日志列表、筛选、详情 | 新版差异主要是详情 Dialog 和 DataTable 筛选 | 形态保留；核对列表字段和详情字段 | Open |
| `/console/account-change-logs` | 账户变更日志列表、筛选、详情 | 新版差异主要是详情 Dialog 和 DataTable 筛选 | 形态保留；核对列表字段和详情字段 | Open |
| `/console/clusters` | SQL Server/MySQL 标签切换；新增/编辑内含基本信息、绑定实例、AG 配置 | 新版已恢复标签切换，但绑定实例和 AG 维护放在列表下方同页区域 | 已把绑定实例和 SQL Server AG 配置从列表下方同页区域收进 shadcn Dialog；详情弹窗仍只做查看和同步，不发起子弹窗 | Done |
| `/console/account-classifications` | 左侧账户分类、右侧规则管理 | 新版增加计数、确认弹窗和卡片分组 | 确认弹窗保留；旧版没有的计数/说明按需删除 | Open |
| `/console/classification-statistics` | 分类统计、趋势、规则贡献和筛选 | 新版有额外说明文案和更细分的图表区 | 核对旧版标题/指标；删减额外说明 | Open |
| `/console/scheduler` | 任务列表/分组、任务状态、触发器参数、操作 | 新版新增顶部任务统计卡 | 如旧版没有统计卡，删除或移入未来增强 | Open |
| `/console/sync-sessions` | 会话列表、筛选、详情、实例记录、错误日志 | 新版差异主要是详情 Dialog 和 DataTable 筛选 | 形态保留；核对字段和详情块 | Open |
| `/console/users` | 用户列表、筛选、详情、新建/编辑/删除 | 新版可能有额外统计卡和说明文字 | 核对旧版是否有统计；没有则删除 | Open |
| `/console/settings` | 设置模块导航；一次只显示告警、JumpServer、风险规则、Veeam、AD 中的一个面板 | 新版纵向展示多个设置区，并增加启用配置/风险规则/AD/Veeam 指标卡 | 已改回模块导航单面板切换；删除顶部系统设置指标卡；保留旧版设置字段和操作入口 | Done |
| `/console/credentials` | 凭据列表、筛选、绑定实例数量、新建/编辑/删除 | 新版可能增加凭据统计和说明文字 | 保留绑定数量口径；删除旧版没有的统计/说明 | Open |
| `/console/tags` | 标签列表、分类、状态、关联数量、批量分配/移除 | 新版可能增加标签统计和说明文字 | 保留旧版数量口径；删除旧版没有的统计/说明 | Open |
| `/console/partitions` | 分区状态、核心指标趋势、分区列表、创建/清理 | 新版增加卡片说明和周期解释 | 保留旧版指标和趋势；删减额外说明 | Open |

## 实施批次

### Batch 1: 明显展示不一致

| 页面 | 任务 | 验收 |
| --- | --- | --- |
| `/console/dashboard` | 删除旧版没有的额外图表和信息块 | 页面只保留旧版四指标、风险告警、错误/告警趋势、系统状态、运行时间 |
| `/console/settings` | 恢复设置模块单面板切换 | 点击模块导航只显示当前设置面板，不再纵向展示全部设置 |
| `/console/clusters` | 调整绑定实例和 AG 配置展示位置 | 展示流程接近旧版新增/编辑 tab，不出现详情弹窗发起子弹窗 |

### Batch 2: 全局说明内容收敛

| 范围 | 任务 | 验收 |
| --- | --- | --- |
| PageHeader | 删除旧版没有的英文 eyebrow 和冗余说明 | 页面标题保留，说明文字不再制造新版额外内容 |
| 指标卡 | 删除旧版没有的统计卡 | 页面指标数量和含义与旧版一致 |
| 表格辅助文案 | 删除 `每页 X 条` 等非旧版信息 | 列表仅保留旧版字段、筛选、批量操作和分页/空态所需信息 |

### Batch 3: 逐页字段复核

| 范围 | 任务 | 验收 |
| --- | --- | --- |
| 列表页 | 对照旧版模板和 JS 核对列、筛选、详情字段 | 每页补 `Done` 记录 |
| 图表页 | 对照旧版图表标题、序列和筛选参数 | 图表展示内容一致，只有图表库和视觉样式不同 |
| 设置/表单页 | 对照旧版字段、默认值和按钮 | 旧版字段不缺项，新版无无依据新增字段 |

## 验证记录

2026-06-18 Batch 1 展示修复验证：

```bash
npm --prefix frontend run test -- DashboardPage.test.tsx --run            # 3 passed
npm --prefix frontend run test -- RemainingReadOnlyPages.test.tsx --run   # 40 passed
```

2026-06-18 Batch 2 PageHeader 收敛验证：

```bash
npm --prefix frontend run test -- DashboardPage.test.tsx --run            # 3 passed
npm --prefix frontend run test -- RemainingReadOnlyPages.test.tsx --run   # 40 passed
npm --prefix frontend run test                                            # 24 files, 137 tests passed
npm --prefix frontend run typecheck                                       # passed
npm --prefix frontend run lint                                            # passed
npm --prefix frontend run build                                           # passed; Vite chunk-size warning remains
git diff --check                                                          # passed
```

后续每批页面调整完成后，至少记录：

```bash
npm --prefix frontend run test
npm --prefix frontend run typecheck
npm --prefix frontend run lint
git diff --check
```

涉及后端路由或契约时，补跑对应 `uv run pytest tests/unit/routes/... -q`。

## 变更记录

- 2026-06-18: 建立页面展示内容差异跟踪文档，拆分出全局差异、逐页差异和三批实施计划。
- 2026-06-18: 完成 Batch 1 展示修复：仪表盘删除旧版没有的账户分类/日志等级/同步趋势/容量利用率展示；系统设置恢复旧版单面板模块切换并删除顶部指标卡；群集绑定实例和 SQL Server AG 配置从页面下方维护区收进 shadcn Dialog。
- 2026-06-18: 完成 Batch 2 首项全局收敛：集中移除 React PageHeader 英文 eyebrow 和说明文字，Dashboard 自定义头同步移除 `React console`。
