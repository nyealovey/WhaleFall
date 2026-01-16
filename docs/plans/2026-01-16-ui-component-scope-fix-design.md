# UI Component Scope Fix Design

> **Goal:** 消除可复用组件固定 id，改为显式 scope 派生，避免同页多实例冲突并符合 DOM id 作用域标准。

## 背景与问题

- `permission_modal` 与 `tag_selector` 组件当前使用固定 id，违反 `component-dom-id-scope-guidelines.md` 的 MUST NOT。
- JS 侧通过全局 id 查询，导致多实例冲突与不可门禁化。

## 方案概述（显式 scope 传递）

- 模板 include 时显式传入 `permission_scope` / `tag_selector_scope`。
- 模板内部所有 id 由 scope 派生：`<scope>-modal`、`<scope>-modal-label`、`<scope>-body/title/meta`。
- 组件外层增加 `data-wf-scope="{{ scope }}"`，JS 仅在容器内查询。
- JS 调用时显式传 `scope`，不再依赖固定 id。

## 变更范围

### 模板

- `app/templates/components/permission_modal.html`
  - 新增 `permission_scope` 参数；外层添加 `data-wf-scope`。
  - `modal_id`/`modal_label_id` 与内部 id 改为 scope 派生。
- `app/templates/components/tag_selector.html`
  - 新增 `tag_selector_scope` 参数；外层添加 `data-wf-scope`。
  - `modal_id`/`modal_label_id` 改为 scope 派生。

### 页面 include

- `app/templates/accounts/ledgers.html`
  - `permission_scope=accounts-permission`
  - `tag_selector_scope=account-tag-selector`
- `app/templates/instances/detail.html`
  - `permission_scope=instance-permission`
- `app/templates/instances/list.html`
  - `tag_selector_scope=instance-tag-selector`
- `app/templates/databases/ledgers.html`
  - `tag_selector_scope=database-tag-selector`

### JS

- `app/static/js/modules/views/components/permissions/permission-modal.js`
  - `showPermissionsModal(permissions, account, { scope })`。
  - `ensurePermissionModal` 按 scope 缓存实例，`modalSelector` 使用 `#${scope}-modal`。
  - 内容更新与 reset 使用容器内查询。
- `app/static/js/modules/views/components/permissions/permission-viewer.js`
  - `viewAccountPermissions` 透传 `scope`。
- `app/static/js/modules/views/instances/detail.js`
  - 调用 `viewAccountPermissions(accountId, { scope: instance-permission })`。
- `app/static/js/modules/views/components/tags/tag-selector-controller.js`
  - `setupForForm/setupForFilter` 默认 `modalSelector` 改为 `#${scope}-modal`（若传 scope）。
- `app/static/js/modules/views/accounts/ledgers.js`
- `app/static/js/modules/views/instances/list.js`
- `app/static/js/modules/views/databases/ledgers.js`
  - `TagSelectorHelper.setupForForm` 明确传 `modalSelector`（基于 scope 派生）。

## 错误处理

- 缺少 scope 或容器未找到时 fail-fast（`console.error` + return），避免半初始化。
- 保持现有 `UI.createModal` 异常路径。

## 验证策略

- 在同页插入两个权限弹窗与标签选择器实例，确认打开/关闭与渲染互不干扰。
- 运行：`rg -n "permissionsModal|tagSelectorModal" app/static/js app/templates`，确保固定 id 被移除。
- 验证 modal aria 关联正确，按钮关闭行为正常。

## 备选方案

- 自动派生 scope（由 page_id 或 DOM 结构推导）被拒绝：不可控且难审查。
- 仅改 data-role 不改 scope 被拒绝：不符合标准的 MUST。
