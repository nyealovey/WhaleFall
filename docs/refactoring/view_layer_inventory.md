# 视图层（View）重构方案

> 目标：在服务层 + 状态层完成的基础上，规范前端视图层（DOM 组件/页面入口）的结构，逐步把页面脚本拆解为“入口 + 组件 + Store”，降低千行脚本的维护成本。

## 1. 定位与责任
- **服务层**：提供接口封装。
- **状态层（Store）**：管理数据与业务状态，暴露 actions、事件。
- **视图层**：只负责 DOM 渲染、事件绑定、交互反馈，直接订阅 Store 事件或调用 Store actions。

视图层的实现可分为三类：
1. **页面入口（bootstrap）**：如 `app/static/js/pages/history/sync_sessions.js`，负责初始化 store、挂载组件、解析后端注入的上下文。
2. **UI 组件（views/）**：如列表视图、统计卡片、模态窗口的渲染器，不包含服务调用，只消费 store/state。
3. **共享组件**：如 TagSelector、FilterBar，可被多个页面复用，需暴露 `mount(container, store)` 等接口。

## 2. 目录与命名
```
app/static/js/modules/
├── services/
├── stores/
└── views/
    ├── sync_sessions/
    │   ├── sessions_table.js
    │   └── pagination_controls.js
    ├── tags/
    │   ├── tag_selector_view.js
    │   └── batch_assign_panel.js
    └── admin/
        └── scheduler_job_card.js
```
- **文件名**：kebab-case 或 snake_case 均可，推荐与组件职责一致（`tag_selector_view.js`）。
- **导出形式**：暴露 `mount`, `update`, `destroy`，或输出一个工厂函数 `createXView(store, options)`。
- 页面入口仍保留在 `app/static/js/pages/**`，但内容精简为“初始化 store + 绑定视图”的逻辑。

## 3. 组件约定
| 维度 | 约定 |
| --- | --- |
| 初始化 | `const tableView = createSessionsTableView({ store, container: '#sessions-container' }); tableView.mount();` |
| 状态更新 | 组件订阅 store 事件（如 `store.subscribe('syncSessions:updated', tableView.render);`），强调单向数据流。 |
| DOM 访问 | 尽量使用 `DOMHelpers`，禁止直接通过 `document.querySelector` 修改 store 状态。 |
| 销毁 | 必须提供 `destroy()`，清理事件监听、定时器等，便于后续 SPA 化或模块化加载。 |
| 模板 | 可使用内联模板字符串或 `<template>` 元素，复杂 UI 可拆多个子组件。 |
| 样式 | 若引入新的结构，需要在 `app/static/css/...` 添加对应样式，并在页面模板 `extra_css` 中加载。 |

## 4. 视图层清单

| 优先级 | 页面 / 组件 | 说明 | Store / Service 依赖 | 进度 |
| --- | --- | --- | --- | --- |
| V1-1 | **SyncSessionsPage** | 列表、分页、详情模态分拆为 view 组件，入口仅负责初始化。 | `SyncSessionsStore`, `SyncSessionsService` | ⏳ 规划 |
| V1-2 | **TagManagementViews** | 标签列表、批量操作面板、TagSelector 重构为 view 组件，可被 accounts/tags 页面复用。 | `TagManagementStore`, `TagManagementService` | ⏳ 规划 |
| V1-3 | **AccountClassificationViews** | 分类列表、规则表格、权限配置区拆分，入口仅 glue store + 组件。 | `AccountClassificationStore`, `AccountClassificationService` | ⏳ 规划 |
| V1-4 | **SchedulerViews** | job card、统计面板、编辑/新增模态统一封装，去除 jQuery 依赖。 | `SchedulerStore`, `SchedulerService` | ⏳ 规划 |
| V1-5 | **InstanceViews** | 实例列表/详情/统计图表拆解，复用连接按钮、同步按钮等子组件。 | `InstanceStore`, `InstanceManagementService` | ⏳ 规划 |
| V1-6 | **LogsViews** | 模块下拉、统计卡、日志表格、详情抽屉拆开，方便单独复用。 | `LogsStore`, `LogsService` | ⏳ 规划 |

> 说明：视图层迁移需在对应 store 准备就绪后进行，表格中 Store/Service 即依赖项。

## 5. 迁移步骤
1. **拆出 Store**：确认页面已使用状态层（S1 完成）。
2. **提炼组件**：识别页面中的独立区域（列表、表单、模态等），为每个区域创建 view 文件。
3. **页面入口瘦身**：入口脚本只做 `const store = createXStore(...); const view = createXView({ store }); view.mount();`。
4. **模板调整**：将页面依赖的 view 脚本（或入口脚本）在 `extra_js` 中按顺序加载；如 view 需要的 HTML 片段可用 `<template>` 或 `data-*` 属性。
5. **销毁流程**：若页面使用模态或自动刷新，确保 `destroy()` 在页面卸载或模块注销时调用（未来 SPA 化预埋 hook）。

## 6. 验收标准
- Page 入口体积显著缩小（只保留 store 初始化与 view glue 逻辑），核心 DOM 操作都位于 `modules/views/`.
- 组件具备 `mount/update/destroy`，并通过 store 事件驱动 UI 更新，避免直接 `document.querySelector` + 手动状态管理。
- 共享视图（如 TagSelector、PermissionViewer）也提供统一 API（`render`, `open`, `close`），供不同页面复用。
- 文档（本文件 + `frontend_script_refactor_plan.md`）更新迁移状态，PR 描述同步列出涉及的 view 组件。

## 7. 下一步
- 在 `modules/views/README.md` 中补充编码规范（DOMHelpers 使用、模板片段约定、事件命名等）。
- 选择首个试点页面（建议 SyncSessions 或 TagManagement），实现 store + view 的全链路，验证模式。
- 结合构建工具（未来引入 Vite/ESM）进一步优化加载与按需渲染。

