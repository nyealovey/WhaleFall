---
title: 前端模块化(modules)规范
aliases:
  - javascript-module-standards
tags:
  - standards
  - standards/ui
status: active
enforcement: design
created: 2025-12-25
updated: 2026-01-25
owner: WhaleFall Team
scope: "`app/static/js/modules/**`(services/stores/views/ui)与相关全局对象(`DOMHelpers/httpU/UI`)"
related:
  - "[[standards/ui/gate/component-dom-id-scope]]"
  - "[[standards/ui/guide/layer/README]]"
  - "[[standards/ui/design/vendor-library-usage]]"
---

# 前端模块化(modules)规范

## 目的

- 把前端代码拆成可复用的 services/stores/views/ui 四层, 降低页面脚本复杂度与重复实现.
- 固化"依赖注入, 事件总线, 错误处理, 安全键白名单"等约定, 避免出现难排查的全局耦合与安全回归.

## 适用范围

- `app/static/js/modules/services/**`: service(API client) 层
- `app/static/js/modules/stores/**`: store(状态 + actions + mitt 事件) 层
- `app/static/js/modules/views/**`: view(DOM 渲染与交互) 层
- `app/static/js/modules/ui/**`: UI modules(可复用 UI 行为) 层

## 规则(MUST/SHOULD/MAY)

> [!info] SSOT
> modules 的分层标准已按层拆分为 SSOT 文档, 本文只保留概览与入口:
> - [[standards/ui/guide/layer/README|前端分层(layer)标准索引]]

### 1) 依赖方向(必须)

- MUST: Page Entry -> Views -> Stores -> Services
- MUST: Services 不得依赖 Stores/Views/UI modules
- MUST: Stores 不得依赖 Views/UI modules, 且不得直接访问 `window.httpU`
- MUST: Views 不得承载业务规则, 业务动作必须通过 store actions 或 service 方法驱动

详细规则见:

- [[standards/ui/design/layer/page-entry-layer|Page Entry 页面入口层编写规范]]
- [[standards/ui/design/layer/services-layer|Services 前端服务层编写规范]]
- [[standards/ui/design/layer/stores-layer|Stores 前端状态层编写规范]]
- [[standards/ui/design/layer/views-layer|Views 视图层编写规范]]
- [[standards/ui/design/layer/ui-layer|UI Modules 工具层编写规范]]

### 2) 文件命名(概览)

- MUST: `services/` 与 `stores/` 文件名使用 `snake_case.js`(与现有目录保持一致).
- SHOULD: `views/` 新文件优先 `kebab-case.js`(历史遗留允许 `snake_case.js`).

### 3) 安全与键白名单(必须)

- MUST: 将对象序列化为 query string, 或写入 map/object 时, 必须过滤危险键:
  - `__proto__`, `prototype`, `constructor`
- SHOULD: 对来自 URL/表单/dataset 的动态对象建立 allowlist(allowed keys), 避免无意透传字段或触发对象注入

### 4) 错误处理(概览)

- MUST: 用户可见错误使用 toast 或页面提示, 不得仅 `console.log`
- MAY: 当关键依赖缺失(`DOMHelpers/httpU/GridWrapper` 等)时使用 `console.error` 并短路退出, 避免页面半初始化

## 正反例

### 正例: 按依赖方向分层

- Page Entry 只做 wiring: 组装 config, 调用 `Views.*.mount(...)`.
- View 只负责 DOM 渲染与事件绑定, 业务动作通过 store actions 或 service 方法驱动.

### 反例: 层级倒置或全局耦合

- View 直接调用 `window.httpU` 或直接发请求(应下沉到 service).
- Store 依赖 View/UI modules, 导致循环依赖与复用困难.

## 逐页迁移最小套路(不引入构建工具)

> [!note] 目标
> 把"巨型页面脚本"拆成可审查的 wiring + services/stores/views, 并保持行为不变.

1) 模板侧

- 为页面设置 `page_id`.
- 页面私有资源放在 `extra_css`/`extra_js`, 避免污染 `base.html`.
- 页面数据通过"单一根节点 dataset"下发(见 Page Entry 标准).

2) Page Entry(入口 wiring)

- 暴露 `window.<PageId> = { mount(global) { ... } }`.
- 读取 dataset, 组装 service -> store -> view.
- 触发首屏动作(通常是 `store.actions.load()`), 并保存 destroy 句柄.

3) Services(API client)

- 只封装请求细节: path, query/payload, 最小错误转换.
- 通过构造器注入 `httpClient`(迁移期允许 fallback `window.httpU`).

4) Stores(状态 + actions)

- 只依赖 service, 不触碰 DOM/toast/httpU.
- actions 出错 emit `<domain>:error` 并 rethrow, 由 view 决定提示策略.

5) Views(DOM + 交互)

- 事件绑定必须可解除(提供 `destroy()`).
- 输出 HTML 时遵循 XSS 规则(escapeHtml, 不拼未转义 innerHTML).
- 列表页遵循 `Views.GridPage` skeleton, 不重复造轮子.

## 门禁/检查方式

- ESLint 报告(改动 `app/static/js` 时建议执行): `./scripts/ci/eslint-report.sh quick`
- 分层/注入 contracts 门禁：`./scripts/ci/frontend-contracts-guard.sh`
- 安全规则提醒: 出现 `security/detect-object-injection` 时优先用 allowlist/固定映射消除, 而不是关闭规则

## 变更历史

- 2025-12-25: 初版, 统一 modules 分层职责, 命名, 依赖注入与安全键白名单策略.
- 2026-01-09: 拆分 layer SSOT 文档(`standards/ui/layer/**`), 本文收敛为概览与索引入口.
