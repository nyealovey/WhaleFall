---
title: 可访问性(A11y)基线标准
aliases:
  - accessibility-baseline-standards
  - ui-a11y-baseline-standards
tags:
  - standards
  - standards/ui
status: active
enforcement: guide
created: 2026-01-24
updated: 2026-01-24
owner: WhaleFall Team
scope: "`app/templates/**` + `app/static/js/**` 的可访问性基线(按钮, 表单, 弹窗, 键盘操作)"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/close-button-accessible-name-guidelines]]"
  - "[[standards/ui/button-hierarchy-guidelines]]"
  - "[[standards/ui/template-event-binding-standards]]"
  - "[[standards/ui/async-task-feedback-guidelines]]"
---

# 可访问性(A11y)基线标准

## 目的

- 让关键操作对键盘与读屏用户可用, 避免"只有鼠标能用".
- 让图标按钮与动态反馈具备可访问名称与状态, 降低误操作与理解成本.
- 把 A11y 变成可审查的基线, 而不是"事后补丁".

## 适用范围

- 页面模板与组件模板: `app/templates/**`.
- JS 动态生成 UI(toast, modal, table actions): `app/static/js/**`.

## 规则(MUST/SHOULD/MAY)

### 1) 可访问名称(Accessible Name)

- MUST: 仅图标按钮必须具备稳定的可访问名称, 优先使用 `aria-label`.
- MUST: 关闭按钮(`btn-close`)必须使用 `aria-label="关闭"`, 见 [[standards/ui/close-button-accessible-name-guidelines]].
- SHOULD: 图标仅用于装饰时加 `aria-hidden="true"`.

### 2) 键盘可用性

- MUST: 关键操作必须可 Tab 聚焦并触发:
  - 使用原生 `<button>`/`<a>` 元素, 避免 `div role="button"`.
  - 不允许用 `onclick` 绑在不可聚焦元素上作为唯一入口.
- MUST NOT: 全站移除 focus 样式或用 CSS 抹掉 outline(会导致键盘用户迷路).

### 3) 表单与错误提示

- MUST: 输入必须有可关联的 label:
  - 优先 `<label for="...">` + `id="..."`.
  - 或使用 `aria-label`/`aria-labelledby`(仅在无法使用 label 时).
- MUST: 校验错误提示必须和输入关联:
  - 推荐为错误信息节点提供 `id`, 并给输入设置 `aria-describedby`.
- SHOULD: loading/提交中状态要可感知:
  - 按钮 loading 时设置 `aria-busy="true"` 或禁用按钮, 并在结束后恢复.

### 4) 弹窗/模态(Modal)

- MUST: Modal 打开后焦点应进入 modal 内可交互元素, 关闭后焦点回到触发按钮(Bootstrap 默认行为通常可满足, 但自定义实现需保证).
- MUST: Modal 必须可通过 ESC 关闭(除非是明确的不可取消高风险流程, 且必须说明原因).
- SHOULD: 对动态创建的 modal, 必须在销毁时 `dispose()`/解除事件绑定, 避免重复 mount 导致行为叠加.

### 5) 动态反馈(toast, alert, loading)

- MUST: 用户可见错误不得只写 `console.log`, 必须有可见反馈(如 toast/alert), 参考 [[standards/ui/async-task-feedback-guidelines]].
- SHOULD: toast/alert 的关闭按钮必须可聚焦且可读屏朗读(包含 `aria-label`).

## 自查清单(人工)

- 键盘 Tab: 能否到达导航, 表格行内按钮, modal 的关闭与确认按钮?
- 读屏: 图标按钮是否能朗读出动作(例如"删除", "刷新", "关闭")?
- 表单: 错误提示出现时, 读屏能否读到提示, 并且提示对应正确输入?

