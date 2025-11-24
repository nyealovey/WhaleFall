# 账户管理页面 Grid.js 重构方案

> 目标：以 `docs/refactoring/new/gridjs-migration-standard.md` 为准绳，在 **功能完整、视觉基本保持原样** 的前提下，把账户管理列表迁移到 Grid.js + GridWrapper。导航按钮、筛选器、工具栏、标签/分类徽章、权限查看等体验均需保持一致。

## 1. 概览与范围
- 页面：`app/templates/accounts/list.html`
- 入口 JS：`app/static/js/modules/views/accounts/list.js`
- 后端：`app/routes/account.py`
- 相关组件：TagSelector、FilterCard、InstanceStore、权限模态
- 既有特性：数据库类型切换、搜索/标签/分类筛选、导出 CSV、同步按钮、权限详情、行内标签+分类展示

## 2. 重构目标
1. **体验保持**：页面结构（头部、筛选卡片、按钮组、工具栏）、配色与徽章样式与现版一致。
2. **功能不缩水**：所有筛选、导出、同步、权限查看、导航按钮必须可用；表格列与旧表一致（含动态“数据库类型”列逻辑）。
3. **接口统一**：列表数据改走 `/account/api/list`，输出 `{ items, total, page, pages }`，由 GridWrapper 管理分页、排序、过滤。
4. **性能**：服务端分页 + 批量加载标签/分类，避免 N+1。

## 3. 现状速览
| 层级 | 位置 | 说明 |
| --- | --- | --- |
| 路由 | `app/routes/account.py` | 目前只有服务页面和零散 API；无 Grid.js 标准端点 |
| 模板 | `app/templates/accounts/list.html` | Bootstrap `<table>`、自定义分页、数据库类型按钮、筛选卡片、导出按钮 |
| JS | `app/static/js/modules/views/accounts/list.js` | 以页面刷新驱动筛选，依赖 InstanceStore/TagSelector |
| 样式 | `app/static/css/pages/accounts/list.css` | 表格、按钮、标签、分类徽章等样式 |

## 4. 方案设计
### 4.1 后端 `/account/api/list`
- 基于 `AccountPermission`（或现有主实体）构建查询：
  - 标准参数：`page`, `limit`, `sort`, `order`；默认 `username asc`。
  - 业务参数：`db_type`, `search`, `classification`, `tags`, `instance_id`, `is_locked`, `is_superuser`。
  - 标签/分类：一次性批量查询，封装 `[{ name, color }]` 列表，避免循环查询。
- 响应示例：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 12,
        "username": "dba",
        "instance_name": "prod-db",
        "instance_host": "10.0.0.1",
        "db_type": "mysql",
        "is_locked": false,
        "is_superuser": true,
        "tags": [{"name": "critical", "display_name": "核心", "color": "danger"}],
        "classifications": [{"name": "生产", "color": "#ff5722"}]
      }
    ],
    "total": 268,
    "page": 1,
    "pages": 14
  }
}
```
- 保留原 `list_accounts()` 以兼容直达地址/旧脚本。

### 4.2 模板调整（`app/templates/accounts/list.html`）
- 引入 Grid.js 资源（mermaid.css、gridjs.umd.js、grid-wrapper.js）。
- 删除 `<table>` 与分页，改为 `<div id="accounts-grid"></div>`。
- 保持现有布局：
  - 页头 + 按钮组（数据库类型、统计入口、同步按钮）。
  - FilterCard（搜索、分类、标签）；TagSelector 模板仍嵌入。
  - 工具栏（导出 CSV、总数展示）。
- 数据库类型按钮添加 `data-db-type-btn` 属性，由 JS 驱动 URL 切换（行为与旧版一致）。

### 4.3 前端脚本（`app/static/js/modules/views/accounts/list.js`）
- 初始化流程：
  1. 解析当前 `db_type`（URL path）。
  2. 初始化 TagSelector、FilterCard、InstanceStore（同步用）。
  3. 创建 `GridWrapper`：
     - 列：账户名、实例信息、IP、标签、[可选]数据库类型、分类、状态、操作。
     - `server.url` 预置 `db_type`，`setFilters/ updateFilters` 追加其余参数。
     - `then` 中返回 `[...data, meta]`；`meta` 用于渲染操作列并缓存给权限详情。
  4. 注入全局操作：`AccountsActions.viewPermissions`、`exportCSV()`、`syncAllAccounts()`。
- 筛选逻辑：
  - FilterCard `onSubmit/onChange` -> 收集 form -> `normalizeFilters`（清空空值/`all`）-> `accountsGrid.updateFilters(filters)`。
  - 数据库类型切换沿用原逻辑：改变 URL 后刷新，使按钮高亮策略与旧 UI 保持一致。
- 标签选择：沿用 `TagSelectorHelper`，确认后触发 FilterCard `change` 事件。
- 导出 CSV：基于当前筛选拼接查询串，访问既有导出接口。
- 权限查看：仍调用既有权限模态脚本，数据来自 grid metadata。

### 4.4 样式（`app/static/css/pages/accounts/list.css`）
- 保留原按钮、徽章、工具栏样式；新增 Grid.js 定制：
  - `.gridjs-wrapper` 圆角及 hover 背景。
  - 标签/分类列允许换行；徽章尺寸与旧版一致。
  - 操作列按钮尺寸、状态徽章宽度按旧 UI 设置。
  - 响应式：按钮组纵向排列、工具栏折行。
- 可以移除不再使用的 `.table` 样式，避免冲突。

## 5. 校验清单
| 类别 | 需验证的点 |
| --- | --- |
| 功能 | 搜索、分类、标签（含多选）、数据库类型切换、分页、导出 CSV、同步按钮、权限详情、标签/分类渲染、状态徽章 |
| 视觉 | 顶部按钮风格、工具栏布局、标签/分类颜色、行 hover、表格字体大小与旧版接近 |
| 行为 | 切换数据库类型后 URL & 高亮正确；FilterCard 自动提交；表格刷新不闪烁；同步完成后手动/自动刷新；导出包含当前筛选条件 |
| API | `/account/api/list` 分页/筛选/排序正确；无 N+1 查询；导出接口复用现有逻辑 |

## 6. 实施顺序建议
1. **API**：实现 `/account/api/list`，补充测试/日志；确认返回数据含 tags/classifications。
2. **模板**：引入 Grid.js 资源+容器，保留按钮、筛选、工具栏结构。
3. **脚本**：重写 `accounts/list.js`，完成 GridWrapper + FilterCard + TagSelector 集成。
4. **样式**：调整 Grid.js 列样式，验证不同 db_type 视图下的对齐。
5. **验证**：按“校验清单”全量回归；重点核对视觉（按钮、徽章）、CSV、权限模态、移动端。
6. **收尾**：更新相关文档（如 README 或 QA 记录），提交 PR 并在描述中强调“功能/样式保持一致”。

> 成功标准：新旧页面在功能与视觉上不可区分，仅网络请求日志可见接口差异；所有操作满足 `gridjs-migration-standard`，并通过手工及自动化测试。EOF