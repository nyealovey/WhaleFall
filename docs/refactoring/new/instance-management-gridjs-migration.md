# 实例管理页面 Grid.js 迁移方案

> 目标：在保持原有功能与视觉体验的前提下，将实例管理列表统一迁移到 Grid.js + GridWrapper，沿用 `docs/refactoring/new/gridjs-migration-standard.md` 的接口/前端规范。

## 1. 范围与现状
| 层级 | 文件 | 说明 |
| --- | --- | --- |
| 路由 | `app/routes/instance.py` | 现有 `/instances/` 页面和若干操作 API；列表仍走模板渲染 + 自定义分页 |
| 模板 | `app/templates/instances/list.html` | Bootstrap `<table>`、分页器、筛选器、批量操作按钮、连接测试入口 |
| JS | `app/static/js/modules/views/instances/list.js` | 负责 DOM 渲染、筛选、批量操作、标签选择（TagSelectorHelper）、InstanceStore 同步 |
| 样式 | `app/static/css/pages/instances/list.css` | 表格/按钮/批量工具条/标签徽章等样式 |

保留特性：数据库类型筛选、标签筛选、批量操作（同步、删除等）、连接测试/详情入口、分页统计、顶部筛选卡片布局。

## 2. 迁移目标
1. **统一接口**：新增 `/instances/api/instances` 支持分页/排序/筛选，返回标准 `{ items,total,page,pages }`。
2. **GridWrapper 驱动**：表格列/分页/筛选全部由 Grid.js 管理，移除模板 `<table>` 与自定义分页。
3. **功能完备**：批量选择、同步、标签筛选、连接/测试按钮、导出/刷新等现有功能全部保留。
4. **视觉一致**：保持按钮组、工具栏、标签徽章、状态徽章等外观；Grid.js 行 hover/字体与旧表一致。
5. **性能**：后端批量加载标签/统计信息，避免 N+1；前端只渲染可视数据。

## 3. 后端 `/instances/api/instances`
- 参数：`page`, `limit`, `sort`, `order`, `search`, `db_type`, `status`, `tags`, `env`, `cluster`, …（与筛选表单一致）。
- Query：基于 `Instance`，按需 JOIN `tags`、`stat` 等；确保 `.all()` 前已分页。
- 输出：
  ```json
  {
    "success": true,
    "data": {
      "items": [
        {
          "id": 1,
          "name": "prod-db",
          "db_type": "mysql",
          "host": "10.0.0.1",
          "port": 3306,
          "main_version": "8.0",
          "is_active": true,
          "tags": [{"name": "critical", "display_name": "核心", "color": "danger"}],
          "active_db_count": 12,
          "active_account_count": 24,
          "last_sync_time": "2025-05-01T08:00:00+08:00"
        }
      ],
      "total": 268,
      "page": 1,
      "pages": 14
    }
  }
  ```
- 函数命名遵守规范：`list_instances_api`（动词短语，无 `api_` 前缀）；日志模块统一 `module="instance"`。

## 4. 模板改造 (`app/templates/instances/list.html`)
1. 引入 Grid.js 资产：`mermaid.min.css`、`gridjs.umd.js`、`grid-wrapper.js`。
2. 保留页头、筛选卡片、批量操作工具栏、统计信息等外层结构。
3. 将 `<table>` + 分页器替换为 `<div id="instances-grid"></div>`；工具栏中保留批量按钮、导出、刷新指标等。
4. 数据库类型/状态按钮组仍使用 `data-` 属性，由 JS 控制 URL 切换或 FilterCard。
5. 继续嵌入标签选择器模板（`components/tag_selector.html`）。

## 5. 前端脚本 (`app/static/js/modules/views/instances/list.js`)
### 5.1 GridWrapper 配置
- 列示例：
  - 多选框（批量勾选，需要 Grid.js formatter 注入 `<input type="checkbox">`）。
  - 实例名称（含图标、副标题 host/环境）。
  - 类型徽章（不同 db_type 不同颜色/icon）。
  - 版本/主从状态。
  - 活跃统计（DB/账户数量）
  - 标签列（badge 列表），支持换行。
  - 状态列（启用/禁用、连接状态）。
  - 操作列（详情、连接测试、同步单个）。
- `server.url` 默认 `/instances/api/instances?sort=id&order=desc`。
- `then(response)`：将后端 `items` 映射为 `[checkbox,id,name,...,meta]`，meta 用于操作按钮。
- `total(response)`：返回 `payload.total`，并更新页面“共 X 个实例”。

### 5.2 筛选联动
- FilterCard `onChange/onSubmit` -> 收集 form -> `instancesGrid.updateFilters(filters)`。
- 标签选择 `TagSelectorHelper.setupForForm`，确认后触发 FilterCard `emit('change')` 或回退到 `handleFilterChange(filters)`。
- 数据库类型切换按钮继续修改 URL（保留历史行为）。

### 5.3 批量/单项操作
- 选中状态通过自定义多选列 + `instancesGrid` 事件管理；保留原 `InstanceStore`/批量按钮逻辑。
- 操作列按钮调用既有函数（例如 `InstanceListActions.openDetail(id)`、`InstanceListActions.testConnection(id)`、`InstanceListActions.sync(id)`）。
- 批量操作成功后调用 `instancesGrid.refresh()`。

### 5.4 其他
- 保留统计卡、导出/刷新按钮、连接测试/监控入口的事件绑定。
- 在 `#instances-grid` 外层元素存放 `data-current-db-type` 等上下文，供 JS 使用。

## 6. 样式 (`app/static/css/pages/instances/list.css`)
- 新增 Grid.js 样式：
  - `.gridjs-wrapper` 圆角 + 阴影。
  - 多选列、操作列固定宽度；按钮尺寸统一。
  - 标签/状态徽章与旧版同色；支持多行展示。
  - 行 hover、字体大小与旧表保持接近。
- 保留批量操作工具栏和按钮组样式。
- 移除不再使用的 `.table` 样式，防止冲突。

## 7. 测试清单
- **基础**：分页、排序、筛选（类型/状态/标签/搜索）均正常；Grid.js 发起的请求带上所有参数。
- **批量操作**：勾选/全选有效；同步/删除等操作成功后刷新列表。
- **单项操作**：详情、连接测试、同步单个按钮可用。
- **标签筛选**：打开 TagSelector、选择/清空标签后列表刷新。
- **视觉**：按钮组/徽章颜色与旧版一致，移动端响应式正常。

## 8. 实施步骤建议
1. **API**：实现 `/instances/api/instances`，补充单元/集成测试，确认响应结构。
2. **模板**：引入 Grid.js 资源并替换表格容器；保留工具栏与筛选结构。
3. **脚本**：重写 `instances/list.js`，完成 GridWrapper + FilterCard + TagSelector + InstanceStore 集成。
4. **样式**：调整 `instances/list.css` 以适配 Grid.js。
5. **验证**：按测试清单回归，特别关注批量按钮、标签筛选、连接测试等交互。
6. **文档**：更新 README/QA notes，标记“实例管理已切换 Grid.js”。

> 成功标准：新旧页面在交互/视觉上基本一致，唯一差别是网络请求走 `/instances/api/instances`，并满足 Grid.js 标准。
