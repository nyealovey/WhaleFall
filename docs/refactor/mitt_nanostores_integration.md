# Mitt & Nanostores 重构方案

## 背景

当前前端在“事件通知”和“跨模块共享状态”方面依赖自建的 EventBus/appStore。随着页面增多：

- 组件之间需要互相引用才能联动（如下拉筛选 → 图表/表格刷新），耦合度高；
- 自定义 EventBus 缺乏统一 API，订阅/解绑分散，容易遗忘导致内存泄露；
- 状态更新后需要显式调用刷新函数，无法“数据驱动 UI”。

引入轻量、成熟的事件与状态库可以降低维护成本，并为“筛选条件变化后自动刷新图表和表格”提供可靠基础。

## 推荐组合

| 功能 | 库 | 核心特性 | 体积（gzip） | 快速示例 |
| --- | --- | --- | --- | --- |
| 事件总线 | [Mitt](https://github.com/developit/mitt) | 极简 `on/off/emit` API，无需实例化；适合一次性事件广播 | `<1KB` | `const bus = mitt(); bus.on('filter', handler); bus.emit('filter', payload);` |
| 状态管理 | [Nanostores](https://nanostores.org/) | 原子 store + 订阅模型，极小（<1KB），可渐进式应用；无框架依赖 | `<1KB` | `const filtersStore = atom({ period: 'daily' }); filtersStore.subscribe(render); filtersStore.set({ period: 'weekly' });` |

## 依赖下载

```bash
# Mitt
mkdir -p app/static/vendor/mitt
curl -L https://unpkg.com/mitt@3.0.1/dist/mitt.umd.js \
  -o app/static/vendor/mitt/mitt.umd.js

# Nanostores
mkdir -p app/static/vendor/nanostores
curl -L https://unpkg.com/nanostores@0.9.5/index.js \
  -o app/static/vendor/nanostores/nanostores.umd.js
```

在 `app/templates/base.html` 中加载（建议放在 `axios` 之后、业务脚本之前）：

```html
<script src="{{ url_for('static', filename='vendor/mitt/mitt.umd.js') }}"></script>
<script src="{{ url_for('static', filename='js/common/event-bus.js') }}"></script>

<script src="{{ url_for('static', filename='vendor/nanostores/nanostores.umd.js') }}"></script>
<script src="{{ url_for('static', filename='js/common/app-state.js') }}"></script>
```

## 封装入口

### EventBus（Mitt）

`app/static/js/common/event-bus.js`：

```js
(function (window) {
  "use strict";
  if (!window.mitt) {
    throw new Error("Mitt 未加载");
  }
  const emitter = window.mitt();
  window.EventBus = {
    on: emitter.on,
    off: emitter.off,
    emit: emitter.emit,
  };
})(window);
```

### AppState（Nanostores）

`app/static/js/common/app-state.js`：

```js
(function (window) {
  "use strict";
  const nanostores = window.nanostores || window;
  const atom = nanostores.atom;
  if (typeof atom !== "function") {
    throw new Error("Nanostores 未加载");
  }

  const filtersStore = atom({
    instanceId: null,
    period: "daily",
  });

  window.AppState = {
    filters: filtersStore,
    subscribe: filtersStore.subscribe,
    setFilters: (next) => filtersStore.set({ ...filtersStore.get(), ...next }),
  };
})(window);
```

> 可根据需要扩展更多 store（如 `selectionStore`, `chartStore`），或使用 `map`, `persistentAtom` 等高级 API。

## 重构路线

1. **事件广播（Mitt）**
   - 替换自建 EventBus/DOM 自定义事件，统一使用 `EventBus.emit('filter-change', payload)`。
   - 各模块通过 `EventBus.on('filter-change', handler)` 接收事件；卸载时 `EventBus.off`。
   - 适合一次性通知（例如“刷新完成”“导出成功”）。

2. **共享状态（Nanostores）**
   - 将常用筛选、分页、图表配置等放入对应 store。
   - 组件通过 `store.subscribe` 监听变化；store 更新后，所有订阅者在回调中自动刷新 UI，无需手动调用刷新函数。
   - 适合“下拉框 → 图表/表格联动”这类需要响应式的场景。

3. **联动示例**

```js
// 下拉组件：更新 store
document.getElementById("period").addEventListener("change", (event) => {
  AppState.setFilters({ period: event.target.value });
});

// 图表模块：订阅 store
AppState.filters.subscribe((filters) => {
  reloadCharts(filters);
});
```

4. **渐进迁移**
   - 先在新模块或重点页面中使用 Nanostores/Mitt，观察效果。
   - 稳定后逐步移除旧的 EventBus/appStore，避免双轨复杂度。

## 验证步骤

1. 执行 `./scripts/refactor_naming.sh --dry-run`，确保命名规范。
2. 手动验证关键页面：选中筛选项后图表/表格是否自动刷新；事件广播是否触发。
3. 运行现有测试或手动用例，确保改动不影响其他功能。

## 对“下拉 → 图表/表格自动刷新”的帮助

- **Mitt**：筛选组件只需 `emit` 一次事件，所有监听者即可刷新，无需层级传参。
- **Nanostores**：状态更新后，订阅者自动得到新值并刷新视图，实现真正的数据驱动 UI。
- 组合使用后，可大幅减少因未手动调用刷新函数而导致的数据不同步问题。

## 风险与缓解

- **依赖缺失**：若 Mitt 或 Nanostores 未加载，将在初始化阶段抛错；需保证模板加载顺序正确。
- **迁移期间的重复状态**：若旧的 appStore 与新 store 并存，要注意保持数据同步或尽快彻底迁移。
- **调试新范式**：响应式状态意味着数据流动方式改变，建议在订阅回调中添加日志，辅助调试。

## 后续计划

1. 落地 `event-bus.js` 与 `app-state.js`，先在核心页面验证。
2. 分模块替换旧的 EventBus/appStore，完成后清理冗余代码。
3. 在团队开发规范中明确：“广播型事件使用 EventBus，跨模块状态使用 Nanostores”，避免重复造轮子。
