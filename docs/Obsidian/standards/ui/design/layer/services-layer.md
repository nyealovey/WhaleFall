---
title: Services 前端服务层编写规范
aliases:
  - ui-services-layer-standards
tags:
  - standards
  - standards/ui
  - standards/ui/layer
status: active
enforcement: design
created: 2026-01-09
updated: 2026-01-25
owner: WhaleFall Team
scope: "`app/static/js/modules/services/**` 下所有前端 API client 服务"
related:
  - "[[standards/ui/guide/layer/README]]"
  - "[[standards/ui/design/javascript-module]]"
  - "[[standards/backend/gate/layer/services-layer]]"
  - "[[standards/backend/standard/action-endpoint-failure-semantics]]"
---

# Services 前端服务层编写规范

> [!note] 说明
> 前端 Services 层的定位是 API client 封装: 统一 API path, query/payload 规整, 错误转换. 它不承担业务编排(那通常发生在 store/actions 与页面控制器), 也不直接触碰 DOM.
>
> 本文为 `enforcement: design`: 描述默认分层与推荐边界. `MUST` 主要保留给安全底线(例如危险键过滤)与明显的错误用法, 其余尽量用 SHOULD 表达(避免为了满足形式而过度封装).

## 目的

- 收敛 API path 与请求细节, 避免散落在页面脚本导致迁移成本高.
- 固化依赖注入(httpClient)与错误口径, 让调用方只关注业务流程.
- 防止 DOM/Toast/EventBus 漂移进 service, 保持分层可审查.

## 适用范围

- `app/static/js/modules/services/**` 下所有服务文件.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- SHOULD: Services 只负责:
  - HTTP 调用(get/post/put/patch/delete).
  - query/payload 序列化(例如 `URLSearchParams`, `FormData` 转换)与**最小**规整.
  - 响应结构规整(例如从 `resp.data` 取值)与最小错误转换.
  - 注: 字段级校验/复杂兼容/默认值策略以服务端为准, 前端 service 避免做“业务语义”的规范化.
- SHOULD NOT: 直接操作 DOM(如 `document.querySelector`, `DOMHelpers`).
- SHOULD NOT: 直接触发 UI 提示(如 `toast.*`)或发全局业务事件(如 `EventBus.emit`).
- SHOULD: 保持 service 方法为"薄"的请求封装, 将编排逻辑放到 store/actions.

### 2) 依赖注入(httpClient)

- SHOULD: service 构造函数接收 `httpClient`, 并允许回退 `window.httpU`(迁移期).
- SHOULD: service 只依赖 `httpClient` 提供的最小接口, 避免绑定具体实现细节.

### 3) API path 与命名

- SHOULD: API path 以常量集中管理(例如 `BASE_PATH`), 且与后端 contracts 保持一致.
- SHOULD: method 命名使用稳定动词:
  - `list`/`fetch*`/`get*` 用于读.
  - `create*`/`update*`/`delete*`/`restore*` 用于写.
  - `*Action` 或 `actions/*` 对应后端 action endpoints, 参考 [[standards/backend/standard/action-endpoint-failure-semantics]].
- SHOULD: 文件命名与导出形态以仓库现状为准(例如 `snake_case.js`), 由 Page Entry 负责 wiring.

### 4) query/payload 序列化与安全键过滤

- MUST NOT: 将来自 URL/表单/dataset 的动态键名不加过滤地写入对象或透传到 URL 参数(原型污染风险).
  - MUST: 过滤危险键: `__proto__`, `prototype`, `constructor`.
- SHOULD: 对调用方传入的 params 建立 allowlist(allowed keys), 防止无意透传字段.
- SHOULD: 优先使用 `URLSearchParams` 构造 query, 禁止手写字符串拼接导致重复编码或注入风险.

### 5) 错误处理

- MUST: 不吞异常. 出错时 reject/throw, 交由上层(store/view)决定用户提示与恢复策略.
- SHOULD: 保留 `httpU` 构造的错误信息(如 `error.status`, `error.response`), 不要丢失上下文.
- MAY: 将后端 `success=false` 的 envelope 转换为 `Error`, 但必须保留原始响应(例如 `error.raw = resp`).

### 6) 依赖规则

允许依赖:

- SHOULD: `window.httpU`(作为默认 httpClient)或由构造器注入的 `httpClient`.
- MAY: `URLSearchParams`, `FormData` 等原生能力.
- MAY: `window.LodashUtils`(仅在必要时, 且避免在 service 内做复杂业务逻辑).

禁止依赖:

- SHOULD NOT: `window.DOMHelpers`, `document`, `window.toast`, `window.EventBus`
- SHOULD NOT: `app/static/js/modules/stores/**`, `app/static/js/modules/views/**`

## 正反例

### 正例: 依赖注入 + 安全 query + window 挂载

- 判定点:
  - 通过构造器注入 `httpClient`, 允许回退到 `window.httpU`(迁移期).
  - query 构造使用 `URLSearchParams`, 并做 allowlist + 危险键过滤.
  - 最终挂载到 `window.<ServiceName>`, 供 Page Entry wiring 使用.
- 长示例见: [[reference/examples/ui-layer-examples#Services 示例|UI Services 示例(长示例)]]

### 反例: service 直接操作 DOM 或 toast

```javascript
class BadService {
  list() {
    document.querySelector("#root").textContent = "loading..."; // 反例: service 不得操作 DOM
    window.toast.error("failed"); // 反例: service 不得直接提示 UI
  }
}
```

## 门禁/检查方式

- 评审检查:
  - service 是否仅包含 HTTP 封装, 无 DOM/Toast/EventBus 逻辑?
  - 是否存在危险键未过滤的 query/payload 构造?
- 自查命令(示例):

```bash
rg -n "document\\.|DOMHelpers|toast\\.|EventBus" app/static/js/modules/services
rg -n "__proto__|prototype|constructor" app/static/js/modules/services
```

## 变更历史

- 2026-01-09: 新增前端 Services 分层标准, 明确其作为 API client 的定位, 并固化依赖注入与安全键过滤规则.
