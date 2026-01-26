---
title: Stores 前端状态层编写规范
aliases:
  - ui-stores-layer-standards
tags:
  - standards
  - standards/ui
  - standards/ui/layer
status: active
enforcement: design
created: 2026-01-09
updated: 2026-01-25
owner: WhaleFall Team
scope: "`app/static/js/modules/stores/**` 下所有前端 Store(状态 + actions)"
related:
  - "[[standards/ui/guide/layer/README]]"
  - "[[standards/ui/design/javascript-module]]"
  - "[[standards/backend/gate/layer/services-layer]]"
---

# Stores 前端状态层编写规范

> [!note] 说明
> Stores 层承载前端的"业务编排 + 状态管理". 它是 view 与 service 之间的中间层: view 触发 actions, store 调用 services, 更新状态并广播事件.
>
> 本文为 `enforcement: design`: 描述默认分层与推荐边界. `MUST` 主要保留给安全底线(例如危险键过滤)与明显的错误用法, 其余尽量用 SHOULD 表达(避免为满足形式而过度封装/过度抽象).

## 目的

- 将"状态 + actions + 事件"集中到 store, 降低页面脚本复杂度与重复实现.
- 固化事件命名与错误口径, 让 UI 更新和异步流程更可预测.
- 避免 DOM/Toast 漂移到 store, 保持可测试与可复用.

## 适用范围

- `app/static/js/modules/stores/**` 下所有 store 工厂函数与相关实现.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- SHOULD: store 只负责:
  - 状态管理(state, derived state).
  - actions(同步/异步), 调用 services 并更新状态.
  - 通过 mitt 广播事件, 通知 view 更新.
- SHOULD NOT: 直接操作 DOM(如 `document.querySelector`, `DOMHelpers`).
- SHOULD NOT: 直接触发 UI 提示(如 `toast.*`), 用户提示由 view 或页面控制器完成.
- SHOULD NOT: 直接调用 `window.httpU` 访问 API(优先通过 service).

### 2) 导出形态与依赖注入

- SHOULD: store 以 `createXStore(options)` 形式导出(便于注入依赖与测试), 是否挂载到 `window.*` 以现有 wiring 方式为准.
- SHOULD: `options.service` 通过注入传入(避免在 store 内直接 new service).
- SHOULD: `options.emitter` 支持注入, 未传入才回退 `window.mitt()`.

### 3) 状态暴露与不可变快照

- SHOULD: 对外暴露的 `getState()` 返回状态快照, 避免直接暴露内部可变引用导致“外部误改 state”.
- SHOULD: 快照中避免返回可变引用(Set/Map), 对外转换为数组或普通对象.
- SHOULD: store 事件 payload 携带快照, 方便 view 在无额外读取的情况下渲染.

### 4) actions 规范

- SHOULD: actions 方法要么同步更新 state, 要么返回 `Promise`.
- SHOULD: 为每个 store 选定一种“错误传播策略”, 并保持一致:
  - A) 抛异常(rethrow) -> 上层(view/page)决定 toast/回退
  - B) 返回显式失败结果(例如 `{ ok: false, error }`) -> 上层按结果分支处理
- MUST: 禁止 silent swallow(吞异常后当成功继续走下去). 异步 actions 出错时至少要让调用方可感知(throw 或显式失败返回).
- SHOULD: 异步 actions 出错时, 记录 `state.lastError` 并 emit `<domain>:error`(携带 error 与 meta), 便于统一 UI 反馈与调试.
- SHOULD: 使用 loading/operation 标记(state.loading, state.operations), 避免 UI 重复点击.
- SHOULD: 需要依赖后端 envelope(`success=false`)时, 在 store 内转换为 `Error`, 并保留原始响应.

### 5) 事件命名与释放

- SHOULD: 事件名遵循 `<domain>:<action>` 约定, 并以常量集中管理.
- SHOULD: 提供 `subscribe(event, handler)` 与 `unsubscribe(event, handler)`(或等价方式), 让 view 可控订阅与释放.
- SHOULD: 提供 `destroy()` 清理 emitter 订阅与内部状态, 避免长驻页面造成泄漏.

### 6) 安全键过滤(对象注入/原型污染防御)

- MUST NOT: 将来自表单/URL/dataset 的动态键名不加过滤地写入对象或作为 map key(原型污染风险).
  - MUST: 过滤危险键: `__proto__`, `prototype`, `constructor`.
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
