# 前端模块化（modules）规范

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：`app/static/js/modules/**`（services/stores/views/ui），以及与之交互的全局对象（`DOMHelpers/httpU/UI`）

## 目的

- 把前端代码拆成可复用的“服务/状态/视图”三层，降低页面脚本复杂度与重复实现。
- 固化“依赖注入、事件总线、错误处理、安全键白名单”等约定，避免出现难排查的全局耦合与安全回归。

## 适用范围

- `app/static/js/modules/services/**`：服务层（HTTP 调用、参数序列化、错误转换）。
- `app/static/js/modules/stores/**`：状态层（状态 + actions + mitt 事件）。
- `app/static/js/modules/views/**`：视图层（DOM 渲染与交互，调用 store/actions）。
- `app/static/js/modules/ui/**`：UI 工具（确认弹窗、按钮 loading、FilterCard 等）。

## 规则（MUST/SHOULD/MAY）

### 1) 文件命名与导出方式

- MUST：`services/` 与 `stores/` 文件名使用 `snake_case.js`（与现有目录保持一致）。
- SHOULD：`views/` 文件名优先使用 `kebab-case.js`（页面与组件更易读）；历史遗留允许 `snake_case.js`，但新文件应避免新增下划线。
- MUST：服务层导出 CapWords 类或工厂函数，并显式挂载到 `window`（当前无打包链路）：
  - `global.TagManagementService = TagManagementService;`
- MUST：store 导出 `createXStore(...)` 工厂函数，并显式挂载到 `window`。

### 2) 分层职责（强约束）

- MUST：`services/` 只负责 HTTP 调用与参数/响应处理，禁止直接操作 DOM。
- MUST：`stores/` 只负责状态与 actions，禁止直接操作 DOM。
- MUST：`views/` 只负责 DOM 与交互，所有业务动作必须通过 store actions 或 service 方法驱动。

### 3) 依赖注入与全局回退

- MUST：service 构造函数或工厂函数接收 `httpClient`（默认允许回退 `window.httpU`），并做能力校验（例如 `typeof client.get === "function"`）。
- SHOULD：store 接收 `service` 与可选 `emitter`（mitt），若未传入才回退全局 `window.mitt()`。
- MUST：view 通过参数接收 store/service；仅在“页面启动入口”层读取 `window.DOMHelpers/httpU/UI` 等全局对象。

### 4) 事件命名与订阅释放

- SHOULD：store 事件名使用 `<domain>:<action>`（例如 `tagManagement:tagsUpdated`、`instances:selectionChanged`）。
- MUST：view 在 `destroy()` 中解除订阅/解绑事件，避免内存泄漏。

### 5) 安全与键白名单（原型污染/对象注入防御）

- MUST：把对象序列化为 query string 或写入 map 时，必须过滤 `__proto__/prototype/constructor` 等危险键。
- SHOULD：对来自 URL/表单/用户输入的对象，建立“允许键白名单”（allowed keys），避免无意中透传敏感字段或触发对象注入。

### 6) 错误处理与用户提示

- MUST：用户可见错误使用 toast 或页面提示，不得仅 `console.log`。
- MAY：当关键依赖缺失（`DOMHelpers/httpU/GridWrapper` 等）时使用 `console.error` 并短路退出，避免页面半初始化。

## 正反例

### 正例：Service 依赖注入并回退 `window.httpU`

```javascript
function ensureHttpClient(client) {
  const resolved = client || window.httpU || null;
  if (!resolved || typeof resolved.get !== "function") {
    throw new Error("httpClient 未初始化");
  }
  return resolved;
}
```

### 反例：Service 直接操作 DOM

- `services/*` 内部直接 `document.querySelector(...)` 并更新页面。

## 门禁/检查方式

- ESLint 报告（改动 `app/static/js` 时建议执行）：`./scripts/ci/eslint-report.sh quick`
- 安全规则提醒：出现 `security/detect-object-injection` 时优先用“允许键白名单/固定映射”消除，而不是关闭规则。

## 变更历史

- 2025-12-25：新增标准文档，统一 modules 分层职责、命名、依赖注入与安全键白名单策略。
