> Status: draft
> Owner: Codex (前端/UI 标准审计员)
> Created: 2026-01-15
> Updated: 2026-01-15
> Scope:
> - Standards: `docs/Obsidian/standards/ui/**/*.md`
> - Code (frontend only):
>   - `app/static/js/**/*.js`（仅项目代码；未扫描 `app/static/vendor/**`）
>   - `app/templates/**/*.html`
>   - `app/static/css/**/*.css`
> Related:
> - `docs/Obsidian/standards/ui/README.md`
> - `docs/Obsidian/standards/ui/layer/README.md`
> - `docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md`
> - `docs/Obsidian/standards/ui/layer/views-layer-standards.md`
> - `docs/Obsidian/standards/ui/javascript-module-standards.md`
> - `docs/Obsidian/standards/ui/vendor-library-usage-standards.md`
> - `docs/reports/clean-code-analysis.md`

# 前端/UI 标准全量审计报告 (2026-01-15)

## 1. 目标

1) 找出标准冲突：同一主题出现相互矛盾的 MUST/MUST NOT/等价强制措辞；或“索引/依赖图 vs 文本”口径不一致；或命名口径不一致等。

2) 找出标准的模糊定义/不可执行点：术语未定义、触发条件不清、例外未写明、缺少可验证规则、用词导致多解。

3) 基于明确可执行的标准，找出前端代码的违规点（严格限于扫描范围内）：每条结论都能回链到 `标准文件:行号` + `app/...:行号`（代码行号来自 AST）。

4) 盘点防御/兼容/回退/适配逻辑（仅限扫描范围），重点关注 `||/??/or/default` 的兜底链与其风险。

## 2. 审计方法与证据

### 2.1 已执行的仓库门禁脚本

说明：门禁脚本输出仅作为“补充证据/交叉验证”，不作为唯一判定依据；违规清单仍以 AST 语义扫描定位为主。

本次执行（均通过）：

- `./scripts/ci/btn-close-aria-guard.sh`
- `./scripts/ci/browser-confirm-guard.sh`
- `./scripts/ci/inline-px-style-guard.sh`
- `./scripts/ci/css-token-guard.sh`
- `./scripts/ci/button-hierarchy-guard.sh`
- `./scripts/ci/danger-button-semantics-guard.sh`
- `./scripts/ci/tag-selector-filter-id-guard.sh`
- `./scripts/ci/pagination-param-guard.sh`
- `./scripts/ci/grid-wrapper-log-guard.sh`

### 2.2 已执行的补充静态扫描

- `rg -n` 仅用于导航/交叉验证（例如快速定位 `btn-close`、`onclick`、`JSON.parse` 线索），不作为代码判定的唯一依据。
- CSS 侧补充扫描（非 AST）：统计颜色字面量(HEX/RGB/HSL/OKLCH)命中行，仅出现在 `app/static/css/variables.css`；其余 `app/static/css/**/*.css` 未发现颜色字面量（用于佐证“颜色收敛到 Token 文件”的现状）。

### 2.3 AST 语义扫描

**覆盖范围（严格按要求限定）：**

- JS：解析 `app/static/js/**/*.js`（共 99 个文件；排除 `app/static/vendor/**`），使用 `espree` 构建 AST，开启 `loc: true`，位置取 `loc.start.line/loc.end.line`。
- Jinja 模板：解析 `app/templates/**/*.html`（共 55 个文件），使用 `jinja2.Environment().parse(...)` 构建 Template AST，位置取节点 `lineno`（以及 `TemplateData.lineno + offset` 的方式定位纯 HTML 片段）。

**必扫模式覆盖情况（摘录）：**

- `||/??` 链（JS）：覆盖 `LogicalExpression`、多段链 flatten、以及高风险字面量兜底（`0/""/false`）识别。
- 三元默认值链（JS）：覆盖 `ConditionalExpression` 中典型的 truthy-default 形态。
- `or/default`（模板）：覆盖 `nodes.Or` 链与 `|default(...)` filter（含 boolean 参数识别）。
- 数据结构兼容（字段别名/旧字段兜底）：覆盖 `obj.newKey || obj.oldKey` / `obj.newKey ?? obj.oldKey`、以及 `snake_case`/`camelCase` 双读。
- 防御/回退：覆盖 `try/catch`、guard clause（例如 `if (!el) return;`）、依赖缺失 fail-fast（`throw/console.error + return`）。
- 分层与全局 allowlist：按路径推断层级，并抽取 `window.*` 使用点用于核对 allowlist。

**范围外说明（按要求忽略）：**

- 未扫描、也不在“违规/问题清单”中判定任何 `app/**/*.py`、`scripts/**`（除门禁脚本作为证据说明）、`tests/**`、`migrations/**` 等范围外代码问题。

### 2.4 强约束索引（可执行口径摘录）

说明：本节只收敛“明确强约束（MUST/MUST NOT/不得/禁止/严禁/必须）”的高频入口，便于后续审计与门禁落地。

| 主题 | 强约束（简述） | 标准位置 | 影响范围 | 典型反例 |
|---|---|---|---|---|
| Page Entry | 每个页面模板必须设置 `page_id`，且必须是安全全局键名 | `docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md:43` | templates/pages | 页面无 `page_id`，`page-loader` 无法 mount |
| Views 全局依赖 | Views 不得读取 allowlist 外全局，且不得读取 `window.httpU` | `docs/Obsidian/standards/ui/layer/views-layer-standards.md:55` | `app/static/js/modules/views/**` | view 里 `new Service(window.httpU)` |
| Grid 列表页入口 | 列表页必须走 `Views.GridPage.mount`；页面脚本不得 `new GridWrapper/new gridjs.Grid` | `docs/Obsidian/standards/ui/grid-standards.md:40` / `docs/Obsidian/standards/ui/grid-standards.md:41` / `docs/Obsidian/standards/ui/grid-standards.md:42` | grid list pages | 页面脚本直接实例化 grid |
| 事件绑定 | 禁止内联 `onclick="..."` | `docs/Obsidian/standards/ui/grid-standards.md:49`（但 scope 见“标准歧义”） | templates/pages | `<button onclick="...">` |
| 高风险确认 | 禁止浏览器 `confirm()`；必须用 `UI.confirmDanger` | `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:37` / `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:38` | `app/static/js/**` | `confirm("...")` |
| 异步任务反馈 | 必须用 `UI.resolveAsyncActionOutcome`；不得扩散 `message || error` 等互兜底链 | `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:43` / `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:44` | views/pages | 每个调用点手写 error/message fallback |
| btn-close 可访问性 | `btn-close` 必须 `aria-label="关闭"`，禁止英文 Close | `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:31` / `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:32` / `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md:33` | templates/js | `aria-label="Close"` 或缺失 |
| 按钮危险语义 | 禁止用 `text-danger` 叠加伪装危险按钮 | `docs/Obsidian/standards/ui/button-hierarchy-guidelines.md:37` | templates/css | `btn-outline-secondary text-danger` |
| Token 定义 | 全站复用 Token 必须集中在 `variables.css` | `docs/Obsidian/standards/ui/design-token-governance-guidelines.md:34` | `app/static/css/**` | 页面/组件 CSS 临时发明全局 Token |
| Token 引用 | `var(--xxx)` 必须能在 `app/static/css/**` 找到定义 | `docs/Obsidian/standards/ui/design-token-governance-guidelines.md:39` | `app/static/css/**` | 引用未定义 Token 导致样式回退 |

## 3. 标准冲突或歧义

> 本节先收敛口径：当标准本身存在冲突/歧义时，代码侧更容易出现“实现分裂”，进而促使 `||/or` 兜底链增长、allowlist 被绕过、封装入口漂移等。

### 3.1 色彩“禁止硬编码”与 Token 定义文件的边界表述不够精确

- 证据：`docs/Obsidian/standards/ui/color-guidelines.md:38` 写明“禁止在 CSS/HTML/JS 中硬编码 HEX/RGB/RGBA”，但同一句又要求色彩“由 `variables.css` 或 Token 输出”。
- 证据：`docs/Obsidian/standards/ui/design-token-governance-guidelines.md:34` 要求全局 Token 必须在 `variables.css` 定义；而 `app/static/css/variables.css`（例如 `app/static/css/variables.css:5`）必然包含颜色字面量用于定义 Token。
- 影响（实现分裂）：
  - reviewer/开发者可能对“`variables.css` 是否允许写 `#fff`”产生分歧，从而出现两种极端：
    - 过度严格：拒绝必要的 token 定义；
    - 过度宽松：在组件 CSS/模板/JS 中也开始写颜色字面量，导致后续需要靠 `||/or`/class 互兜底来维持视觉一致。
- 建议：在 `color-guidelines.md` 明确例外边界（建议用一句话写清）：
  - “除 `app/static/css/variables.css`（及必要的主题文件）中用于定义 Token 的字面量外，其余 CSS/HTML/JS 禁止出现 HEX/RGB/RGBA。”

### 3.2 allowlist（可访问）与“优先封装入口”（推荐/强约束）的关系容易被误读

- 证据：allowlist（SSOT）允许 Views 访问 vendor globals（例如 `docs/Obsidian/standards/ui/layer/README.md:83`）。
- 证据：vendor 标准要求业务代码优先走项目封装，不直接调用 vendor global（`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:29`），并强调 `window.*` 边界以 allowlist 为 SSOT（`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:31`）。
- 影响（实现分裂）：
  - allowlist 本意是“安全边界”，但容易被误读为“最佳实践清单”，从而出现：
    - 代码直接使用 vendor global（因为 allowlist 允许），绕过封装入口；
    - 升级/替换库时，调用点不得不引入 `a || b` 兜底链来兼容不同 global/行为（典型是 locale/timezone/plugin 差异），兼容链无限增长。
- 建议：在 `layer/README.md` 的 allowlist 段落增加一句“allowlist 仅代表可访问边界，不代表推荐入口”，并在 `vendor-library-usage-standards.md` 给出“允许直接访问 vendor global 的最小场景定义”（例如：仅 view 层、仅 bootstrap.Modal 且必须 destroy/dispose）。

### 3.3 `onclick` 禁止规则的适用范围与落点存在歧义

- 证据：Grid 标准写明 `MUST NOT: 页面内绑定内联 onclick`（`docs/Obsidian/standards/ui/grid-standards.md:49`）。
- 证据：Views 层标准也写明 `MUST: 禁止内联 onclick`（`docs/Obsidian/standards/ui/layer/views-layer-standards.md:61`），但其 scope 是 `app/static/js/modules/views/**`，不是模板。
- 影响（实现分裂）：
  - 当前规则出现在“Grid 列表页标准”中，但语义像是“全站模板/页面通用禁令”。当它被用于非 Grid 页面（例如错误页）时，开发者/审查者会对“是否适用”产生争议。
  - 一旦争议无法快速收敛，常见结果是“暂时保留 inline onclick”，并在 JS 侧做更多兜底（例如 `document.querySelector(...) || ...`）来补救交互差异。
- 建议：新增一个更上位的“模板事件绑定规范”入口（或把该条移动到更通用的标准，如 `javascript-module-standards.md`），明确：模板是否一律禁止 inline handler。

### 3.4 layout sizing 的“例外条款”不可机器验证，容易导致口径漂移

- 证据：`docs/Obsidian/standards/ui/layout-sizing-guidelines.md:60` / `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:61` 禁止模板新增 `height/width: Npx`，但又允许“非布局性质微调”例外，并要求“评审中说明原因”。
- 影响（实现分裂）：
  - “关键布局尺寸/非布局微调”的判定没有明确规则时，容易让实现分裂：有的页面继续写 inline px 并声称是“微调”，有的页面改 token/class。
  - 例外无法被静态门禁稳定识别时，最终会促使代码侧引入更多兜底（例如在 JS 里动态测量并 fallback），增加不可控行为。
- 建议：
  - 明确“允许的例外清单”（例如仅 `border`/`hairline`），并要求例外点必须配套同一行注释（固定格式，便于门禁 whitelist）。

### 3.5 “评审中说明原因/迁移计划”属于强约束但缺少落地载体

- 证据：多处出现“必须在评审中说明原因/给出迁移计划”的强措辞（例如 `docs/Obsidian/standards/ui/layer/README.md:103`、`docs/Obsidian/standards/ui/vendor-library-usage-standards.md:32`、`docs/Obsidian/standards/ui/layout-sizing-guidelines.md:61`）。
- 影响（实现分裂）：
  - 静态审计无法判断“是否已在 PR 描述说明”，导致同类例外在不同 PR 中口径漂移；
  - 最终倾向把例外永久化（兼容链、allowlist 外 global 读取、inline px 逐步累积）。
- 建议：把“说明原因/迁移计划”落到一个可复用载体（例如 PR 模板字段或代码注释约定），让审计与门禁都能有稳定抓手。

## 4. 不符合标准的代码行为(需要修复)

> 本节仅收录：标准为明确强约束（MUST/MUST NOT/不得/禁止等）且证据清晰的点。

### 4.1 Page Entry：页面模板缺失 `page_id`

- 结论：存在页面模板 `{% extends "base.html" %}` 但未设置 `page_id`，导致 `body[data-page]` 为空，页面启动契约不完整。
- 标准依据：`docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md:43`
- 代码证据（Jinja AST：`Extends` 存在但无 `Assign(page_id)`）：
  - `app/templates/about.html:1`
  - `app/templates/accounts/statistics.html:1`
  - `app/templates/errors/error.html:1`
- 影响：
  - `app/static/js/bootstrap/page-loader.js` 读取 `body.dataset.page`（`app/static/js/bootstrap/page-loader.js:9`）后会直接 return（`app/static/js/bootstrap/page-loader.js:10` / `app/static/js/bootstrap/page-loader.js:11`），使页面无法通过统一入口挂载 JS 行为；后续一旦需要为这些页面增加 page-level JS，容易出现“临时脚本 + 全局变量”漂移。
- 修复建议：
  - 为上述页面补齐 `{% set page_id = "..." %}`（且确保不使用 `__proto__/prototype/constructor`）。
  - 若页面确实不需要 JS，也建议仍设置稳定 `page_id` 作为可审计的入口契约（未来可在 page-loader 侧做 noop mount）。
- 验证方式：
  - 复跑模板 AST 扫描（检查 extends 页面 `page_id` 覆盖率）。
  - 浏览器中查看页面 DOM：`<body data-page="...">` 不应为空。

### 4.2 Views(排除 Page Entry)：直接读取 `window.httpU`（违反分层与 allowlist）

- 说明：本仓库存在 legacy Page Entry 脚本仍位于 `app/static/js/modules/views/**`（例如暴露 `window.<PageId>.mount`）。这类文件按 Page Entry 标准审查，不适用本条 Views 规则；本节仅统计“非 Page Entry”的 view 组件/控制器脚本中的 `window.httpU` 读取。
- 结论：在“非 Page Entry”的 view 组件/控制器脚本中，存在直接读取 `window.httpU` 的用法。
- 标准依据：
  - `docs/Obsidian/standards/ui/layer/views-layer-standards.md:55`
  -（补充口径一致性）`docs/Obsidian/standards/ui/javascript-module-standards.md:79`
- 代码证据（JS AST：`MemberExpression(window.httpU)`）：
  - `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:9`
  - `app/static/js/modules/views/auth/modals/user-modals.js:18`
  - `app/static/js/modules/views/components/charts/data-source.js:8`
  - `app/static/js/modules/views/components/connection-manager.js:29`
  - `app/static/js/modules/views/components/permissions/permission-viewer.js:22`
  - `app/static/js/modules/views/components/tags/tag-selector-controller.js:213`
  - `app/static/js/modules/views/credentials/modals/credential-modals.js:18`
  - `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:15`
  - `app/static/js/modules/views/instances/modals/instance-modals.js:18`
  - `app/static/js/modules/views/tags/modals/tag-modals.js:18`
- 影响：
  - 破坏“入口读全局、下层不碰全局”的分层推进路径，增加隐式耦合与测试难度；
  - 容易绕过 `Services` 层的统一错误处理/参数规整/安全键过滤，从而逼迫调用点扩散 `||` 兜底链（以及更难审计的 fallback）。
- 修复建议：
  -（已确认统一口径：全部按 C）将所有 `http.*("/api/...")` 与 API path 常量/拼接下沉到 `app/static/js/modules/services/**`；view/controller 只调用 service 方法。
  - 对“view 内读取 `window.httpU` 或 `http = window.httpU` 默认值”的模式：改为依赖 service（例如 `new Service()` + `service.method(...)`），并由 service 构造函数内部按 `client || window.httpU || window.http` 回退选择 httpClient（迁移期允许）。
- 验证方式：
  - 复跑 JS AST 扫描（排除 Page Entry 文件）：在“非 Page Entry”的 views 组件/控制器脚本中，`window.httpU` 命中数应为 0。
  -（辅助）`rg -n "window\.httpU" app/static/js/modules/views` 仅用于快速复核；输出需结合“是否为 Page Entry(暴露 `window.<PageId>.mount` )”过滤解读。

## 5. 符合标准的关键点(通过项摘要)

- 关闭按钮可访问名称：统一宏 `btn_close(...)` 输出 `aria-label` 默认值为“关闭”（`app/templates/components/ui/macros.html:6`），且门禁 `./scripts/ci/btn-close-aria-guard.sh` 通过。
- 高风险操作确认：门禁 `./scripts/ci/browser-confirm-guard.sh` 通过；仓库已提供统一入口 `UI.confirmDanger`（标准见 `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:38`，实现见 `app/static/js/modules/ui/danger-confirm.js:187`）。
- Token 治理：`./scripts/ci/css-token-guard.sh` 通过；颜色字面量仅出现在 `app/static/css/variables.css`，其余 CSS 未发现（符合“Token 输出”的现状）。
- Token 兼容别名治理：`app/static/css/variables.css:9` / `app/static/css/variables.css:10` 的别名旁有“兼容别名”与清理意图注释，对齐 `docs/Obsidian/standards/ui/design-token-governance-guidelines.md:51`。
- Grid/分页/日志门禁：`./scripts/ci/pagination-param-guard.sh` 与 `./scripts/ci/grid-wrapper-log-guard.sh` 通过，符合 `docs/Obsidian/standards/ui/grid-standards.md:65` 与 `docs/Obsidian/standards/ui/grid-standards.md:74` 的约束方向。

## 6. 防御/兼容/回退/适配逻辑清单(重点: ||/or 兜底)

> 说明：本节聚焦“高信号、可解释”的兜底/兼容点（不是穷举全仓库所有 `||`）。每条都标注：合理回退 / 危险兜底 / 需人工复核，并给出建议。

- 位置：`app/static/js/bootstrap/page-loader.js:9`
  类型：防御
  描述：读取 `body.dataset.page` 后使用 guard clause（合理回退：缺 `page_id` 时直接 return，避免半初始化）
  建议：补齐缺失 `page_id` 的页面；如需更友好可观测性，可考虑在缺 pageId 时输出一次可观测日志/提示（视产品需求）

- 位置：`app/static/js/bootstrap/page-loader.js:18`
  类型：回退
  描述：`dataset.pageMount || "mount"` 选择 mount 方法名（合理回退：空/缺失时回到默认方法）
  建议：如需要支持多入口方法，优先在标准中明确 allowlist（例如仅允许 `mount/destroy`），避免 method 名兼容链增长

- 位置：`app/static/js/bootstrap/page-loader.js:33`
  类型：防御
  描述：`mountFn.call(...)` 外包 `try/catch`（需人工复核：catch 仅 `console.error`，用户不可见；但可防止异常扩散导致后续脚本整体失效）
  建议：对关键页面可考虑提供“可见错误提示”或上报；同时避免吞异常后继续做半初始化

- 位置：`app/static/js/core/http-u.js:221`
  类型：回退
  描述：`body.message || body.error || ...` 解析错误消息（需人工复核：使用 `||` 可能把合法空字符串当缺失覆盖；但作为错误消息兜底通常可接受）
  建议：若后端契约已统一，建议改为更精确的 `??` 或显式判空，并逐步淘汰旧字段 `error`

- 位置：`app/static/js/core/http-u.js:344`
  类型：回退
  描述：请求配置使用 `config.responseType || "json"` / `config.timeout || DEFAULT_TIMEOUT`（需人工复核：`||` 会覆盖合法 falsy；但这些字段的合法值域通常不包含 falsy）
  建议：对值域可能包含 `0/""/false` 的字段统一改用 `??`

- 位置：`app/static/js/core/dom.helpers.js:155`
  类型：防御
  描述：DOM 包装器在目标不存在时直接返回（合理回退：避免对空节点继续操作）
  建议：对“必须存在”的关键节点可改为 fail-fast（抛错/提示），避免静默不生效

- 位置：`app/static/js/modules/ui/async-action-feedback.js:32`
  类型：回退
  描述：`global.EventBus?.emit?.(...)` 可选链上报 unknown（合理回退：缺 EventBus 时不报但不报错）
  建议：若 unknown 必须可观测，建议确保 UI Modules 层总能拿到 EventBus（或在缺失时走替代上报通道）

- 位置：`app/static/js/modules/ui/async-action-feedback.js:61`
  类型：回退
  描述：对 `options.*Message/resultUrl/resultText` 做“非空字符串判定”并回退到默认值（合理回退：避免 `||` 把空字符串等合法 falsy 误当缺失）
  建议：把该“非空字符串”规则作为 UI 通用 helper（若多处复用），避免各处再造 `||` 链

- 位置：`app/static/js/modules/ui/async-action-feedback.js:68`
  类型：兼容
  描述：`response?.data?.session_id ?? null` 读取会话 id（合理回退：使用 `??` 精确区分 nullish vs falsy）
  建议：当后端契约稳定后，可把 meta 字段的“可选性”收敛为单一 schema（减少兼容分支）

- 位置：`app/static/js/common/table-query-params.js:4`
  类型：防御
  描述：对 query key 做危险键过滤（`__proto__/prototype/constructor`）（合理回退：拒绝危险键写入/读取）
  建议：对业务 filters 再叠加 `allowedKeys`（标准已建议），并在 Grid 标准中把 allowlist 作为 MUST 落地（见 `docs/Obsidian/standards/ui/grid-standards.md:60`）

- 位置：`app/static/js/common/table-query-params.js:74`
  类型：数据迁移
  描述：规范化分页 filters 时删除历史键 `page_size/pageSize`（合理回退：兼容旧参数形状，同时输出 canonical `page/limit`）
  建议：在迁移完成后删除这些兼容删除逻辑，并增加门禁阻止新代码再引入旧键

- 位置：`app/static/js/modules/stores/instance_store.js:91`
  类型：回退
  描述：store emitter 支持注入，未传入时回退 `window.mitt()`（合理回退：有显式存在性检查，不依赖 `||` 的 truthy 语义）
  建议：长期建议由 Page Entry 注入 emitter（便于测试/隔离），并把全局回退作为迁移期策略

- 位置：`app/static/js/modules/stores/instance_store.js:106`
  类型：防御
  描述：对象写入前过滤危险键 + allowlist（合理回退：防止对象注入/原型污染）
  建议：对所有“从 URL/表单/dataset 来的动态键”统一复用同一 helper，避免漏网

- 位置：`app/static/js/modules/stores/instance_store.js:179`
  类型：兼容
  描述：`item.name || item.label || ""` / `item.dbType || item.db_type || null` 字段别名兜底（需人工复核：使用 `||` 可能覆盖合法空字符串；但也可能是期望空字符串回退）
  建议：若字段允许合法空值，建议改用 `??`；并在接口契约稳定后移除旧字段兜底

- 位置：`app/static/js/modules/stores/sync_sessions_store.js:113`
  类型：版本化
  描述：分页字段同时兼容 `snake_case/camelCase`，使用 `??` 多段链（合理回退：nullish-aware，不覆盖合法 falsy）
  建议：与后端契约收敛后，逐步收敛为单一字段名并删除兼容链，避免长期背负

- 位置：`app/static/js/modules/stores/logs_store.js:469`
  类型：防御
  描述：`if (!logId && logId !== 0)` 允许 `0` 作为合法值（合理回退：显式区分 0 与缺失）
  建议：对所有“可能为 0 的输入”优先使用这种显式判定，避免 `||` 把 0 当缺失

- 位置：`app/static/js/modules/stores/logs_store.js:482`
  类型：兼容
  描述：`payload.log ?? payload.data ?? payload` 提取数据形状（合理回退：使用 `??` 兼容不同响应结构）
  建议：当后端响应结构收敛后，删除 `data` 等旧字段分支

- 位置：`app/static/js/modules/views/instances/detail.js:1366`
  类型：防御
  描述：`data?.error || data?.message || "..."` 错误文案兜底链（危险兜底：使用 `||` 可能覆盖合法空字符串/0/false；并且容易在调用点扩散互兜底链）
  建议：优先收敛为 `UI.resolveErrorMessage`/`UI.resolveAsyncActionOutcome`（按标准适用范围），或改用 `??` + 明确字段优先级

- 位置：`app/static/js/modules/views/components/charts/data-source.js:5`
  类型：防御
  描述：依赖缺失时直接 `throw`（合理回退：fail-fast，避免无声失败）
  建议：对 page-level 可考虑捕获并转为用户可见提示（避免“页面空白但控制台有错”）

- 位置：`app/static/js/modules/views/components/charts/data-source.js:51`
  类型：兼容
  描述：`Array.isArray(payload.items) ? payload.items : payload.data` 兼容字段形状（需人工复核：fallback 分支 `payload.data` 的语义不明，可能隐藏 schema 漂移）
  建议：明确后端返回结构（建议统一为 `data.items`），并在迁移完成后删除兼容分支

- 位置：`app/templates/base.html:57`
  类型：回退
  描述：`body[data-page]` 使用 `page_id|default('')`（合理回退：`default` 默认仅对 undefined 生效，不覆盖 falsy；但会“掩盖”未设置 page_id 的页面）
  建议：对所有 extends base 的页面补齐 `page_id`；必要时在 page-loader 侧对空 pageId 做可观测提示

- 位置：`app/templates/base.html:8`
  类型：回退
  描述：`config.APP_NAME or '鲸落'`（需人工复核：`or` 是 truthy 兜底，会把空字符串当缺失；是否允许空字符串需明确）
  建议：若希望仅在 undefined/None 时兜底，优先用 `|default('鲸落')`（不带 boolean=true）

- 位置：`app/templates/accounts/ledgers.html:27`
  类型：回退
  描述：`current_db_type or 'all'` 作为 dataset 默认值（需人工复核：`or` 会把空字符串当缺失；需确认空字符串是否为合法状态）
  建议：如要精确区分空字符串，改用 `|default('all')` 或在后端确保 `current_db_type` 不为空字符串

- 位置：`app/templates/accounts/statistics.html:7`
  类型：回退
  描述：`stats.total_accounts or 0`（合理回退：0 与兜底值相同，不会把合法 0 覆盖成其他值）
  建议：若字段类型不确定，优先在后端/序列化层输出数字，减少模板侧兜底

- 位置：`app/templates/components/ui/macros.html:6`
  类型：回退
  描述：`aria_label|default('关闭')`（合理回退：仅对 undefined 生效，且保证可访问名称默认值）
  建议：统一通过该宏输出 `btn-close`，避免手写导致漏标/英文混用回归

- 位置：`app/static/css/variables.css:10`
  类型：数据迁移
  描述：Token 兼容别名 `--surface-default: var(--surface-base);` 且带注释（合理回退：显式别名，避免未定义 Token 导致样式回退）
  建议：给别名设置清理时间窗/追踪 issue，迁移完成后删除旧 Token

## 7. 修复优先级建议

- P0：修复 Views 层直接读取 `window.httpU`（见 4.2）。这是明确 MUST 违规且会持续阻碍分层推进，优先级最高。
- P1：补齐缺失 `page_id` 的页面模板（见 4.1）。这是 Page Entry 统一入口契约，影响未来扩展与一致性。
- P2：收敛标准歧义与不可执行点（见第 3 节）：
  - 明确“颜色字面量”的允许边界（只在 Token 定义文件中允许）；
  - 明确 `onclick` 禁令是否为全站模板规则；
  - 明确 layout sizing 例外的可审核/可门禁表达方式。
