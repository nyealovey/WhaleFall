# React Display Parity Tracker

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-06-18
> 更新: 2026-06-25
> 范围: `/console` React 新前端与旧版页面展示内容对齐
> 关联: `docs/plans/2026-06-11-react-frontend-migration-checklist.md`, `frontend/`, `app/templates/`, `app/static/js/modules/views/`

## 目标

本文档只跟踪“页面展示内容”的新旧差异，不跟踪 API 缺口、写操作缺口和部署问题。

React 新前端的迁移目标是旧版功能等价替代：展示形态可以换成 shadcn、TanStack Table、Recharts 等成熟组件，但页面展示的信息口径要和旧版一致。旧版模板没有的展示内容，不因为新版 API 能拿到数据就默认新增。

## 处理口径

- 旧版有的指标、字段、筛选项、详情块、状态说明和空态，新版必须保留。
- 旧版没有的卡片、图表、说明段落和统计信息，默认删除；不在本次迁移清单里保留占位。
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

## 优先级

1. 先处理用户已经明确感知的问题：仪表盘额外图表、系统设置空白/展示形态、群集页展示形态。
2. 再处理全局额外说明文字和非旧版指标卡。
3. 最后逐页复核列表字段、详情块、筛选项和图表标题。

## 全局差异跟踪

| 范围 | 差异 | 处理方式 | 状态 |
| --- | --- | --- | --- |
| 所有 React 页面 | 新版 PageHeader 通常包含英文 eyebrow 和页面说明，旧版多数页面没有 | 已集中移除 PageHeader 英文 eyebrow 和说明；Dashboard 自定义头部同步移除 `React console` | Done |
| 所有 React 页面 | `在旧版打开` 入口旧版没有 | 作为迁移期回滚入口保留 | Keep - migration |
| 全局 Shell | 旧版顶部有“修改密码”，React 早期只有用户信息和退出 | 已补“修改密码”入口，链接到 `/auth/change-password` | Done |
| 全局页脚 | 旧版所有页面底部有版本信息和“关于”入口，React 早期没有页脚 | 已在 AppShell 补回全局页脚和 `/console/about` 入口 | Done |
| 所有列表页 | 旧版独立筛选区被新版 DataTable 工具栏吸收 | 已逐页核对筛选字段；保留 DataTable 工具栏形态，筛选内容与旧版等价 | Done |
| 多数页面 | 新版新增顶部指标卡、`每页 X 条`、描述性副标题 | 已按页面完成收口：旧版没有的删除，旧版已有指标保留并恢复原口径 | Done |
| 所有写操作页面 | 新版 Sonner toast 反馈旧版没有 | 保留，属于交互反馈，不改变展示数据口径 | Keep - migration |
| 所有服务端列表 | 早期 React 只请求第一页并做客户端分页，旧版可访问完整分页数据；大页数时分页按钮组曾换行溢出 | 已引入 shadcn Pagination 和受控服务端分页；默认每页 20，可选 20/50/100，筛选和搜索回到第一页；分页按钮组保持单行，窄宽度时横向滚动 | Done |

## 页面差异跟踪

| 页面 | 旧版展示口径 | 新版确认差异 | 处理方式 | 状态 |
| --- | --- | --- | --- | --- |
| `/console/dashboard` | 4 个核心指标、风险告警、错误和告警日志趋势、系统状态、运行时间 | 新版额外展示账户分类、日志等级图、同步趋势图、容量利用率标记和说明文字；风险告警正文曾被截断 | 已删除旧版没有的账户分类、日志等级图、同步趋势图和容量利用率标记；风险告警不再 `slice` 截断，页面保留旧版驾驶舱核心内容 | Done |
| `/console/about` | 页脚“关于”页面展示鲸落 WhaleFall、作者、项目介绍、核心功能、技术栈、支持数据库和更新日志 | React 早期未迁移该页，导致所有页面底部也缺少“关于”入口 | 已新增 React 关于页，内容对齐旧版 `about.html` 静态展示；全局页脚入口从所有 React 页面可达 | Done |
| `/console/risk-center` | 风险看板、风险卡、严重度/类型/状态等筛选 | 新版分组为风险墙、高优先级风险、核心信号，展示分组与旧版不同；早期只请求 12 张风险卡 | 已删除高优先级风险独立区、主机/score/首条风险详情等额外内容；恢复启用/停用状态筛选、标签 code 输入、紧凑图标信号卡和实例详情链接；风险卡默认每页 20 并接入服务端分页 | Done |
| `/console/instances` | 独立筛选区、实例列表、批量操作、实例详情入口 | 新版有详情弹窗和详情页两个入口，并有额外说明/每页条数；2026-06-25 复核仍发现 `RESOURCE INVENTORY` 残留 | 已删除列表详情弹窗入口，只保留一个 `/console/instances/{id}` 详情页入口；列表英文 eyebrow 和说明文字已继续收敛 | Done |
| `/console/instances/:id` | 实例基础信息、账户信息、AG 账户、容量、审计、备份等详情块；旧版详情内容在标签框内切换 | 新版早期缺实例 ID、版本、标签、详情页编辑/回收站、账户/容量汇总、账户操作和备份字段；审计和备份曾独立显示在页签框外；2026-06-25 复核仍发现 `Instance detail` 和连接状态原始值 `poor` | 已删除原始实例 JSON 和旧版没有的说明头；补齐实例 ID、数据库版本、标签、编辑、移入回收站、账户/容量四项汇总、查看权限、变更历史、表容量入口、Backup ID、覆盖数量、平台、数据大小、备份大小和压缩率；账户、AG 账户、容量、审计、备份统一在同一个 shadcn Tabs 卡片中切换；连接状态统一映射为中文业务文本 | Done |
| `/console/database-ledgers` | 数据库台账列表、筛选、同步、导出、表容量详情 | 新版主要差异为筛选位置和说明文字；2026-06-25 复核仍发现 `Database ledger` 残留 | 字段、筛选和动作已核对；删除旧版没有的 `每页 X 条` 辅助说明；英文 eyebrow 和说明文字已继续收敛 | Done |
| `/console/account-ledgers` | 账户台账列表、筛选、同步、导出、权限/变更历史 | 新版主要差异为筛选位置和说明文字 | 字段、筛选和动作已核对；删除旧版没有的 `每页 X 条` 辅助说明 | Done |
| `/console/capacity/instances` | 容量筛选、核心指标、三类容量趋势图、容量列表 | 新版额外展示起止日期、英文页头、每页条数、内部来源名和旧版没有的大容量明细列表 | 已移除旧版没有的可见日期输入、英文说明、分页辅助文案、内部来源名和大容量明细列表；容量单位按 MB/GB/TB 自适应；保留默认统计区间、旧版筛选、指标和三组图表 | Done |
| `/console/capacity/databases` | 容量筛选、核心指标、三类容量趋势图、容量列表 | 新版额外展示起止日期、英文页头、每页条数、内部来源名和旧版没有的大容量明细列表 | 已移除旧版没有的可见日期输入、英文说明、分页辅助文案、内部来源名和大容量明细列表；容量单位按 MB/GB/TB 自适应；保留默认统计区间、旧版筛选、指标和三组图表 | Done |
| `/console/instance-statistics` | 刷新统计、实例指标、类型/端口/版本/备份等分布 | 新版有额外 PageHeader 说明 | 已移除英文页头和说明；旧版指标、分布、图表标题及刷新动作保留 | Done |
| `/console/account-statistics` | 刷新统计、账户指标、来源/AD/类型/分类分布 | 新版额外展示旧版没有的规则命中快照和 PageHeader 说明 | 已删除规则命中独立展示及英文说明；保留旧版账户来源、AD、数据库类型和分类分布 | Done |
| `/console/database-statistics` | 刷新统计、数据库指标、类型/实例/同步状态/容量排行 | 新版有额外 PageHeader 说明 | 已移除英文页头和说明；旧版指标、分布、容量排行字段及刷新动作保留 | Done |
| `/console/logs` | 四项日志指标、日志筛选、列表、详情；旧版详情含复制消息、复制 JSON、复制堆栈、展开上下文、复制详情 | 新版把“信息日志”替换成了“Top 模块”指标，并有额外页头和分页说明；时间范围曾只影响静态控件；2026-06-25 复核发现详情辅助动作缺失 | 已恢复总日志数、错误日志、警告日志、信息日志及其旧版辅助口径；时间范围同时作用于列表和统计，模块选项从 v1 加载；保留筛选、列表和详情，删除额外说明；日志详情已补复制消息、复制 JSON、复制堆栈、展开上下文、复制详情 | Done |
| `/console/account-change-logs` | 四项变更指标、变更筛选、列表、详情 | 新版把成功率改成成功数量，且指标名称、页头和分页说明与旧版不一致；统计与列表曾使用不同时间口径 | 已恢复变更总数、成功率、失败变更、影响账号数及旧版辅助口径；默认全部时间口径，时间范围同时作用于列表和统计，实例选项从 v1 加载；保留筛选、列表和详情，删除额外说明 | Done |
| `/console/clusters` | SQL Server/MySQL 标签切换；新增/编辑内含基本信息、绑定实例、AG 配置；旧版 AG 账户和 AG 状态均为可查看弹窗 | 新版已恢复标签切换；详情弹窗发起子弹窗的交互与旧版不一致；2026-06-25 复核发现 AG 账户无可见弹窗，AG 状态缺副本/数据库明细 | 绑定实例和 SQL Server AG 配置从列表操作进入维护 Dialog，详情弹窗只做查看和同步，不再发起子弹窗；列表状态字段按旧版业务字段映射；已补 AG 账户查看弹窗和 AG 状态副本/数据库同步明细 | Done |
| `/console/account-classifications` | 左侧账户分类、右侧规则管理；管理员可维护，只读角色仅查看 | 新版增加面板计数/说明，且没有按角色隐藏写入口 | 已删除面板计数和说明；路由传入当前用户，非管理员隐藏自动分类、新建、编辑和删除，只保留规则查看 | Done |
| `/console/classification-statistics` | 分类筛选、规则列表、分类趋势和规则贡献 | 新版额外增加四张汇总卡、分类排行和图表说明 | 已删除汇总卡、分类排行和额外图表说明；保留旧版筛选联动、规则列表、两张图表及覆盖信息 | Done |
| `/console/scheduler` | 任务列表/分组、任务状态、触发器参数、操作；旧版编辑任务按任务名称、执行函数、秒/分/时/日/月/周/年拆字段 | 新版新增顶部任务统计卡；2026-06-25 复核发现编辑弹窗只暴露 Cron 表达式 | 已删除旧版没有的任务总数、运行任务、内置任务、可配置四张统计卡；编辑任务弹窗已恢复旧版拆字段形态 | Done |
| `/console/sync-sessions` | 会话列表、筛选、任务详情、执行记录和错误日志 | 新版额外增加会话汇总卡、列表说明和原始同步 JSON；早期接入 `sync-sessions` 数据源而非旧版 `task-runs` | 已删除汇总卡、列表说明和原始 JSON；切换到 `task-runs`，保留旧版列表字段、固定业务筛选、详情、执行记录、错误信息和取消动作 | Done |
| `/console/users` | 用户列表、筛选、新建/编辑/删除；非管理员只读 | 新版额外增加用户统计卡、分页说明和旧版没有的查看详情入口 | 已删除统计卡、分页说明和详情入口；保留旧版列、筛选和管理员写操作，非管理员操作列只读 | Done |
| `/console/settings` | 设置模块导航；一次只显示告警、JumpServer、风险规则、Veeam、AD 中的一个面板；旧版 AD 列表有测试入口 | 新版纵向展示多个设置区，并增加启用配置/风险规则/AD/Veeam 指标卡；早期缺 Webhook 清空、容量阈值、风险规则说明、JumpServer/Veeam/AD 状态字段；2026-06-25 复核发现 AD 列表测试入口缺失 | 已改用 shadcn Tabs 单面板切换；删除顶部系统设置指标卡；补齐告警 Webhook 脱敏/清空、容量增长阈值、风险规则分类/名称/描述/严重级别、JumpServer 凭据/SSL/同步状态、Veeam 凭据/启用/同步/Provider 汇总、AD 默认新增模式和域控/凭据/同步/AD-SQL 统计；AD 列表已补测试 AD 连接入口 | Done |
| `/console/credentials` | 凭据列表、筛选、绑定实例数量、新建/编辑/删除；旧版非数据库凭据表单不展示数据库类型 | 新版额外增加凭据统计卡、分页说明和查看详情入口；2026-06-25 复核发现新建/编辑凭据无条件展示数据库类型 | 已删除统计卡、分页说明和详情入口；保留旧版字段、筛选、绑定数量与管理员写操作；数据库类型字段仅在数据库凭据下展示 | Done |
| `/console/tags` | 四项标签指标、标签列表、筛选、批量分配/移除 | 新版标签辅助指标口径不完整，并增加分类说明和查看详情入口 | 已恢复均值/分类、启用数、停用数、启用/分类及一位小数百分比；删除分类说明和详情入口 | Done |
| `/console/partitions` | 两个命令、四项指标、核心趋势、分区列表；创建和清理参数位于弹窗；旧版表头为分区名称、表类型、大小、记录数、分区月份、状态 | 新版把分区日期和保留月份提前到工具栏，并增加图表状态/时间和分页说明；2026-06-25 复核发现表头语义被合并 | 已把创建年月与保留月数移回 shadcn Dialog/AlertDialog；删除图表额外状态/时间和分页说明；分区列表表头恢复旧版展示语义 | Done |

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

### Batch 6: 线上审计 P0/P1 修复

| 范围 | 任务 | 验收 |
| --- | --- | --- |
| 列表基础设施 | 改为服务端分页、固定页大小选项和筛选回第一页 | 旧版可访问的完整列表数据不再被前端首批请求截断 |
| 数据源与口径 | 会话中心切换 task-runs；日志、账户变更、规则命中数和筛选选项接旧版同源 API | 页面列表、统计卡和筛选项口径一致 |
| 汇总与详情 | 补仪表盘风险项、风险中心分页、容量单位、群集状态、分区指标、实例详情和系统设置字段 | 展示内容与旧版一致，旧版没有的大列表或正文不再显示 |

### Batch 7: 2026-06-25 线上复核修复

| 范围 | 任务 | 验收 |
| --- | --- | --- |
| 全局与说明文字 | 补修改密码入口，继续删除残留英文 eyebrow 和说明文字 | Shell 有旧版修改密码入口；实例、数据库台账等页面不再显示旧版没有的英文说明 |
| 群集、调度、日志 | 补 AG 账户、AG 状态副本/数据库明细、任务拆字段编辑、日志详情复制/上下文动作 | 弹窗展示内容不低于旧版 |
| 凭据、分区、实例状态 | 凭据数据库类型条件展示，分区列名恢复旧版语义，实例连接状态中文化 | 新版不再暴露旧版没有的非数据库凭据字段，状态和表头按旧版业务文本展示 |

## 验证记录

2026-06-18 Batch 1 展示修复验证：

```bash
npm --prefix frontend run test -- DashboardPage.test.tsx --run            # 3 passed
npm --prefix frontend run test -- ConsolePages.test.tsx --run             # 40 passed
```

2026-06-18 Batch 2 PageHeader 收敛验证：

```bash
npm --prefix frontend run test -- DashboardPage.test.tsx --run            # 3 passed
npm --prefix frontend run test -- ConsolePages.test.tsx --run             # 40 passed
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
npm --prefix frontend run test -- ConsolePages.test.tsx --run              # 40 passed
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
npm --prefix frontend run test -- ConsolePages.test.tsx --run              # 40 passed
npm --prefix frontend run test                                             # 24 files, 137 tests passed
npm --prefix frontend run typecheck                                        # passed
npm --prefix frontend run lint                                             # passed
npm --prefix frontend run build                                            # passed; Vite chunk-size warning remains
git diff --check                                                           # passed
```

2026-06-23 Batch 6 线上审计修复验证：

```bash
npm --prefix frontend run test                                             # 26 files, 147 tests passed
npm --prefix frontend run typecheck                                        # passed
npm --prefix frontend run lint                                             # passed
npm --prefix frontend run build                                            # passed; Vite chunk-size warning remains
uv run pytest tests/unit/routes/test_api_v1_task_runs_contract.py tests/unit/routes/test_api_v1_history_logs_contract.py tests/unit/routes/test_api_v1_account_change_logs_contract.py tests/unit/routes/test_api_v1_accounts_statistics_contract.py tests/unit/routes/test_api_v1_accounts_classifications_contract.py tests/unit/routes/test_api_v1_sqlserver_clusters_contract.py tests/unit/routes/test_api_v1_mysql_clusters_contract.py tests/unit/routes/test_api_v1_partition_contract.py -q  # 36 passed
git diff --check                                                           # passed
```

2026-06-25 Batch 7 线上复核修复验证：

```bash
npm --prefix frontend run test -- src/layout/AppShell.test.tsx src/pages/ListPages.test.tsx src/pages/AuditPages.test.tsx src/pages/ConsolePages.test.tsx  # 4 files, 60 tests passed
npm --prefix frontend run test -- src/layout/AppShell.test.tsx src/migration/legacyParity.test.ts src/pages/AboutPage.test.tsx  # 3 files, 5 tests passed
npm --prefix frontend run test                                             # 28 files, 154 tests passed
npm --prefix frontend run typecheck                                        # passed
npm --prefix frontend run lint                                             # passed
npm --prefix frontend run build                                            # passed; no Vite chunk-size warning
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
- 2026-06-18: 完成 Batch 1 展示修复：仪表盘删除旧版没有的账户分类/日志等级/同步趋势/容量利用率展示；系统设置恢复旧版单面板模块切换并删除顶部指标卡；群集绑定实例和 SQL Server AG 配置改为从列表操作入口维护，详情弹窗不发起子弹窗。
- 2026-06-18: 完成 Batch 2 首项全局收敛：集中移除 React PageHeader 英文 eyebrow 和说明文字，Dashboard 自定义头同步移除 `React console`。
- 2026-06-22: 继续 Batch 2 页面内容收敛：风险中心恢复旧版筛选和紧凑信号墙、删除独立高优先级区；实例列表删除重复详情弹窗入口；调度器删除旧版没有的顶部统计卡。
- 2026-06-22: 继续 Batch 2 实例与台账内容收敛：实例详情删除旧版没有的原始 JSON、账户/AG/容量汇总卡和说明头；实例、数据库台账、账户台账删除 `每页 X 条` 辅助文案。
- 2026-06-22: 完成 Batch 4 七页收口：容量页移除额外日期输入与说明；三张统计页移除额外说明和账户规则命中增强区；两张审计页恢复旧版四项指标名称、数值及辅助口径。
- 2026-06-22: 完成 Batch 5 剩余七页收口：分类页删除额外汇总并恢复只读权限；会话、用户、凭据删除旧版没有的增强展示；标签恢复旧版指标辅助口径；分区参数移回 shadcn 弹窗。
- 2026-06-23: 按线上审计 P0/P1 完成 Batch 6 修复：服务端分页、会话 task-runs、审计时间口径、账户规则命中数、容量单位/明细列表、群集状态字段、分区指标、实例详情和系统设置字段均已在代码侧收口；用户重新构建部署后需按审计报告线上复核。
- 2026-06-23: 根据生产复核继续修复：实例详情的账户、AG 账户、容量、审计、备份统一进入同一个 Tabs 卡片；DataTable 分页按钮组改为单行不可换行，避免 383 页这类大页数场景溢出。
- 2026-06-25: 按新一轮线上对比文档完成 Batch 7 代码侧修复：全局修改密码入口、群集 AG 账户弹窗、AG 状态副本/数据库明细、调度任务拆字段编辑、日志详情复制/上下文、凭据数据库类型条件展示、分区旧版表头语义、实例连接状态中文化和残留英文说明收敛；待重新构建部署后线上复核。
- 2026-06-25: 按“旧版没有直接删除”口径收口：展示跟踪文档不再保留占位状态；React 只读 API 层移除未使用的用户/凭据/标签详情读取封装。
- 2026-06-25: 补全旧版页脚关于入口：所有 React 页面恢复全局页脚，`/console/about` 展示项目介绍、核心功能、技术栈、支持数据库和更新日志。
- 2026-06-25: 完成构建拆包优化：路由页面懒加载，重页面通过独立懒入口按需加载，vendor 分包覆盖 React、TanStack、Radix、icons 和 charts；生产构建不再出现 Vite 大 chunk 警告。
- 2026-06-25: 移除迁移期临时聚合页面命名，页面源码按群集、分类、调度、会话、设置、用户/凭据/标签、分区拆分，保留 `ConsolePageScaffold` 承载共享布局与 formatter。
