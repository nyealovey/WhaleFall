# 数据库实例管理页面色彩与栅格重构方案

## 背景
- 实例管理页 (`app/templates/instances/list.html` + `app/static/js/modules/views/instances/list.js` + `app/static/css/pages/instances/list.css`) 仍沿用多色徽章：数据库类型 `badge bg-*`、状态 `bg-success/danger`、活跃数双 badge、标签彩底等，单屏语义色 > 8，偏离《界面色彩与视觉疲劳控制指南》与账户台账试点的成果。
- 批量操作工具栏存在“outline-danger/outline-info/outline-success”等混色按钮，筛选卡片也缺乏统一 chip 样式，整体视觉节奏凌乱。

## 重构目标
1. 参考账户台账落地方案，将页面颜色控制在 2-3-4 规则内，状态/标签/类型全部复用 `status-pill`、`chip-outline`、`ledger-chip-stack` 组件。
2. 统一表格列宽：状态列 70px，类型列 110px，标签列 ≥ 220px，操作列 90px，确保视觉节奏一致。
3. 工具栏与筛选器仅保留一个主色 CTA（如“添加实例”），其余按钮使用描边或中性色，批量按钮根据操作危险度使用 icon + 文案而非颜色区分。

## 设计策略
### 1. 筛选与工具栏
- `filter_card` 内部：引用 `ledger-chip` 样式渲染已选标签、分类；搜索栏与下拉保持灰底。
- 页面 header 按钮参考账户台账：`实例统计` 改为 `btn-outline-primary`，`添加实例` 使用主色，批量按钮改为描边（危险操作可在 icon 上加 `text-danger` 提示）。
- selection summary 仅用文字 + `status-pill--muted`，不要再出现红/绿背景。

### 2. Grid 组件
- `renderDbTypeBadge` 改为 `chip-outline chip-outline--brand`，由 CSS 控制色彩。
- `renderStatusBadge` 改用 `status-pill`，文案统一为“正常/禁用”。
- `active_counts` 列由双彩色 badge 改为竖向数据栈：文本+中性图标或 `status-pill--muted`，并提供 Tooltip。
- `renderTags` 采用 `renderChipStack`（可复用账户台账实现），默认展示全部标签，必要时 `+N`。
- `renderActions` 中按钮统一为 `btn-icon btn-outline-secondary`，测试连接成功后用 toast 提示，不再使用绿色按钮。

### 3. CSS 调整
- 在 `app/static/css/pages/instances/list.css` 引入 `ledger-chip`、`status-pill` 等公共类（或直接引用公共文件），删除旧 `.stat-badge` 色值。
- 表格行交替背景与 hover 行为沿用账户台账：`color-mix(in srgb, var(--surface-muted) 10%, transparent)`。

## 实施步骤
1. **组件引入**：将 `ledger-chip`/`status-pill` 样式抽成公共文件并在 `instances/list.css` 中引用；JS 层引入 `renderChipStack` 工具（可直接复制账户台账实现）。
2. **Grid 列改造**：
   - 更新 `buildColumns` 中的 `width` 定义；
   - 替换 `renderDbTypeBadge`、`renderStatusBadge`、`renderTags`、`renderActions`、`active_counts` 渲染方式；
   - 统一文案（例如“测试连接”按钮 tooltip）。
3. **筛选卡片**：在 `filter_card` 模板中为 tag 选择器加 `col-md-6 col-12` 并使用新 chip 样式；清理 `btn-outline-*` 多色按钮。
4. **批量操作按钮**：按危险度提供 icon + 描边，必要时只在 icon 上加语义色；引用 `status-pill--danger` 作为删除确认提示。
5. **自检与回归**：
   - 浏览器检查首屏颜色数 ≤ 7；
   - 验证批量操作、导出、筛选交互；
   - 运行 `./scripts/refactor_naming.sh --dry-run` 与 `make test`（或 `pytest -k instances_list`）。

## 风险与缓解
- **用户辨识度下降**：对危险操作提供 icon + tooltip，而不是依赖背景色；必要时保留 `status-pill--danger`。
- **组件复用不足**：若其它页面还未引入 `ledger-chip`，在公共 CSS 中加命名空间（如 `.ledger-chip`）避免冲突。
- **批量按钮权限**：只读用户不展示批量按钮，避免空状态破坏布局。

## 推广
- 完成后在 `docs/standards/ui/color-guidelines.md` 的“案例”章节补充“实例管理”，并将本方案链接到相关 PR，供其它 CRUD 页面参考。
