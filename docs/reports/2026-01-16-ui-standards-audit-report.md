> Status: 完成（只读静态审计）
> Owner: Codex
> Created: 2026-01-16
> Updated: 2026-01-16
> Scope: `docs/Obsidian/standards/ui/**/*.md` + `app/static/js/**/*.js`（仅项目代码；不扫描 `app/static/vendor/**`）+ `app/templates/**/*.html` + `app/static/css/**/*.css`
> Related: `docs/Obsidian/standards/ui/README.md`, `docs/Obsidian/standards/ui/layer/README.md`, `docs/Obsidian/standards/ui/template-event-binding-standards.md`, `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md`, `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md`, `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md`, `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md`, `docs/Obsidian/standards/ui/grid-standards.md`, `docs/Obsidian/standards/ui/vendor-library-usage-standards.md`, `docs/Obsidian/standards/ui/layout-sizing-guidelines.md`, `docs/Obsidian/standards/ui/design-token-governance-guidelines.md`, `docs/Obsidian/standards/ui/color-guidelines.md`

# 前端/UI 标准全量审计报告 (2026-01-16)

## 1. 目标

- 找出标准冲突：同一主题出现相互矛盾的 MUST/MUST NOT/等价强制措辞，或索引/依赖图 vs 文本口径不一致。
- 找出标准的模糊定义/不可执行点：术语未定义、触发条件不清、例外未写明、缺少可验证规则等。
- 基于明确可执行的强约束（MUST/MUST NOT/等价强制措辞），定位前端代码违规点（严格限定扫描范围）。
- 盘点防御/兼容/回退/适配逻辑（仅限扫描范围），重点关注 `||`/`??`/模板 `or` 的兜底链与数据结构兼容。

## 2. 审计方法与证据

> [!important] 范围约束声明
> 本次只读静态审计严格限定在「标准范围 + 前端代码扫描范围」内：不扫描、也不在报告中判定/列出范围外的任何代码问题（例如 `app/**/*.py`、`scripts/**`、`tests/**` 等）。如某问题与范围外代码有关，仅在方法里说明“按范围忽略”，不进入违规清单。

### 2.1 已执行的仓库门禁脚本

- `./scripts/ci/btn-close-aria-guard.sh`：通过（未发现缺失/英文混用）。
- `./scripts/ci/inline-handler-guard.sh`：通过（命中 0）。
- `./scripts/ci/inline-px-style-guard.sh`：通过（命中 0）。
- `./scripts/ci/css-token-guard.sh`：通过（未发现未定义 token）。
- `./scripts/ci/button-hierarchy-guard.sh`：通过（未发现 `.btn { border:none/0 }` 覆盖）。
- `./scripts/ci/danger-button-semantics-guard.sh`：通过（未发现 `text-danger` 伪装危险按钮）。
- `./scripts/ci/grid-wrapper-log-guard.sh`：通过（未发现 `console.log`）。
- `./scripts/ci/pagination-param-guard.sh`：通过（使用 `limit`，未使用 `page_size`）。
- `./scripts/ci/tag-selector-filter-id-guard.sh`：通过（该门禁只覆盖 TagSelectorFilter 的固定 id 场景）。
- `./scripts/ci/browser-confirm-guard.sh`：通过（但 JS AST 扫描发现 1 处 `confirm?.(`，见 4.1；说明该门禁对 optional chaining 存在漏检——本次只记录，不修改脚本）。

> [!note]
> 未运行 `./scripts/ci/eslint-report.sh quick`：该脚本会在 `docs/reports/` 生成额外输出文件，超出本次“只允许写入审计报告文件”的约束。

### 2.2 已执行的补充静态扫描

- CSS（补充扫描，不作为唯一判定依据）：对 `app/static/css/**/*.css` 做 token 定义/引用一致性、颜色字面量（`#hex`/`rgb(a)`）出现位置检查。
- `rg -n` 仅用于导航/交叉验证（例如确认门禁脚本与 AST 扫描结果不一致的场景），不作为任何违规结论的唯一证据。

### 2.3 AST 语义扫描

#### 2.3.1 JavaScript（espree / ESLint AST）

- 覆盖范围：解析 `app/static/js/**/*.js` 共 103 个文件（排除 `app/static/vendor/**`）。
- 解析器：`espree`（开启 `loc: true` / `range: true`），行号来自 AST 的 `loc.start.line/loc.end.line`。
- 扫描模式（至少覆盖）：
  - `||`/`??` 多段兜底链（`LogicalExpression`）与局部兼容模式（如 `obj.new || obj.old`）。
  - 高风险确认：`confirm()` 调用（`CallExpression`）。
  - Grid.js 入口：`new GridWrapper(...)` / `new gridjs.Grid(...)`（`NewExpression`）。
  - 分层/全局：基于路径推断 layer（services/stores/views/ui/page_entry），并扫描 `window.*`/`global.*` 访问点（用于对照 allowlist 规则）。
  - XSS 风险信号：`innerHTML = ...`（仅作为“需人工复核”的风险提示，不强判违规）。

#### 2.3.2 Jinja2 模板（jinja2.Environment().parse AST）

- 覆盖范围：解析 `app/templates/**/*.html` 共 55 个文件。
- 解析器：`jinja2.Environment().parse`，行号来自 AST 节点的 `lineno`（例如 `nodes.Or.lineno`）。
- 扫描模式（至少覆盖）：
  - 模板 `or` 兜底链（`nodes.Or`）。
  - `default` filter（`nodes.Filter(name='default')`），区分是否启用 `boolean=true`。
  - 基于 `TemplateData` 的静态 HTML 风险信号：`on*=` 内联事件处理器、`style="height/width: Npx"`、组件模板中的“固定 id”属性（仅在能被 AST 节点定位时记录）。

#### 2.3.3 CSS（补充扫描）

- 覆盖范围：`app/static/css/**/*.css` 共 47 个文件。
- 规则：
  - `var(--xxx)` 引用必须在 `app/static/css/**` 内存在 `--xxx:` 定义（排除 `--bs-*` 前缀）。
  - `variables.css` 之外不应出现颜色字面量（按 `: #hex`/`: rgb(a)(` 形式抽样检查）。

### 2.4 约束索引（强约束摘录/对照用）

| 约束(简述) | 位置 | 影响范围 | 说明 |
|---|---|---|---|
| 禁止浏览器 `confirm()`；必须使用 `UI.confirmDanger` | `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:37`, `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:38` | 高风险操作的前端确认交互 | 统一样式/文案/可审查的 impacts 与结果入口 |
| Sync/Batch 必须使用 `UI.resolveAsyncActionOutcome`；禁止扩散 `message || error` 等互兜底链 | `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:43`, `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:44` | 触发异步任务/批量操作的 JS 入口 | 避免“每页一套 started/failed/unknown”与兜底链无限增长 |
| 可复用组件禁止固定 `id`；必须提供 scope 容器并派生内部 `id` | `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33`, `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:42`, `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:44` | 组件模板与组件 JS | 避免同页多实例冲突与“静默命中错误节点” |
| 模板禁止内联事件处理器；必须用 `data-action` 等 hook | `docs/Obsidian/standards/ui/template-event-binding-standards.md:34`, `docs/Obsidian/standards/ui/template-event-binding-standards.md:35` | `app/templates/**` | 统一事件绑定落点，降低安全与维护成本 |
| `btn-close` 必须 `aria-label="关闭"` 且优先用宏输出 | `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:31`, `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:33` | Alert/Modal/Toast | 避免英文可访问名与漏标 |
| 模板禁止新增 `style="height/width: Npx"` | `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:60` | `app/templates/**` | 尺寸应收敛到 Token + class |
| `var(--xxx)` 必须有定义并通过门禁 | `docs/Obsidian/standards/ui/design-token-governance-guidelines.md:39`, `docs/Obsidian/standards/ui/design-token-governance-guidelines.md:40` | `app/static/css/**` | 避免 Token 未定义导致样式回退 |
| `.btn { border:none/0 }` 等破坏性覆盖禁止 | `docs/Obsidian/standards/ui/button-hierarchy-guidelines.md:41` | `app/static/css/**` | 防止 `btn-outline-*` 丢失语义边界 |
| Views 必须遵循 `window.*` allowlist；不得读取 allowlist 外全局 | `docs/Obsidian/standards/ui/layer/views-layer-standards.md:54`, `docs/Obsidian/standards/ui/layer/views-layer-standards.md:55` | `app/static/js/modules/views/**` | 入口读全局，下层靠注入/封装 |
| Grid 列表页必须走 `Views.GridPage.mount`；页面脚本禁止 `new GridWrapper/gridjs.Grid` | `docs/Obsidian/standards/ui/grid-standards.md:40`, `docs/Obsidian/standards/ui/grid-standards.md:41`, `docs/Obsidian/standards/ui/grid-standards.md:42` | Grid 列表页 wiring | 收敛 wiring 与分页/排序约束 |

## 3. 标准冲突或歧义

### 3.1 Page Entry 的“物理目录 vs 逻辑层”口径容易误判

- 证据：Page Entry 标准明确提到入口脚本“legacy 可能位于 `app/static/js/modules/views/**`” (`docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md:37`)；但 Views 标准 scope 又写明“`modules/views/**` 不含 Page Entry” (`docs/Obsidian/standards/ui/layer/views-layer-standards.md:13`, `docs/Obsidian/standards/ui/layer/views-layer-standards.md:38`)。
- 影响（实现分裂/兜底链增长）：
  - 审查与门禁会出现“同一个文件在不同人眼里属于不同层”的情况，导致 allowlist、依赖注入、错误处理等规则被不同方式执行。
  - 迁移期容易出现“为了让旧入口跑起来”而在 Views 内添加 allowlist 外全局读取 + `||` 兜底链（例如 `window.X || legacyX`），形成长期债。
- 建议：在标准中补充一个可验证的判定规则（例如“满足 `window.<PageId> = { mount(...) }` 的即视为 Page Entry，无论物理路径”），并配套静态扫描门禁。

### 3.2 vendor global allowlist 与“业务代码不得直接调用 vendor global”的张力

- 证据：vendor 标准要求“业务代码优先使用项目封装，不直接调用 vendor global” (`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:29`)；同时分层 SSOT 允许 Views/Page Entry 读取 vendor globals (`docs/Obsidian/standards/ui/layer/README.md:74`, `docs/Obsidian/standards/ui/layer/README.md:83`)。
- 影响（实现分裂/回退链增长）：
  - 在“允许读取”与“不得直接调用”之间缺少可执行边界，容易出现：同一库（如 Chart/Grid/Bootstrap）既有人直接 new，又有人走封装，导致升级/locale/cleanup 策略分叉。
  - 后续修复往往只能通过在各处加兼容分支与兜底链（`global.Chart || legacyChart` / `new Chart(...)` vs `UI.createChart(...)`）来维持。
- 建议：在 allowlist 章节补充一句“允许读取不等于允许直用；除封装层/adapter 外，业务代码仍需通过封装入口”，并明确“封装层的物理路径范围”。

### 3.3 DOMHelpers 必须用 vs 原生 DOM API 允许用：口径不一致

- 证据：vendor 标准在 Umbrella.js 章节写明“DOM: MUST 使用 `window.DOMHelpers`” (`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:134`)；但 Views 标准对事件绑定允许 `DOMHelpers` 或原生 `addEventListener` (`docs/Obsidian/standards/ui/layer/views-layer-standards.md:61`)。
- 影响（实现分裂/适配层漂移）：
  - 如果按 vendor 标准严格执行，则大量 `document.getElementById/querySelector` 会被视为违规；但 Views 标准没有给出等价禁止项，导致 reviewer 口径漂移。
  - 团队可能会在“必须 DOMHelpers”的压力下写 wrapper/facade（再加 `||` 兜底），而不是真正收敛到单一入口。
- 建议：明确 DOMHelpers 的强制范围：例如“DOM 查询/写入必须走 DOMHelpers，但事件绑定允许原生 addEventListener”；并给出可门禁的规则（哪些 API 禁止/允许）。

### 3.4 “可复用组件禁止固定 id”缺少对“全站单例组件”的例外说明

- 证据：标准明确禁止可复用组件内部固定 id (`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33`)；但仓库存在明显“全站单例”倾向的组件（如危险确认 modal）仍使用固定 id（见 4.2）。
- 影响（实现分裂/兜底链增长）：
  - 如果不写明例外，实践上会出现“标准被选择性忽略”；反过来若强推改造，可能导致对单例组件的调用方再加一层兼容逻辑（旧 id/new id 互兜底）。
- 建议：二选一收敛：
  - A) 标准补充“单例组件必须显式声明并确保全站唯一”的例外；
  - B) 继续坚持“禁止固定 id”，则要求单例组件也通过 `scope` 参数化，并在 base 模板只实例化一次。

### 3.5 Grid.js 标准对“非列表页场景（如 Modal 内表格）”缺少明确口径

- 证据：Grid 标准适用范围描述为“所有 Grid.js 列表页…以及 `GridWrapper` 调用方” (`docs/Obsidian/standards/ui/grid-standards.md:33`)，并禁止页面脚本 `new gridjs.Grid(...)` (`docs/Obsidian/standards/ui/grid-standards.md:42`)；但当前存在在 Modal 内直接 `new gridjs.Grid` 的实现（见 6.1 的清单项 `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:199`）。
- 影响（实现分裂/适配层漂移）：
  - 若 Modal 表格不纳入 GridPage/Wrapper 生态，Grid.js 的 wiring、destroy、分页参数、样式密度会在不同页面各自演化。
- 建议：在标准中补充“Modal 内 Grid.js”应走的统一入口（可以是 `Views.GridPage` 的子能力，或新增 `Views.ModalGrid`/UI module），否则至少明确允许直接 new 的范围与约束（destroy、分页参数、样式 token 等）。

## 4. 不符合标准的代码行为(需要修复)

### 4.1 使用浏览器 `confirm()`（禁止项）

- 结论：Views 中存在 `confirm()` 调用（带 optional chaining），违反“禁止浏览器 confirm”的强约束。
- 标准依据：`docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:37`, `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:38`
- 代码证据（JS AST）：`app/static/js/modules/views/history/sessions/sync-sessions.js:569`
- 影响：确认交互样式不可控；无法统一 impacts/结果入口；与门禁口径不一致（脚本漏检 `confirm?.(`）。
- 修复建议：
  - 用 `UI.confirmDanger({...})` 替换 `confirm?.(...)`；补齐 impacts（会话 id/名称/影响范围）与结果入口（如取消后跳转/刷新）。
  - 同时建议补强门禁脚本的匹配模式（至少覆盖 `confirm?.(`），但该脚本位于范围外，本报告只提出方案。
- 验证方式：
  - AST 复扫：确保 `CallExpression` 中不存在 `*.confirm` / `confirm` 调用。
  - 交叉验证（辅助）：`rg -n "\\.confirm\\?\\." app/static/js/modules/views/history/sessions/sync-sessions.js` 应无命中。

### 4.2 可复用组件内部存在固定 `id`（禁止项）

- 结论：组件模板存在固定 `id="instance"/"database"/"dangerConfirmModal"/...`，违反“可复用组件禁止固定 id”的强约束。
- 标准依据：`docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:33`, `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:42`, `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:44`
- 代码证据（Jinja AST / TemplateData）：
  - `app/templates/components/filters/macros.html:109`（`id="instance"`）
  - `app/templates/components/filters/macros.html:128`（`id="database"`）
  - `app/templates/components/ui/danger_confirm_modal.html:3`（`id="dangerConfirmModal"`）
  - `app/templates/components/ui/danger_confirm_modal.html:12`（`id="dangerConfirmModalLabel"`）
- 影响：
  - 宏/组件被同页多次复用时会出现 id 冲突，导致 label/aria 引用错位、事件绑定命中错误节点、更新错位等“静默错误”。
  - 单例组件（如危险确认 modal）当前实现与标准口径存在张力，容易促使调用方增加“旧 id/new id”兼容链。
- 修复建议：
  - `components/filters/macros.html`：为 `instance_filter`/`database_filter` 增加 `scope` 参数，并将 `id` 改为 `<scope>-instance`/`<scope>-database` 派生；调用方在页面级确保 scope 唯一。
  - `components/ui/danger_confirm_modal.html`：改为接收 `scope` 并派生 modal id/label id；如坚持单例，也应在 base 模板只渲染一次并在标准里显式声明单例例外（避免后续漂移）。
- 验证方式：
  - AST 复扫：组件目录内不应再出现静态 `id="..."`。
  - 交叉验证（辅助）：`rg -n "id=\"(instance|database|dangerConfirmModal)\"" app/templates/components` 应无命中。

### 4.3 Views 读取 allowlist 外全局 `window.EventBus`

- 结论：Views 组件直接读取 `window.EventBus`，违反“Views 禁止读取 allowlist 外全局”的强约束。
- 标准依据：`docs/Obsidian/standards/ui/layer/views-layer-standards.md:54`, `docs/Obsidian/standards/ui/layer/views-layer-standards.md:55`
- 代码证据（JS AST）：`app/static/js/modules/views/components/charts/manager.js:19`
- 影响：形成隐式全局耦合（EventBus 的存在性、事件命名与生命周期不再可控）；后续迁移只能通过注入/回退分支修补。
- 修复建议：
  - 将“filters:* 事件监听”上移到 Page Entry 或 Store（由 store 私有 emitter 订阅并驱动 view 更新）；或将该监听逻辑下沉到 UI Modules，并由 view 只接收注入的 emitter。
  - 若确有跨组件观测需求，标准侧应明确“Views 是否允许 EventBus”并写入 allowlist（否则保持禁止）。
- 验证方式：
  - AST 复扫：Views 层不再出现 `window.EventBus` 的 `MemberExpression`。
  - 交叉验证（辅助）：`rg -n "window\.EventBus" app/static/js/modules/views` 应无命中。

### 4.4 批量/异步任务反馈未统一 outcome helper，且扩散 `message || ...` / `error || ...` 兜底链

- 结论：批量操作在调用点自行处理 `success` 分支并扩散 `message || ...` / `error || ...` 兜底链，未使用 `UI.resolveAsyncActionOutcome`。
- 标准依据：`docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:43`, `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:44`
- 代码证据（JS AST）：
  - `app/static/js/modules/views/instances/list.js:873`（`response?.message || '批量移入回收站失败'`）
  - `app/static/js/modules/views/instances/list.js:876`（`response?.message || '批量移入回收站成功'`）
  - `app/static/js/modules/views/instances/list.js:913`（`result?.error || '批量测试失败'`）
  - `app/static/js/modules/views/instances/list.js:916`（`result?.message || '批量测试任务已提交'`）
  - `app/static/js/modules/views/instances/list.js:920`（`error?.message || '批量测试失败'`）
- 影响：
  - started/failed/unknown 的文案与行为无法统一；unknown 分支的可观测性与结果入口（会话中心）容易缺失。
  - 容易推动 `message || error || fallback` 在各处蔓延，形成长期兼容链与语义漂移。
- 修复建议：
  - 在批量/异步任务的响应处理统一改为：
    - `const outcome = UI.resolveAsyncActionOutcome(resp, { action, startedMessage, failedMessage, unknownMessage, resultUrl: '/history/sessions', resultText: '...' })`
    - 统一根据 `outcome.tone` 选择 toast 方法；确保 unknown 分支可观测。
  - 将 `message || ...`、`error || ...` 的兜底链收敛到 outcome helper 内或统一 `UI.resolveErrorMessage`（避免散落到各调用点）。
- 验证方式：
  - AST 复扫：对应调用点不再出现 `response?.message || ...` / `result?.error || ...` 兜底链，且出现 `UI.resolveAsyncActionOutcome(...)` 调用。
  - 交叉验证（辅助）：在文件内搜索 `resolveAsyncActionOutcome` 应有命中。

## 5. 符合标准的关键点(通过项摘要)

- 模板内联事件处理器命中 0（Jinja AST 未发现 `on*=`），符合 `docs/Obsidian/standards/ui/template-event-binding-standards.md:34`。
- 模板 `style="height/width: Npx"` 命中 0，符合 `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:60`。
- `btn-close` 可访问名称门禁通过，且宏集中输出：`docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:33` 与 `app/templates/components/ui/macros.html:6` 的用法一致。
- CSS Token 门禁通过，补充扫描也未发现未定义 token：符合 `docs/Obsidian/standards/ui/design-token-governance-guidelines.md:39`。
- JS AST 扫描未发现 `app/static/js/modules/**` 直接调用 `dayjs()`/`numeral()`/`u()`（vendor global 直用），与 `docs/Obsidian/standards/ui/vendor-library-usage-standards.md:29` 的方向一致。

## 6. 防御/兼容/回退/适配逻辑清单(重点: ||/or 兜底)

> [!note]
> 本节清单在扫描范围内提供以下“全量/近全量”覆盖：
> - JS：字段别名/兼容模式（AST 识别 37 处）+ guard clause（AST 识别 9 处）。
> - 模板：`or` 表达式（Jinja AST 识别 36 处）+ `default` filter（Jinja AST 识别 18 处）。
> 另对少量“适配/桥接”场景单独列出。

### 6.1 JavaScript：`||`/`??` 字段别名与回退（AST 识别到的兼容模式全量 37 处）

- 位置：`app/static/js/common/grid-wrapper.js:66`
  类型：兼容（需人工复核）
  描述：col.id || col.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/stores/sync_sessions_store.js:381`
  类型：兼容/数据结构（需人工复核）
  描述：response?.data?.pagination || response?.pagination（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/theme/color-tokens.js:72`
  类型：防御/回退（合理回退）
  描述：document.head || document.documentElement（判定理由：DOM 节点对象回退（head 缺失时用 documentElement），不涉及合法 falsy 覆盖。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/ui/modal.js:100`
  类型：兼容（需人工复核）
  描述：confirmButton.dataset.originalHtml || confirmButton.innerHTML（判定理由：字符串回退，若 originalHtml 允许为空字符串，|| 会覆盖；建议改用 ?? 或显式 undefined 判定。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/accounts/account-classification/index.js:694`
  类型：防御/回退（合理回退）
  描述：evt?.currentTarget || evt?.target（判定理由：事件目标对象回退（currentTarget 缺失时回退 target），不涉及合法 falsy 覆盖。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js:104`
  类型：兼容/数据结构（合理回退）
  描述：response?.data?.classification ?? response?.classification（判定理由：使用 ?? 仅在 null/undefined 时回退，避免覆盖合法 falsy。）
  建议：迁移期保留；完成后端/前端字段收敛后删除旧字段回退。

- 位置：`app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js:263`
  类型：兼容/数据结构（合理回退）
  描述：response?.data?.rule ?? response?.rule（判定理由：使用 ?? 仅在 null/undefined 时回退，避免覆盖合法 falsy。）
  建议：迁移期保留；完成后端/前端字段收敛后删除旧字段回退。

- 位置：`app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js:315`
  类型：兼容/数据结构（合理回退）
  描述：response?.data?.rule ?? response?.rule（判定理由：使用 ?? 仅在 null/undefined 时回退，避免覆盖合法 falsy。）
  建议：迁移期保留；完成后端/前端字段收敛后删除旧字段回退。

- 位置：`app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js:337`
  类型：兼容（需人工复核）
  描述：rule.classification_name || rule.classification?.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/accounts/ledgers.js:189`
  类型：兼容/字段别名（需人工复核）
  描述：source.search || source.q（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/accounts/ledgers.js:351`
  类型：兼容（需人工复核）
  描述：tag?.display_name || tag?.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/accounts/ledgers.js:354`
  类型：兼容（需人工复核）
  描述：tag?.display_name || tag?.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/accounts/ledgers.js:671`
  类型：回退（合理回退）
  描述：toast?.warning || toast?.info（判定理由：方法存在性回退（toast 方法缺失时降级到另一个方法），不涉及合法 falsy 覆盖。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/views/admin/partitions/charts/partitions-chart.js:656`
  类型：兼容（需人工复核）
  描述：payload?.metrics || payload?.state?.metrics（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:108`
  类型：兼容/字段别名（需人工复核）
  描述：job.func || job.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:262`
  类型：兼容/字段别名（需人工复核）
  描述：originalJob.func || originalJob.id（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/components/charts/manager.js:681`
  类型：回退（合理回退）
  描述：PERIOD_TEXT.daily || PERIOD_TEXT.default（判定理由：配置对象回退（缺失时回退 default），对象为 truthy，合法 falsy 风险低。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/views/components/charts/transformers.js:243`
  类型：兼容/规范化（合理回退）
  描述：item.total_size_mb ?? item.avg_size_mb（判定理由：使用 ?? 仅在 null/undefined 时回退，避免覆盖合法 falsy。）
  建议：迁移期保留；完成后端/前端字段收敛后删除旧字段回退。

- 位置：`app/static/js/modules/views/components/tags/tag-selector-view.js:238`
  类型：兼容/规范化（需人工复核）
  描述：item.label || item.value（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/credentials/modals/credential-modals.js:219`
  类型：兼容/数据结构（需人工复核）
  描述：response.data?.credential || response.data（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/databases/ledgers.js:247`
  类型：兼容/字段别名（需人工复核）
  描述：tag.display_name || tag.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/databases/ledgers.js:250`
  类型：兼容（需人工复核）
  描述：tag?.display_name || tag?.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/databases/ledgers.js:270`
  类型：兼容/字段别名（需人工复核）
  描述：meta?.db_type || meta?.instance?.db_type（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/history/logs/log-detail.js:130`
  类型：回退（合理回退）
  描述：toast.warning || toast.info（判定理由：方法存在性回退（toast 方法缺失时降级到另一个方法），不涉及合法 falsy 覆盖。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/views/history/logs/log-detail.js:131`
  类型：回退（合理回退）
  描述：toast.warning || toast.info（判定理由：方法存在性回退（toast 方法缺失时降级到另一个方法），不涉及合法 falsy 覆盖。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/views/history/logs/logs.js:315`
  类型：兼容（需人工复核）
  描述：sourceValues?.search || sourceValues?.q（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/history/logs/logs.js:330`
  类型：兼容/字段别名（需人工复核）
  描述：source.search || source.q（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/history/sessions/session-detail.js:125`
  类型：回退（合理回退）
  描述：toast.warning || toast.info（判定理由：方法存在性回退（toast 方法缺失时降级到另一个方法），不涉及合法 falsy 覆盖。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/views/history/sessions/session-detail.js:126`
  类型：回退（合理回退）
  描述：toast.warning || toast.info（判定理由：方法存在性回退（toast 方法缺失时降级到另一个方法），不涉及合法 falsy 覆盖。）
  建议：保留该回退以提升健壮性；但应确保主依赖在正常路径可用，并避免在业务层无限扩散类似兜底链。

- 位置：`app/static/js/modules/views/history/sessions/session-detail.js:365`
  类型：兼容/字段别名（需人工复核）
  描述：session.created_at || session.started_at（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/instances/detail.js:1362`
  类型：兼容（需人工复核）
  描述：data?.error || data?.message（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/instances/list.js:515`
  类型：兼容/字段别名（需人工复核）
  描述：tag.display_name || tag.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/instances/list.js:521`
  类型：兼容（需人工复核）
  描述：tag?.display_name || tag?.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/instances/list.js:637`
  类型：兼容（需人工复核）
  描述：source?.search || source?.q（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/instances/modals/instance-modals.js:137`
  类型：兼容/数据结构（需人工复核）
  描述：resp?.data?.instance || resp?.data（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/tags/batch-assign.js:191`
  类型：兼容（需人工复核）
  描述：tag?.display_name || tag?.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

- 位置：`app/static/js/modules/views/tags/batch-assign.js:317`
  类型：兼容/字段别名（需人工复核）
  描述：tag.display_name || tag.name（判定理由：使用 || 的 truthy/falsy 兜底可能覆盖合法 falsy；仅从 AST 难以确认值域。）
  建议：如值域允许合法 falsy（例如空字符串/0/false），优先改为 `??` 或显式 `x === null || x === undefined` 判定；迁移完成后删除旧字段/旧 key。

### 6.2 JavaScript：guard clause（缺依赖/缺 DOM 的防御性短路，AST 识别到 9 处）

- 位置：`app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js:154`
  类型：防御（合理回退）
  描述：if (!form) return;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:312`
  类型：防御（合理回退）
  描述：if (!selected) return false;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:1288`
  类型：防御（合理回退）
  描述：if (!selected) return false;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:69`
  类型：防御（合理回退）
  描述：if (!field) return;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js:129`
  类型：防御（合理回退）
  描述：if (!raw) return {};（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/instances/modals/instance-modals.js:129`
  类型：防御（合理回退）
  描述：if (!instanceId) return;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/instances/modals/instance-modals.js:187`
  类型：防御（合理回退）
  描述：if (!payload) return;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/instances/modals/instance-modals.js:274`
  类型：防御（合理回退）
  描述：if (!submitBtn) return;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

- 位置：`app/static/js/modules/views/instances/modals/instance-modals.js:303`
  类型：防御（合理回退）
  描述：if (!error) return fallback;（判定理由：缺关键对象/DOM 时短路退出，避免半初始化。）
  建议：保留；如该短路会让用户无反馈，建议同时输出一次可观测错误（toast 或 console.error）。

### 6.3 Jinja2：`or` 兜底链（全量 36 处）

- 位置：`app/templates/accounts/account-classification/classifications_form.html:52`
  类型：回退（合理回退）
  描述：{% for option in risk_level_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/account-classification/classifications_form.html:62`
  类型：回退（合理回退）
  描述：{% for option in color_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/account-classification/classifications_form.html:72`
  类型：回退（合理回退）
  描述：{% for option in icon_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/account-classification/rules_form.html:35`
  类型：回退（合理回退）
  描述：{% for option in classification_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/account-classification/rules_form.html:59`
  类型：回退（合理回退）
  描述：{% for option in db_type_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/account-classification/rules_form.html:69`
  类型：回退（合理回退）
  描述：{% for option in operator_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/ledgers.html:27`
  类型：回退（需人工复核）
  描述：<div id="accounts-page-root" data-current-db-type="{{ current_db_type or 'all' }}" data-export-url="/api/v1/accounts/ledgers/exports">（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/ledgers.html:46`
  类型：回退（需人工复核）
  描述：class="btn {% if not current_db_type or current_db_type == 'all' %}btn-primary{% else %}btn-outline-primary border-2 fw-bold{% endif %}"（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/accounts/statistics.html:8`
  类型：回退（合理回退）
  描述：{% set total_accounts = stats.total_accounts or 0 %}（判定理由：数值兜底为 0；当左值为 0 时结果不变。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/admin/scheduler/index.html:6`
  类型：回退（需人工复核）
  描述：{% block title %}定时任务管理 - {{ config.APP_NAME or '鲸落' }}{% endblock %}（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/auth/list.html:7`
  类型：回退（需人工复核）
  描述：{% block title %}用户管理 - {{ config.APP_NAME or '鲸落' }}{% endblock %}（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/base.html:8`
  类型：回退（需人工复核）
  描述：<title id="page-title">{% block title %}{{ config.APP_NAME or '鲸落' }} - 数据同步管理平台{% endblock %}</title>（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/base.html:65`
  类型：回退（需人工复核）
  描述：<span id="app-name">{{ config.APP_NAME or '鲸落' }}</span>（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/base.html:238`
  类型：回退（需人工复核）
  描述：&copy; 2025 <span id="footer-app-name">{{ config.APP_NAME or '鲸落' }}</span>（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/base.html:239`
  类型：回退（需人工复核）
  描述：{{ config.APP_VERSION or 'unknown' }} - 数据同步管理平台 |（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/filters/macros.html:20`
  类型：回退（合理回退）
  描述：{% set option_list = options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/filters/macros.html:36`
  类型：回退（需人工复核）
  描述：<option value="">{{ placeholder or '全部' }}</option>（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/filters/macros.html:45`
  类型：回退（合理回退）
  描述：{% if value in (current_value or []) %}selected{% endif %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/filters/macros.html:114`
  类型：回退（合理回退）
  描述：{% for option in options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/filters/macros.html:133`
  类型：回退（合理回退）
  描述：{% for option in options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/filters/macros.html:144`
  类型：回退（合理回退）
  描述：{% set selected_values = selected or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/filters/macros.html:146`
  类型：回退（合理回退）
  描述：{% for option in options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/forms/macros.html:13`
  类型：回退（危险兜底）
  描述：value="{{ value if value is not none else field.default or '' }}"（判定理由：可能把合法 falsy(0/False) 覆盖为空字符串。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/forms/macros.html:29`
  类型：回退（危险兜底）
  描述：>{{ value if value is not none else field.default or '' }}</textarea>（判定理由：可能把合法 falsy(0/False) 覆盖为空字符串。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/forms/macros.html:42`
  类型：回退（需人工复核）
  描述：<option value="">{{ field.placeholder or '请选择' }}</option>（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/components/forms/macros.html:59`
  类型：回退（需人工复核）
  描述：{% if value or field.default %}checked{% endif %}（判定理由：checkbox/表单场景，value 为 False 时会被视为缺失并回退 default，需确认期望语义。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/databases/ledgers.html:22`
  类型：回退（需人工复核）
  描述：data-current-db-type="{{ current_db_type or 'all' }}">（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/instances/form.html:48`
  类型：回退（合理回退）
  描述：{% for option in database_type_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/instances/form.html:82`
  类型：回退（合理回退）
  描述：{% for option in credential_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/instances/form.html:104`
  类型：回退（合理回退）
  描述：{% set selected_tag_list = selected_tag_names or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/instances/form.html:109`
  类型：回退（需人工复核）
  描述：{% set selected_tag_list = form_values.get('tag_names') or selected_tag_list %}（判定理由：get(...) 可能返回空列表/空字符串；or 会覆盖合法 falsy。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/instances/form.html:115`
  类型：回退（合理回退）
  描述：{% for option in tag_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/instances/statistics.html:8`
  类型：回退（合理回退）
  描述：{% set total_instances = stats.total_instances or 0 %}（判定理由：数值兜底为 0；当左值为 0 时结果不变。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/instances/statistics.html:203`
  类型：回退（需人工复核）
  描述：<span class="chip-outline chip-outline--muted"><i class="fas fa-tag me-1"></i>{{ stat.version or '未知版本' }}</span>（判定理由：字符串/配置兜底，or 会覆盖空字符串等合法 falsy；需确认值域。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/tags/index.html:33`
  类型：回退（合理回退）
  描述：{% set stats = tag_stats or {'total': 0, 'active': 0, 'inactive': 0, 'category_count': 0} %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

- 位置：`app/templates/users/form.html:73`
  类型：回退（合理回退）
  描述：{% for option in role_options or [] %}（判定理由：对 None/未传值回退到空集合，避免模板异常；对空列表回退仍为同值。）
  建议：优先用 `default(..., boolean=false)` 或显式 `is not none` 判定，避免覆盖合法 falsy；迁移完成后删除旧来源兜底。

### 6.4 Jinja2：`default` filter（全量 18 处，均未启用 boolean=true）

- 位置：`app/templates/accounts/account-classification/permissions/policy-center-view.html:2`
  类型：回退（合理回退）
  描述：<div class="permission-policy-center" id="{{ permissions_id|default('permissionsConfig') }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/accounts/statistics.html:99`
  类型：回退（合理回退）
  描述：<span class="status-pill status-pill--muted">已删除 {{ type_stats.deleted|default(0) }}</span>（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/base.html:57`
  类型：回退（合理回退）
  描述：<body data-page="{{ page_id|default('') }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/base.html:204`
  类型：回退（合理回退）
  描述：<div class="main-content" data-density="{{ page_density|default('regular') }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/macros.html:6`
  类型：回退（合理回退）
  描述：<button type="button" class="btn-close {{ extra_class|default('') }}" data-bs-dismiss="{{ dismiss_target }}" aria-label="{{ aria_label|default('关闭') }}"></button>（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/macros.html:6`
  类型：回退（合理回退）
  描述：<button type="button" class="btn-close {{ extra_class|default('') }}" data-bs-dismiss="{{ dismiss_target }}" aria-label="{{ aria_label|default('关闭') }}"></button>（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:2`
  类型：回退（合理回退）
  描述：<div class="modal fade {{ modal_class|default('') }}" id="{{ modal_id }}" tabindex="-1" aria-labelledby="{{ modal_label_id }}" aria-hidden="true" data-bs-backdrop="{{ backdrop|default('true') }}" data-bs-keyboard="{{ keyboard|default('true'（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:2`
  类型：回退（合理回退）
  描述：<div class="modal fade {{ modal_class|default('') }}" id="{{ modal_id }}" tabindex="-1" aria-labelledby="{{ modal_label_id }}" aria-hidden="true" data-bs-backdrop="{{ backdrop|default('true') }}" data-bs-keyboard="{{ keyboard|default('true'（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:2`
  类型：回退（合理回退）
  描述：<div class="modal fade {{ modal_class|default('') }}" id="{{ modal_id }}" tabindex="-1" aria-labelledby="{{ modal_label_id }}" aria-hidden="true" data-bs-backdrop="{{ backdrop|default('true') }}" data-bs-keyboard="{{ keyboard|default('true'（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:3`
  类型：回退（合理回退）
  描述：<div class="modal-dialog {{ dialog_class|default('') }} {{ 'modal-dialog-scrollable' if scrollable else '' }} {{ 'modal-xl' if size == 'xl' else 'modal-lg' if size == 'lg' else 'modal-sm' if size == 'sm' else '' }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:5`
  类型：回退（合理回退）
  描述：<div class="modal-header {{ header_class|default('') }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:7`
  类型：回退（合理回退）
  描述：{{ btn_close('modal', close_aria_label|default('关闭'), close_button_class|default('')) }}（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:7`
  类型：回退（合理回退）
  描述：{{ btn_close('modal', close_aria_label|default('关闭'), close_button_class|default('')) }}（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:9`
  类型：回退（合理回退）
  描述：<div class="modal-body {{ body_class|default('') }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/modal.html:13`
  类型：回退（合理回退）
  描述：<div class="modal-footer {{ footer_class|default('') }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/stats_card.html:2`
  类型：回退（合理回退）
  描述：<div class="card shadow-sm border-0 stats-card {{ card_class|default('bg-primary text-white') }}">（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/stats_card.html:7`
  类型：回退（合理回退）
  描述：<h3 class="fw-bold mb-0" id="{{ value_id }}">{{ default_value|default('-') }}</h3>（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

- 位置：`app/templates/components/ui/stats_card.html:10`
  类型：回退（合理回退）
  描述：<i class="{{ icon_class|default('fas fa-chart-line') }} fa-2x"></i>（判定理由：default filter 未启用 boolean=true，通常仅在 undefined 时回退。）
  建议：保留；如需要对空字符串/0/False 也回退，请显式传入 boolean 参数并在评审中说明。

### 6.5 JavaScript：适配/桥接（第三方库直接使用的场景）

- 位置：`app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:199`
  类型：适配（需人工复核）
  描述：在 Modal 内直接 `new gridjs.Grid(...)`（Grid.js 非列表页/非 GridPage 场景），标准对该类场景缺少明确口径（见 3.5）。
  建议：补齐统一入口（如 `Views.ModalGrid`/UI module），或在标准中明确允许范围与必备约束（destroy、分页参数、样式密度）。

## 7. 修复优先级建议

### P0（阻断级）

1) 替换浏览器 `confirm()`：修复 `app/static/js/modules/views/history/sessions/sync-sessions.js:569`，统一改用 `UI.confirmDanger` 并补齐 impacts/结果入口。
2) 批量/异步任务反馈收敛：修复 `app/static/js/modules/views/instances/list.js:873` 等调用点，统一改用 `UI.resolveAsyncActionOutcome`，并移除 `message || ...`/`error || ...` 兜底链。

### P1（高优先级）

1) Views 禁止读取 allowlist 外全局：修复 `app/static/js/modules/views/components/charts/manager.js:19` 的 `window.EventBus` 依赖，改为注入 emitter 或迁移到 UI Modules。
2) 可复用组件固定 id 清理：修复 `app/templates/components/filters/macros.html:109`、`app/templates/components/ui/danger_confirm_modal.html:3` 等固定 id，改为 scope 派生。

### P2（建议改进/避免再漂移）

1) 补齐标准的可执行边界：
   - Page Entry 的判定规则（避免“物理路径决定层级”的误判）。
   - DOMHelpers 的强制范围（DOM 查询/写入 vs 事件绑定）。
   - Grid.js 在 Modal/非列表页场景的统一入口与约束。
2) 补强门禁脚本覆盖面（范围外，仅提方案）：
   - `browser-confirm-guard.sh` 覆盖 `confirm?.(`。
   - 为“可复用组件固定 id”提供更通用的门禁（不只覆盖 TagSelectorFilter）。
