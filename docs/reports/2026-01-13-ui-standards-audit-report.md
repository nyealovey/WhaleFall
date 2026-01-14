> 状态: Draft
> Owner: WhaleFall Team
> Created: 2026-01-13
> Updated: 2026-01-13
> Scope: 复核 `docs/Obsidian/standards/ui/**` 标准一致性, 识别冲突/模糊定义/跨界风险
> Related:
> - `docs/Obsidian/standards/ui/README.md`
> - `docs/Obsidian/standards/ui/javascript-module-standards.md`
> - `docs/Obsidian/standards/ui/layer/README.md`
> - `docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md`
> - `docs/Obsidian/standards/ui/layer/views-layer-standards.md`
> - `docs/Obsidian/standards/ui/layer/stores-layer-standards.md`
> - `docs/Obsidian/standards/ui/layer/services-layer-standards.md`
> - `docs/Obsidian/standards/ui/layer/ui-layer-standards.md`
> - `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md`
> - `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md`
> - `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md`
> - `docs/Obsidian/standards/ui/layout-sizing-guidelines.md`

# UI 标准一致性审阅报告 (2026-01-13)

## 1. 摘要

本报告审阅 `docs/Obsidian/standards/ui/**`, 聚焦 3 个问题:

1) 标准之间是否存在冲突/不一致.
2) 标准中是否存在模糊定义, 导致不可执行或难以门禁.
3) 标准是否存在跨界/违规(例如把后端强约束写进 UI 标准, 导致多处 SSOT 风险).

说明: 本报告以"标准文本本身"为证据, 不展开全量代码符合性审计.

## 2. 标准冲突与不一致

### 2.1 "仅 Page Entry 可读取 window.*" 与 "UI Modules 可依赖 window.*" 口径冲突

证据:
- `docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md:60` 明确 "仅 Page Entry 允许直接读取 window.DOMHelpers/httpU/UI/toast".
- `docs/Obsidian/standards/ui/layer/views-layer-standards.md:53` 同样明确 "仅 Page Entry 允许读取 window.DOMHelpers/httpU/UI/toast".
- `docs/Obsidian/standards/ui/layer/ui-layer-standards.md:55` 又写 "UI Modules 允许依赖 window.DOMHelpers/window.UI".

问题:
- "谁可以读 window.*" 在不同文档中存在相互矛盾的强约束, 导致评审与门禁难以一致执行.

建议(二选一, 需要明确落点并在相关标准中同步):
- 方案 A: 明确允许 UI Modules 读取的全局 allowlist(例如仅 DOMHelpers/UI/bootstrap), 其余下层仍禁止读 window.*.
- 方案 B: 统一改为 "除 Page Entry 外禁止读取 window.*", UI Modules 也必须通过参数注入依赖(由 Page Entry 注入).

### 2.2 EventBus/可观测性落点不统一

证据:
- `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:45` 提到 unknown 分支默认 `EventBus.emit(...)` + `console.warn`.
- `docs/Obsidian/standards/ui/layer/services-layer-standards.md:86` 明确禁止 `window.EventBus`.
- `docs/Obsidian/standards/ui/layer/ui-layer-standards.md:55` 允许依赖列表未提 EventBus, 且未明确是否允许.

问题:
- "unknown 可观测性" 属于 UI 标准要求, 但实现落点(是否允许依赖 EventBus, 允许在哪一层)缺少统一口径.

建议:
- 明确可观测性的统一实现方式与落点:
  - 如果 EventBus 是标准依赖: 在允许的层(例如 UI Modules)显式列入 allowlist, 并补齐 event name/payload 规范与门禁.
  - 如果 EventBus 不应成为标准依赖: 将文档中的 EventBus 改为统一的 telemetry/logger helper, 并在 UI 标准中禁止 EventBus.

## 3. 模糊定义与可执行性不足

### 3.1 `data-*-scope` 不是可直接落地的契约

证据:
- `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:42` 使用 `data-*-scope="<scope>"` 作为推荐形态.
- `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md:49` 给出的 selector 写法为占位形式.

问题:
- attribute 命名与 selector 示例都属于"占位写法", 不足以形成可门禁的统一约定.

建议:
- 固化一个可门禁的属性名, 例如 `data-wf-scope="<scope>"`.
- 给出可直接复制使用的 selector 示例, 并定义 `<scope>` 的命名规则(字符集/前缀/唯一性).

### 3.2 "资源风险但可恢复" 判定缺失

证据:
- `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md:51` 直接将该类操作映射到 `btn-warning`.

问题:
- 标准未定义 "资源风险但可恢复" 的判定口径(例如是否可撤销, 是否可回滚, 是否可取消, 影响范围是否可控).

建议:
- 补一张决策表或例子清单, 将风险类型与按钮语义做 1:1 映射, 例如:
  - 不可逆删除 -> `btn-danger`
  - 权限风险 -> (定义后决定)
  - 高成本但可取消/可回滚 -> `btn-warning`

### 3.3 Draft 标准大量使用 MUST, 但门禁是 "建议"

证据:
- `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:8` 标记 `status: draft`.
- `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:36` 起存在大量 MUST 规则.

问题:
- draft 与 MUST 的强度组合, 会让团队对 "是否必须阻断 PR" 产生分歧, 且该文档门禁表述包含 "建议门禁".

建议(二选一):
- 若该标准应作为基线: 升级为 `active`, 并将对应 guard 变为 MUST 门禁.
- 若该标准为试点: 将 MUST 降级为 SHOULD, 并明确 "试点范围"(例如仅新页面/指定模块/指定时间窗口).

### 3.4 dataset `kebab-case` 与 JS 读取映射缺少示例

证据:
- `docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md:69` 要求 dataset key 使用 `kebab-case`, 并通过 `element.dataset.*` 读取.

问题:
- 缺少 `data-foo-bar` -> `dataset.fooBar` 的直观示例, 容易造成重复踩坑.

建议:
- 增加 1-2 个映射示例, 并建议使用统一 helper 做 dataset 安全读取与 parse.

## 4. 跨界/违规与多处 SSOT 风险

### 4.1 UI 标准包含后端强约束与后端实现落点

证据:
- `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md:64` 开始写后端契约(MUST 返回 JSON envelope, MUST 返回 data.session_id 等).
- `docs/Obsidian/standards/ui/pagination-sorting-parameter-guidelines.md:45` 强约束后端必须通过 `app/utils/pagination_utils.py` 的函数解析分页参数.
- `docs/Obsidian/standards/ui/gridjs-migration-standard.md:56` 进一步定义列表 API 的输入/返回结构与错误结构.

问题:
- UI 标准直接规定后端实现细节与契约细节, 容易与 `docs/Obsidian/standards/backend/**` 形成双 SSOT.

建议:
- 将后端 MUST 迁移到后端标准或统一 contracts SSOT, UI 文档保留 "前端依赖契约摘要 + 链接" 作为入口即可.

### 4.2 Page Entry 与 Views 的物理目录边界不清

证据:
- `docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md:37` 表述 Page Entry 脚本 "通常位于 app/static/js/modules/views/**".

问题:
- 分层概念与物理目录混住, 会放大违规概率(例如 Page Entry 被当作 view component), 也不利于门禁脚本按目录执行.

建议:
- 为 Page Entry 建立独立目录(例如 `app/static/js/modules/pages/**` 或 `modules/entry/**`), 并在标准中明确 legacy 迁移策略.

### 4.3 scope 包含标准目录本身, 容易产生边界混乱

证据:
- `docs/Obsidian/standards/ui/layout-sizing-guidelines.md:12` scope 包含 `docs/Obsidian/standards/ui/**`.

问题:
- 实现标准的 scope 覆盖到标准文本本身, 容易造成 "标准约束标准" 的理解歧义(尤其是写作格式与实现约束混在一起).

建议:
- scope 聚焦到实现载体(`app/templates/**`, `app/static/css/**`), 文档自身的写作/格式交由 `docs/Obsidian/standards/doc/documentation-standards.md` 约束.

## 5. 建议的下一步动作(按优先级)

1) 统一 "window.* 访问规则" 的 SSOT, 明确 allowlist 与迁移期策略, 并同步修正文档冲突点.
2) 固化 DOM scope 属性命名(例如 `data-wf-scope`)并更新/新增门禁脚本, 防止 id 冲突治理漂移.
3) 将 UI 文档中的后端 MUST 契约迁移到后端标准或 contracts SSOT, UI 文档只保留摘要 + 链接, 避免双 SSOT.
4) 补齐危险操作风险分类与按钮语义映射(决策表), 提升可审查性与一致性.
5) 解决 `layout-sizing-guidelines.md` 的 draft/MUST 强度不一致, 推进为 active+门禁, 或降级为 SHOULD+试点范围.
