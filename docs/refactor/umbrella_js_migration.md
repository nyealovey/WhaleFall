# 使用 Umbrella JS 替换原生 DOM 操作/事件/AJAX 的改造指南

> 目标：统一 DOM 查询、事件绑定/委托、AJAX 调用到 Umbrella JS（简称 uQuery）体系，降低手写兼容代码，配合 Lodash 改造完成前端基础库收敛。

## 1. 获取基础库

我们使用官方发行包，统一由 `static/vendor/umbrella/umbrella.min.js` 引入。

1. 仓库已内置 `app/static/vendor/umbrella/umbrella.min.js`（版本 3.3.1），若需更新，可重新下载：
   ```bash
   curl -L https://unpkg.com/umbrella@3.3.1/dist/umbrella.min.js -o app/static/vendor/umbrella/umbrella.min.js
   ```
2. 在模板或入口脚本中引入（需早于业务脚本、晚于 Lodash）：
   ```html
   <script src="{{ url_for('static', filename='vendor/umbrella/umbrella.min.js') }}"></script>
   ```
3. 所有业务代码直接调用全局 `u(...)`，不得再保留 `$`、`$u` 等别名，避免多套 DOM API。

## 2. DOM 查询与遍历

| 场景 | 旧写法 | Umbrella JS 写法 |
| --- | --- | --- |
| 查询单个元素 | `document.querySelector('#selector')` | `u('#selector')`（返回类数组对象） |
| 多元素循环 | `document.querySelectorAll('.item').forEach(fn)` | `u('.item').each((el, i) => { ... })` |
| 属性/数据操作 | `element.dataset.foo = 'bar'` | `u(el).data('foo', 'bar')` |
| class 切换 | `element.classList.add('is-active')` | `u(el).addClass('is-active')` / `removeClass` / `toggleClass` |

**迁移建议**
1. 新增 `dom.helpers.js`，封装常用模式（例如 `selectOne`, `selectAll`），只返回 Umbrella 对象，不再暴露原生节点。
2. Lodash 专注数据整形，Umbrella 专注 DOM/事件，两个层次都必须引入。

## 3. 事件绑定与委托

| 场景 | 旧写法 | Umbrella 写法 |
| --- | --- | --- |
| 绑定事件 | `element.addEventListener('click', handler)` | `u(element).on('click', handler)` |
| 移除事件 | `element.removeEventListener('click', handler)` | `u(element).off('click', handler)` |
| 事件委托 | `container.addEventListener('click', e => { if (e.target.matches('.btn')) ... })` | `u(container).on('click', '.btn', handler)` |

**最佳实践**
- 将大量事件绑定的模块改造为“单 root + 委托”模式，替换散落的 `addEventListener`。
- 与 Lodash 的 `debounce/throttle` 组合使用，替代手写 `setTimeout`。

## 4. DOM 结构操作

| 操作 | Umbrella 示例 |
| --- | --- |
| 插入 | `u('#list').append('<li>...</li>')` |
| 修改文本 | `u('.title').text('新标题')` |
| 切换属性 | `u(el).attr('disabled', true)` |
| 获取表单值 | `u(form).serialize()`（返回 URL 查询字符串，可配合 `URLSearchParams` 或自定义解析） |

复杂表单序列化统一使用 Umbrella 的 `serialize()` 或 `form.helpers.js` 中的封装，禁止继续依赖 `FilterUtils.serializeForm`。

## 5. AJAX（请求/响应）

Umbrella 的 `u.ajax` 可覆盖多数场景；若需要自定义 header/鉴权，可封装 `httpUmbrella.js`。

```javascript
u.ajax({
  url: '/logs/api/search',
  method: 'GET',
  data: filters,        // 对象会自动转换为 query string
  headers: { 'X-CSRFToken': window.getCSRFToken() },
}).then(res => {
  // res.response 包含原始响应；res.data 需手动 JSON.parse
  const payload = JSON.parse(res.response || '{}');
}).catch(err => {
  console.error('请求失败', err);
});
```

**封装建议**
1. 建立 `app/static/js/core/http-u.js`，暴露 `get/post/del` 等函数，内部可以继续复用 axios 也可以改用 `u.ajax`，但对外语义必须一致（自动附带 CSRF、错误提示、返回 Promise）。
2. 立即在所有模块中改用 `http-u`，并移除 `window.http` 的直接引用，后续如需从 axios 迁移到 `u.ajax` 只需修改这一处封装。

## 6. 迁移步骤

1. **引入基础库**：下载 `umbrella.min.js` 并在模板加载。
2. **封装工具层**：
   - `dom.helpers.js`：对常用 DOM 操作（查询、class、data）提供语义化函数。
   - `http-u.js`：对 `u.ajax` 做统一头信息、错误处理。
3. **模块逐个迁移**：
   - 优先处理事件密集的页面（例如 `history/logs.js`, `instances/list.js`）。
   - 替换 `document.querySelectorAll + forEach` 为 `u('.selector').each`。
   - 替换 `addEventListener`/`removeEventListener` 为 `on/off`。
4. **移除手写 Polyfill**：迁移时直接删除自定义事件委托、DOM 工具函数，禁止回退到旧实现。
5. **自动化校验**：扩展 `scripts/audit_lodash_usage.py`，新增 Umbrella 检测（如 `querySelectorAll`, `addEventListener` 等），持续提醒开发者使用统一封装。

## 7. 示例：日志列表页面

```javascript
// 旧写法
const rows = document.querySelectorAll('.log-row');
rows.forEach(row => row.addEventListener('click', () => showDetail(row.dataset.id)));

// 新写法
u('#logsContainer').on('click', '.log-row', (event, row) => {
  showDetail(u(row).data('id'));
});
```

```javascript
// 旧 AJAX
http.get(`/logs/api/search?${params}`).then(handleResponse);

// 新 AJAX
httpU.get('/logs/api/search', filters).then(handleResponse);
```

## 8. 验收标准

- 任何新页面的 DOM 查询、事件绑定、AJAX 均通过 Umbrella 抽象层完成。
- 旧代码迁移后不再直接调用 `querySelector(All)`, `addEventListener`, `fetch`/`http.*`。
- 自动化检测（lint/脚本）无违规输出，并在 PR checklist 中新增 “Umbrella JS” 检查项。

## 9. FAQ

- **Umbrella 与 Lodash 冲突吗？** 不冲突。Umbrella 负责 DOM/事件，Lodash 负责数据操作，互补使用即可。
- **如何处理大型表单序列化？** 使用 Umbrella 的 `serialize()` 或基于其封装的 `form.helpers.js`；`FilterUtils` 已淘汰。
- **可以和 jQuery 共存吗？** 不可以。迁移完成后必须移除 jQuery，以免加载多个 DOM 库。

## 10. 2025-11-14 扫描结果：仍需 Umbrella 改造的脚本

> 扫描方式：使用 `rg "document\\.(querySelector|querySelectorAll|getElementById)" app/static/js`, `rg "addEventListener" app/static/js`, `rg "window\\.http\\b" app/static/js`, `rg "http\\.(get|post|put|delete|patch)" app/static/js`, `rg "fetch\\(" app/static/js`，定位仍旧直接操作 DOM 或旧 HTTP 封装的模块。

### 10.1 表单 / 页面脚本（按文件行数升序）
- `app/static/js/pages/instances/list.js`（658 行）：部分批量操作、CSV 导入仍在使用 `document.*`，需要继续替换为 DOMHelpers。
- `app/static/js/pages/tags/batch_assign.js`（854 行）：大量 `document.*`、`innerHTML` 和 `window.http`；需要改为 `DOMHelpers` + `httpU`，并替换节点操作为 `u(...)`。
- `app/static/js/pages/admin/scheduler.js`（984 行）：任务表格、模态框均使用原生 DOM/事件，需要 Umbrella 化并引入统一 HTTP 封装。
- `app/static/js/pages/accounts/account_classification.js`（1010 行）：渲染、表单、按钮事件都直接触 DOM，且依赖全局函数调用，应拆分为 Umbrella 事件委托。

### 10.2 共享组件 / 工具
- `app/static/js/common/permission_policy_center.js`（716 行）：动态构建权限树仍依赖原生 query，需要 Umbrella 化。
- `app/static/js/components/tag_selector.js`（1099 行）：自定义组件仍以 `document.querySelector*`、`closest` 直接操作 DOM，并调用 `window.http`；需要改为 `DOMHelpers` 与 `httpU`。

### 10.3 容量统计子系统
当前批次的容量统计相关脚本（filters/summary_cards/data_source/chart_renderer/manager 及实例、数据库聚合页面）已完成 Umbrella 改造，无新增待迁移项；后续若有新模块加入再补充清单。

以上脚本需要纳入下一轮 Umbrella JS 改造计划，迁移完成后务必运行 `scripts/audit_lodash_usage.py`（可扩展 Umbrella 检测）确保无新增 `document.*`/`addEventListener` 调用。
