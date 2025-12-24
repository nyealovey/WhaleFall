# 按钮层级与状态规范

## 目标
1. 主/次/危险操作在默认态即可一眼区分，减少误点。
2. `btn-outline-*` 次按钮始终“看起来像按钮”（有清晰边框与可见的键盘焦点）。
3. 全站按钮状态（hover/active/disabled/focus）一致且可预期。

## 语义选型（模板必须按语义选）
- 主操作（页面核心 CTA）：`btn btn-primary`（同屏最多 1 个主按钮；其余用次按钮或图标按钮）。
- 次操作（不抢主 CTA 注意力，但仍需明显可点）：`btn btn-outline-secondary`。
- 危险操作（删除/不可逆）：优先 `btn btn-outline-danger`；需要强提醒才用 `btn btn-danger`。
- 仅图标操作：`btn btn-outline-secondary btn-icon`（不要用“无边框 + 仅图标”替代按钮语义）。
- 禁止伪装危险按钮：不要用 `text-danger` 叠加到 `btn-outline-secondary` / `btn-icon` 来“伪装危险语义”；危险操作必须直接选择 danger 语义按钮类（`btn-outline-danger/btn-danger`）。

## 实现基线（禁止破坏）
### 1) 禁止覆盖 `.btn` 的边框语义
- 禁止新增/恢复 `.btn { border: none; }`、`.btn { border: 0; }` 这类全局覆盖。
- 原因：Bootstrap 的 `btn-outline-*` 依赖 border 体现“按钮边界”；抹掉边框会直接削弱层级与可点性。
- 若确需“无边框”的交互外观：使用更具体的语义类（如 `btn-link`）或新增组件类，不要在 `.btn` 上做破坏性覆盖。

### 2) 状态规范（最小要求）
- hover：允许轻微强调（颜色/阴影），但不应影响布局稳定性。
- focus-visible：必须有清晰 focus ring（键盘 Tab 可见）。
- disabled：视觉上降低对比度，同时保持按钮形态（不要消失成文本）。

### 3) Loading 与内容恢复（尤其是图标按钮）
- 禁止把按钮内容“简化”为纯文本再恢复：图标按钮（`btn-icon`）在 loading/恢复后不得丢失 `<i>` 结构或变成意外文本。
- Loading 必须可逆：进入 loading 前要缓存并在结束后恢复原始 `innerHTML`，避免出现空白按钮/宽度抖动。
- A11y 最小要求：loading 时设置 `aria-busy="true"`；icon-only 按钮必须有稳定的可访问名称（优先 `aria-label`，允许用 `title` 兜底）。
- 推荐统一实现：使用 `UI.setButtonLoading(...)` / `UI.clearButtonLoading(...)`，禁止在页面脚本中散落 `showLoadingState/hideLoadingState` 私有实现。

## 代码落点
- 按钮统一实现：`app/static/css/components/buttons.css`
- 图标按钮基线：`btn-icon` 同步归口在 `app/static/css/components/buttons.css`，pages 禁止再写 `.btn-icon {}` 全局覆盖（仅允许容器作用域覆写）。
- 按钮 loading 工具：`app/static/js/modules/ui/button-loading.js`
- 例外策略：页面级 CSS 如需特殊外观，必须在容器作用域内覆盖（例如 `.filter-actions .btn-primary`），且不得破坏 `btn-outline-*` 的边框语义。

## 审查与门禁
- 建议在 PR 自检运行：`./scripts/code_review/button_hierarchy_guard.sh`
- 建议同步运行：`./scripts/code_review/component_style_drift_guard.sh`
- 建议同步运行：`./scripts/code_review/danger_button_semantics_guard.sh`
- 评审检查项：
  - 是否新增全局 `.btn` 覆盖（尤其是 border/outline）？
  - 是否在模板中错误使用了按钮语义（主按钮过多、危险按钮伪装成次按钮等）？
  - 是否出现硬编码颜色（HEX/RGB/RGBA）？
