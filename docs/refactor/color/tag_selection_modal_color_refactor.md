# 选择标签（Tag Selection Modal）色彩与交互重构方案

## 背景
- 组件：`app/templates/components/tag_selector.html`、`app/templates/components/filters/macros.html` 中 `tag_selector_filter` 宏、`app/static/js/modules/views/components/tags/tag-selector-{view,controller}.js`、`tag-selector-modal-adapter.js` 以及 `app/static/css/components/tag-selector.css`，并被账户、数据库、实例等页面复用。
- 截图（2025-12 桌面端）显示：模态页头为高饱和橙色，分类按钮使用 `btn` + 手写像素滚动条，统计区和列表充斥 `badge text-bg-light`、`bg-light`、`text-danger` 等硬编码色，单屏非图表颜色达到 10+，已经偏离《界面色彩与视觉疲劳控制指南》的 2-3-4 规则与 Dashboard 基线。
- 痛点：
  1. 已选标签区用 `bg-light` 容器与 `badge bg-*`/HEX，自定义颜色难以回收，chip 无统一尺寸。
  2. 分类筛选是横向 radio + `.btn`，滚动条颜色被直接写入，且 hover/active 与语义色混用。
  3. 统计条的 `badge text-bg-light` 与 `text-success` 混搭，信息层级依赖颜色深浅而非字重。
  4. 列表项高亮通过 `bg-primary` 与渐变实现，`disabled` 仅靠透明度，缺乏 token；外部 `filter_card` 入口在部分页面传 `col-md-6 col-12` 并渲染 `badge`，违反“列宽固定 + 使用 chip-outline/ledger-chip 展示选中项”的准则。

## 目标
1. 单屏非图表可视色彩 ≤7，所有背景/描边/状态色均来自 `app/static/css/variables.css` token，并复用 `status-pill`、`chip-outline`、`ledger-chip` 体系。
2. 统一交互行为：筛选器、已选区、列表 hover/active 仅用描边/字重表达状态，保留一个 `btn-primary` CTA（确认），其它按钮 `btn-outline-secondary`/`btn-icon`。
3. 组件复用化：`TagSelectorHelper` 对外暴露 `open/close/update` 时不再注入内联颜色；`tag_selector_filter` 入口固定 `col-md-2 col-12` 且 preview chip 走 `ledger-chip`。
4. 质检可复用：加入色彩自检脚本、命名脚本以及组件 checklist，确保未来任何页面嵌入 Tag Selector 都遵循指南。

## 设计策略
### 1. 结构与视觉基线
- Modal 外壳沿用《系统仪表盘色彩与交互重构方案》的白底 + 淡描边 + `--shadow-md`，头部图标改 `text-muted`，避免额外高饱和背景。
- 内容区域按“已选 → 分类筛选 → 统计 → 标签列表”分区，所有 section 顶部标题使用 12px/`var(--text-muted)`，区块留白与 Dashboard Widget 持平。
- 整体禁用移动端 @media，保持桌面栅格。

### 2. 已选标签区
- 使用 `ledger-chip-stack` 组件呈现选中项；chip 文字 12px，使用 `chip-outline--brand`（系统标签）或 `chip-outline--muted`（自定义）。
- 删除 `bg-light` 容器，替换为 `surface` token（`var(--surface-elevated)`）+ `var(--gray-200)` 描边 + 8px 圆角；空状态展示 `status-pill status-pill--muted`。
- 删除 `btn-close-white`，改为 `btn-icon btn-icon--sm` 放置在 chip 内（icon 使用 `--text-muted`），响应 hover 仅改变描边。

### 3. 分类切换与筛选
- Radio 列表改为 `chip-outline` 风格，可水平滚动，但滚动条颜色使用 `color-mix + token`，禁止 HEX。
- 默认包含“全部/公司/其他...”等 8 类；控件以 `chip-outline chip-outline--muted` 表达，选中态 `chip-outline--brand`，激活状态通过 `fw-semibold` 与双描边体现，不改变背景色。
- 过滤器顶部 label + helper text 说明“共 X 类”，保持 `col-md-12` 宽度；额外筛选（搜索、标签类型）统一为 `btn-outline-secondary btn-icon` 触发的下拉。

### 4. 统计区
- 四个指标使用 `tags-stat-card` 样式（参考 Dashboard Stats）：白底描边卡片 + `status-pill` 表示数值趋势；数据值 `data-value-tone` 控制字色（`muted|info|success|danger`）。
- badge 体例改为 `chip-outline`，展示“总标签/已选择/已激活/当前可见”，数字使用 `NumberFormat`，并在空数据时隐藏整块 section。

### 5. 标签列表
- 列表元素替换为 `list-group` + `ledger-row` 组合：左右两列（主信息、操作），主信息包含名称 + 描述 + `chip-outline` 分类 + `status-pill` 状态（启用/停用/草稿），不再使用 `badge bg-*`。
- 行 hover 使用 `color-mix(in srgb, var(--surface-muted) 10%, transparent)`；active/选中行 `15%`。禁用行增加 `opacity: 0.6` + `cursor-not-allowed`。
- “标签”按钮换成 `btn-outline-secondary btn-icon`（比如“查看”“应用”），危险动作仅在 icon 上增加 `text-danger`。
- 搜索匹配高亮通过 `background-color: color-mix(in srgb, var(--info-color) 20%, transparent)`，禁止使用 `var(--warning-color)` 造成误导。

### 6. filter_card 入口与多页面复用
- `tag_selector_filter` 固定 `col_class='col-md-2 col-12'`，特殊布局需在页面注释说明理由。入口按钮使用 `btn-outline-primary` + `btn-icon`，下方 preview 区走 `ledger-chip-stack`，并展示 `+N` 超量逻辑。
- 组件开放 `data-tag-selector-scope` 属性，`TagSelectorHelper.setupForForm/setupForFilter` 根据 scope 在不同页面共享状态；helper 输出 chip 数据时仅携带 token 名称，禁止传递颜色值，全部交给 view 中的 token→class map 处理。

## 实施步骤
1. **模板**  
   - 重写 `tag_selector.html`：引入 `ledger-chip`、`chip-outline`、`status-pill` 片段（可 include 共用宏），删除所有 `badge text-bg-light`。  
   - 更新宏 `tag_selector_filter`，新增 `selected_tags_preview()` 辅助，将旧 badge 改为 `ledger-chip`，并提供 `data-tag-name`、`data-tag-scope` 供 JS 控制。  
   - modal footer：主 CTA `btn-primary`，取消 `btn-outline-secondary`，附加 tooltip 提示“仅桌面端”满足响应式限制。
2. **CSS**  
   - 将 tag selector 样式迁入 `app/static/css/components/tag-selector.css`，但引用 `status-pill`/`ledger-chip` 变量，不再定义新的颜色。  
   - 删除 `--tag-selector-min-selected-height` 或改为 `var(--spacer-6)`；滚动条/hover/active 使用 token。  
   - 增补 `.tag-selector__categories`、`.tag-selector__stats` 的栅格和阴影，禁止写死像素宽度。
3. **JS**  
   - `tag-selector-view.js`：移除 `resolveBadge`，改为 `resolveChipVariant(tag)` 返回 `chip-outline--brand|muted|custom`；`renderSelectedTags`/`renderTagList` 使用 ledger-chip/status-pill DOM 模板。  
   - 将分类、统计、列表 DOM 渲染统一成纯 class + data 属性，无内联颜色；`orderTags` 后根据 `is_active` 映射 `status-pill` variant。  
   - `tag-selector-controller.js` 与 `TagSelectorHelper`：对外 API 仅接受标签 id/名称；当 filter preview 更新时，使用公共 `renderChipStack(container, tags)` 函数，复用凭据/仪表盘实现。
4. **QA 与质检**  
   - 开发自检：执行 `./scripts/refactor_naming.sh --dry-run`、`rg -n '#[A-Fa-f0-9]{3,6}' app/templates/components/tag_selector.html app/static/css/components/tag-selector.css`，确保无硬编码颜色。  
   - 手测：桌面端全屏/窄屏宽度下，统计卡、列表、chip 颜色 ≤7；`filter_card` 中标签入口保持 `col-md-2 col-12`。  
   - 自动化：补充 `tests/unit/tags/test_tag_selector_helper.py`（如已有），验证 helper 输出不带颜色值；UI 层依赖现有集成测试或添加 Cypress 脚本模拟打开模态并勾选标签。

## 风险与缓解
- **标签过多导致 chip 堆叠溢出**：使用 `ledger-chip-stack` 的 `max-visible` 属性（默认 3），溢出以 `+N` 展示，并提供 tooltip 显示完整列表。
- **旧页面未加载新组件样式**：在 `base.html` 中集中引入 `components/tag-selector.css`，并在 PR checklist 中要求验证 `accounts/databases/instances` 页面；必要时添加特性旗 `data-tag-selector-version="2025Q4"` 渐进切换。
- **激活状态不够明显**：在 `TagSelectorView` 中为选中行添加 `aria-selected` + `fw-semibold` 文本，必要时在 `status-pill` 内加入 `fa-check` 图标，保持可访问性。

## 推广与后续
- 将本方案列入《界面色彩与视觉疲劳控制指南》附录，新增“标签选择器”章节，说明所用 token、组件、列宽；任何新页面调用 Tag Selector 时需引用此文档 checklist。
- 抽象 `renderLedgerChipStack`、`renderStatusPill` 到 `app/static/js/modules/components/shared/ui_helpers.js`，Tag Selector/凭据/实例共享，减少重复。
- 在 PR 模板加入“Tag Selector 自检”小节：需粘贴 `./scripts/refactor_naming.sh --dry-run` 与 `rg '#` 扫描结果，并说明筛选列宽是否存在例外。
