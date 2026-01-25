---
title: UI Modules 工具层编写规范
aliases:
  - ui-modules-layer-standards
tags:
  - standards
  - standards/ui
  - standards/ui/layer
status: active
enforcement: design
created: 2026-01-09
updated: 2026-01-25
owner: WhaleFall Team
scope: "`app/static/js/modules/ui/**` 下可复用 UI 工具与交互组件"
related:
  - "[[standards/ui/layer/README]]"
  - "[[standards/ui/javascript-module-standards]]"
  - "[[standards/ui/button-hierarchy-guidelines]]"
  - "[[standards/ui/danger-operation-confirmation-guidelines]]"
  - "[[standards/ui/component-dom-id-scope-guidelines]]"
---

# UI Modules 工具层编写规范

> [!note] 说明
> UI Modules 层承载"可复用的 UI 行为". 它提供与业务无关的交互能力(确认弹窗, 按钮 loading, filter card, modal adapter 等), 供 Views 组合使用. UI Modules 不应依赖具体业务域的 services/stores.
>
> 本文为 `enforcement: design`: 描述默认分层与推荐边界. `MUST` 主要保留给安全底线(例如危险键过滤)与明显的错误用法, 其余尽量用 SHOULD 表达(避免为满足形式而过度抽象).

## 目的

- 收敛 UI 行为实现, 避免每个页面重复实现确认弹窗/防抖提交/按钮 loading 等逻辑.
- 固化可复用组件的 DOM id 作用域与事件清理约束, 降低组件冲突与泄漏风险.
- 保持 UI 模块"无业务", 让其可跨页面复用并可独立演进.

## 适用范围

- `app/static/js/modules/ui/**`

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- SHOULD: UI Modules 只负责:
  - UI 行为与交互(显示/隐藏, loading, confirm, modal wiring, filter serialize).
  - 安全与一致性约束(危险键过滤, DOM id scope, 可访问性属性).
- SHOULD NOT: 直接调用业务 API 或依赖业务 services/stores.
- SHOULD NOT: 内置任何业务域常量(如特定页面 selector, 业务枚举值).

### 2) 导出与命名

- SHOULD: 通用 helper 优先挂载到 `window.UI` 命名空间(避免污染顶层 `window`).
- MAY: 独立模块可挂载为 `window.<ModuleName>`(例如 `window.TermsModal`), 但必须在 README/用法处说明.
- SHOULD: 文件命名与目录约定保持一致(新文件优先 `kebab-case.js`).

### 3) 依赖与全局读取

- SHOULD: `window.*` 的访问规则以 [[standards/ui/layer/README#全局依赖(window.*) 访问规则(SSOT)|全局依赖(window.*) 访问规则(SSOT)]] 为单一真源.
- SHOULD: UI Modules 允许依赖:
  - `window.DOMHelpers`
  - `window.UI`(同层工具)
  - `window.EventBus`(仅在需要跨组件同步/观测时使用)
  - vendor libs(如 `bootstrap`)
- SHOULD: 依赖缺失时 fail fast(抛异常/显式返回错误结果), 避免半初始化与 silent fallback.

### 4) DOM id 作用域与可访问性

- SHOULD: 遵循 [[standards/ui/component-dom-id-scope-guidelines|可复用组件 DOM id 作用域规范]](该文档为 `enforcement: gate`, 以门禁为准).
- SHOULD: 为可点击/可关闭组件补齐可访问名称(aria-label), 参考 [[standards/ui/close-button-accessible-name-guidelines]].

### 5) 安全键过滤

- MUST NOT: 将来自表单/URL/dataset 的动态键名不加过滤地写入对象(原型污染风险).
  - MUST: 过滤危险键: `__proto__`, `prototype`, `constructor`.
- SHOULD: 对可序列化字段建立 allowlist, 避免意外收集无关字段.

### 6) 事件绑定与 destroy

- SHOULD: UI 模块绑定的事件保持可解除, 并提供 `destroy()` 或返回 destroyer.
- SHOULD: 多次初始化同一组件必须可预测(避免重复绑定导致触发多次).

## 正反例

### 正例: UI 模块挂载到 window.UI, 并提供 destroyer

- 判定点:
  - UI 行为模块优先挂载到 `window.UI`, 避免污染顶层 `window`.
  - 事件绑定可解除, 初始化可重复执行且行为可预测.
  - 输入序列化/对象写入前做危险键过滤, 避免原型污染.
- 长示例见: [[reference/examples/ui-layer-examples#UI Modules 示例|UI Modules 示例(长示例)]]

### 反例: UI 模块直接依赖业务 service

```javascript
// 反例: UI 模块不得直接 new 业务 service 并调用 API.
const service = new window.InstanceService(window.httpU);
service.fetchInstances();
```

## 门禁/检查方式

- 评审检查:
  - UI 模块是否无业务依赖, 且事件绑定可解除?
  - 是否存在未过滤危险键的表单序列化实现?
- 自查命令(示例):

```bash
rg -n "new\\s+.*Service\\(|create.*Store\\(" app/static/js/modules/ui
rg -n "__proto__|prototype|constructor" app/static/js/modules/ui
```

## 变更历史

- 2026-01-09: 新增 UI Modules 分层标准, 明确其"无业务依赖"定位, 并固化 DOM id scope, 安全键过滤与 destroy 约束.
- 2026-01-14: 对齐 `window.*` allowlist SSOT, 明确 `EventBus` 仅用于跨组件同步/观测.
