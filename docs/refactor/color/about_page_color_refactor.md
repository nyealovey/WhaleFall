# 关于页面色彩与组件重构方案

## 背景
- `app/templates/about.html` 仍大量使用 Bootstrap 默认色（`bg-primary/bg-success/bg-info/bg-secondary`、`text-danger`、`text-warning` 等）与 `text-white` 覆盖色，单屏彩色元素 > 12，远超《界面色彩与视觉疲劳控制指南》（`docs/standards/color-guidelines.md`）提出的“色彩 2-3-4 规则”。
- 版本时间线与功能列表使用 `text-primary`、`text-info` 图标手动着色，没有复用 `status-pill`、`chip-outline`、`ledger-chip-stack` 组件，也未使用 token 暴露语义，导致颜色语义与其它页面不一致。
- 卡片 header 采用纯色实底 + 反白文本，且页面左侧存在 `text-white` 标题、彩色 ICON，整体视觉与仪表盘基线（白底卡片 + pill/chip 体系）偏差明显，难以延续品牌一致性。

## 重构目标
1. 将关于页面统一到仪表盘视觉基线，严格遵守“主色 ≤ 2、辅助色 ≤ 3、语义色 ≤ 4”约束，剔除所有 `bg-*`、`text-*` 直接着色，全部改用 `variables.css` token。
2. 复用既有组件：模块标签采用 `chip-outline`，版本时间线使用 `ledger-chip-stack` 和 `status-pill` 承载日期/版本状态，信息提示统一 `status-pill--info|muted`。
3. 调整模板与 CSS，使卡片结构、排版、图标、阴影均与 Stats Cards 策略一致（白底 + 描边 + `--shadow-sm`），并确保未来版本更新只需维护数据结构而非样式。

## 设计策略
### 1. 页面骨架与栅格
- 保持现有左右两列结构，但移除 `.col-6` 上的深色背景与 `text-white`，父层改用标准容器 + `section-header`（标题 `var(--text-primary)`，副标题 `var(--text-muted)`）。
- 左列顶部 logo 与标题改为白底卡片：Logo 保持灰阶滤镜，标题用 `chip-outline chip-outline--brand` 或 `status-pill--info` 标注版本口号，避免单独的 `text-white`。

### 2. 信息卡片（项目介绍/核心功能/技术栈/支持数据库）
- 所有卡片 header 去掉彩色背景，统一用 `card-subtitle` + `chip-outline` 标识模块类型；若需要强调（如“项目介绍”），仅允许使用 `var(--accent-primary)` 作为 1 个主色。
- 功能列表中的图标改为 `status-pill` + 图标栈，`status-pill` 背景透明 20%，文本 ≤ 4 字；列表 bullet 使用中性文本，禁止再为不同类别着色。
- “支持的数据库”区块改成自适应网格：每个数据库名配 `chip-outline` + 单色线框图标（`--text-muted`），用 `ledger-chip-stack` 表示存在多种版本/Edition。

### 3. 版本时间线
- 使用 `ledger-chip-stack` 表示版本标签（芯片展示版本号、`status-pill--muted` 展示日期），并将摘要文本保持 `var(--text-muted)`。
- 提供“最新版本”聚合卡：复用 Stats Card 模板，突出当前版本/发布日期，辅助信息用 `status-pill--info`（如“聚焦 CRUD”），保证右列仍遵循 2-3-4 规则。
- Scroll 区域背景保持白色，使用 `color-mix` 10% 交替行区分条目，符合“列表与卡片”段落要求。

### 4. CSS 与 token 管理
- 将现有 `bg-*`、`text-*` 删除，统一引用 `app/static/css/variables.css` 中的 token（`--accent-primary`、`--surface-muted`、`--text-muted` 等）。
- 使用公共组件样式：在 `about.css` 中仅做排版/动画控制，所有 chip/pill/卡片视觉从 `components/` 导入，确保未来改动受单点控制。
- 引入 `color-mix` 提供 hover/交替行效果，透明度遵循指南（20%/10%）。

## 实施步骤
1. **模板拆分**：重写 `app/templates/about.html` 的卡片 header，移除 `bg-*` 与 `text-*` 类，插入 `chip-outline`、`status-pill`、`ledger-chip-stack` 组件；更新版本时间线循环，输出组件化结构。
2. **数据结构调整**：为 `version_timeline` 增加字段（如 `type`, `status`），便于映射到 `status-pill` 变体；最大 4 行展示 `status-pill--danger`/`--warning` 等语义色，并仅在确有对应语义时启用。
3. **CSS 清理**：整理 `app/static/css/pages/about.css`，删除对 `.card-header` 的彩色定义，增加对 `section-header`、logo 卡片、时间线条目的排版控制，并从公共组件样式中导入 chip/pill。
4. **自检脚本**：执行 `rg -n "bg-" app/templates/about.html`、`rg -n "text-" app/templates/about.html` 确认无 Bootstrap 彩色类；运行 `./scripts/refactor_naming.sh --dry-run` 以及 `make quality`，确保命名与 lint 通过。

## 风险与缓解
- **品牌识别度下降**：关于页承担品牌展示，可在 hero 区保留单个 `var(--accent-primary)` 主色，并以插画/照片建立差异；如需第二主色，须在设计评审会登记。
- **组件依赖缺失**：若 `chip-outline`、`ledger-chip-stack` 未在 about 页面打包，需要在入口 JS/CSS 中显式引入公共组件，避免构建时被 tree-shaking；同时在模板中添加容错（组件缺失时 fallback 为文本）。
- **时间线可读性**：大量版本会导致纵向滚动，需控制高度 600px 并启用柔和滚动；若依旧拥挤，可按季度折叠或分页，避免再用颜色区分层级。

## 推广
- 将本页面重构经验同步到 `docs/standards/color-guidelines.md` 的“实施步骤”案例列表，提醒所有品牌/宣传类页面同样遵循 2-3-4 规则。
- 在后续新建的“关于/品牌/介绍”模板中预置 chip/pill 写法，减少彩色类回流；对营销页面也执行 `make quality` + HEX 扫描，防止硬编码颜色再度出现。
