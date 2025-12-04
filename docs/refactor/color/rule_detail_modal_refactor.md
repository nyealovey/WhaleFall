# 规则详情弹窗色彩与组件重构方案

## 背景
- 当前“规则详情”弹窗仍沿用旧版 UI：纯橙色头部 + 白底内容 + 彩色按钮块，与《界面色彩与视觉疲劳控制指南》（`docs/standards/color-guidelines.md`）所要求的 2-3-4 规则不符，页面一屏出现 10+ 彩色元素。
- 权限配置面板使用 `btn` + `badge` 手写渐变，未复用 `chip-outline`、`status-pill` 等公共组件；状态/分类标签缺乏 token 映射，不便统一调色和主题切换。
- 信息布局混乱：字段对齐靠 `table-row` 样式拼凑，缺少分组标题和留白，移动鼠标时还会因`btn` hover 改色而分散注意力。

## 重构目标
1. 将规则详情弹窗统一至仪表盘视觉基线：主色仅保留 `var(--accent-primary)`，辅助色≤3、语义色≤4，全部引用 `variables.css` token，无硬编码 HEX。
2. 使用公共组件栈：基础信息区采用 `chip-outline` 标识字段，状态/分类/逻辑等字段以 `status-pill` 呈现；权限配置列表使用 `ledger-chip-stack` 展示权限类型，禁用彩色 `btn`。
3. 调整排版与可读性：保留原有字段结构顺序，但为每组信息提供 `section-card`，统一间距与分隔线，同时在空状态提供 `status-pill--muted` 提示。

## 设计策略
### 1. 模态骨架
- 顶部改为白底 + `chip-outline chip-outline--brand` 标题“规则详情”，右侧 `status-pill--info` 显示分类或命中范围，`status-pill--muted` 显示数据库类型。
- 主体背景使用 `color-mix(in srgb, var(--surface-muted) 6%, var(--surface-elevated))`，圆角 `var(--border-radius-lg)`，阴影 `var(--shadow-sm)`，与账户弹窗一致。

### 2. 基础信息区
- 按“规则名称/分类/数据库类型/匹配逻辑/状态/创建/更新时间”拆分为两列 `definition-grid`，每个字段使用 `chip-outline--muted` + 文本，状态字段改为 `status-pill`（启用=success，禁用=muted，草稿=warning）。
- 匹配逻辑（AND/OR）使用 `status-pill--info`，附备注 `chip-outline--ghost` 说明“任一条件满足即可”。

### 3. 权限配置
- 将“全局权限/数据库权限”等条目重构为 `permission-section`：左侧 icon + `chip-outline` 展示维度，右侧 `ledger-chip-stack` 显示具体操作（DROP/ALTER 等）。
- 若该维度为空，显示 `status-pill status-pill--muted`（如“无全局权限”）。
- 多个权限块使用 `permission-stack-row` 垂直排列，避免彩色按钮。

### 4. 样式与交互
- 新增 `app/static/css/pages/rules/detail.css` 或复用 `change-history.css` 模板，只定义布局/间距；所有颜色来自 token。
- 模态按钮保持 `btn-outline-secondary`，hover 用 `var(--accent-primary-ring)` 构建视觉反馈。
- 添加 `status-pill status-pill--danger` 提示“规则停用”或“风险规则”，避免再使用大面积红色背景。

## 实施步骤
1. **模板调整**：更新 `app/templates/rules/detail.html`（若无则对应组件）——替换 header、基础信息布局与权限面板 HTML，引入 chip/pill 结构，删除 `bg-*`、`btn` 彩色类。
2. **样式文件**：在 `app/static/css/pages/rules/detail.css` 中定义 `.rule-detail-modal`、`.definition-grid`、`.permission-section` 等布局；在 `base.html` 或模块模板中按需引用。
3. **JS 渲染**：若数据由 JS 渲染，更新 `rule-viewer.js`（或同类文件）以输出新结构，并将状态/分类映射到 `status-pill` 变体；提供空状态 fallback。
4. **自检**：运行 `rg -n "bg-" app/templates/rules/detail.html`、`rg -n "#" app/templates/rules/detail.html` 确认无硬编码颜色；执行 `./scripts/refactor_naming.sh --dry-run` 与 `make quality`。

## 风险与缓解
- **权限列表长度**：若权限配置过多，需限制单屏高度并在 section 内部滚动，防止 modal 过长；同时可合并同类权限为 chip stack。
- **历史浏览器**：新样式依赖 `color-mix`，需在旧版浏览器提供 fallback（可设置半透明背景色作为后备）。
- **数据缺失**：若某些字段后端未返回，前端要显示 `status-pill--muted` 提示，避免空白区域。

## 推广
- 将此方案作为“规则/策略类弹窗”模板，推广到账户策略、调度策略等页面，形成统一视觉语言。
- 在 `docs/standards/color-guidelines.md` 的“组件级指导-状态与徽章”章节附上“规则详情”示例，提醒后续新增策略页面复用该结构。
