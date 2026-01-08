---
title: Layout Sizing Guidelines
aliases:
  - layout-sizing-guidelines
tags:
  - standards
  - standards/ui
status: draft
created: 2025-12-28
updated: 2026-01-08
owner: WhaleFall FE
scope: "`app/templates/**`, `app/static/css/**`, `docs/Obsidian/standards/ui/**`"
related:
  - docs/changes/refactor/012-no-inline-px-sizes-plan.md
  - "[[standards/ui/design-token-governance-guidelines]]"
  - "[[standards/halfwidth-character-standards]]"
---

# Layout Sizing Guidelines

## 目的

- 为页面框架, 容器, 表单控件, 列表/表格, 图表等提供一致的"尺寸语言", 避免每个页面单独发明宽高.
- 把尺寸决策从模板 inline style 与零散 CSS 中收敛到 Token + 组件 class, 让密度可调, 可审查, 可门禁.
- 明确桌面端主视口基线, 确保在 1920x1080 与 2560x1440 下的首屏信息密度可预测.

## 适用范围

- 页面框架: navbar, main content, footer, page header, page sections.
- 容器类: card, filter card, data panels, chart/table stage.
- 控件类: button, icon button, input/select, pagination.
- 列表类: Grid.js 表格, 传统 table, 详情列表.
- 图表类: Chart.js canvas 与其外层容器.

## 规则 (MUST/SHOULD/MAY)

### 1) 视口基线与验收截图 (MUST)

- MUST: 桌面端布局至少覆盖 2 个基线视口:
  - 1920x1080 (default review)
  - 2560x1440 (large screen)
- MUST: 禁止出现水平滚动条作为常态布局手段 (业务表格的横向滚动容器除外).

### 2) 页面框架宽度与 gutter (MUST)

- MUST: 页面内容必须包在 `.layout-shell > .layout-shell-inner` 内, 统一 gutter 与 max width.
- MUST: 仅在必要时切换宽度 tier, 并保持全站可检索:
  - default: `.layout-shell` (max width: `--layout-max-width`)
  - wide: `.layout-shell.layout-shell--wide` (max width: `--layout-max-width-wide`)
  - narrow: `.layout-shell.layout-shell--narrow` (max width: `--layout-max-width-narrow`)
- SHOULD: 表单类页面优先使用 narrow, 图表与多列信息密集页面可使用 wide, 其余默认 default.

### 3) 页面垂直节奏 (MUST)

- MUST: 页面内纵向分组使用 `.page-section`, 相邻 section 间距由 Token 控制 (`--page-spacing-regular` / `--page-spacing-tight`).
- MUST NOT: 用 "随手写 margin-top: 37px" 作为页面节奏方案. 如现有 Token 不满足, 先补 Token 再使用 (见 `design-token-governance-guidelines.md`).
  - 参考: [[standards/ui/design-token-governance-guidelines|设计 Token 治理]]

### 4) 尺寸单位与写法 (MUST)

- MUST: 关键布局尺寸必须由 "Token + class" 提供, 模板中禁止新增 `style="height: Npx"` / `style="width: Npx"`.
  - 例外: 仅允许非布局性质的微调 (例如 1px hairline) 且必须在代码评审中说明原因.
- SHOULD: 固定尺寸优先使用 `rem`, 响应式高度/宽度优先使用 `clamp()` 或 `min()/max()` 组合视口单位.
- MAY: 在第三方库强约束场景使用 `px` (例如渲染像素对齐), 但必须落在组件 CSS 内, 禁止回到模板 inline.

### 5) 控件尺寸 tier (SHOULD)

- SHOULD: 表单控件与按钮至少提供 2 套密度:
  - regular: 默认, 可读性优先
  - compact: 数据密集页面, 信息密度优先
- SHOULD: 通过 `data-density="regular|compact"` 驱动, 而不是每个页面单独改 padding.

### 6) 列表/表格密度 (MUST)

- MUST: 列表页的行高与操作按钮尺寸必须成套调整, 禁止只缩字不缩 padding, 或只缩 padding 不缩点击面积.
- SHOULD: Grid.js 表格沿用 `app/static/css/components/table.css` 的 compact 语义, 并把"行内操作"尺寸控制收敛到组件 CSS.

### 7) 图表容器高度 tier (MUST)

- MUST: 图表容器高度必须由组件 class 管理, 禁止模板 inline px.
- SHOULD: 图表容器至少提供 3 档高度, 并以 `clamp()` 控制桌面端在不同高度屏幕下的密度:
  - `.chart-stage--lg`: 用于主图/趋势图
  - `.chart-stage--md`: 用于辅助图
  - `.chart-stage--sm`: 用于小卡片内图表

### 8) Modal 与侧滑面板宽度 (SHOULD)

- SHOULD: Modal 宽度必须由 class 或 Token 决定, 禁止在模板中写 `style="width: ..."` 做布局.
- SHOULD: 以内容类型分 tier, 并在 1920x1080 与 2560x1440 下不遮挡关键操作:
  - sm: 确认/短表单
  - md: 常规 CRUD 表单
  - lg: 多 section 的复杂表单或详情

## 推荐的尺寸契约 (Reference)

说明: 以下是团队约定的推荐值, 作为实现与重构时的默认起点. 如需调整, 优先改 Token, 避免改 N 个页面.

### A) Page frame

- Navbar: fixed, 高度建议在一个可控 Token 中定义 (例如 `--layout-navbar-height`), main content 的 `margin-top` 与 `min-height` 必须与之匹配.
- Layout max width tiers (desktop 推荐值, 对齐 1920x1080 与 2560x1440):
  - default: `--layout-max-width: 1440px`
  - wide: `--layout-max-width-wide: 1920px`
  - narrow: `--layout-max-width-narrow: 1200px`
- Main content padding:
  - top: page spacing (不叠加 navbar 占位)
  - bottom: 至少 `--spacing-xl` 以避免 footer 挤压
- Page header:
  - icon size 建议 2.5rem tier, 标题与操作区在窄屏 (Bootstrap < lg) 自动换行.

### B) Controls

- Regular 控件高度建议: 2.5rem (40px) 左右, 保持可点击与可读.
- Icon button 建议:
  - md: 2.25rem
  - sm: 2rem
  - xs: 1.75rem
- 表格行内按钮:
  - height 建议不低于 28px, 并与行 padding 同步调整.

### C) Tables and lists

- 表头与单元格 padding 必须成对定义, 推荐以 spacing token 的倍数表达.
- Column width:
  - SHOULD: 优先通过 column id 规则或 colgroup/class 管理, 禁止在 th/td 上零散写 inline width.

### D) Charts

- 图表高度建议起点 (仅桌面端):
  - lg: `clamp(22rem, 50vh, 44rem)`
  - md: `clamp(18rem, 40vh, 36rem)`
  - sm: `clamp(14rem, 30vh, 28rem)`

## 正反例

### 正例: 用 class 管理 chart 高度

```html
<div class="chart-stage chart-stage--lg">
  <canvas class="chart-canvas"></canvas>
</div>
```

```css
.chart-stage--lg { height: clamp(22rem, 50vh, 44rem); }
```

### 反例: 模板 inline 固定 px

```html
<div style="height: 550px">
  <canvas style="height: 550px; width: 100%"></canvas>
</div>
```

## 门禁/检查方式

- 人工检查: PR review 时搜索 `style="` 并确认无新增 `height/width: Npx` 用于关键布局.
- 自查命令:
  - `rg -n \"style=\\\"[^\\\"]*(height|width)\\s*:\\s*\\d+px\" app/templates`
- 建议门禁:
  - 新增 `scripts/ci/inline-px-style-guard.sh` 扫描 templates 中的 inline px layout sizing, 阻止回归 (见 `docs/changes/refactor/012-no-inline-px-sizes-plan.md`).

## 变更历史

- 2025-12-28: 新增标准草案, 明确 page frame, controls, tables, charts 的 sizing contract, 为后续移除 inline px 与尺寸收敛提供依据.
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter, 并更新 standards 引用路径.
