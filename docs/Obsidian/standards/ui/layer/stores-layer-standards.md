---
title: Stores 前端状态层编写规范
aliases:
  - ui-stores-layer-standards
tags:
  - standards
  - standards/ui
  - standards/ui/layer
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: "`app/static/js/modules/stores/**` 下所有前端 Store(状态 + actions)"
related:
  - "[[standards/ui/layer/README]]"
  - "[[standards/ui/javascript-module-standards]]"
  - "[[standards/backend/layer/services-layer-standards]]"
---

# Stores 前端状态层编写规范

> [!note] 说明
> Stores 层承载前端的"业务编排 + 状态管理". 它是 view 与 service 之间的中间层: view 触发 actions, store 调用 services, 更新状态并广播事件.

## 目的

- 将"状态 + actions + 事件"集中到 store, 降低页面脚本复杂度与重复实现.
- 固化事件命名与错误口径, 让 UI 更新和异步流程更可预测.
- 避免 DOM/Toast 漂移到 store, 保持可测试与可复用.

## 适用范围

- `app/static/js/modules/stores/**` 下所有 store 工厂函数与相关实现.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: store 只负责:
  - 状态管理(state, derived state).
  - actions(同步/异步), 调用 services 并更新状态.
  - 通过 mitt 广播事件, 通知 view 更新.
- MUST NOT: 直接操作 DOM(如 `document.querySelector`, `DOMHelpers`).
- MUST NOT: 直接触发 UI 提示(如 `toast.*`), 用户提示由 view 或页面控制器完成.
- MUST NOT: 直接调用 `window.httpU` 访问 API(应通过 service).

### 2) 导出形态与依赖注入

- MUST: store 以 `createXStore(options)` 形式导出, 并挂载 `window.createXStore`.
- MUST: `options.service` 为必填依赖, 并在创建时校验方法存在.
- SHOULD: `options.emitter` 支持注入, 未传入才回退 `window.mitt()`.

### 3) 状态暴露与不可变快照

- MUST: 对外暴露的 `getState()` 返回状态快照, 禁止直接返回内部 state 引用.
- SHOULD: 快照中避免返回可变引用(Set/Map), 对外转换为数组或普通对象.
- SHOULD: store 事件 payload 携带快照, 方便 view 在无额外读取的情况下渲染.

### 4) actions 规范

- MUST: actions 方法要么同步更新 state, 要么返回 `Promise`.
- MUST: 异步 actions 在 `catch` 中:
  - 记录 `state.lastError`.
  - emit `<domain>:error` 事件(携带 error 与 meta).
  - rethrow, 让上层决定是否 toast/回退.
- SHOULD: 使用 loading/operation 标记(state.loading, state.operations), 避免 UI 重复点击.
- SHOULD: 需要依赖后端 envelope(`success=false`)时, 在 store 内转换为 `Error`, 并保留原始响应.

### 5) 事件命名与释放

- SHOULD: 事件名遵循 `<domain>:<action>` 约定, 并以常量集中管理.
- MUST: 提供 `subscribe(event, handler)` 与 `unsubscribe(event, handler)`.
- MUST: 提供 `destroy()` 清理 emitter 订阅与内部状态, 避免长驻页面造成泄漏.

### 6) 安全键过滤(对象注入/原型污染防御)

- MUST: 对来自表单/URL/dataset 的动态键名, 在写入对象或作为 map key 前过滤:
  - `__proto__`, `prototype`, `constructor`
- SHOULD: 对允许键建立 allowlist(Set), 并在写入时校验, 避免误写入未知字段.

## 正反例

### 正例: createXStore + emitter + error event + rethrow

- 判定点:
  - `createXStore({ service, emitter })` 形态导出, 并挂载到 `window.createXStore`.
  - actions 出错时 emit `<domain>:error` 且 rethrow, 交由上层决定提示策略.
  - `getState()` 返回快照, 不暴露内部可变引用.
- 长示例见: [[reference/examples/ui-layer-examples#Stores 示例|UI Stores 示例(长示例)]]

### 反例: store 直接操作 DOM 或直接调用 httpU

```javascript
function createBadStore() {
  return {
    actions: {
      load: function () {
        document.querySelector("#root").textContent = "loading..."; // 反例: store 不得操作 DOM
        return window.httpU.get("/api/v1/tags"); // 反例: store 不得直接调用 httpU
      },
    },
  };
}
```

## 门禁/检查方式

- 评审检查:
  - store 是否只依赖 service, 且不触碰 DOM/toast/httpU?
  - actions 是否在错误时 emit error 并 rethrow?
  - `getState()`/payload 是否返回快照而非内部引用?
- 自查命令(示例):

```bash
rg -n "document\\.|DOMHelpers|toast\\.|httpU\\." app/static/js/modules/stores
rg -n "create[A-Za-z0-9]+Store\\s*\\(" app/static/js/modules/stores
```

## 变更历史

- 2026-01-09: 新增前端 Stores 分层标准, 明确其作为"状态 + actions"的业务编排层定位, 并固化 emitter/错误事件/快照暴露规则.
