# Mitt 事件总线整合方案

> 尽管文件名沿用“mitt_nanostores”，本方案仅采用 Mitt 来统一事件通信；不再引入 Nanostores。

## 背景

现有前端在跨模块通信上依赖多种自定义方式（手写 EventBus、DOM 自定义事件、直接函数调用）。随着页面增多：

- 筛选组件与图表/表格之间耦合度高，难以复用；
- 事件订阅与解绑分散，容易遗漏导致内存泄露；
- 下拉框更新后常常忘记通知所有依赖模块，导致数据不同步。

引入一个统一、轻量的事件总线有助于把“谁触发”“谁响应”解耦，实现“筛选变动 → 图表/表格自动刷新”的目标。

## 推荐库

| 功能 | 库 | 核心特性 | 体积（gzip） | 快速示例 |
| --- | --- | --- | --- | --- |
| 事件总线 | [Mitt](https://github.com/developit/mitt) | 极简 `on/off/emit` API，无需实例化；任何对象都可发事件 | `<1KB` | `const bus = mitt(); bus.on('filter', handler); bus.emit('filter', payload);` |

## 下载与加载

```bash
mkdir -p app/static/vendor/mitt
curl -L https://unpkg.com/mitt@3.0.1/dist/mitt.umd.js \
  -o app/static/vendor/mitt/mitt.umd.js
```

在 `app/templates/base.html`（建议放在 `axios` 之后、业务脚本之前）添加：

```html
<script src="{{ url_for('static', filename='vendor/mitt/mitt.umd.js') }}"></script>
<script src="{{ url_for('static', filename='js/common/event-bus.js') }}"></script>
```

## 封装

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

> 只暴露 `on/off/emit`，避免直接泄露 mitt 实例，便于后续扩展（如记录日志、自动解绑等）。

## 使用模式

1. **事件命名**：推荐使用 `模块:动作` 形式（如 `filters:changed`、`charts:refresh`），方便调试。
2. **统一负载**：payload 建议为结构化对象，例如：
   ```js
   EventBus.emit("filters:changed", {
     source: "capacity-filter",
     values: { period: "weekly", dbType: "mysql" },
   });
   ```
3. **集中订阅/解绑**：模块初始化时 `EventBus.on`；销毁/离开页面时 `EventBus.off`，确保不会泄露。

## 实现“下拉 → 图表/表格自动刷新”

```js
// 筛选组件
document.getElementById("period").addEventListener("change", (event) => {
  EventBus.emit("filters:changed", {
    source: "capacity-filter",
    values: { period: event.target.value },
  });
});

// 图表模块
const onFiltersChange = ({ values }) => {
  reloadCharts(values);
};
EventBus.on("filters:changed", onFiltersChange);

// 表格模块
const onTableFilters = ({ values }) => {
  reloadTable(values);
};
EventBus.on("filters:changed", onTableFilters);

// 模块销毁时记得解绑
// EventBus.off("filters:changed", onFiltersChange);
// EventBus.off("filters:changed", onTableFilters);
```

这样，筛选条件变化后所有订阅者都会收到同一条事件并刷新自身数据，无需互相引用或调用。

## 验证步骤

1. 运行 `./scripts/refactor_naming.sh --dry-run`，确保新增文件/命名符合规范。
2. 手动验证关键页面：切换筛选条件后，图表/表格/统计卡是否自动刷新。
3. 检查模块卸载是否正确解绑事件，防止内存泄露。

## 风险与缓解

- **依赖缺失**：若 mitt 未加载，`event-bus.js` 会抛错并阻断初始化；务必保证模板加载顺序。
- **事件风暴**：大量组件频繁 `emit` 可能导致性能问题，可结合 `LodashUtils.debounce`/`throttle` 对输入做节流。
- **未解绑**：频繁创建/销毁的组件（如弹窗）要在销毁时调用 `EventBus.off`，否则事件处理函数会持续驻留。

## 后续计划

1. 在容量统计、实例列表等页面优先替换成 Mitt 事件模式，实现筛选 → 图表/表格联动。
2. 清理旧的自定义 EventBus/DOM 事件，统一依赖 `window.EventBus`。
3. 在团队开发规范中补充：“跨模块事件通信必须通过 Mitt 事件总线”，避免重复造轮子。
