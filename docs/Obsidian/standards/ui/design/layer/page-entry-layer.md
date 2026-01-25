---
title: Page Entry 页面入口层编写规范
aliases:
  - page-entry-layer-standards
tags:
  - standards
  - standards/ui
  - standards/ui/layer
status: active
enforcement: design
created: 2026-01-09
updated: 2026-01-25
owner: WhaleFall Team
scope: "`app/templates/**` 的 page_id + `app/static/js/bootstrap/page-loader.js` + 各页面入口脚本"
related:
  - "[[standards/ui/layer/README]]"
  - "[[standards/ui/javascript-module-standards]]"
  - "[[standards/ui/performance-standards]]"
  - "[[standards/ui/grid-standards]]"
  - "[[standards/ui/component-dom-id-scope-guidelines]]"
  - "[[standards/backend/layer/routes-layer-standards]]"
---

# Page Entry 页面入口层编写规范

> [!note] 说明
> Page Entry 是前端的"请求入口层". 它负责读取模板下发的数据, 组合 services/stores/views, 启动页面并完成 wiring. 类比后端 [[standards/backend/layer/routes-layer-standards|Routes 路由层]], Page Entry 必须保持"薄", 业务逻辑应下沉到 store/actions 或 view components.
>
> 本文为 `enforcement: design`: 描述默认方案与推荐边界. 除明确的安全底线外, 尽量用 SHOULD 表达(避免为了满足形式而过度抽象/过度拆分).

## 目的

- 统一页面启动方式, 降低脚本加载顺序与全局变量耦合带来的不确定性.
- 固化"依赖注入"与"入口读全局, 下层不碰全局"的规则, 让分层可持续推进.
- 让页面脚本更易审查: 只保留 wiring 与 domain renderers, 避免重复实现通用能力.

## 适用范围

- `app/templates/**` 中设置 `page_id` 并通过 `body[data-page]` 暴露给前端.
- `app/static/js/bootstrap/page-loader.js` 作为统一启动器.
- 各页面入口脚本(推荐位于 `app/static/js/modules/pages/**`; legacy 可能位于 `app/static/js/modules/views/**`, 需逐步迁移), 负责挂载 `window.<PageId>`.

## 规则(MUST/SHOULD/MAY)

### 1) 单一入口(page_id + page-loader)

- SHOULD: 默认通过 `page_id + page-loader` 启动页面.
- MUST: 若页面走 `page-loader` 路径, 模板必须设置 `page_id`, 且值必须为安全的全局键名(禁止 `__proto__/prototype/constructor` 等危险键).
- MUST: 若页面走 `page-loader` 路径, 页面入口脚本必须在 `window` 上暴露 `window.<PageId>`:
  - 允许: `window.<PageId> = function mount(global) {}`
  - 推荐: `window.<PageId> = { mount(global) { ... } }`
- SHOULD: `mount` 支持接收 `global` 参数(由 page-loader 传入 `window`), 便于测试与隔离.

### 2) 职责边界(入口必须薄)

- SHOULD: Page Entry 只负责 wiring:
  - 读取 DOM dataset/模板下发的 `data-*`.
  - 实例化 service/store, 组合 view, 注册事件与插件.
  - 触发首屏加载动作(例如 `store.actions.load()`).
- SHOULD NOT: 在 Page Entry 内实现可复用组件的 DOM 细节(应下沉到 view/ui modules).
- SHOULD NOT: 在 Page Entry 内写入 API path 常量或拼接复杂 query(优先下沉到 service 或 `Views.GridPage`).

### 3) 全局依赖读取规则

- SHOULD: Page Entry 负责读取全局依赖并完成 wiring.
- SHOULD: `window.*` 的访问规则以 [[standards/ui/layer/README#全局依赖(window.*) 访问规则(SSOT)|全局依赖(window.*) 访问规则(SSOT)]] 为单一真源.
- SHOULD: 下层优先通过参数接收依赖; 如确需读取 `window.*`, 仅允许访问 allowlist 内的全局.
- MAY: 迁移期 legacy 代码可临时读取 allowlist 外 `window.*`, 但必须在评审中说明原因, 并给出迁移计划.

### 4) 模板数据下发与 dataset 契约

- SHOULD: 页面模板通过"单一根节点"承载页面配置, 使用 `data-*` 下发, 避免散落全局变量.
- SHOULD: dataset key 使用 `kebab-case`, 对应 JS 侧通过 `element.dataset.*`(camelCase) 读取.
  - 示例: `data-page-size="20"` -> `root.dataset.pageSize`
  - 示例: `data-user-id="42"` -> `root.dataset.userId`
- SHOULD: 对 JSON 字符串仅解析一次并尽早失败(fail fast): `JSON.parse` 失败时抛异常/中止 mount, 避免页面进入半初始化状态.
- MUST NOT: 将来自 dataset/URL/表单的动态键名不加过滤地写入对象或透传到 URL 参数(原型污染风险).
  - MUST: 过滤危险键: `__proto__`, `prototype`, `constructor`.
  - SHOULD: 对动态键建立 allowlist(allowed keys), 避免无意透传未知字段.

### 5) 列表页 wiring 必须使用 GridPage skeleton

- SHOULD: Grid 列表页遵循 [[standards/ui/grid-standards|Grid 列表页标准]](该文档为 `enforcement: gate`, 以门禁为准).

### 6) 生命周期与清理

- SHOULD: 页面入口维护可销毁句柄(如 `gridPage.destroy()`), 并在需要时提供 `destroy()`.
- SHOULD: 事件绑定保持可解除(使用 delegation/plugin destroyers 或显式 removeEventListener), 避免重复 mount 导致的多次绑定.

### 7) 性能约束(SSR first + no waterfalls)

- SHOULD: 首屏关键内容优先由 SSR 输出, 避免把页面变成"空壳 + JS 拉数据".
- SHOULD: 若 Page Entry 启动阶段需要多个独立异步任务, 优先并行执行(例如 `Promise.all`), 避免无依赖的串行 await.
- SHOULD: 对可跳过路径, 延后 `await` 到分支内部, 避免阻塞未走到的路径.

## 正反例

### 正例: 模板设置 page_id 并按需引入页面脚本

```jinja2
{% extends "base.html" %}
{% set page_id = "InstancesListPage" %}

{% block extra_js %}
  <script src="{{ url_for('static', filename='js/modules/views/instances/list.js') }}"></script>
{% endblock %}
```

### 正例: 页面脚本暴露 window.<PageId>.mount, 只做 wiring

- 判定点:
  - 入口只做 wiring: 读取 dataset/DOM, 组装 services/stores/views, 启动首屏加载.
  - Grid 列表页通过 `Views.GridPage.mount(...)` 统一入口, 入口层只写配置.
  - 最终暴露 `window.<PageId>.mount(global)` 供 page-loader 调用.
- 长示例见: [[reference/examples/ui-layer-examples#Page Entry 示例|Page Entry 示例(长示例)]]

### 反例: 页面入口硬编码 API path 或实现通用 helper

```javascript
// 反例: API path 不应散落在页面脚本, 应下沉到 service.
const url = "/api/v1/instances/actions/batch-delete";

// 反例: 列表页脚本不得新增通用 escapeHtml/serializeForm 等实现.
function escapeHtml(s) {
  return String(s).replace(/</g, "&lt;");
}
```

## 门禁/检查方式

- 评审检查:
  - 页面脚本是否只保留 wiring 与 domain renderers?
  - Grid 列表页是否通过 `Views.GridPage.mount` 统一入口?
  - 是否存在在页面脚本内新增 `escapeHtml/serializeForm` 等通用 helper?
- 自查命令(示例):

```bash
rg -n "\\{%\\s*set\\s+page_id\\s*=\\s*" app/templates
rg -n "new\\s+GridWrapper\\(|new\\s+gridjs\\.Grid\\(" app/static/js/modules
rg -n "function\\s+(escapeHtml|serializeForm|resolveErrorMessage)\\(" app/static/js/modules
```

## 变更历史

- 2026-01-09: 新增 Page Entry 分层标准, 对齐后端 Routes 层的"入口薄"原则, 并与 `Views.GridPage` skeleton 约束对齐.
- 2026-01-14: 对齐 `window.*` allowlist SSOT, 明确 `modules/pages/**` 迁移方向, 并补齐 dataset `kebab-case` -> `dataset.camelCase` 示例.
