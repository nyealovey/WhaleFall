# 界面色彩与视觉疲劳控制指南

## 背景
- “仪表盘 Dashboard” 已经过一轮视觉治理（白底卡片 + pill/chip 体系），效果最佳，被选为所有管理页面的视觉基线。
- 在“实例列表”“账户台账”等页面仍可看到高饱和 `badge bg-*`、多主色 CTA 等旧实现；本指南以仪表盘现有代码为蓝本，约束其它页面的色彩布局与组件实现。

## 总体目标
1. **降低颜色数量**：在单一视区内，非图表信息的可视色彩 ≤ 7（含灰阶）。
2. **强化语义映射**：同一语义状态绑定固定 token（例如“正常”= `var(--success-color)`）。
3. **构建可复用组件**：状态、标签、数据库类型等均复用 `status-pill`、`chip-outline`、`ledger-chip-stack`，禁止页面自定义样式。
4. **提升阅读节奏**：通过字重、留白与交替行背景承载层级，颜色只做辅助提示。

## 色彩 2-3-4 规则
- **主色 ≤ 2**：品牌主色 `var(--accent-primary)` 与一种中性色（通常 `var(--text-primary)` 或 `var(--surface-contrast)`）。
- **辅助色 ≤ 3**：用于导航、次级按钮或图表；推荐从 `--orange-muted`、`--sidebar-accent`、`--surface-muted` 中择优；不得另行定义新 token。
- **语义色 ≤ 4**：固定使用 `--success-color`、`--warning-color`、`--danger-color`、`--info-color`；当页面不包含对应语义时，不得“装饰性”使用这四类颜色。
- **执行方式**：在设计稿与前端落地前完成色彩盘点，超过阈值需删减或合并信息层级。

## 组件级指导
### 状态与徽章（参考仪表盘 Stats 卡片）
1. `status-pill` 是唯一的状态载体：背景使用语义色 20% 透明度（代码示例见 `app/static/css/pages/dashboard/overview.css`），文案 ≤4 个字，支持 `success|info|warning|danger|muted` 五种变体。
2. 状态列默认 70px 宽；禁止在 pill 外叠加 `badge bg-*` 或额外底色。
3. 类型/分类/时间等辅助信息使用 `chip-outline`，白底描边；品牌语义（如“总模块”）用 `chip-outline--brand`，中性文本用 `chip-outline--muted`。
4. 多标签或上下文元数据通过 `ledger-chip-stack` 呈现，遵循“展示全部，超出用 `+N`”的实例列表实现。

### 列表与卡片
1. 表格交替行采纳仪表盘同款样式：偶数行 `color-mix(in srgb, var(--surface-muted) 10%, transparent)`，hover 时 20%。
2. 操作按钮默认 `btn-outline-secondary btn-icon`（圆角 2.25rem），只有全局 CTA（如“刷新数据”）允许 `btn-primary`；危险动作通过图标着色或二次确认提示，不再使用 `btn-danger` 实心按钮。
3. 列宽策略：状态列 70-110px，类型/分类列 110px，进度/标签列 ≥220px，操作列 90-110px。若自定义宽度，需在评审中说明并记录在文档。

### 导航与筛选
1. 参考 `history/logs` 与仪表盘筛选卡：所有输入/下拉统一 `col-md-3 col-12`，按钮区域只保留一个 `btn-primary` 和一个 `btn-outline-secondary`。
2. 筛选结果/选中项只能使用 `chip-outline` 或 `ledger-chip` 显示，禁止使用 `badge bg-light`。
3. 页头按钮组遵循“单主色 CTA”策略：仪表盘当前仅保留“刷新数据”一个 `btn-primary`，其余动作全部描边或 icon。

### 图标与文本
1. 通用图标颜色固定为 `--text-muted`，仅在异常/危险语义中引用语义色。
2. 文本层级采用字号/字重：标题 18px/600、正文 14px/400、辅助 12px/400；禁止靠颜色深浅区分层级。
3. 表格中不再为 IP、版本等常驻字段配色，保持纯文本。

### 统计卡片（Stats Cards = Dashboard Baseline）
1. **结构**：白底 + `color-mix(in srgb, var(--surface-muted) 60%, transparent)` 描边 + `--shadow-sm` 阴影，圆角 `var(--border-radius-lg)`；禁止在卡片背景上再叠加语义色或渐变。
2. **内容排布**：
   - 标题 0.9rem / `var(--text-muted)`。
   - 数值 ≥2rem/600，颜色根据语义调整（示例：错误= `--danger-color`，警告=`--warning-color`），参考 `app/templates/dashboard/overview.html`。
   - 附件信息使用 `chip-outline`（如“模块”）或 `status-pill`（如同比变化），不再使用 “x 条” 等单位描边。
3. **图标策略**：默认无图标；如确需展示，使用 `--text-muted` 且尺寸 ≤24px，避免与数值争夺注意力。
4. **数量约束**：单屏统计卡最多出现 4 张；若需更多，请改为列表或折叠面板。

## 研发与质检流程
1. **设计交付检查**：UI 需附上“色彩清单”+ 组件表（使用了哪些 chip/pill）；评审时根据 2-3-4 规则确认通过。
2. **开发自检**：落地前运行 `./scripts/refactor_naming.sh --dry-run`，并通过 `rg` 检查是否存在 HEX/RGB；仅允许引用 token 或组件 class。
3. **质检表**（新增“视觉疲劳”项）：
   - 2 分钟注视表格页面后，焦点是否自然停留在主任务区域？
   - 页面内是否存在超出语义的语义色使用？
   - 同一行内多于 3 个彩色块是否可以合并？
4. **可用性回归**：试点页面上线前组织 ≥5 名内部用户体验 48 小时，记录完成任务时间、误点击率及主观疲劳反馈。

## 实施步骤
1. **试点复盘**：账户台账已完成治理；其它表格页面上线前需对照本文检查。
2. **推广**：将 `ledger-chip`、`status-pill` 提炼为公共组件，在 `app/static/css/components/` 中引用；页面如需自定义 chip，必须先在指南登记。
3. **文档维护**：任何新增 token 或例外方案，必须补充“场景+来源+退场计划”；若 2 个版本内未使用，需回收该 token。

## 附：推荐 token 映射
| 语义 | token / class | 示例代码 |
| --- | --- | --- |
| 品牌主色 CTA | `btn btn-primary` + `var(--accent-primary)` | 仪表盘“刷新数据”按钮 |
| 描边按钮 | `btn-outline-secondary` | 列表操作 icon 按钮 |
| 状态 pill | `status-pill status-pill--success` 等 | `history/logs`、`history/sessions` 状态列 |
| 类型/分类 chip | `chip-outline chip-outline--brand`/`--muted` | 会话“操作方式/分类”列 |
| 标签堆叠 | `.ledger-chip-stack .ledger-chip` | 账户/实例标签列 |
| 进度条 | `.progress` + `.progress-bar--success` | 会话进度列 |
| 中性副标题 | `var(--text-muted)` | Stats 卡标题、筛选提示 |

> 注：若确需新增颜色，请先在设计评审会上给出“原因 + 退场机制”，并在 `app/static/css/variables.css` 定义 token；未经审批严禁在 CSS/HTML/JS 中硬编码。
