> Status: Draft
> Owner: Codex (前端/UI 标准审计员 + 代码合规审计员 + 静态分析审计员)
> Created: 2026-01-24
> Updated: 2026-01-24
> Scope: `docs/Obsidian/standards/ui/**/*.md` + `app/static/js/**/*.js`(排除 `app/static/vendor/**`) + `app/templates/**/*.html` + `app/static/css/**/*.css`
> Related:
> - `docs/Obsidian/standards/ui/README.md`
> - `docs/Obsidian/standards/ui/layer/README.md`
> - `docs/Obsidian/standards/ui/javascript-module-standards.md`
> - `docs/Obsidian/standards/ui/vendor-library-usage-standards.md`
> - `docs/Obsidian/standards/ui/template-event-binding-standards.md`
> - `docs/Obsidian/standards/ui/layout-sizing-guidelines.md`
> - `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md`
> - `docs/Obsidian/standards/ui/metric-card-standards.md`
> - `docs/Obsidian/standards/ui/design-token-governance-guidelines.md`
> - `docs/Obsidian/standards/ui/color-guidelines.md`

# 前端/UI 标准全量审计报告 (2026-01-24)

## 1. 目标
- 找出标准冲突：同一主题的强约束口径不一致/索引与正文不一致/命名口径不一致等。
- 找出标准的模糊定义/不可执行点：术语未定义、触发条件不清、缺少可验证规则导致多解。
- 基于明确强约束（MUST/MUST NOT/等价强制措辞），找出前端代码违规点（严格限于扫描范围）。
- 盘点防御/兼容/回退/适配逻辑（重点：JS 的 `||/??`，模板的 `or/default`），区分合理回退/危险兜底/需人工复核。

## 2. 审计方法与证据
### 2.1 已执行的仓库门禁脚本
- 本次为“只读静态审计”，未执行 `scripts/ci/**` 门禁脚本（避免产生与报告无关的工作区副作用）。

### 2.2 已执行的补充静态扫描
- 使用 `rg --files` 仅做范围内文件枚举/导航，不作为任何违规判定的唯一依据。
- CSS 侧做了基于源码逐行的 Token 定义/引用一致性扫描与硬编码颜色扫描（给出 `app/static/css/...:line` 证据）。

### 2.3 AST 语义扫描
- JS：使用 `espree` 解析所有 `app/static/js/**/*.js`（共 116 个文件，解析失败 0 个），开启 `loc: true`，所有 JS 侧位置来自 `loc.start.line/loc.end.line`。
- Templates：使用 `jinja2.Environment().parse` 解析所有 `app/templates/**/*.html`（共 54 个文件，解析失败 0 个），所有模板侧位置来自 Template AST 的 `lineno`（对 `TemplateData` 片段内匹配按换行偏移校准）。
- CSS：扫描所有 `app/static/css/**/*.css`（共 43 个文件）。

本次 AST 扫描覆盖的“强约束高风险模式”（摘要）：
- 模板：`on*="..."` 内联事件处理器、`btn-close` 的 `aria-label`、`style="height/width: Npx"`（标准：`template-event-binding-standards.md`、`close-button-accessible-name-guidelines.md`、`layout-sizing-guidelines.md`）。
- JS：`new gridjs.Grid(...)`、`confirm()`、vendor 直接调用（dayjs/numeral/lodash/umbrella/JustValidate）、以及 `||/??` 兜底链（标准：`grid-standards.md`、`vendor-library-usage-standards.md`、`danger-operation-confirmation-guidelines.md`）。
- CSS：`var(--token)` 必须有 `--token:` 定义，且除 `variables.css` 外不得硬编码颜色（标准：`design-token-governance-guidelines.md`、`color-guidelines.md`）。

### 2.4 强约束索引（摘录）
- 模板禁止内联事件：`docs/Obsidian/standards/ui/template-event-binding-standards.md:34`。
- 模板必须以 `data-action`/`data-*` 表达意图：`docs/Obsidian/standards/ui/template-event-binding-standards.md:35`。
- 模板禁止新增 `style="height: Npx"` / `style="width: Npx"`：`docs/Obsidian/standards/ui/layout-sizing-guidelines.md:60`。
- `btn-close` 必须 `aria-label="关闭"` 且禁止英文 Close：`docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:31`、`docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:32`。
- `var(--xxx)` 必须能在 `app/static/css/**` 找到 `--xxx:` 定义：`docs/Obsidian/standards/ui/design-token-governance-guidelines.md:39`。
- 除 `variables.css` 定义 Token 外，CSS/HTML/JS 禁止硬编码 HEX/RGB/RGBA：`docs/Obsidian/standards/ui/color-guidelines.md:38`。
- Grid 列表页唯一入口：`docs/Obsidian/standards/ui/grid-standards.md:40`；页面脚本禁止 `new gridjs.Grid(...)`：`docs/Obsidian/standards/ui/grid-standards.md:42`。
- vendor 使用总原则：业务代码优先使用封装、不得直接调用 vendor global：`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:29`。
- 可复用组件内部禁止固定全局 id：`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33`。
- 可复用组件必须提供 scope 容器（`data-wf-scope` 或 `id="<scope>-container"`）：`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:42`。
- MetricCard：必须使用组件/macro：`docs/Obsidian/standards/ui/metric-card-standards.md:33`；视觉只能由组件 CSS 提供且页面 CSS 禁止新增 `*.stat-card`：`docs/Obsidian/standards/ui/metric-card-standards.md:41`、`docs/Obsidian/standards/ui/metric-card-standards.md:42`。

## 3. 标准冲突或歧义
### 3.1 `window.*` allowlist 的“全局”定义不够可执行
- 证据：`docs/Obsidian/standards/ui/layer/README.md:68`~`docs/Obsidian/standards/ui/layer/README.md:70` 提到“仅允许访问 allowlist 内的全局/除 allowlist 外禁止读取 `window.*`”。
- 歧义点：allowlist 列举的是项目封装与 vendor global（如 `window.DOMHelpers/window.UI/window.toast/bootstrap/Chart`），但文本未明确“浏览器原生 `window.location/window.setTimeout/...` 是否在约束范围内”。
- 可能导致实现分裂：
  - 一派按字面理解，开始为原生 API 也造 wrapper/注入，增加复杂度与 `||` 兼容链。
  - 一派继续直接用原生 `window.*`，在审计/门禁中被误判为违规。
- 建议口径收敛：明确 allowlist 仅约束“项目/业务全局（含 vendor global）”，原生 Web API 不在此表内；或在文档中新增“原生 global 白名单/豁免规则”。

### 3.2 DOM id scope 标准缺少“单例组件/Portal 组件”例外说明
- 证据：`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33` 明确禁止组件内固定 id；同时 `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:42` 将容器定位方式限定为 `data-wf-scope` 或 `id="<scope>-container"`。
- 现状信号：仓库内存在“全站复用但页面通常只会引入一次”的 modal 组件实现（例如 `danger_confirm_modal.html`），天然倾向固定 id 以适配 Bootstrap modal 触发方式。
- 可能导致实现分裂：
  - 一派对所有 modal 强制 scope 派生 id，带来 `data-bs-target`/JS 选择器的迁移成本。
  - 一派继续使用固定 id 并在 JS 中使用 `getElementById`，导致“可复用组件多实例”时出现静默冲突。
- 建议口径收敛：为“单例/Portal 组件”补充明确例外（例如：允许固定 id，但必须约定唯一注入点与禁止重复 include），或提供统一的 modal scope 派生模板/宏。

### 3.3 Grid 标准对“非列表页 Grid 表格（如 modal 内表格）”覆盖范围不够明确
- 证据：`docs/Obsidian/standards/ui/grid-standards.md:42` 禁止页面脚本直接 `new gridjs.Grid(...)`；`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:55` 同样禁止绕过 `Views.GridPage`。
- 歧义点：标准标题/目的强调“列表页”，但规则文本使用“页面脚本”措辞，容易被理解为“任何 gridjs.Grid 的直接创建都禁止”。
- 可能导致实现分裂：
  - 一派将 modal 内小表格也强行迁入 `Views.GridPage`/plugins，增加复杂度。
  - 一派在 modal 里直接 new gridjs.Grid，导致封装入口漂移、升级难控。
- 建议口径收敛：明确“允许/禁止的 Grid.js 使用场景清单”，并给出 modal/table 的官方封装入口（例如 `Views.GridTable`/`UI.createGridTable`）。

### 3.4 颜色硬编码禁令与“缺 Token/缺 ColorTokens 的降级策略”未对齐
- 证据：`docs/Obsidian/standards/ui/color-guidelines.md:38` 禁止在 JS 中硬编码 HEX/RGB/RGBA。
- 歧义点：当 `window.ColorTokens`/CSS token 缺失或加载时序异常时，标准没有定义“fail-fast vs graceful degradation”的统一策略（允许什么级别的兜底）。
- 可能导致实现分裂：fail-fast 直接报错/不渲染 vs 私有 HEX 兜底（违背标准）并导致兼容链增长。
- 建议口径收敛：把兜底收敛到 Token 层（`variables.css` 兼容别名/缺省）或约定统一的 `ColorTokens` fail-fast 行为 + 告警。

## 4. 不符合标准的代码行为(需要修复)
### 4.1 MetricCard 未按组件标准落地（存在页面私有 `*-stat-card` 体系）
- 结论：`instances/detail` 页面使用 `instance-stat-card` 页面私有结构与 CSS，而非 `MetricCard` 组件，违反“统一组件 + 统一 CSS”约束。
- 标准依据：
  - `docs/Obsidian/standards/ui/metric-card-standards.md:33`（MUST 使用 `MetricCard` 组件或 macro）。
  - `docs/Obsidian/standards/ui/metric-card-standards.md:41`（MUST 卡片视觉只能由组件 CSS 定义）。
  - `docs/Obsidian/standards/ui/metric-card-standards.md:42`（MUST NOT 页面 CSS 新增/恢复 `.xxx-stat-card { border/shadow/padding/... }`）。
  - `docs/Obsidian/standards/ui/metric-card-standards.md:53`（MUST NOT 为更新值引入页面私有 value class）。
- 代码证据：
  - 模板：`app/templates/instances/detail.html:207`（`instance-stat-card`）/ `app/templates/instances/detail.html:209`（`instance-stat-card__value`）。
  - 模板：`app/templates/instances/detail.html:270`（第二处 `instance-stat-card`）。
  - CSS：`app/static/css/pages/instances/detail.css:49`（`.instance-stat-card { ... }`）及其子类。
- 影响：
  - 指标卡视觉与交互将持续漂移，导致“每页一套 stat card”。
  - JS 更新锚点与门禁难统一（未来迁移 `data-role="metric-value"`/`data-stat-key` 成本更高）。
- 修复建议：
  - 将页面顶部指标卡改为使用 `app/templates/components/ui/metric_card.html` 或 `components/ui/macros.html` 的 `metric_card` macro。
  - 删除 `app/static/css/pages/instances/detail.css` 中 `instance-stat-card*` 的视觉定义，将布局保留为 page CSS（如 `row/gap`）。
  - 若需要 JS 更新，按标准使用 `data-stat-key` + `[data-role="metric-value"]` 或页面唯一 `id`。
- 验证方式：
  - 静态检查：模板/CSS 中不再出现 `instance-stat-card` 相关 class。
  - 视觉回归：对照 1920x1080 与 2560x1440 确认密度与样式一致。

### 4.2 可复用组件内部存在固定全局 `id`（多实例冲突风险）
- 结论：`components/filters/macros.html` 的宏内部使用固定 `id="instance"/id="database"`；`components/ui/danger_confirm_modal.html` 使用固定 modal id。按标准“可复用组件不得固定 id”，该实现存在多实例冲突风险。
- 标准依据：
  - `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33`（MUST NOT 在可复用组件内部写死固定 id）。
  - `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:42`（MUST 为组件最外层提供 scope 容器：`data-wf-scope` 或 `id="<scope>-container"`）。
  - `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:45`（MUST: `<scope>` 使用 `kebab-case` 且页面唯一）。
- 代码证据：
  - `app/templates/components/filters/macros.html:117`（`id="instance"`）。
  - `app/templates/components/filters/macros.html:136`（`id="database"`）。
  - `app/templates/components/ui/danger_confirm_modal.html:3`（`id="dangerConfirmModal"`）。
  - `app/templates/components/ui/danger_confirm_modal.html:12`（`id="dangerConfirmModalLabel"`）。
- 影响：
  - 同页出现第二个实例时将发生 DOM id 冲突，典型表现是事件绑定命中错误节点或更新错位（且往往是静默错误）。
  - 促使 JS 侧不断引入 `document.getElementById`/全局 selector 与 `||` 兜底链，进一步扩大漂移。
- 修复建议：
  - 为 `instance_filter/database_filter` 增加 `field_id/scope` 参数，内部 id 从 scope 派生（例如 `${scope}-instance`）。
  - 组件容器使用 `data-wf-scope="<scope>"`（推荐）或 `id="<scope>-container"`（允许），并在 JS 侧改为“先找容器再容器内查询”。
  - 对 `danger_confirm_modal` 明确选择策略：
    - 若定位为“单例 portal 组件”，建议在标准中补充例外并在 include 点保证只引入一次；或
    - 将其改为 scope 派生 id（`kebab-case`），并同步触发器的 `data-bs-target`/JS 选择器。
- 验证方式：
  - 静态检查：`app/templates/components/**` 内不再出现固定 id（或仅保留标准明确允许的单例例外）。
  - 交互回归：在同页渲染两份 filter 组件时，事件绑定与值更新不串扰。

### 4.3 在 Views 代码中直接 `new gridjs.Grid(...)`（绕过 GridPage/封装入口）
- 结论：存在在视图代码中直接实例化 `gridjs.Grid` 的实现点，违反 Grid 单一入口/封装收敛规则。
- 标准依据：
  - `docs/Obsidian/standards/ui/grid-standards.md:42`（MUST NOT 页面脚本直接 `new gridjs.Grid(...)`）。
  - `docs/Obsidian/standards/ui/vendor-library-usage-standards.md:55`（禁止在页面脚本直接 `new gridjs.Grid(...)` 或绕过 `Views.GridPage`）。
- 代码证据：
  - `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:176`（`new gridjs.Grid({ ... })`）。
- 影响：
  - Grid 配置/行为在各处分叉，升级 Grid.js/收敛分页/错误处理/URL 同步将变得不可控。
- 修复建议：
  - 若该表格属于“列表页 wiring”，应迁入 `Views.GridPage.mount` + plugins 体系。
  - 若属于“modal 内小表格”，建议新增/复用一个明确的封装入口（例如 `Views.GridTable`/`UI.createGridTable`），由封装层统一 new/destroy/默认配置。
- 验证方式：
  - 静态检查：除 `app/static/js/modules/views/grid-page.js` 外，`new gridjs.Grid(` 不再出现。

### 4.4 JS 中存在硬编码 HEX 颜色（违反 Token 化输出）
- 结论：存在 JS 侧硬编码颜色值的 fallback，违反“除 `variables.css` 外禁止硬编码颜色”约束。
- 标准依据：
  - `docs/Obsidian/standards/ui/color-guidelines.md:38`（除 `variables.css` 定义 Token 的颜色字面量外，其余 CSS/HTML/JS 禁止硬编码 HEX/RGB/RGBA）。
- 代码证据：
  - `app/static/js/modules/views/accounts/classification_statistics.js:994`（`"#3498db"`）。
- 影响：主题/配色体系被绕开，出现“局部颜色不随 Token 调整而变”的漂移。
- 修复建议：移除 HEX fallback，统一通过 `window.ColorTokens` 或 `var(--status-info)` 输出颜色；如担心 Token 缺失，应在 `variables.css` 做兼容别名/缺省，而不是在业务 JS 写私有 HEX。
- 验证方式：JS 内不再出现 `#RRGGBB` 字面量（允许存在于 `app/static/css/variables.css`）。

## 5. 符合标准的关键点(通过项摘要)
- 模板事件绑定：未发现任何 `on*="..."` 内联事件处理器（扫描范围 `app/templates/**/*.html`），符合 `docs/Obsidian/standards/ui/template-event-binding-standards.md:34`。
- 关闭按钮可访问名称：未发现 `aria-label="Close"`，且模板宏 `btn_close` 默认输出 `aria-label="关闭"`（`app/templates/components/ui/macros.html:29`~`app/templates/components/ui/macros.html:31`）。
- Inline px layout sizing：未发现模板新增 `style="height/width: Npx"`，符合 `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:60`。
- CSS Token 治理：未发现 `var(--token)` 引用但缺少 `--token:` 定义，符合 `docs/Obsidian/standards/ui/design-token-governance-guidelines.md:39`。
- CSS 颜色硬编码：除 `app/static/css/variables.css` 外未发现硬编码颜色字面量，符合 `docs/Obsidian/standards/ui/color-guidelines.md:38`（但 JS 侧存在 1 处违规，见 4.4）。
- 危险操作确认：JS AST 未发现 `confirm()` 调用，符合 `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:37`。
- vendor 直接调用：在 `app/static/js/modules/**` 内未发现 `dayjs()/numeral()/window._/new JustValidate()` 等直连 vendor global 的实现点（封装文件除外），符合 `docs/Obsidian/standards/ui/vendor-library-usage-standards.md:29` 及各库级 MUST NOT 约束。

## 6. 防御/兼容/回退/适配逻辑清单(重点: ||/or 兜底)
> 说明：JS 的 `||` 数量非常大。本清单优先收录“高信号”兜底：`??`（nullish 兜底）与多段 `||` 链（`chainLen >= 3`）。模板侧则全量列出 `or/default`。

### 6.1 JS: `??` 与多段 `||` 兜底链
- 扫描统计：`??` 兜底点 186 个；多段 `||` 链 183 个。

| 位置 | 类型 | 兜底判定 | 描述 | 建议 |
|---|---|---|---|---|
| `app/static/js/common/number-format.js:57` | 回退 | 合理回退 | ?? (chainLen=2): fallback ?? "--"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:73` | 回退 | 合理回退 | ?? (chainLen=2): options.fallback ?? "0"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:156` | 回退 | 合理回退 | ?? (chainLen=2): options.fallback ?? "0 B"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:169` | 回退 | 合理回退 | ?? (chainLen=2): options.fallback ?? "0 B"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:172` | 回退 | 合理回退 | ?? (chainLen=2): options.trimZero ?? true<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:186` | 回退 | 合理回退 | ?? (chainLen=2): options.fallback ?? "0 B"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:206` | 回退 | 合理回退 | ?? (chainLen=2): options.trimZero ?? false<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:207` | 回退 | 合理回退 | ?? (chainLen=2): options.fallback ?? "0"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:227` | 回退 | 合理回退 | ?? (chainLen=2): options.fallback ?? "0%"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/number-format.js:235` | 回退 | 合理回退 | ?? (chainLen=2): options.trimZero ?? false<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_change_logs_store.js:48` | 回退 | 合理回退 | ?? (chainLen=2): raw?.account_id ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_change_logs_store.js:49` | 回退 | 合理回退 | ?? (chainLen=2): raw?.instance_id ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_change_logs_store.js:57` | 回退 | 合理回退 | ?? (chainLen=2): raw?.session_id ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_change_logs_store.js:58` | 回退 | 合理回退 | ?? (chainLen=2): raw?.privilege_diff_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_change_logs_store.js:59` | 回退 | 合理回退 | ?? (chainLen=2): raw?.other_diff_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_change_logs_store.js:108` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:128` | 回退 | 合理回退 | ?? (chainLen=2): filters.classificationId ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:130` | 回退 | 合理回退 | ?? (chainLen=2): filters.dbType ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:131` | 回退 | 合理回退 | ?? (chainLen=2): filters.instanceId ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:132` | 回退 | 合理回退 | ?? (chainLen=2): filters.ruleId ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:166` | 回退 | 合理回退 | ?? (chainLen=2): next.classificationId ?? state.filters.classificationId<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:167` | 回退 | 合理回退 | ?? (chainLen=2): next.ruleId ?? state.filters.ruleId<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:170` | 回退 | 合理回退 | ?? (chainLen=2): next.periodType ?? state.filters.periodType<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:171` | 回退 | 合理回退 | ?? (chainLen=2): next.dbType ?? state.filters.dbType<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:172` | 回退 | 合理回退 | ?? (chainLen=2): next.instanceId ?? state.filters.instanceId<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:174` | 回退 | 合理回退 | ?? (chainLen=2): next.ruleStatus ?? state.filters.ruleStatus<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:211` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:304` | 回退 | 合理回退 | ?? (chainLen=3): payload?.data?.instances ?? payload?.instances ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:349` | 回退 | 合理回退 | ?? (chainLen=3): payload?.data ?? payload ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:408` | 回退 | 合理回退 | ?? (chainLen=3): payload?.data ?? payload ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:437` | 回退 | 合理回退 | ?? (chainLen=3): payload?.data?.trend ?? payload?.trend ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:455` | 回退 | 合理回退 | ?? (chainLen=3): payload?.data?.trend ?? payload?.trend ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:473` | 回退 | 合理回退 | ?? (chainLen=3): payload?.data ?? payload ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_store.js:99` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.classifications ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_store.js:104` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.rules_by_db_type ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_store.js:138` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.rule_stats ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_store.js:146` | 回退 | 合理回退 | ?? (chainLen=2): item.matched_accounts_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_store.js:159` | 回退 | 合理回退 | ?? (chainLen=2): statsMap[rule.id] ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/account_classification_store.js:180` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/accounts_statistics_store.js:57` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/accounts_statistics_store.js:94` | 回退 | 合理回退 | ?? (chainLen=3): payload?.data?.stats ?? payload?.stats ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/auth_store.js:74` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/credentials_store.js:79` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/dashboard_store.js:59` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/dashboard_store.js:96` | 回退 | 合理回退 | ?? (chainLen=3): data?.data ?? data ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/instance_crud_store.js:79` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/instance_store.js:239` | 回退 | 合理回退 | ?? (chainLen=3): response?.data ?? response ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/instance_store.js:345` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/logs_store.js:94` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/partition_store.js:185` | 回退 | 合理回退 | ?? (chainLen=4): response?.data?.data ?? response?.data ?? response ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/partition_store.js:188` | 回退 | 合理回退 | ?? (chainLen=2): payload.total_partitions ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/partition_store.js:189` | 回退 | 合理回退 | ?? (chainLen=2): payload.total_size ?? "0 B"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/partition_store.js:190` | 回退 | 合理回退 | ?? (chainLen=2): payload.total_records ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/partition_store.js:204` | 回退 | 合理回退 | ?? (chainLen=4): response?.data?.data ?? response?.data ?? response ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/partition_store.js:287` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/scheduler_store.js:177` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? cloneState()<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_batch_store.js:106` | 回退 | 合理回退 | ?? (chainLen=2): response?.data ?? response<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_batch_store.js:107` | 回退 | 合理回退 | ?? (chainLen=3): payload?.instances ?? payload?.items ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_batch_store.js:112` | 回退 | 合理回退 | ?? (chainLen=2): response?.data ?? response<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_batch_store.js:113` | 回退 | 合理回退 | ?? (chainLen=3): payload?.tags ?? payload?.items ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_batch_store.js:185` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_list_store.js:82` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_management_store.js:194` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_management_store.js:328` | 回退 | 合理回退 | ?? (chainLen=2): tag?.name ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_management_store.js:331` | 回退 | 合理回退 | ?? (chainLen=2): tag?.display_name ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_management_store.js:333` | 回退 | 合理回退 | ?? (chainLen=2): tag?.name ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_management_store.js:404` | 回退 | 合理回退 | ?? (chainLen=4): response?.categories ?? response?.data?.categories ?? response?.data ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/tag_management_store.js:478` | 回退 | 合理回退 | ?? (chainLen=4): response?.data?.tags ?? response?.tags ?? response?.data ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/task_runs_store.js:78` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/stores/users_store.js:80` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? { state: cloneState(state) }<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/theme/color-tokens.js:118` | 回退 | 合理回退 | ?? (chainLen=2): rgba.a ?? 1<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/theme/color-tokens.js:150` | 回退 | 合理回退 | ?? (chainLen=2): rgba.a ?? 1<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/theme/color-tokens.js:159` | 回退 | 合理回退 | ?? (chainLen=2): hsl.a ?? 1<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/theme/color-tokens.js:176` | 回退 | 合理回退 | ?? (chainLen=2): hsl.a ?? 1<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/theme/color-tokens.js:332` | 回退 | 合理回退 | ?? (chainLen=2): index ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/ui/async-action-feedback.js:68` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.run_id ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/ui/async-action-feedback.js:69` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.session_id ?? null<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/ui/danger-confirm.js:140` | 回退 | 合理回退 | ?? (chainLen=2): item?.value ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:18` | 回退 | 合理回退 | ?? (chainLen=2): window.DEBUG_ACCOUNT_CLASSIFICATION ?? true<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:329` | 回退 | 合理回退 | ?? (chainLen=2): classification?.id ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:368` | 回退 | 合理回退 | ?? (chainLen=2): classification?.id ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:375` | 回退 | 合理回退 | ?? (chainLen=2): classification?.id ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:458` | 回退 | 合理回退 | ?? (chainLen=2): label ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:553` | 回退 | 合理回退 | ?? (chainLen=2): rule?.id ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:556` | 回退 | 合理回退 | ?? (chainLen=2): rule?.id ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:559` | 回退 | 合理回退 | ?? (chainLen=2): rule?.id ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js:102` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.classification ?? response?.classification<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js:334` | 回退 | 合理回退 | ?? (chainLen=2): classification.priority ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js:263` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.rule ?? response?.rule<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js:315` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.rule ?? response?.rule<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:86` | 回退 | 合理回退 | ?? (chainLen=2): aParts.find((_, index) => index === i) ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:87` | 回退 | 合理回退 | ?? (chainLen=2): bParts.find((_, index) => index === i) ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:1251` | 回退 | 合理回退 | ?? (chainLen=2): response?.data?.permissions ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:356` | 回退 | 合理回退 | ?? (chainLen=2): latestAvg ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:565` | 回退 | 合理回退 | ?? (chainLen=3): payload?.contributions ?? payload?.data?.contributions ?? []<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:643` | 回退 | 合理回退 | ?? (chainLen=2): meta?.value_avg ?? context.parsed?.y<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:706` | 回退 | 合理回退 | ?? (chainLen=2): meta?.value_avg ?? context.parsed?.y<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:781` | 回退 | 合理回退 | ?? (chainLen=2): lastPoint?.coverage_days ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:782` | 回退 | 合理回退 | ?? (chainLen=2): lastPoint?.expected_days ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:970` | 回退 | 合理回退 | ?? (chainLen=2): value ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/statistics.js:79` | 回退 | 合理回退 | ?? (chainLen=2): stats?.total_accounts ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/statistics.js:80` | 回退 | 合理回退 | ?? (chainLen=2): stats?.active_accounts ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/statistics.js:81` | 回退 | 合理回退 | ?? (chainLen=2): stats?.locked_accounts ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/statistics.js:82` | 回退 | 合理回退 | ?? (chainLen=2): stats?.total_instances ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/accounts/statistics.js:164` | 回退 | 合理回退 | ?? (chainLen=2): meta?.deleted ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js:601` | 回退 | 合理回退 | ?? (chainLen=2): payload?.loading?.metrics ?? false<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/partitions/index.js:200` | 回退 | 合理回退 | ?? (chainLen=2): options.silent ?? true<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/partitions/index.js:227` | 回退 | 合理回退 | ?? (chainLen=2): stats.total_partitions ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/partitions/index.js:228` | 回退 | 合理回退 | ?? (chainLen=2): stats.total_records ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/partitions/index.js:261` | 回退 | 合理回退 | ?? (chainLen=2): currentPartition?.record_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/partitions/index.js:447` | 回退 | 合理回退 | ?? (chainLen=4): response?.data?.data ?? response?.data ?? response ?? {}<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/partitions/partition-list.js:91` | 回退 | 合理回退 | ?? (chainLen=2): item.record_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:163` | 回退 | 合理回退 | ?? (chainLen=2): triggerArgs.second ?? '0'<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:164` | 回退 | 合理回退 | ?? (chainLen=2): triggerArgs.minute ?? '0'<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:165` | 回退 | 合理回退 | ?? (chainLen=2): triggerArgs.hour ?? '0'<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:166` | 回退 | 合理回退 | ?? (chainLen=2): triggerArgs.day ?? '*'<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:167` | 回退 | 合理回退 | ?? (chainLen=2): triggerArgs.month ?? '*'<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:168` | 回退 | 合理回退 | ?? (chainLen=2): triggerArgs.day_of_week ?? '*'<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:169` | 回退 | 合理回退 | ?? (chainLen=2): triggerArgs.year ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:287` | 回退 | 合理回退 | ?? (chainLen=2): value ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/databases.js:125` | 回退 | 合理回退 | ?? (chainLen=2): summary?.total_databases ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/databases.js:126` | 回退 | 合理回退 | ?? (chainLen=2): summary?.total_instances ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/databases.js:155` | 回退 | 合理回退 | ?? (chainLen=2): summary?.max_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/databases.js:156` | 回退 | 合理回退 | ?? (chainLen=2): summary?.avg_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/databases.js:172` | 回退 | 合理回退 | ?? (chainLen=2): summary?.max_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/databases.js:173` | 回退 | 合理回退 | ?? (chainLen=2): summary?.total_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/instances.js:99` | 回退 | 合理回退 | ?? (chainLen=2): value ?? "-"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/instances.js:110` | 回退 | 合理回退 | ?? (chainLen=2): value ?? "-"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/instances.js:123` | 回退 | 合理回退 | ?? (chainLen=2): summary?.max_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/instances.js:124` | 回退 | 合理回退 | ?? (chainLen=2): summary?.total_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/instances.js:140` | 回退 | 合理回退 | ?? (chainLen=2): summary?.max_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/capacity/instances.js:141` | 回退 | 合理回退 | ?? (chainLen=2): summary?.avg_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/change-history/change-history-renderer.js:4` | 回退 | 合理回退 | ?? (chainLen=2): value ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/filters.js:159` | 回退 | 合理回退 | ?? (chainLen=2): (typeof getOptionValue === "function" ? getOptionValue(item) : item?.value) ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/filters.js:163` | 回退 | 合理回退 | ?? (chainLen=3): (typeof getOptionLabel === "function" ? getOptionLabel(item) : item?.label) ?? value ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/filters.js:187` | 回退 | 合理回退 | ?? (chainLen=2): value ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/manager.js:457` | 回退 | 合理回退 | ?? (chainLen=3): event?.target?.value ?? event?.currentTarget?.value ?? ""<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:166` | 回退 | 合理回退 | ?? (chainLen=2): ctx.p0?.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:167` | 回退 | 合理回退 | ?? (chainLen=2): ctx.p1?.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:174` | 回退 | 合理回退 | ?? (chainLen=2): ctx.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:189` | 回退 | 合理回退 | ?? (chainLen=2): ctx.p0?.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:190` | 回退 | 合理回退 | ?? (chainLen=2): ctx.p1?.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:197` | 回退 | 合理回退 | ?? (chainLen=2): ctx.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:200` | 回退 | 合理回退 | ?? (chainLen=2): ctx.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:207` | 回退 | 合理回退 | ?? (chainLen=2): ctx.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:211` | 回退 | 合理回退 | ?? (chainLen=2): ctx.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:214` | 回退 | 合理回退 | ?? (chainLen=2): ctx.parsed?.y ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/charts/transformers.js:243` | 回退 | 合理回退 | ?? (chainLen=2): item.total_size_mb ?? item.avg_size_mb<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/components/permissions/permission-modal.js:44` | 回退 | 合理回退 | ?? (chainLen=2): item.label ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/credentials/list.js:279` | 回退 | 合理回退 | ?? (chainLen=2): item.instance_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/credentials/list.js:321` | 回退 | 合理回退 | ?? (chainLen=2): meta.instance_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:421` | 回退 | 合理回退 | ?? (chainLen=2): payload.total_changes ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:422` | 回退 | 合理回退 | ?? (chainLen=2): payload.success_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:423` | 回退 | 合理回退 | ?? (chainLen=2): payload.failed_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:424` | 回退 | 合理回退 | ?? (chainLen=2): payload.affected_accounts ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/log-detail.js:345` | 回退 | 合理回退 | ?? (chainLen=2): payload ?? error<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/logs.js:500` | 回退 | 合理回退 | ?? (chainLen=3): stats.total_logs ?? stats.total ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/logs.js:501` | 回退 | 合理回退 | ?? (chainLen=3): stats.error_logs ?? stats.error_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/logs.js:502` | 回退 | 合理回退 | ?? (chainLen=3): stats.warning_logs ?? stats.warning_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/logs.js:503` | 回退 | 合理回退 | ?? (chainLen=2): stats.info_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/logs.js:532` | 回退 | 合理回退 | ?? (chainLen=2): stats.critical_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/logs.js:533` | 回退 | 合理回退 | ?? (chainLen=2): stats.debug_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/history/logs/logs.js:549` | 回退 | 合理回退 | ?? (chainLen=2): top1?.count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/detail.js:1217` | 回退 | 合理回退 | ?? (chainLen=2): payload.active_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/detail.js:1218` | 回退 | 合理回退 | ?? (chainLen=2): payload.filtered_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/detail.js:1219` | 回退 | 合理回退 | ?? (chainLen=2): payload.total_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/detail.js:1700` | 回退 | 合理回退 | ?? (chainLen=2): payload?.total_size_mb ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/detail.js:1703` | 回退 | 合理回退 | ?? (chainLen=2): payload?.filtered_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/detail.js:1704` | 回退 | 合理回退 | ?? (chainLen=2): payload?.active_count ?? (databases.length - filteredCount)<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/list.js:401` | 回退 | 合理回退 | ?? (chainLen=2): meta?.id ?? ''<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:230` | 回退 | 合理回退 | ?? (chainLen=2): payload.saved_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:231` | 回退 | 合理回退 | ?? (chainLen=2): payload.deleted_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:232` | 回退 | 合理回退 | ?? (chainLen=2): payload.elapsed_ms ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:435` | 回退 | 合理回退 | ?? (chainLen=2): stats?.total_instances ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:436` | 回退 | 合理回退 | ?? (chainLen=2): stats?.active_instances ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:437` | 回退 | 合理回退 | ?? (chainLen=2): stats?.inactive_instances ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:438` | 回退 | 合理回退 | ?? (chainLen=2): stats?.deleted_instances ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:465` | 回退 | 合理回退 | ?? (chainLen=2): b?.count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:465` | 回退 | 合理回退 | ?? (chainLen=2): a?.count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:468` | 回退 | 合理回退 | ?? (chainLen=2): top1?.count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/instances/statistics.js:491` | 回退 | 合理回退 | ?? (chainLen=2): global.NumberFormat?.formatInteger?.(resolved, { fallback: resolved }) ?? resolved<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/tags/batch-assign.js:197` | 回退 | 合理回退 | ?? (chainLen=2): instance?.port ?? "-"<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/tags/index.js:500` | 回退 | 合理回退 | ?? (chainLen=2): stats.total ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/tags/index.js:501` | 回退 | 合理回退 | ?? (chainLen=2): stats.active ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/tags/index.js:502` | 回退 | 合理回退 | ?? (chainLen=2): stats.inactive ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/modules/views/tags/index.js:503` | 回退 | 合理回退 | ?? (chainLen=2): stats.category_count ?? 0<br>使用 ?? 仅在 null/undefined 时回退，不会覆盖合法 falsy。 | 通常可保留；若希望仅对 undefined 生效/或需要保留 ""，请避免退回到 \|\|。 |
| `app/static/js/common/grid-wrapper.js:278` | 回退 | 需人工复核 | \|\| (chainLen=3): normalizedBase \|\| sourceUrl \|\| ""<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/common/toast.js:165` | 回退 | 需人工复核 | \|\| (chainLen=3): options.ariaLive \|\| typeConfig.ariaLive \|\| 'polite'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/core/http-u.js:221` | 回退 | 需人工复核 | \|\| (chainLen=3): body.message \|\| body.error \|\| (fallbackStatus >= 500 ? '服务器错误' : '请求失败')<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/account_change_logs_service.js:7` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/account_classification_service.js:15` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/account_classification_statistics_service.js:7` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/accounts_statistics_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/auth_service.js:17` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/capacity_stats_service.js:22` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/connection_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/credentials_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/dashboard_service.js:12` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/instance_management_service.js:12` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/instance_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/logs_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/partition_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/permission_service.js:12` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/scheduler_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/tag_management_service.js:23` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/task_runs_service.js:7` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/services/user_service.js:14` | 回退 | 需人工复核 | \|\| (chainLen=4): client \|\| global.httpU \|\| global.http \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_change_logs_store.js:65` | 回退 | 需人工复核 | \|\| (chainLen=4): resp.message \|\| resp.error \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_change_logs_store.js:168` | 回退 | 需人工复核 | \|\| (chainLen=3): resolved?.data \|\| resolved \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_change_logs_store.js:200` | 回退 | 需人工复核 | \|\| (chainLen=3): resolved?.data \|\| resolved \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:351` | 回退 | 需人工复核 | \|\| (chainLen=3): data.window_start \|\| data.data?.window_start \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:352` | 回退 | 需人工复核 | \|\| (chainLen=3): data.window_end \|\| data.data?.window_end \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:353` | 回退 | 需人工复核 | \|\| (chainLen=3): data.latest_period_start \|\| data.data?.latest_period_start \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_classification_statistics_store.js:354` | 回退 | 需人工复核 | \|\| (chainLen=3): data.latest_period_end \|\| data.data?.latest_period_end \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/account_classification_store.js:54` | 兼容 | 需人工复核 | \|\| (chainLen=4): response.message \|\| response.error \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/auth_store.js:41` | 兼容 | 需人工复核 | \|\| (chainLen=3): response.message \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/credentials_store.js:46` | 兼容 | 需人工复核 | \|\| (chainLen=3): response.message \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/instance_crud_store.js:46` | 兼容 | 需人工复核 | \|\| (chainLen=3): response.message \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/instance_store.js:189` | 回退 | 需人工复核 | \|\| (chainLen=3): item.name \|\| item.label \|\| ""<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/instance_store.js:190` | 回退 | 需人工复核 | \|\| (chainLen=3): item.dbType \|\| item.db_type \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/instance_store.js:256` | 兼容 | 需人工复核 | \|\| (chainLen=3): response.message \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/logs_store.js:49` | 回退 | 需人工复核 | \|\| (chainLen=3): raw.timestamp_display \|\| raw.timestamp \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/logs_store.js:160` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/logs_store.js:195` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/logs_store.js:196` | 兼容 | 需人工复核 | \|\| (chainLen=4): payload.log \|\| payload.data \|\| payload \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/partition_store.js:227` | 兼容 | 需人工复核 | \|\| (chainLen=3): response.message \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/partition_store.js:363` | 回退 | 需人工复核 | \|\| (chainLen=3): params.periodType \|\| state.metrics.periodType \|\| "daily"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/scheduler_store.js:84` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.message \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/tag_batch_store.js:41` | 回退 | 需人工复核 | \|\| (chainLen=3): lodash \|\| window.LodashUtils \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/tag_batch_store.js:50` | 兼容 | 需人工复核 | \|\| (chainLen=4): response.message \|\| response.error \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/tag_list_store.js:40` | 回退 | 需人工复核 | \|\| (chainLen=4): resp.message \|\| resp.error \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/tag_list_store.js:141` | 回退 | 需人工复核 | \|\| (chainLen=3): resolved?.data \|\| resolved \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/tag_list_store.js:142` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.tag \|\| payload?.data?.tag \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/tag_management_store.js:251` | 回退 | 需人工复核 | \|\| (chainLen=3): name.includes(query) \|\| displayName.includes(query) \|\| categoryValue.includes(query)<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/task_runs_store.js:38` | 回退 | 需人工复核 | \|\| (chainLen=4): resp.message \|\| resp.error \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/task_runs_store.js:136` | 回退 | 需人工复核 | \|\| (chainLen=3): resolved?.data \|\| resolved \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/task_runs_store.js:165` | 回退 | 需人工复核 | \|\| (chainLen=3): resolved?.data \|\| resolved \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/users_store.js:40` | 回退 | 需人工复核 | \|\| (chainLen=4): resp.message \|\| resp.error \|\| fallbackMessage \|\| "操作失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/users_store.js:133` | 回退 | 需人工复核 | \|\| (chainLen=3): resolved?.data \|\| resolved \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/stores/users_store.js:134` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.user \|\| payload?.data?.user \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/ui/async-action-feedback.js:44` | 兼容 | 需人工复核 | \|\| (chainLen=3): typeof response.success === "boolean" \|\| typeof response.error === "boolean" \|\| isNonEmptyString(response.message)<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/ui/danger-confirm.js:34` | 回退 | 需人工复核 | \|\| (chainLen=3): parsed?.request_id \|\| parsed?.requestId \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/ui/filter-card.js:171` | 兼容 | 需人工复核 | \|\| (chainLen=3): form.dataset.filterName \|\| normalizedFormId \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/ui/filter-card.js:229` | 回退 | 需人工复核 | \|\| (chainLen=3): control \|\| event?.target \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/ui/filter-card.js:236` | 回退 | 需人工复核 | \|\| (chainLen=3): control?.name \|\| control?.id \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/ui/ui-helpers.js:34` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.data \|\| error?.data \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:671` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.error \|\| error.message \|\| '自动分类失败'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/account-classification/index.js:766` | 兼容 | 需人工复核 | \|\| (chainLen=4): error?.response?.error \|\| error?.message \|\| fallbackMessage \|\| '操作失败'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js:331` | 回退 | 需人工复核 | \|\| (chainLen=3): classification.display_name \|\| classification.name \|\| ""<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:772` | 回退 | 需人工复核 | \|\| (chainLen=4): (selected.server_roles && selected.server_roles.length > 0) \|\| (selected.server_permissions && selected.server_permissions.length > 0) \|\| (selected.database_...<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:969` | 回退 | 需人工复核 | \|\| (chainLen=3): (selected.predefined_roles && selected.predefined_roles.length > 0) \|\| (selected.role_attributes && selected.role_attributes.length > 0) \|\| (selected.databas...<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:1249` | 兼容 | 需人工复核 | \|\| (chainLen=3): response.error \|\| response.message \|\| "加载权限配置失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:220` | 回退 | 需人工复核 | \|\| (chainLen=3): snapshot.rulesWindow?.latestStart \|\| snapshot.rulesWindow?.windowStart \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:221` | 回退 | 需人工复核 | \|\| (chainLen=3): snapshot.rulesWindow?.latestEnd \|\| snapshot.rulesWindow?.windowEnd \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:295` | 回退 | 需人工复核 | \|\| (chainLen=3): item?.display_name \|\| name \|\| `实例 ${id}`<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:1001` | 回退 | 需人工复核 | \|\| (chainLen=3): ColorTokens?.getOrangeColor?.({ tone: "muted", alpha: 0.2 }) \|\| getChartColor(0, 0.12) \|\| withAlpha(contrast, 0.08)<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/classification_statistics.js:1004` | 回退 | 需人工复核 | \|\| (chainLen=3): ColorTokens?.getOrangeColor?.({ tone: "strong" }) \|\| getChartColor(0, 0.25) \|\| withAlpha(contrast, 0.2)<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/ledgers.js:195` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/accounts/ledgers.js:388` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/index.js:289` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.stats \|\| payload?.state?.stats \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/index.js:290` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.partitions \|\| payload?.state?.partitions \|\| []<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/index.js:450` | 回退 | 需人工复核 | \|\| (chainLen=3): components?.database?.status \|\| components?.database \|\| ''<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/partition-list.js:84` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/partition-list.js:98` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/partition-list.js:175` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.display_name \|\| fallback \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/partition-list.js:183` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.table \|\| cell \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/partitions/partition-list.js:191` | 回退 | 需人工复核 | \|\| (chainLen=3): cell \|\| meta.size \|\| "0 B"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/scheduler/index.js:222` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.message \|\| error?.message \|\| '网络或服务器错误'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/scheduler/index.js:540` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.message \|\| error?.message \|\| '未知错误'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/scheduler/index.js:566` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.message \|\| error?.message \|\| '未知错误'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/scheduler/index.js:592` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.message \|\| error?.message \|\| '未知错误'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/scheduler/index.js:644` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.message \|\| error?.message \|\| '未知错误'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/scheduler/index.js:803` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.jobs \|\| schedulerStore.getState().jobs \|\| []<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:200` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.message \|\| error?.message \|\| '未知错误'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/list.js:145` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/list.js:146` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload.total \|\| payload.pagination?.total \|\| 0<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/list.js:385` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/list.js:386` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload.items \|\| payload.users \|\| []<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/list.js:392` | 回退 | 需人工复核 | \|\| (chainLen=3): item.created_at_display \|\| item.created_at \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/list.js:466` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.created_at_display \|\| cell \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/modals/change-password-modals.js:17` | 兼容 | 需人工复核 | \|\| (chainLen=3): error?.response?.data \|\| error?.data \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/modals/change-password-modals.js:29` | 回退 | 需人工复核 | \|\| (chainLen=4): normalized === "1" \|\| normalized === "true" \|\| normalized === "yes" \|\| normalized === "on"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/auth/modals/user-modals.js:206` | 兼容 | 需人工复核 | \|\| (chainLen=3): editingUserMeta?.username \|\| payload.username \|\| ''<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/capacity/databases.js:36` | 回退 | 需人工复核 | \|\| (chainLen=3): item?.database_name \|\| item?.database?.database_name \|\| "未知数据库"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/capacity/databases.js:40` | 回退 | 需人工复核 | \|\| (chainLen=3): item?.instance?.name \|\| item?.instance_name \|\| "未知实例"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/capacity/databases.js:44` | 回退 | 需人工复核 | \|\| (chainLen=3): item?.instance?.id \|\| item?.instance_id \|\| `unknown-${instanceName}`<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/capacity/instances.js:36` | 回退 | 需人工复核 | \|\| (chainLen=4): item?.instance?.name \|\| item?.instance_name \|\| item?.name \|\| "未知实例"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/capacity/instances.js:41` | 回退 | 需人工复核 | \|\| (chainLen=3): item?.instance?.id \|\| item?.instance_id \|\| instanceName<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/change-history/change-history-renderer.js:88` | 回退 | 需人工复核 | \|\| (chainLen=4): entry?.object \|\| entry?.label \|\| entry?.field \|\| "权限"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/change-history/change-history-renderer.js:148` | 回退 | 需人工复核 | \|\| (chainLen=3): entry?.label \|\| entry?.field \|\| "数据库特性"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/change-history/change-history-renderer.js:186` | 回退 | 需人工复核 | \|\| (chainLen=3): entry?.label \|\| entry?.field \|\| "其他字段"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/charts/chart-renderer.js:19` | 回退 | 需人工复核 | \|\| (chainLen=5): ColorTokens.getOrangeColor({ tone: 'muted', alpha: 0.2 }) \|\| ColorTokens.getChartColor(0, 0.2) \|\| ColorTokens.getSurfaceColor(0.2) \|\| ColorTokens.withAlpha(c...<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/charts/manager.js:815` | 回退 | 需人工复核 | \|\| (chainLen=3): item.name \|\| item.instance_name \|\| "未知实例"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/charts/transformers.js:45` | 回退 | 需人工复核 | \|\| (chainLen=3): result.key \|\| result.label \|\| "unknown"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/charts/transformers.js:46` | 回退 | 需人工复核 | \|\| (chainLen=3): result.label \|\| result.key \|\| "未知"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/charts/transformers.js:259` | 回退 | 需人工复核 | \|\| (chainLen=3): sortedKeys.length \|\| topN \|\| 1<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/charts/transformers.js:309` | 回退 | 需人工复核 | \|\| (chainLen=3): sortedKeys.length \|\| topN \|\| 1<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/charts/transformers.js:359` | 回退 | 需人工复核 | \|\| (chainLen=3): sortedKeys.length \|\| topN \|\| 1<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/permissions/permission-viewer.js:138` | 回退 | 需人工复核 | \|\| (chainLen=3): data?.error \|\| data?.message \|\| "获取权限信息失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/permissions/permission-viewer.js:168` | 回退 | 需人工复核 | \|\| (chainLen=3): data?.error \|\| data?.message \|\| "获取权限信息失败"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/tags/tag-selector-controller.js:45` | 回退 | 需人工复核 | \|\| (chainLen=4): tag.display_name \|\| tag.name \|\| tag.hiddenValue \|\| ""<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/tags/tag-selector-controller.js:168` | 回退 | 需人工复核 | \|\| (chainLen=3): options.modalElement \|\| this.root.closest("[data-tag-selector-modal]") \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/tags/tag-selector-controller.js:525` | 回退 | 需人工复核 | \|\| (chainLen=3): scope \|\| (container?.dataset?.tagSelectorScope \|\| "")<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/tags/tag-selector-view.js:299` | 回退 | 需人工复核 | \|\| (chainLen=3): tag.display_name \|\| tag.name \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/components/tags/tag-selector-view.js:371` | 回退 | 需人工复核 | \|\| (chainLen=3): tag.display_name \|\| tag.name \|\| ""<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/credentials/list.js:150` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/credentials/list.js:229` | 回退 | 需人工复核 | \|\| (chainLen=3): cell \|\| meta.name \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/credentials/list.js:272` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/credentials/list.js:337` | 回退 | 需人工复核 | \|\| (chainLen=3): value \|\| meta.created_at_display \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/credentials/modals/credential-modals.js:387` | 回退 | 需人工复核 | \|\| (chainLen=3): normalized === '1' \|\| normalized === 'true' \|\| normalized === 'yes'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/databases/ledgers.js:100` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/databases/ledgers.js:149` | 回退 | 需人工复核 | \|\| (chainLen=3): dbType \|\| currentDbType \|\| "all"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/databases/ledgers.js:190` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:84` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.stats \|\| payload?.state?.stats \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:85` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.windowHours \|\| payload?.state?.windowHours \|\| 24<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:121` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:155` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:181` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.change_time \|\| cell \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:213` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.message \|\| cell \|\| ""<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/logs/logs.js:105` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.stats \|\| payload?.state?.stats \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/logs/logs.js:106` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.windowHours \|\| payload?.state?.windowHours \|\| 24<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/logs/logs.js:152` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/logs/logs.js:186` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/logs/logs.js:218` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.timestamp_display \|\| cell \|\| '-'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/logs/logs.js:240` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.message \|\| cell \|\| ''<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/sessions/sync-sessions.js:165` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/sessions/sync-sessions.js:302` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/history/sessions/sync-sessions.js:343` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.task_name \|\| meta.task_key \|\| '-'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:214` | 回退 | 需人工复核 | \|\| (chainLen=3): event?.currentTarget \|\| event?.target \|\| fallbackBtn<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:302` | 回退 | 需人工复核 | \|\| (chainLen=3): event?.currentTarget \|\| event?.target \|\| fallbackBtn<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:348` | 回退 | 需人工复核 | \|\| (chainLen=3): toast?.warning \|\| toast?.info \|\| console.info<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:478` | 回退 | 需人工复核 | \|\| (chainLen=3): event?.currentTarget \|\| event?.target \|\| fallbackBtn<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:522` | 回退 | 需人工复核 | \|\| (chainLen=3): toast?.warning \|\| toast?.info \|\| console.info<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:644` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:690` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:969` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1003` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1201` | 兼容 | 需人工复核 | \|\| (chainLen=3): resp?.data \|\| resp \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1331` | 回退 | 需人工复核 | \|\| (chainLen=4): entry?.object \|\| entry?.label \|\| entry?.field \|\| '权限'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1372` | 回退 | 需人工复核 | \|\| (chainLen=3): entry?.label \|\| entry?.field \|\| '其他字段'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1428` | 兼容 | 需人工复核 | \|\| (chainLen=3): resp?.data \|\| resp \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1588` | 回退 | 需人工复核 | \|\| (chainLen=3): root.dataset?.instanceId \|\| root.getAttribute('data-instance-id') \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1590` | 回退 | 需人工复核 | \|\| (chainLen=3): root.dataset?.instanceName \|\| root.getAttribute('data-instance-name') \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1592` | 回退 | 需人工复核 | \|\| (chainLen=3): root.dataset?.dbType \|\| root.getAttribute('data-db-type') \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1594` | 回退 | 需人工复核 | \|\| (chainLen=3): root.dataset?.syncAccountsUrl \|\| root.getAttribute('data-sync-accounts-url') \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1653` | 兼容 | 需人工复核 | \|\| (chainLen=3): resp?.data \|\| resp \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/detail.js:1658` | 回退 | 需人工复核 | \|\| (chainLen=3): resp?.error \|\| resp?.message \|\| '加载失败'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/list.js:272` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/list.js:440` | 回退 | 需人工复核 | \|\| (chainLen=3): cell \|\| meta.host \|\| ''<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/list.js:516` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/list.js:558` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.display_name \|\| typeStr \|\| '-'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/list.js:714` | 回退 | 需人工复核 | \|\| (chainLen=5): value === undefined \|\| value === null \|\| value === '' \|\| value === 'all' \|\| (Array.isArray(value) && !value.length)<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/list.js:1186` | 回退 | 需人工复核 | \|\| (chainLen=3): result?.error \|\| result?.message \|\| '连接失败'<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/modals/batch-create-modal.js:150` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:9` | 回退 | 需人工复核 | \|\| (chainLen=3): options?.toast \|\| window.toast \|\| { success: console.info, error: console.error, info: console.info, warning: console.warn, }<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:201` | 兼容 | 需人工复核 | \|\| (chainLen=3): resp?.data \|\| resp \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:225` | 兼容 | 需人工复核 | \|\| (chainLen=3): resp?.data \|\| resp \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:249` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.database_id \|\| payload?.databaseId \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:250` | 兼容 | 需人工复核 | \|\| (chainLen=3): payload?.database_name \|\| payload?.databaseName \|\| null<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/instances/statistics.js:153` | 兼容 | 需人工复核 | \|\| (chainLen=4): payload?.stats \|\| payload?.state?.stats \|\| payload \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/batch-assign.js:267` | 回退 | 需人工复核 | \|\| (chainLen=3): tag?.display_name \|\| tag?.name \|\| (id !== null ? `标签 ${id}` : "未知标签")<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/batch-assign.js:436` | 回退 | 需人工复核 | \|\| (chainLen=3): tag?.display_name \|\| tag?.name \|\| `标签 ${id}`<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/index.js:135` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/index.js:372` | 兼容 | 需人工复核 | \|\| (chainLen=3): response?.data \|\| response \|\| {}<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/index.js:377` | 回退 | 需人工复核 | \|\| (chainLen=3): item.display_name \|\| item.name \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/index.js:379` | 回退 | 需人工复核 | \|\| (chainLen=3): item.color_name \|\| item.color \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/index.js:392` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.display_name \|\| meta.name \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/index.js:414` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.color_name \|\| meta.color \|\| "-"<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |
| `app/static/js/modules/views/tags/index.js:444` | 回退 | 需人工复核 | \|\| (chainLen=3): meta.display_name \|\| meta.name \|\| ""<br>多段 \|\| 兜底链存在优先级隐式漂移与兼容链增长风险；值域不明时可能覆盖合法 falsy。 | 优先收敛到单一 helper/normalize；能用 ?? 就用 ??；必要时用显式 null/undefined 判定并补迁移计划。 |

### 6.2 Templates: `or` / `default` 兜底点
- 扫描统计：`or` 表达式 45 个；`default` filter 16 个。

| 位置 | 类型 | 兜底判定 | 描述 | 建议 |
|---|---|---|---|---|
| `app/templates/accounts/account-classification/permissions/policy-center-view.html:2` | 回退 | 合理回退 | <div class="permission-policy-center" id="{{ permissions_id\|default('permissionsConfig') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/accounts/classification_statistics.html:29` | 回退 | 合理回退 | {% for option in classification_options or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/classification_statistics.html:57` | 回退 | 合理回退 | {% for option in database_type_options or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/classification_statistics.html:72` | 回退 | 合理回退 | {% for option in instance_options or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/classification_statistics.html:80` | 回退 | 合理回退 | <input type="hidden" name="rule_id" id="rule_id" value="{{ selected_rule_id or '' }}"><br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/classification_statistics.html:108` | 回退 | 危险兜底 | {% set selected_status = (selected_rule_status or 'active') %}<br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/ledgers.html:27` | 回退 | 危险兜底 | <div id="accounts-page-root" data-current-db-type="{{ current_db_type or 'all' }}" data-export-url="/api/v1/accounts/ledgers/exports"><br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/ledgers.html:46` | 回退 | 需人工复核 | class="btn {% if not current_db_type or current_db_type == 'all' %}btn-primary{% else %}btn-outline-primary border-2 fw-bold{% endif %}"<br>Jinja or 走 truthy 语义，值域不明时可能覆盖合法 falsy | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:9` | 回退 | 合理回退 | {% set total_accounts = stats.total_accounts or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:10` | 回退 | 合理回退 | {% set active_accounts = stats.active_accounts or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:11` | 回退 | 合理回退 | {% set locked_accounts = stats.locked_accounts or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:12` | 回退 | 合理回退 | {% set total_instances = stats.total_instances or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:35` | 回退 | 合理回退 | {% call metric_card('总账户数', value=(stats.total_accounts or 0), icon_class='fas fa-users', data_stat_key='total_accounts') %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:48` | 回退 | 合理回退 | {% call metric_card('活跃账户', value=(stats.active_accounts or 0), icon_class='fas fa-user-check', tone='success', data_stat_key='active_accounts') %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:55` | 回退 | 合理回退 | {% call metric_card('锁定账户', value=(stats.locked_accounts or 0), icon_class='fas fa-user-lock', tone='warning', data_stat_key='locked_accounts') %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:62` | 回退 | 合理回退 | {% call metric_card('在线实例', value=(stats.total_instances or 0), icon_class='fas fa-server', tone='info', data_stat_key='total_instances') %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/accounts/statistics.html:107` | 回退 | 合理回退 | <span class="status-pill status-pill--muted">已删除 {{ type_stats.deleted\|default(0) }}</span><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/admin/scheduler/index.html:6` | 回退 | 危险兜底 | {% block title %}定时任务管理 - {{ config.APP_NAME or '鲸落' }}{% endblock %}<br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/auth/list.html:7` | 回退 | 危险兜底 | {% block title %}用户管理 - {{ config.APP_NAME or '鲸落' }}{% endblock %}<br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/base.html:2` | 回退 | 危险兜底 | {%- set app_name = config.APP_NAME or '鲸落' -%}<br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/base.html:62` | 回退 | 合理回退 | <body data-page="{{ page_id\|default('') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/base.html:214` | 回退 | 合理回退 | <div class="main-content" data-density="{{ page_density\|default('regular') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/base.html:249` | 回退 | 危险兜底 | {{ config.APP_VERSION or 'unknown' }} - 数据同步管理平台 \|<br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/filters/macros.html:20` | 回退 | 合理回退 | {% set option_list = options or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/filters/macros.html:36` | 回退 | 危险兜底 | <option value="">{{ placeholder or '全部' }}</option><br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/filters/macros.html:45` | 回退 | 合理回退 | {% if value in (current_value or []) %}selected{% endif %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/filters/macros.html:122` | 回退 | 合理回退 | {% for option in options or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/filters/macros.html:141` | 回退 | 合理回退 | {% for option in options or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/filters/macros.html:152` | 回退 | 合理回退 | {% set selected_values = selected or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/filters/macros.html:154` | 回退 | 合理回退 | {% for option in options or [] %}<br>右值为空列表，主要用于把 None/undefined 规整为可迭代对象 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/forms/macros.html:13` | 回退 | 合理回退 | value="{{ value if value is not none else field.default or '' }}"<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/forms/macros.html:29` | 回退 | 合理回退 | >{{ value if value is not none else field.default or '' }}</textarea><br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/forms/macros.html:42` | 回退 | 危险兜底 | <option value="">{{ field.placeholder or '请选择' }}</option><br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/forms/macros.html:59` | 回退 | 需人工复核 | {% if value or field.default %}checked{% endif %}<br>Jinja or 走 truthy 语义，值域不明时可能覆盖合法 falsy | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/components/ui/macros.html:30` | 回退 | 合理回退 | <button type="button" class="btn-close {{ extra_class\|default('') }}" data-bs-dismiss="{{ dismiss_target }}" aria-label="{{ aria_label\|default('关闭') }}"></button><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/macros.html:30` | 回退 | 合理回退 | <button type="button" class="btn-close {{ extra_class\|default('') }}" data-bs-dismiss="{{ dismiss_target }}" aria-label="{{ aria_label\|default('关闭') }}"></button><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/metric_card.html:5` | 回退 | 合理回退 | class="card wf-metric-card {{ card_class\|default('') }}"<br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:2` | 回退 | 合理回退 | <div class="modal fade {{ modal_class\|default('') }}" id="{{ modal_id }}" tabindex="-1" aria-labelledby="{{ modal_label_id }}" aria-hidden="true" data-bs-backdrop="{{ backdrop\|default('true') }}" data-bs-keyboard="{{ keyboard\|default('true') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:2` | 回退 | 合理回退 | <div class="modal fade {{ modal_class\|default('') }}" id="{{ modal_id }}" tabindex="-1" aria-labelledby="{{ modal_label_id }}" aria-hidden="true" data-bs-backdrop="{{ backdrop\|default('true') }}" data-bs-keyboard="{{ keyboard\|default('true') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:2` | 回退 | 合理回退 | <div class="modal fade {{ modal_class\|default('') }}" id="{{ modal_id }}" tabindex="-1" aria-labelledby="{{ modal_label_id }}" aria-hidden="true" data-bs-backdrop="{{ backdrop\|default('true') }}" data-bs-keyboard="{{ keyboard\|default('true') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:3` | 回退 | 合理回退 | <div class="modal-dialog {{ dialog_class\|default('') }} {{ 'modal-dialog-scrollable' if scrollable else '' }} {{ 'modal-xl' if size == 'xl' else 'modal-lg' if size == 'lg' else 'modal-sm' if size == 'sm' else '' }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:5` | 回退 | 合理回退 | <div class="modal-header {{ header_class\|default('') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:7` | 回退 | 合理回退 | {{ btn_close('modal', close_aria_label\|default('关闭'), close_button_class\|default('')) }}<br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:7` | 回退 | 合理回退 | {{ btn_close('modal', close_aria_label\|default('关闭'), close_button_class\|default('')) }}<br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:9` | 回退 | 合理回退 | <div class="modal-body {{ body_class\|default('') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/components/ui/modal.html:13` | 回退 | 合理回退 | <div class="modal-footer {{ footer_class\|default('') }}"><br>default 未开启 boolean=true（默认仅对 undefined 生效） | 通常可保留；若需要把 None 也视为缺省，请在模板侧明确约定值域并补注释。 |
| `app/templates/databases/ledgers.html:23` | 回退 | 危险兜底 | data-current-db-type="{{ current_db_type or 'all' }}"><br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/detail.html:265` | 回退 | 合理回退 | {% set active_accounts = account_summary.active or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/detail.html:266` | 回退 | 合理回退 | {% set deleted_accounts = account_summary.deleted or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/detail.html:267` | 回退 | 合理回退 | {% set superuser_accounts = account_summary.superuser or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/statistics.html:9` | 回退 | 合理回退 | {% set total_instances = stats.total_instances or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/statistics.html:10` | 回退 | 合理回退 | {% set active_instances = stats.active_instances or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/statistics.html:11` | 回退 | 合理回退 | {% set inactive_instances = stats.inactive_instances or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/statistics.html:12` | 回退 | 合理回退 | {% set deleted_instances = stats.deleted_instances or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/statistics.html:55` | 回退 | 合理回退 | {% call metric_card('数据库类型', value=(stats.db_types_count or 0), icon_class='fas fa-layer-group', tone='info', data_stat_key='db_types_count') %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/instances/statistics.html:207` | 回退 | 危险兜底 | <span class="chip-outline chip-outline--muted"><i class="fas fa-tag me-1"></i>{{ stat.version or '未知版本' }}</span><br>Jinja or 走 truthy 语义，可能把合法 falsy(0/""/false) 覆盖为右值 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/tags/index.html:33` | 回退 | 需人工复核 | {% set stats = tag_stats or {'total': 0, 'active': 0, 'inactive': 0, 'category_count': 0} %}<br>Jinja or 走 truthy 语义，值域不明时可能覆盖合法 falsy | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/tags/index.html:34` | 回退 | 合理回退 | {% set total_tags = stats.total or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/tags/index.html:35` | 回退 | 合理回退 | {% set active_tags = stats.active or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/tags/index.html:36` | 回退 | 合理回退 | {% set inactive_tags = stats.inactive or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |
| `app/templates/tags/index.html:37` | 回退 | 合理回退 | {% set tag_categories = stats.category_count or 0 %}<br>右值为中性默认值(0/""/false/None)，通常用于缺省规整 | 若值域可能包含 0/""/false 且需要保留，避免使用 `or`；可改为显式判定（如 `is not none`）或改用 `default` 且谨慎处理 None。 |

## 7. 修复优先级建议
- P0：MetricCard 统一（`instances/detail` 的 `instance-stat-card*` 模板 + CSS）——会持续制造 UI/样式漂移与门禁失效。
- P0：移除 JS 硬编码颜色 `#3498db` ——直接违反颜色 Token 化强约束，且容易引发更多私有 fallback。
- P1：可复用组件固定 id（filters 宏）——存在多实例冲突风险，且会诱发全局 selector 与兼容链增长。
- P1：直接 `new gridjs.Grid` ——建议明确“modal 表格”的官方封装入口后再迁移，避免标准口径继续分裂。
- P2：`or/default` 与 `||/??` 兜底链治理 ——优先从多段链与跨层 fallback 开始收敛，逐步减少“值域不明导致的危险兜底”。

---
### 附：本次扫描结果摘要（机器输出）
- JS：文件 116，解析失败 0。
- Templates：文件 54，解析失败 0。
- CSS：文件 43，未定义 Token 引用 0，非 variables.css 的硬编码颜色 0。
- 模板内联事件：0；`btn-close` 英文 aria-label：0；inline px height/width：0。
- 组件固定 id：4；`*-stat-card` 类出现次数：6。
