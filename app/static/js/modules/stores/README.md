# Stores 目录说明

该目录用于承载前端状态层（Store）实现，命名与服务层保持一致：

- 文件名使用 `snake_case`，例如 `sync_sessions_store.js`。
- Store 导出 `createXStore()` 或 `XStore`（CapWords）函数/类，内部封装状态、actions、订阅 API。
- 每个 store 默认使用 `mitt()` 创建私有事件总线；如需与全局 `window.EventBus` 交互，记得在 `destroy()` 中解除绑定。

Store 的职责：
1. 调用 `app/static/js/modules/services/` 中的服务，请勿直接访问 `window.httpU`。
2. 维护可观察状态，提供 `getState()`/`select()` 等只读访问方法。
3. 暴露 `actions`（如 `loadSessions`, `applyFilters`），所有 UI 事件应通过 actions 驱动。
4. 提供 `subscribe(eventName, handler)`/`unsubscribe` 或直接透出 `emitter.on/off`。

在添加新 store 前，请更新 `docs/refactoring/state_layer_inventory.md`，同步迁移进度。

