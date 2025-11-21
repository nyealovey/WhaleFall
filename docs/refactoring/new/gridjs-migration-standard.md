# Grid.js 列表与分页替换标准

> 适用于将现有 Bootstrap/Table 渲染的列表升级为基于 Grid.js + GridWrapper 的统一实现，本文以凭据管理页面为基线。

## 1. 功能目标
- 统一分页 / 排序 / 筛选逻辑，支持服务端数据源。
- 前后端交互使用 `/xxx/api/xxx` REST 接口，响应格式需包含 `items`, `total`, `page`, `pages`。
- 表格列渲染支持自定义 HTML（使用 `gridjs.html`）。

## 2. 通用资产
- **脚本与样式**
  - `app/static/vendor/gridjs/gridjs.umd.js`
  - `app/static/vendor/gridjs/mermaid.min.css`
  - `app/static/js/common/grid-wrapper.js`（禁止擅自修改）
- **引用模板**：在 `templates/foo/list.html` 中添加
  ```html
  <link rel="stylesheet" href="{{ url_for('static', filename='vendor/gridjs/mermaid.min.css') }}">
  <script src="{{ url_for('static', filename='vendor/gridjs/gridjs.umd.js') }}"></script>
  <script src="{{ url_for('static', filename='js/common/grid-wrapper.js') }}"></script>
  ```

## 3. 接口约定
- `GET /<module>/api/<resource>` 支持参数：`page`, `limit`, `sort`, `order`，以及业务筛选参数。
- 返回结构：
  ```json
  {
    "data": {
      "items": [...],
      "total": 123,
      "page": 1,
      "pages": 7
    },
    "success": true,
    "message": "操作成功"
  }
  ```

## 4. 前端脚本标准流程
1. **入口脚本**：创建 `app/static/js/modules/views/<module>/list.js`，导出 `mount()`。
2. **初始化**：
   ```javascript
   credentialsGrid = new global.GridWrapper(container, {
     columns: [...],
     server: {
       url: '/<module>/api/<resource>?sort=id&order=desc'
     }
   });
   const initialFilters = normalizeFilters(resolveFormValues());
   credentialsGrid.init();
   if (Object.keys(initialFilters).length) {
     credentialsGrid.setFilters(initialFilters);
   }
   ```
3. **列配置**：每列需定义 `name` 与 `id`，如需渲染 HTML 使用 `gridjs.html`。
4. **`server.then`**：处理响应，返回二维数组。最后一列可附带 metadata 方便 formatter 使用。
5. **`server.total`**：返回 `payload.total`，驱动分页。

## 5. 筛选与搜索
- 筛选表单使用统一的 filter-card 组件（`components/filters/macros.html` + `js/modules/ui/filter-card.js`）。
- `applyFilters()` 中调用 `credentialsGrid.updateFilters(filters)`，由 GridWrapper 接管 URL 拼接。
- 输入框默认带 400ms 防抖，select / checkbox change 直接触发。

## 6. 模板结构
- 保留原卡片、筛选区、网格容器（例如 `<div id="credentials-grid"></div>`）。
- 模态 / 操作按钮按需保留。

## 7. 回归清单
- 搜索、筛选、分页、排序均能触发带参数的 Network 请求。
- 删除 / 编辑等操作结束后调用 `grid.refresh()` 重新加载数据。
- 关闭模态不会触发无效请求。

## 8. 注意事项
- **禁止修改** `app/static/js/common/grid-wrapper.js`，如需扩展功能先讨论评审。
- 所有引入新命名需符合 AGENTS.md 中命名规范。
- 部署后强制刷新浏览器缓存（Ctrl/Cmd + Shift + R）。

## 9. 参考实现
- 凭据管理页面：`app/templates/credentials/list.html`、`app/static/js/modules/views/credentials/list.js`、`app/routes/credentials.py:200+`

