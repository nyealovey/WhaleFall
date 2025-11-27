# 筛选表单宽度统一重构提案

> 目标：让所有页面的搜索框与“数据库类型/状态”等下拉框在视觉上保持一致宽度与高度，避免当前 150px 固定宽度导致的割裂感。

## 现状分析

- `components/filters/macros.html` 中的 `search_input` 宏在 `filter-common.css` 里被 `.filter-search-input` 强制设置为 150px 宽度；下拉框 (`select_filter` 等) 则根据栅格列宽度自适应。
- 在“数据库实例管理”等页面，为了视觉统一额外加粗下拉框边框（如 `.filter-form .form-select` 自带 2.5rem 高度）。但搜索框窄且无法与下拉框对齐。
- 多个页面共享 `filter_card`（实例、账户、标签、台账等），因此需要一套统一策略，而不是在每个页面单独 hack。

## 重构原则

1. **移除固定宽度**：删除 `.filter-search-input { width: 150px; }` 等强制属性，改由栅格 (`col-*`) 控制宽度。
2. **统一列宽**：在 `filter_card` 调用处为搜索、下拉框设置相同 `col_class`（如 `col-md-3`），并在移动端依旧占满全宽。
3. **高度/边框一致**：`filter-form .form-control` 与 `.form-select` 已保持 2.5rem 高度，如有自定义（如实例页的状态下拉高亮），需通过 `:focus`、`:hover` 状态统一。
4. **渐进式替换**：先在全局 CSS 中移除固定宽度，再逐页确认没有布局回归；若个别页面需要窄版搜索框，改为在局部添加 utility class。

## 预期影响页面

- 数据库实例/账户/凭据/标签台账等所有使用 `filter_card` 的页面。
- 相关 CSS：`app/static/css/components/filters/filter-common.css`、页面私有样式（如 `instances/list.css`）。
- 触发式脚本：`FilterCard` 组件无需修改，但要确保 `autoSubmit` 行为不受影响。

## 执行步骤

1. 删除 `.filter-form .filter-search-field { ... }` 和 `.filter-form .filter-search-input { width:150px; }` 等全局宽度设置。
2. 在常用过滤器宏（如 `search_input`、`db_type_filter`）中默认使用相同 `col_class` (`col-md-3 col-12`)，并在各页面适配布局。
3. 检查所有使用 `search_input` 的页面，确保未覆盖新的样式；若有特殊布局（如仪表板），在局部 CSS 中添加 `max-width`。
4. 设计验收：在 1440px 和 1024px 视口下对比“数据库实例管理”、“数据库台账”、“账户台账”等页面，确认搜索框/下拉框等宽并保持对齐。
5. 文档更新：在 `AGENTS.md` 的命名/样式规范中补充“filter 卡片中的搜索与下拉需使用统一列宽，不得再单独设定固定像素宽度”。

## 验收指标

- 所有 filter 卡片的搜索框宽度与相邻下拉框一致（通过截图对比）；
- Lighthouse/Chrome DevTools 检查无横向滚动/溢出；
- `make quality` & `./scripts/refactor_naming.sh --dry-run` 通过。

## 对齐节点

- **Day 1**：移除全局固定宽度、更新 CSS；
- **Day 2**：逐页验证，处理页面特例；
- **Day 3**：终审 + 文档更新。
