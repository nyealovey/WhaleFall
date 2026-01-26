---
title: 可复用组件 DOM id 作用域规范
aliases:
  - component-dom-id-scope-guidelines
tags:
  - standards
  - standards/ui
status: active
enforcement: gate
created: 2025-12-29
updated: 2026-01-25
owner: WhaleFall Team
scope: "`app/templates/**` 与 `app/static/js/**` 中所有可复用组件(含 Jinja 宏)"
related:
  - "[[standards/ui/design/javascript-module]]"
---

# 可复用组件 DOM id 作用域规范

## 目的

- 避免同页多实例组件发生 DOM id 冲突（事件绑定命中错误节点、预览更新错位等隐性 bug）。
- 让组件具备“可复用、可审查、可门禁”的最小契约：容器可定位、内部节点可在容器内查找。

## 适用范围

- 以 Jinja 宏/模板片段形式复用的组件（例如筛选器、弹窗触发器、列表工具条等）。
- 以 JS 模块形式提供交互、并可能在多个页面或同页多处复用的组件。

## 规则（MUST/SHOULD/MAY）

### 1) 禁止固定全局 id（MUST NOT）

- MUST NOT：在可复用组件内部写死固定 id，例如 `id="open-tag-filter-btn"`。
- MUST NOT：JS 使用 `document.getElementById(...)` / `document.querySelector('#fixed-id')` 绑定可复用组件内部节点。

原因：同页出现第二个实例时必然冲突，且冲突行为常常是“静默错误”（更新了第一个实例）。

### 2) 推荐“容器 scope + 派生 id”（MUST）

模板侧：

- MUST：为组件最外层提供可定位容器：
  - `data-wf-scope="<scope>"`(推荐)或 `id="<scope>-container"`(允许).
- MUST：内部节点 id 必须从 `<scope>` 派生，形式建议为：`<scope>-<part>`。
- MUST: `<scope>` 使用 `kebab-case`, 且必须在页面内唯一.
- SHOULD: `<scope>` 以组件/域前缀开头, 例如 `tag-selector-<field-id>`.

JS 侧：

- MUST：先定位 scope 容器，再在容器内查找内部节点：
  - `const container = document.querySelector('[data-wf-scope="<scope>"]')`
  - `container.querySelector(...)`

### 3) 内部节点查询优先“容器内 querySelector”（SHOULD）

- SHOULD：优先使用 `container.querySelector(...)`，避免全局选择器。
- SHOULD：当必须使用 `id` 时，也应通过容器作用域查找（保证多实例安全）。

### 4) `data-role` 作为长期演进方向（MAY）

- MAY：在组件内部使用 `data-role="..."` 表达内部节点语义，减少对 `id` 的依赖。
- 本标准不强制迁移到 `data-role`，以“先解决冲突 + 可门禁”为优先。

## 正反例：TagSelectorFilter

模板宏（示意）：

```html
<div data-wf-scope="{{ field_id }}">
  <button id="{{ field_id }}-open">选择标签</button>
  <div id="{{ field_id }}-preview"><div id="{{ field_id }}-chips"></div></div>
  <input id="{{ field_id }}-selected" type="hidden" name="tags">
</div>
```

JS（示意）：

```js
TagSelectorHelper.setupForForm({
  scope: "instance-tag-selector",
  onConfirm: () => { /* ... */ },
});
```

## 门禁/检查方式

- `./scripts/ci/tag-selector-filter-id-guard.sh`
- 聚合 audit 门禁（fixed id 回归）：`./scripts/ci/ui-standards-audit-guard.sh`

## 变更历史

- 2025-12-29：初始化标准，作为 TagSelectorFilter 多实例治理的通用约束入口。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
- 2026-01-14: 固化容器属性为 `data-wf-scope`, 补齐 selector 示例与 `<scope>` 命名规则.
