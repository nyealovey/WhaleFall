---
title: 按钮层级与状态
aliases:
  - button-hierarchy-guidelines
tags:
  - standards
  - standards/ui
status: active
created: 2025-12-23
updated: 2026-01-08
owner: WhaleFall Team
scope: "`app/templates/**` 与 `app/static/css/**` 中所有按钮与按钮状态实现"
related:
  - "[[standards/ui/danger-operation-confirmation-guidelines]]"
---

# 按钮层级与状态

## 目的

- 让主/次/危险操作在默认态即可一眼区分，降低误点成本。
- 统一按钮的 hover/focus/disabled/loading 行为，避免“每页一套按钮交互”。

## 适用范围

- Bootstrap `btn` 系列按钮（含 outline/图标按钮）。
- 页面级按钮组、表格行内操作、模态框操作区按钮。

## 规则（MUST/SHOULD/MAY）

### 1) 语义选型（模板必须按语义选）

- MUST：主操作（页面核心 CTA）使用 `btn btn-primary`，同屏 SHOULD ≤1 个主按钮。
- MUST：次操作使用 `btn btn-outline-secondary`，保持“像按钮”的边框与焦点外观。
- MUST：危险操作（删除/不可逆）优先使用 `btn btn-outline-danger`；只有在确认弹窗的最终确认动作等“强提醒场景”才使用 `btn btn-danger`。
- MUST：仅图标操作使用 `btn btn-outline-secondary btn-icon`，并提供稳定的可访问名称（`aria-label` 优先，`title` 允许作为兜底）。
- MUST NOT：使用 `text-danger` 叠加到次按钮/图标按钮以“伪装危险语义”（危险操作必须直接选择 danger 语义类）。

### 2) 实现基线（禁止破坏）

- MUST NOT：新增/恢复全局 `.btn { border: none; }` / `.btn { border: 0; }` 等破坏性覆盖（会让 `btn-outline-*` 失去语义边界）。
- SHOULD：页面级差异如确需覆盖，必须限定在容器作用域内（例如 `.filter-actions .btn-primary { ... }`），不得影响全站 `btn-outline-*` 的边框语义。

### 3) Loading 与内容恢复（尤其是图标按钮）

- MUST：loading 必须可逆；进入 loading 前缓存并在结束后恢复原始 `innerHTML`，禁止把图标按钮“简化”为纯文本再恢复。
- MUST：loading 时设置 `aria-busy="true"`，并至少禁用一个按钮以防重复提交。
- SHOULD：统一使用 `UI.setButtonLoading(...)` / `UI.clearButtonLoading(...)`，禁止页面脚本散落私有 `showLoadingState/hideLoadingState` 实现。

## 正反例

### 正例：危险操作使用 outline danger，最终确认使用 danger

```html
<!-- 列表行内：触发按钮 -->
<button class="btn btn-outline-danger btn-icon" type="button" aria-label="删除">
  <i class="fa-solid fa-trash"></i>
</button>

<!-- 确认弹窗：最终确认按钮 -->
<button class="btn btn-danger" type="submit">确认删除</button>
```

### 反例：伪装危险按钮

```html
<button class="btn btn-outline-secondary text-danger" type="button">删除</button>
```

## 门禁/检查方式

- `./scripts/ci/button-hierarchy-guard.sh`
- `./scripts/ci/danger-button-semantics-guard.sh`
- `./scripts/ci/component-style-drift-guard.sh`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 补齐标准结构与门禁入口，统一术语与示例。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
