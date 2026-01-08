---
title: 设计 Token 治理(CSS Variables)
aliases:
  - design-token-governance-guidelines
tags:
  - standards
  - standards/ui
status: active
created: 2025-12-23
updated: 2026-01-08
owner: WhaleFall Team
scope: "`app/static/css/**` 中的全局 Token、组件 Token 与引用规范"
related:
  - "[[standards/ui/color-guidelines]]"
---

# 设计 Token 治理(CSS Variables)

## 目的

- 让全站颜色/圆角/阴影/间距等视觉基线可预测、可复用、可统一调整。
- 避免出现 `var(--xxx)` 未定义导致的样式回退（例如圆角变直角、阴影漂移）。

## 适用范围

- 全站 CSS：`app/static/css/**`
- 核心 Token：`app/static/css/variables.css`
- 主题覆盖（如有）：`app/static/css/theme-*.css`

## 规则（MUST/SHOULD/MAY）

### 1) 全局 Token 必须集中定义

- MUST：全站复用的 Token（`--surface-*`、`--text-*`、`--border-radius-*`、`--shadow-*`、`--spacing-*` 等）必须在 `app/static/css/variables.css` 定义。
- MUST NOT：页面 CSS/组件 CSS 临时发明“看起来像全局”的 Token 名称；如确需局部变量，必须在同一作用域内定义（例如 `.component { --local-x: ... }`）。

### 2) 禁止引用未定义 Token

- MUST：任意 CSS 中出现 `var(--xxx)` 时，必须能在 `app/static/css/**` 内找到 `--xxx:` 的定义（外部库 Token 例外见 4)）。
- MUST：合并前通过门禁脚本 `scripts/ci/css-token-guard.sh`。

### 3) 兼容别名必须显式标注

- SHOULD：历史 Token 需要改名时，允许在 `variables.css` 以“别名”方式指向新 Token，例如：

```css
/* 兼容别名：历史代码使用 --surface-default，后续应逐步清理引用 */
--surface-default: var(--surface-base);
```

- MUST：别名旁必须注明“兼容别名”与清理意图，避免永久背负技术债。

### 4) 外部库 Token（允许）

- MAY：Bootstrap 等外部库 Token（例如 `--bs-*`）允许在本仓库 CSS 中直接引用。
- SHOULD：如引入新的外部 Token 前缀，需要同步更新门禁脚本允许列表。

## 正反例

### 正例：先定义再使用

- 在 `variables.css` 补齐 `--surface-muted`，然后在组件 CSS 中引用 `var(--surface-muted)`。

### 反例：先用后补

- 页面 CSS 直接写 `var(--new-token)`，但 `variables.css` 未定义，导致线上样式回退。

## 门禁/检查方式

- 脚本：`./scripts/ci/css-token-guard.sh`
- 作用：扫描 `app/static/css/**`，发现 `var(--xxx)` 引用但没有任何 `--xxx:` 定义时阻断（默认忽略 `--bs-*`）。

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 补齐标准结构与正反例，明确 Token 别名治理规则。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
