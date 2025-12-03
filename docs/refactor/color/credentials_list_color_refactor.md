# 凭据管理页面色彩与交互重构方案

## 背景
- 页面：`app/templates/credentials/list.html`、`app/static/js/modules/views/credentials/list.js`、`app/static/css/pages/credentials/list.css`。
- 问题：页头按钮与筛选卡片仍然是亮色/浅灰混搭；Grid 中 `badge bg-success/bg-danger`、类型标签以及状态图标均重复使用高饱和语义色；删除确认、模态框按钮也沿用 `btn-danger`。整体与《界面色彩与视觉疲劳控制指南》、账户台账/实例管理试点方案不一致。

## 目标
1. 统一按钮、筛选、Grid 视觉——所有 chip、状态、标签均复用 `ledger-chip`、`status-pill` 组件，列宽策略与实例/台账保持一致。
2. 只保留一个主色 CTA（“添加凭据”），其余操作（导出、删除）使用描边 + 图标提示风险。
3. 清理 CSS/JS 中的硬编码颜色，全部改用 `app/static/css/variables.css` token。

## 设计策略
### 1. 页头/按钮
- `添加凭据` 改为 `btn-primary`，其余按钮（导入、导出、筛选）使用 `btn-outline-primary/btn-outline-secondary`。
- 删除确认模态的“删除”按钮可保留红色，但需使用 `status-pill--danger` 提示而非整块背景。

### 2. 筛选卡片
- 搜索/下拉列宽采用 `col-md-3 col-12`，确保留白；选中项展示 `ledger-chip`。
- 过滤按钮遵循“单主色”规则，清除 `btn-light`。

### 3. Grid 列
- 列宽设置：凭据名列弹性；类型列 110px；数据库类型列 110px；状态列 70px；标签/描述列 220px；操作列 90px。
- `renderCredentialType/renderDbType` 使用 `chip-outline`；状态列 `renderStatusPill('启用/停用', variant)`；敏感信息（例如“是否默认”）可使用 `status-pill--muted`。
- 操作列按钮统一 `btn-outline-secondary btn-icon`，点击后通过 toast 告知结果。

### 4. CSS 扩展
- 在 `credentials/list.css` 中引入公共 `ledger-chip`/`status-pill` 样式（或引用组件文件），删除 `badge-*`。
- 表格交替行、hover 背景与实例/台账保持一致。

## 实施步骤
1. **模板**：修改页头按钮、筛选器栅格，确保标签选择器使用新的 chip 样式。
2. **CSS**：导入公共样式，新增 `.credential-chip-stack` 等辅助类，移除旧 `.badge` 颜色。
3. **JS**：
   - 在 `credentials/list.js` 内实现 `renderChipStack`/`renderStatusPill`；
   - 更新列定义与宽度；
   - 操作列按钮事件传入触发元素，避免 loading 时界面跳色。
4. **QA**：检查多角色（管理员/只读）视图，确认色彩数 ≤7；运行 `./scripts/refactor_naming.sh --dry-run` 与相关 pytest。

## 风险与缓解
- **状态辨识**：从红/绿 badge 改为中性 pill，可能降低辨识度，可在图标上加 `fa-lock/fa-unlock` 并提供 Tooltip。
- **批量删除风险**：描边按钮可能让危险感下降，可在点击时弹出 `status-pill--danger` 提醒。

## 推广
- 将本方案链接到所有“管理列表”类页面 PR，要求遵循统一的 chip/pill 组件和单主色策略，确保界面体验一致。
