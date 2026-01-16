> Status: 完成
> Owner: Codex
> Created: 2026-01-16
> Updated: 2026-01-16
> Scope: `docs/Obsidian/standards/ui/**` + `app/static/js/**/*.js`(排除 `app/static/vendor/**`) + `app/templates/**/*.html` + `app/static/css/**/*.css`
> Related: `docs/Obsidian/standards/ui/README.md`, `docs/Obsidian/standards/ui/layer/README.md`, `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md`, `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md`, `docs/Obsidian/standards/ui/vendor-library-usage-standards.md`

# 前端/UI 标准全量审计报告 (2026-01-16)

## 1. 目标

- 全量梳理 `docs/Obsidian/standards/ui/**` 的可执行约束与冲突/歧义
- 使用 JS AST + Jinja2 AST 作为主证据源，定位前端代码违规点
- 盘点防御/兼容/回退/适配逻辑，重点关注 `||`/`??`/`or` 兜底
- 输出可修复建议与验证方式

## 2. 审计方法与证据

### 2.1 已执行的仓库门禁脚本

- 未执行门禁脚本（本次为只读审计）。

### 2.2 已执行的补充静态扫描

- `rg -n "document\\.querySelector" app/static/js`（辅助定位 DOM 访问点）
- `rg -n "message\\s*\\|\\|" app/static/js/modules`（辅助定位兜底链，交叉验证 AST 结果）
- 自定义临时脚本（不落盘）：CSS Token 定义/引用一致性检查、HEX/RGB 硬编码检查
- 测试（按用户要求）：`uv run pytest -m unit`

### 2.3 AST 语义扫描

- JS：使用 `espree` 解析 `app/static/js/**/*.js`（排除 `app/static/vendor/**`），开启 `loc`，记录 `loc.start.line/loc.end.line`。
- Jinja2：使用 `jinja2.Environment().parse` 解析 `app/templates/**/*.html`，记录 `nodes.lineno`。
- 扫描规则（核心）：
  - JS：`LogicalExpression`(`||`/`??`)、`ConditionalExpression`、`TryStatement`、guard clause（`if (!x) return`）、`document.querySelector/getElementById`、`window.*` 访问、`innerHTML` 赋值。
  - Jinja：`Or` 表达式、`default` filter、`CondExpr`、`TemplateData`/`Const` 中的 `id=...`、`btn-close`、`on*=`、`style="height/width: Npx"`。
- 结论中的行号均来自 AST 节点的 `lineno` 或 `loc`。

### 2.4 约束索引(可执行约束)

| 约束(简述) | 位置 | 影响范围 | 典型反例/说明 |
|---|---|---|---|
| 可复用组件禁止固定 `id`，必须提供 scope 容器并派生内部 `id` | `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33-45` | `app/templates/**` + `app/static/js/**` 的可复用组件 | 固定 `id="tagSelectorModal"` 或全局 `#permissionsModalBody` 导致多实例冲突 |
| 异步/批量任务必须使用 `UI.resolveAsyncActionOutcome`，禁止 `message || error` 兜底链 | `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:43-44` | 触发异步任务/批量操作的 JS 入口 | 在 view 内直接 `response?.message || '失败'` |
| 模板内联事件处理器禁止 | `docs/Obsidian/standards/ui/template-event-binding-standards.md:34-35` | `app/templates/**` | `onclick="..."` |
| `btn-close` 必须 `aria-label="关闭"` | `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:31-33` | Alert/Modal/Toast | `aria-label="Close"` |
| 模板禁止 `style="height/width: Npx"` | `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:60-61` | `app/templates/**` | 模板内联 `height: 320px` |
| 颜色字面量仅允许出现在 `variables.css` | `docs/Obsidian/standards/ui/color-guidelines.md:38-39` | `app/static/css/**` | 组件 CSS 中硬编码 `#ff5a00` |

## 3. 标准冲突或歧义

- **DOM 入口口径不一致**：`vendor-library-usage-standards` 要求 DOM 操作必须走 `window.DOMHelpers` (`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:134`)，但 `views-layer-standards` 允许原生 `addEventListener` 与 DOM 操作 (`docs/Obsidian/standards/ui/layer/views-layer-standards.md:60-61`)，造成“是否允许直接 `document.querySelector`”口径不一致，易导致实现分裂与额外的兼容/回退包装。
- **vendor global 允许 vs 必须封装**：`layer/README` 的 Views allowlist 明确允许 vendor globals (`docs/Obsidian/standards/ui/layer/README.md:79-83`)，但 `vendor-library-usage-standards` 又要求“业务代码不得直接调用 vendor global” (`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:29-32`)。该冲突会让代码在“直用 vendor”与“封装入口”间摇摆，导致升级策略与 fallback 链条不一致。
- **颜色字面量与局部 Token 的边界模糊**：颜色标准禁止 `variables.css` 之外出现 HEX/RGB (`docs/Obsidian/standards/ui/color-guidelines.md:38-39`)，而 Token 治理允许组件局部变量 (`docs/Obsidian/standards/ui/design-token-governance-guidelines.md:34-35`)；未明确“局部 Token 是否可以包含颜色字面量”，可能引发实现分裂（有人在组件中用局部色值，有人强行提升到全局 Token）。
- **“可复用组件”范围未明示**：`component-dom-id-scope-guidelines` 未说明“全局唯一单例组件”是否豁免（例如危险确认弹窗）。导致不同页面/组件对固定 `id` 采取不同策略，增加后续迁移时 `||/or` 兜底与 selector 兼容链。

## 4. 不符合标准的代码行为(需要修复)

### 4.1 TagSelector 组件使用固定 `id` 且缺少 `data-wf-scope`

- 结论：TagSelector 组件未提供 `data-wf-scope` 容器，且使用固定 `modal_id`/`modal_label_id`。
- 标准依据：`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33-45`
- 代码证据：`app/templates/components/tag_selector.html:57`, `app/templates/components/tag_selector.html:59`, `app/templates/components/tag_selector.html:60`
- 影响：同页多实例时 `id` 冲突，事件/渲染可能命中错误实例；后续只能通过增加选择器 fallback 链缓解。
- 修复建议：为组件最外层增加 `data-wf-scope`（或 `<scope>-container`），派生 `modal_id`/`modal_label_id`；调用方传入 scope，JS 在容器内查找节点。
- 验证方式：`rg -n "tagSelectorModal" app/templates/components/tag_selector.html` 确认固定 id 消除；复跑 AST 检查确保存在 `data-wf-scope`。

### 4.2 PermissionModal 组件固定 `id` + 全局选择器

- 结论：权限模态组件内部与 JS 侧均使用固定 `id`/全局选择器，违反 scope 约束。
- 标准依据：`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33-45`
- 代码证据：`app/templates/components/permission_modal.html:3`, `app/templates/components/permission_modal.html:18`, `app/templates/components/permission_modal.html:19`, `app/templates/components/permission_modal.html:20`, `app/static/js/modules/views/components/permissions/permission-modal.js:143`, `app/static/js/modules/views/components/permissions/permission-modal.js:171`, `app/static/js/modules/views/components/permissions/permission-modal.js:182`
- 影响：多实例共存时更新错位；组件复用受限，易产生兼容分支。
- 修复建议：改为 `data-wf-scope` + 派生 `id`；JS 侧先定位容器，再在容器内选择节点；避免全局 `#permissionsModal*`。
- 验证方式：`rg -n "permissionsModal" app/static/js/modules/views/components/permissions/permission-modal.js` 应只剩 scope 派生字段；组件模板中不再出现固定 `id`。

### 4.3 过滤器宏固定 `id`（可复用组件）

- 结论：`instance_filter` / `database_filter` 宏使用固定 `id`，与“可复用组件禁止固定 id”冲突。
- 标准依据：`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33-45`
- 代码证据：`app/templates/components/filters/macros.html:109`, `app/templates/components/filters/macros.html:128`
- 影响：同页多 filter card 时 `label for` 与控件绑定错乱；JS 查询容易误命中。
- 修复建议：宏新增 `scope` 参数，内部 `id` 使用 `<scope>-instance`/`<scope>-database` 派生；调用方传入唯一 scope。
- 验证方式：`rg -n "id=\"instance\"|id=\"database\"" app/templates/components/filters/macros.html` 应无固定 id。

### 4.4 Views 读取 `window.EventBus`（allowlist 外全局）

- 结论：Views 层组件读取并使用 `window.EventBus`，不在 Views allowlist 内。
- 标准依据：`docs/Obsidian/standards/ui/layer/views-layer-standards.md:54-55`, `docs/Obsidian/standards/ui/layer/README.md:79-87`
- 代码证据：`app/static/js/modules/views/components/charts/manager.js:19`, `app/static/js/modules/views/components/charts/manager.js:224`
- 影响：引入跨层全局耦合，破坏分层与依赖注入规则，后续迁移需加入兼容/兜底逻辑。
- 修复建议：由 Page Entry 注入 emitter，或迁移到 UI Modules 并明确使用场景；若确需保留，更新 allowlist 与评审说明。
- 验证方式：`rg -n "EventBus" app/static/js/modules/views` 应无命中。

### 4.5 批量任务反馈未使用 `UI.resolveAsyncActionOutcome`

- 结论：批量操作直接使用 `message || '默认文案'` 兜底，未统一 outcome helper。
- 标准依据：`docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:43-44`
- 代码证据：`app/static/js/modules/views/instances/list.js:872`, `app/static/js/modules/views/instances/list.js:876`, `app/static/js/modules/views/instances/list.js:916`, `app/static/js/modules/views/instances/list.js:920`
- 影响：started/failed/unknown 口径不一致，unknown 分支缺失，易出现“成功/失败文案漂移”。
- 修复建议：改为 `UI.resolveAsyncActionOutcome`，统一 `started/failed/unknown` 文案与结果入口，移除 `message ||` 链。
- 验证方式：`rg -n "resolveAsyncActionOutcome" app/static/js/modules/views/instances/list.js` 应命中；并确认 `message ||` 兜底链消除。

## 5. 符合标准的关键点(通过项摘要)

- 模板侧未发现内联事件处理器（AST 扫描 `on*=` 结果为空），符合 `template-event-binding-standards` (`docs/Obsidian/standards/ui/template-event-binding-standards.md:34-35`)。
- `btn_close` 宏集中输出关闭按钮并默认 `aria-label="关闭"`，符合可访问性要求：`app/templates/components/ui/macros.html:6` + `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:31-33`。
- 模板内未发现 `style="height/width: Npx"`（AST 扫描结果为空），符合 layout sizing 约束：`docs/Obsidian/standards/ui/layout-sizing-guidelines.md:60-61`。
- CSS 中未发现 `variables.css` 以外的 HEX/RGB 字面量（AST/脚本扫描结果为空），符合 `color-guidelines`：`docs/Obsidian/standards/ui/color-guidelines.md:38-39`。
- 已有部分异步入口使用 `UI.resolveAsyncActionOutcome`（如 `app/static/js/modules/views/accounts/ledgers.js:639`, `app/static/js/modules/views/instances/detail.js:293`），与 `async-task-feedback-guidelines` 方向一致。

## 6. 防御/兼容/回退/适配逻辑清单(重点: ||/or 兜底)

- 位置：`app/static/js/common/toast.js:9`
  类型：防御/回退
  描述：依赖缺失即 `!bootstrapLib || !bootstrapLib.Toast` 直接 fail-fast（判定：合理回退）。
  建议：保留 fail-fast，同时确保依赖缺失有可观测告警。

- 位置：`app/static/js/common/grid-wrapper.js:5`
  类型：防御/回退
  描述：`!gridjs || !gridjs.Grid` 时直接退出（判定：合理回退）。
  建议：保持早失败，避免半初始化；可补充告警指标。

- 位置：`app/static/js/modules/views/components/tags/tag-selector-controller.js:10`
  类型：防御/回退
  描述：多依赖缺失时通过 `||` 合并判断并提前返回（判定：合理回退）。
  建议：保留 fail-fast，确保依赖注入路径可观测。

- 位置：`app/static/js/modules/views/components/permissions/permission-modal.js:115`
  类型：兼容
  描述：`account.db_type || (account.instance_name ? account.instance_name : 'unknown')` 作为类型兜底（判定：需人工复核，可能覆盖合法空字符串）。
  建议：用 `??` 或显式 `null/undefined` 判断，避免覆盖合法 falsy。

- 位置：`app/static/js/modules/views/components/tags/tag-selector-controller.js:74`
  类型：兼容
  描述：`tag.display_name || tag.name || tag.hiddenValue || ''` 作为字段别名链（判定：需人工复核，可能覆盖空字符串）。
  建议：若 `display_name` 允许为空，改为 `??` 或显式空字符串判定。

- 位置：`app/static/js/modules/views/components/tags/tag-selector-controller.js:195`
  类型：防御/适配
  描述：`options.modalElement || this.root.closest(...) || null` 兜底寻找 modal 容器（判定：合理回退）。
  建议：结合 scope 约束，避免 fallback 误命中错误容器。

- 位置：`app/static/js/common/number-format.js:73`
  类型：回退/规范化
  描述：`options.fallback ?? '0'` 使用 `??` 明确区分 `null/undefined`（判定：合理回退）。
  建议：保持 `??`，避免 `0` 被误判。

- 位置：`app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js:349`
  类型：防御
  描述：`renderDisplay(...) || '<div...>'` 缺失时回退占位（判定：需人工复核，可能覆盖空输出）。
  建议：区分 `null/undefined` 与空字符串，避免误替换。

- 位置：`app/static/js/modules/views/history/sessions/session-detail.js:699`
  类型：兼容/回退
  描述：`record.instance_name || '实例'` + `record.error_message || safeStringify(record.sync_details || {})` 兼容字段缺失（判定：需人工复核，可能覆盖合法空值）。
  建议：对可能为空但有效的字段改用 `??`。

- 位置：`app/templates/base.html:8`
  类型：回退
  描述：`config.APP_NAME or '鲸落'` 默认应用名兜底（判定：合理回退）。
  建议：若允许空字符串为有效值，改用 `default` filter。

- 位置：`app/templates/components/forms/macros.html:13`
  类型：兼容/回退
  描述：`field.default or ''` 在模板层使用 truthy 兜底（判定：危险兜底，可能覆盖 `0/false` 默认值）。
  建议：改用 `default` filter 或显式 `is not none` 判断。

- 位置：`app/templates/instances/statistics.html:203`
  类型：回退
  描述：`stat.version or '未知版本'` 默认展示（判定：合理回退）。
  建议：若版本允许空字符串，改用 `default` filter。

- 位置：`app/templates/accounts/ledgers.html:27`
  类型：回退
  描述：`current_db_type or 'all'` 兜底 DB 类型（判定：合理回退）。
  建议：若空字符串为合法态，改用 `default` filter。

## 7. 修复优先级建议

- P0：无。
- P1：组件 DOM id scope 违规（TagSelector、PermissionModal、filter 宏）；批量任务反馈未使用 `UI.resolveAsyncActionOutcome`。
- P2：Views 使用 `window.EventBus`（allowlist 外）应收敛为注入依赖或 UI Modules。
