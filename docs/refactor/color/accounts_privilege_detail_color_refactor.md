# 账户权限详情弹窗色彩与组件重构方案

## 背景
- `账户权限详情` 弹窗沿用早期纯色 UI：顶栏、角色标签使用高饱和 HEX（`#ff5a00`、`#ff6b00` 等）+ 100% 实底，完全脱离《界面色彩与视觉疲劳控制指南》（`docs/standards/color-guidelines.md`）提出的“色彩 2-3-4 规则”。
- 状态/权限标签以自定义 button 绘制，未复用 `status-pill`、`chip-outline`、`ledger-chip-stack`，且使用了 `UNLIMITED TABLESPACE`、`CREATE SESSION` 等直接描白文字，颜色语义无法映射到 token。
- 弹窗内容区块（角色/系统权限/表空间权限等）层级仅靠颜色与 icon 撑开，缺少统一的排版、间距与交替背景，导致信息密度不均衡且对比度过高。

## 重构目标
1. 使用仪表盘基线组件重新搭建弹窗：主色 ≤ 2、辅助色 ≤ 3、语义色 ≤ 4，完全引用 `variables.css` token，无硬编码颜色。
2. 角色、权限、配额等标签统一采用 `chip-outline` + `status-pill`，根据语义切换 `success|warning|danger|muted` 变体，不再自定义彩色按钮。
3. 调整模态结构：顶部条、内容区、列表项全部统一留白与分隔线，确保阅读节奏依赖字体/排版而非大块色块。

## 设计策略
### 1. 模态框与头部
- 弹窗头部改为白底 + `chip-outline chip-outline--brand` 显示“账户权限详情”，右侧使用 `status-pill--muted` 呈现账户名或实例名，保留一个 `btn-icon` 关闭按钮。
- 页眉背景使用 `var(--surface-elevated)`，禁用纯橙渐变；若需强调“高风险账户”，仅允许 `status-pill--warning` 放置在标题旁。

### 2. 信息分组
- 将“角色”“系统权限”“表空间权限”“表空间配额”拆为 `section-card`，每个区块包含：标题（`chip-outline` + icon）、数据描述（`about-body-text`），以及内容列表。
- 列表内使用 `ledger-chip-stack` 承载多个权限标签，超出部分显示 `+N` counter，避免一行多个彩块。
- 无数据时使用 `status-pill status-pill--muted` 显示“无角色”“无系统权限”等提示，替代灰色文字。

### 3. 标签与语义
- 角色：`chip-outline chip-outline--brand` 展示角色名称，`status-pill--info` 标注来源；危险角色（如 `DBA`）使用 `status-pill--danger`。
- 系统权限：`ledger-chip` + `tooltip` 格式，文字大写统一改为 Title Case；危险权限（`IMPERSONATE ANY USER`）映射 `status-pill--warning`。
- 表空间权限/配额：采用两列布局，左侧 `status-pill` 显示权限状态，右侧 `chip-outline` 显示数值或“未配置”，确保语义色≠装饰色。

### 4. 样式与交互
- 将弹窗宽度限制在 720px，主体背景使用 `color-mix(in srgb, var(--surface-muted) 6%, var(--surface-elevated))` 防止雪白刺眼。
- 使用 `table.css` 内现有分隔/间距变量，行 hover 颜色遵循指南（10%/20% 透明度）。
- 关闭按钮沿用 `btn btn-icon btn-outline-secondary`，禁用自定义 X 图标颜色。

## 实施步骤
1. **模板改造**：更新 `app/templates/accounts/privileges/detail.html`（或对应片段），拆分区块结构，加入 `chip-outline`、`ledger-chip-stack`、`status-pill`，删除原有 `badge`、`btn` 彩色类。
2. **CSS 调整**：在 `app/static/css/pages/accounts/privileges.css`（如不存在则创建）引入公共组件样式，仅补充排版/间距规则；确保无硬编码 HEX。
3. **JS/数据**：格式化权限数据，提供 `type` 字段映射到 `status-pill` 变体，统一 Title Case；无数据时返回空数组让模板渲染“无权限” pill。
4. **自检**：`rg -n "#" app/templates/accounts/privileges/detail.html` + `rg -n "bg-" ...` 确保无硬编码颜色；执行 `./scripts/refactor_naming.sh --dry-run` 与 `make quality`。

## 风险与缓解
- **权限类型多样**：若新增权限类别可扩展 `privilege_type_to_variant` 映射；确保默认回退 `status-pill--muted`，防止超出 4 个语义色。
- **信息密度**：当角色/权限过多时切换为分页或折叠，而非增加色彩；必要时使用 `ledger-chip-stack` 的 `+N` 机制。
- **兼容性**：模态样式需兼容移动滚动条（尽管当前仅桌面端），确保 `max-height: 80vh` 与内部滚动生效。

## 推广
- 将该模式推广到其它弹窗（例如实例标签、调度日志详情），形成“弹窗组件指南”。
- 在 `docs/standards/color-guidelines.md` 的“组件级指导-状态与徽章”下追加案例截图，提醒所有权限/详情模态必须使用 chip/pill 体系。
