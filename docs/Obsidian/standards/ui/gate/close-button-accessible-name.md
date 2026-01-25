---
title: 关闭按钮(btn-close)可访问名称
aliases:
  - close-button-accessible-name-guidelines
tags:
  - standards
  - standards/ui
status: active
enforcement: gate
created: 2025-12-23
updated: 2026-01-08
owner: WhaleFall Team
scope: Bootstrap `btn-close`(Alert/Modal/Toast 等)与所有"仅图标关闭"交互
related:
  - "[[standards/terminology]]"
---

# 关闭按钮(`btn-close`)可访问名称

## 目的

- 确保全站关闭按钮具备稳定的可访问名称（Accessible Name），读屏能正确朗读“关闭”。
- 避免中英文混用（例如 `aria-label="Close"`）导致读屏语言错乱与体验割裂。

## 适用范围

- 模板内的 Alert/Modal/Toast 关闭按钮。
- JS 动态生成的 toast/弹窗关闭按钮。

## 规则（MUST/SHOULD/MAY）

- MUST：关闭按钮统一使用 `aria-label="关闭"`。
- MUST NOT：使用英文 `aria-label="Close"` 或其他英文描述。
- MUST：优先通过统一模板宏输出关闭按钮，避免手写导致漏标或回归：
  - 模板宏：`app/templates/components/ui/macros.html` 的 `btn_close(...)`
  - 通用模态：`app/templates/components/ui/modal.html`

## 正反例

### 正例

```html
<button type="button" class="btn-close" aria-label="关闭"></button>
```

### 反例

```html
<button type="button" class="btn-close" aria-label="Close"></button>
```

## 门禁/检查方式

- 静态门禁：`./scripts/ci/btn-close-aria-guard.sh`
- 人工抽检：用键盘 Tab 聚焦关闭按钮，读屏必须朗读“关闭”

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 补齐标准结构与门禁说明，统一标题与示例。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
