# Views 目录说明

视图层组件存放在 `app/static/js/modules/views/`,用于承载 DOM 渲染和交互逻辑.约定如下:

1. **文件命名**:snake_case 或 kebab-case,如 `sync_sessions_table.js`、`tag_selector_view.js`.
2. **导出接口**:推荐 `createXView({ store, container, ...})`,返回 `{ mount, update, destroy }`;或直接导出 `mountXView(store, container)`.
3. **依赖注入**:通过参数接收 store/service,不在组件内部 import `window.*` 全局.
4. **事件订阅**:使用 `store.subscribe` 或 `mitt`,在 `destroy()` 中解除订阅,避免内存泄漏.
5. **DOM 操作**:统一使用 `DOMHelpers`(`selectOne`, `from` 等),严禁在视图内直接修改 store 状态.
6. **模板**:可使用 `<template>`、字符串模板或文档片段,确保对 XSS 做好转义.

在新增 view 组件前,请更新 `docs/refactoring/view_layer_inventory.md` 的清单,以便跟踪迁移进度.
