# 用户管理页面色彩与表格重构方案

## 背景
- 页面：`app/templates/auth/list.html`、`app/static/js/modules/views/auth/list.js`、`app/static/css/pages/auth/list.css`。
- 现状：页头按钮使用 `btn-light`、筛选器为默认 Bootstrap 风格；Grid 中角色/状态/操作按钮仍采用 `badge bg-*` 与多色按钮。与《color-guidelines》以及账户/实例台账重构不一致。

## 目标
1. 统计卡（若存在）及操作按钮仅保留 1 个主色，其余使用中性描边；
2. 角色/状态/标签列复用 `chip-outline`、`status-pill`；列宽与其它 CRUD 页面一致（状态 70px、角色 110px、标签 220px、操作 90px）；
3. 模态与表单组件无硬编码颜色，手动校验命名脚本通过。

## 设计策略
### 1. 页头/筛选
- `用户管理` 页头按钮（新增用户/导出）分别使用 `btn-primary` 与 `btn-outline-primary`；
- 筛选卡片 `col-md-3 col-12` 栅格，选中的角色/状态在预览区显示 `ledger-chip`。

### 2. Grid 列
- `renderRole` 输出 `chip-outline`（角色名称 + 图标），`renderStatus` 输出 `status-pill`（激活/禁用）。
- 多重标签（权限、所属组）使用 `ledger-chip-stack`。
- 操作列按钮为 `btn-outline-secondary btn-icon`，危险操作在确认环节提示。

### 3. 模态
- 新建/编辑用户模态中的状态提示使用 `status-pill--muted`，提交按钮保留主色。

## 实施步骤
1. **CSS**：导入公共 chip/pill 样式，删除 `.badge-*`、`text-*` 定义。
2. **JS**：在 `auth/list.js` 中实现 `renderStatusPill/renderChipStack`，调整列宽与渲染；
3. **模板**：更新按钮类名，与色彩指南一致。
4. **验证**：色彩数量 ≤7，`./scripts/refactor_naming.sh --dry-run` 通过，运行用户管理相关测试。

## 风险
- 角色区分依赖颜色，去色后可通过图标/文字提示补足（如 `fa-shield` 表示管理员）。

## 推广
- 方案可推广到权限/凭据等页面，形成统一的后台管理视觉标准。
