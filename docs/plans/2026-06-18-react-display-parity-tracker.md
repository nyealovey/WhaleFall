# React Display Parity Tracker

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-06-18
> 更新: 2026-06-22
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
| 所有列表页 | 旧版独立筛选区被新版 DataTable 工具栏吸收 | 已逐页核对筛选字段；保留 DataTable 工具栏形态，筛选内容与旧版等价 | Done |
| 多数页面 | 新版新增顶部指标卡、`每页 X 条`、描述性副标题 | 已按页面完成收口：旧版没有的删除，旧版已有指标保留并恢复原口径 | Done |
| 所有写操作页面 | 新版 Sonner toast 反馈旧版没有 | 保留，属于交互反馈，不改变展示数据口径 | Keep - migration |

## 页面差异跟踪

| 页面 | 旧版展示口径 | 新版确认差异 | 处理方式 | 状态 |
| --- | --- | --- | --- | --- |
| `/console/dashboard` | 4 个核心指标、风险告警、错误和告警日志趋势、系统状态、运行时间 | 新版额外展示账户分类、日志等级图、同步趋势图、容量利用率标记和说明文字 | 已删除旧版没有的账户分类、日志等级图、同步趋势图和容量利用率标记；页面保留旧版驾驶舱核心内容 | Done |
| `/console/risk-center` | 风险看板、风险卡、严重度/类型/状态等筛选 | 新版分组为风险墙、高优先级风险、核心信号，展示分组与旧版不同 | 已删除高优先级风险独立区、主机/score/首条风险详情等额外内容；恢复启用/停用状态筛选、标签 code 输入、紧凑图标信号卡和实例详情链接 | Done |
| `/console/instances` | 独立筛选区、实例列表、批量操作、实例详情入口 | 新版有详情弹窗和详情页两个入口，并有额外说明/每页条数 | 已删除列表详情弹窗入口，只保留一个 `/console/instances/{id}` 详情页入口；列表辅助说明继续按全局项跟踪 | Done |
| `/console/instances/:id` | 实例基础信息、账户信息、AG 账户、容量、审计、备份等详情块 | 新版增加汇总卡片和更强分区说明 | 已删除原始实例 JSON、账户/AG/容量额外汇总卡和“数据库信息”说明头；保留旧版基础信息、操作、详情数据和页签 | Done |
| `/console/database-ledgers` | 数据库台账列表、筛选、同步、导出、表容量详情 | 新版主要差异为筛选位置和说明文字 | 字段、筛选和动作已核对；删除旧版没有的 `每页 X 条` 辅助说明 | Done |
| `/console/account-ledgers` | 账户台账列表、筛选、同步、导出、权限/变更历史 | 新版主要差异为筛选位置和说明文字 | 字段、筛选和动作已核对；删除旧版没有的 `每页 X 条` 辅助说明 | Done |
| `/console/capacity/instances` | 容量筛选、核心指标、三类容量趋势图、容量列表 | 新版额外展示起止日期、英文页头和每页条数 | 已移除旧版没有的可见日期输入、英文说明和分页辅助文案；保留默认统计区间、旧版筛选、指标、图表与列表字段 | Done |
| `/console/capacity/databases` | 容量筛选、核心指标、三类容量趋势图、容量列表 | 新版额外展示起止日期、英文页头和每页条数 | 已移除旧版没有的可见日期输入、英文说明和分页辅助文案；保留默认统计区间、旧版筛选、指标、图表与列表字段 | Done |
| `/console/instance-statistics` | 刷新统计、实例指标、类型/端口/版本/备份等分布 | 新版有额外 PageHeader 说明 | 已移除英文页头和说明；旧版指标、分布、图表标题及刷新动作保留 | Done |
| `/console/account-statistics` | 刷新统计、账户指标、来源/AD/类型/分类分布 | 新版额外展示旧版没有的规则命中快照和 PageHeader 说明 | 已删除规则命中独立展示及英文说明；保留旧版账户来源、AD、数据库类型和分类分布 | Done |
| `/console/database-statistics` | 刷新统计、数据库指标、类型/实例/同步状态/容量排行 | 新版有额外 PageHeader 说明 | 已移除英文页头和说明；旧版指标、分布、容量排行字段及刷新动作保留 | Done |
| `/console/logs` | 四项日志指标、日志筛选、列表、详情 | 新版把“信息日志”替换成了“Top 模块”指标，并有额外页头和分页说明 | 已恢复总日志数、错误日志、警告日志、信息日志及其旧版辅助口径；保留筛选、列表和详情，删除额外说明 | Done |
| `/console/account-change-logs` | 四项变更指标、变更筛选、列表、详情 | 新版把成功率改成成功数量，且指标名称、页头和分页说明与旧版不一致 | 已恢复变更总数、成功率、失败变更、影响账号数及旧版辅助口径；保留筛选、列表和详情，删除额外说明 | Done |
| `/console/clusters` | SQL Server/MySQL 标签切换；新增/编辑内含基本信息、绑定实例、AG 配置 | 新版已恢复标签切换，但绑定实例和 AG 维护放在列表下方同页区域 | 已把绑定实例和 SQL Server AG 配置从列表下方同页区域收进 shadcn Dialog；详情弹窗仍只做查看和同步，不发起子弹窗 | Done |
| `/console/account-classifications` | 左侧账户分类、右侧规则管理；管理员可维护，只读角色仅查看 | 新版增加面板计数/说明，且没有按角色隐藏写入口 | 已删除面板计数和说明；路由传入当前用户，非管理员隐藏自动分类、新建、编辑和删除，只保留规则查看 | Done |
| `/console/classification-statistics` | 分类筛选、规则列表、分类趋势和规则贡献 | 新版额外增加四张汇总卡、分类排行和图表说明 | 已删除汇总卡、分类排行和额外图表说明；保留旧版筛选联动、规则列表、两张图表及覆盖信息 | Done |
| `/console/scheduler` | 任务列表/分组、任务状态、触发器参数、操作 | 新版新增顶部任务统计卡 | 已删除旧版没有的任务总数、运行任务、内置任务、可配置四张统计卡 | Done |
| `/console/sync-sessions` | 会话列表、筛选、任务详情、执行记录和错误日志 | 新版额外增加会话汇总卡、列表说明和原始同步 JSON | 已删除汇总卡、列表说明和原始 JSON；保留旧版列表字段、筛选、详情、执行记录、错误信息和取消动作 | Done |
| `/console/users` | 用户列表、筛选、新建/编辑/删除；非管理员只读 | 新版额外增加用户统计卡、分页说明和旧版没有的查看详情入口 | 已删除统计卡、分页说明和详情入口；保留旧版列、筛选和管理员写操作，非管理员操作列只读 | Done |
| `/console/settings` | 设置模块导航；一次只显示告警、JumpServer、风险规则、Veeam、AD 中的一个面板 | 新版纵向展示多个设置区，并增加启用配置/风险规则/AD/Veeam 指标卡 | 已改回模块导航单面板切换；删除顶部系统设置指标卡；保留旧版设置字段和操作入口 | Done |
| `/console/credentials` | 凭据列表、筛选、绑定实例数量、新建/编辑/删除 | 新版额外增加凭据统计卡、分页说明和查看详情入口 | 已删除统计卡、分页说明和详情入口；保留旧版字段、筛选、绑定数量与管理员写操作 | Done |
| `/console/tags` | 四项标签指标、标签列表、筛选、批量分配/移除 | 新版标签辅助指标口径不完整，并增加分类说明和查看详情入口 | 已恢复均值/分类、启用数、停用数、启用/分类及一位小数百分比；删除分类说明和详情入口 | Done |
| `/console/partitions` | 两个命令、四项指标、核心趋势、分区列表；创建和清理参数位于弹窗 | 新版把分区日期和保留月份提前到工具栏，并增加图表状态/时间和分页说明 | 已把创建年月与保留月数移回 shadcn Dialog/AlertDialog；删除图表额外状态/时间和分页说明 | Done |

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

### Batch 4: 容量、统计与审计页面收口

| 范围 | 任务 | 验收 |
| --- | --- | --- |
| 容量 2 页 | 对齐旧版筛选、指标、三类趋势图和列表内容 | 不显示旧版没有的日期输入、英文说明和每页条数；API 默认统计区间保持不变 |
| 统计 3 页 | 对齐实例、账户、数据库统计分区 | 删除英文说明和账户规则命中增强区；旧版指标、分布和排行完整保留 |
| 审计 2 页 | 对齐日志与账户变更的四项核心指标 | 指标名称、值和辅助口径与旧模板一致；筛选、列表、详情继续使用 React 组件 |

### Batch 5: 剩余七页展示收口

| 范围 | 任务 | 验收 |
| --- | --- | --- |
| 分类 2 页 | 删除额外计数、汇总和排行，恢复角色权限口径 | 分类管理只显示旧版面板和角色允许的动作；分类统计只保留筛选、规则列表和两张图表 |
| 会话、用户、凭据 | 删除旧版没有的统计、说明、详情增强 | 会话保留任务详情；用户与凭据不出现旧版没有的查看详情入口 |
| 标签、分区 | 对齐指标辅助值和表单位置 | 标签四项指标口径一致；分区创建/清理参数只在对应 shadcn 弹窗出现 |

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

2026-06-22 Batch 2 页面内容收敛定向验证：

```bash
npm --prefix frontend run test -- RiskCenterPage.test.tsx --run            # 4 passed
npm --prefix frontend run test -- ListPages.test.tsx --run                 # 13 passed
npm --prefix frontend run test -- RemainingReadOnlyPages.test.tsx --run    # 40 passed
npm --prefix frontend run test                                             # 24 files, 137 tests passed
npm --prefix frontend run typecheck                                        # passed
npm --prefix frontend run lint                                             # passed
npm --prefix frontend run build                                            # passed; Vite chunk-size warning remains
git diff --check                                                           # passed
```

2026-06-22 Batch 2 实例与台账内容收敛定向验证：

```bash
npm --prefix frontend run test -- ListPages.test.tsx --run                 # 13 passed
npm --prefix frontend run test                                             # 24 files, 137 tests passed
npm --prefix frontend run typecheck                                        # passed
npm --prefix frontend run lint                                             # passed
npm --prefix frontend run build                                            # passed; Vite chunk-size warning remains
git diff --check                                                           # passed
```

2026-06-22 Batch 4 容量、统计与审计页面定向验证：

```bash
npm --prefix frontend run test -- CapacityPages.test.tsx --run             # 7 passed
npm --prefix frontend run test -- StatisticsPages.test.tsx --run           # 7 passed
npm --prefix frontend run test -- AuditPages.test.tsx --run                # 6 passed
npm --prefix frontend run test                                             # 24 files, 137 tests passed
npm --prefix frontend run typecheck                                        # passed
npm --prefix frontend run lint                                             # passed
npm --prefix frontend run build                                            # passed; Vite chunk-size warning remains
git diff --check                                                           # passed
```

2026-06-22 Batch 5 剩余七页展示收口定向验证：

```bash
npm --prefix frontend run test -- RemainingReadOnlyPages.test.tsx --run    # 40 passed
npm --prefix frontend run test                                             # 24 files, 137 tests passed
npm --prefix frontend run typecheck                                        # passed
npm --prefix frontend run lint                                             # passed
npm --prefix frontend run build                                            # passed; Vite chunk-size warning remains
git diff --check                                                           # passed
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
- 2026-06-22: 继续 Batch 2 页面内容收敛：风险中心恢复旧版筛选和紧凑信号墙、删除独立高优先级区；实例列表删除重复详情弹窗入口；调度器删除旧版没有的顶部统计卡。
- 2026-06-22: 继续 Batch 2 实例与台账内容收敛：实例详情删除旧版没有的原始 JSON、账户/AG/容量汇总卡和说明头；实例、数据库台账、账户台账删除 `每页 X 条` 辅助文案。
- 2026-06-22: 完成 Batch 4 七页收口：容量页移除额外日期输入与说明；三张统计页移除额外说明和账户规则命中增强区；两张审计页恢复旧版四项指标名称、数值及辅助口径。
- 2026-06-22: 完成 Batch 5 剩余七页收口：分类页删除额外汇总并恢复只读权限；会话、用户、凭据删除旧版没有的增强展示；标签恢复旧版指标辅助口径；分区参数移回 shadcn 弹窗。
