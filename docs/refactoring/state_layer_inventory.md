# 状态层（Store）迁移方案

> 目标：在已完成的服务层基础上，为页面/组件提供统一的状态管理抽象，降低页面脚本体积、复用业务状态，并与 Mitt 事件总线协同。

## 1. 背景与定位
- 服务层已经在 `app/static/js/modules/services/` 收敛所有 HTTP 请求，当前页面脚本仍直接持有大量 UI 状态（筛选条件、分页信息、模态开关等）。
- 状态层需要负责“数据 + 行为”的中间层，实现以下目标：
  1. 统一管理页面/组件的可观察状态，减少 DOM 逻辑与业务状态耦合。
  2. 将服务层调用封装为 store 的 actions，便于视图层订阅和复用。
  3. 充分利用现有的 Mitt (`app/static/js/common/event-bus.js`) 作为发布/订阅基础，避免重复造轮子。

## 2. 目录与命名
```
app/static/js/modules/
├── services/
└── stores/
    ├── sync_sessions_store.js
    ├── tag_management_store.js
    ├── account_classification_store.js
    ├── scheduler_store.js
    ├── instance_store.js
    ├── logs_store.js
    ├── partition_store.js
    └── credentials_store.js
```
- **文件名**：snake_case；**导出**：`createXStore()` 或 `XStore`（CapWords），遵守命名规范指南。日后若 store 数量继续扩张，再考虑子目录分层。
- **Store 公共 README**：创建 `app/static/js/modules/stores/README.md`，记录编码规范（状态字段命名、订阅 API、Mitt 使用方式等）。

## 3. Store 设计约定
| 维度 | 说明 |
| --- | --- |
| 初始化 | `const store = createSyncSessionsStore({ service, emitter }); store.init(initialFilters);` |
| 状态持有 | Store 内部维护 `const state = { ... }`，通过 `getState()` 返回快照，禁止视图层直接修改。 |
| 事件分发 | Store 内置 Mitt emitter（默认使用全局 `window.EventBus`，也可创建局部 emitter），统一事件命名，如 `syncSessions:updated`、`scheduler:error`。 |
| 订阅 API | `store.subscribe(eventName, handler)` / `store.unsubscribe(eventName, handler)`，也可暴露 `store.on`/`store.off` 原语，与 Mitt 对齐。 |
| Actions | 只调用服务层并更新 state，例如 `store.actions.loadSessions(filters)`；action 内处理 loading/error，并通过事件通知视图。 |
| 派生数据 | Store 可维护 memo（如统计、Map），视图层通过 `store.select(selectorFn)` 获取。 |
| 销毁 | 视图卸载时调用 `store.destroy()` 清理定时器、事件监听。 |

### Mitt 的使用方式
1. **局部 emitter**（推荐）：每个 store 实例通过 `mitt()` 创建私有 emitter，避免不同页面事件名称冲突。
2. **桥接全局 EventBus**：当需要与全局联动（例如筛选组件的 `filters:change`），store 可以在内部 `window.EventBus.on(...)` 并在 `destroy()` 中解除绑定。
3. **事件命名规范**：`<domain>:<action>`，如 `tags:selectionChanged`、`scheduler:jobsUpdated`。需在 README 中列出。

## 4. Store 清单与状态

| 优先级 | Store | 覆盖范围 | 主要状态/动作 | 进度 |
| --- | --- | --- | --- | --- |
| S1-1 | **SyncSessionsStore** | `pages/history/sync_sessions.js` | `sessions`, `filters`, `pagination`, `autoRefresh`; actions：`loadSessions`、`cancelSession`、`viewDetail` | ⏳ 规划 |
| S1-2 | **TagManagementStore** | `components/tag_selector.js`, `pages/tags/batch_assign.js`, `pages/tags/index.js`, `pages/accounts/list.js` | 标签/分类/实例数据、已选项；actions：`loadTags`、`applySelection`、`batchAssign`、`batchDelete` | ⏳ 规划 |
| S1-3 | **AccountClassificationStore** | `pages/accounts/account_classification.js`, `common/permission_policy_center.js` | `classifications`, `rules`, `permissions`, `stats`; actions：CRUD、`loadPermissions`、`autoClassify` | ⏳ 规划 |
| S1-4 | **SchedulerStore** | `pages/admin/scheduler.js` | `currentJobs`, `filters`, `modalState`; actions：`loadJobs`、`resumeJob`、`pauseJob`、`runJob`、`updateJob` | ⏳ 规划 |
| S1-5 | **InstanceStore**（可拆三子 store） | `pages/instances/detail.js`, `pages/instances/list.js`, `pages/instances/statistics.js`, `pages/accounts/list.js` | 实例/账户/容量/批量状态；actions：`syncAccounts`、`syncCapacity`、`batchDelete`、`batchCreate`、`loadStats` | ⏳ 规划 |
| S1-6 | **LogsStore** | `pages/history/logs.js` | `modules`, `filters`, `logs`, `pagination`; actions：`loadModules`、`loadStats`、`searchLogs`、`loadDetail` | ⏳ 规划 |
| S1-7 | **PartitionStore** | `pages/admin/partitions.js`, `pages/admin/aggregations_chart.js` | `partitions`, `stats`, `charts`; actions：`loadInfo`、`createPartition`、`cleanupPartitions`、`loadCoreMetrics` | ⏳ 规划 |
| S1-8 | **CredentialsStore** | `pages/credentials/list.js` | `credentials`, `filters`, `modalState`; actions：`deleteCredential`、`loadList` | ⏳ 规划 |

> 说明：表格列举的是当前需要迁移到 Store 的页面/组件。落地过程中可依据场景复杂度拆细（例如 InstanceStore 拆成 detail/list/statistics 子 store）。

## 5. 渐进迁移策略（S1 阶段）
顺序建议参考服务层核心场景：
1. **SyncSessionsStore**（历史会话页面）：状态包括 `sessions`, `filters`, `pagination`, `autoRefresh`. Actions：`loadSessions`, `viewDetail`, `viewErrors`, `cancelSession`.
2. **TagManagementStore**（标签页面 + 批量分配 + TagSelector）：维护标签、分类、实例及选择集，向不同视图暴露订阅点。
3. **AccountClassificationStore**：集中管理分类/规则/权限，在 store 内封装 stats/permissions 缓存，视图层仅关心事件。
4. **SchedulerStore**：持有 `currentJobs`, `filters`, `modals` 状态；所有启停/执行操作通过 store action 调度。
5. **InstanceStore**（列表 + 详情 + 统计分三个子 store 或共享核心逻辑）：统一管理同步/容量/批量操作状态。

每迁移一个页面，流程如下：
1. **定义 store**：引用对应服务 + Mitt，梳理初始状态、事件列表、action。
2. **页面入口注入**：`const store = createSchedulerStore({ service: schedulerService }); store.init();`
3. **视图层订阅**：使用 `store.subscribe('scheduler:jobsUpdated', renderJobs);`；DOM 事件触发时调用 `store.actions.resumeJob(id)` 等。
4. **清理遗留逻辑**：将页面内的 `let currentJobs = []` 等局部状态删除，避免“双写”。

## 6. Store 示例
```js
// app/static/js/modules/stores/history/sync_sessions_store.js
import mitt from 'mitt';

export function createSyncSessionsStore({ service, emitter = mitt() }) {
  const state = {
    sessions: [],
    filters: {},
    pagination: { page: 1, totalPages: 1 },
    loading: false,
  };

  const api = {
    getState: () => ({ ...state }),
    subscribe: emitter.on,
    unsubscribe: emitter.off,
    actions: {
      async loadSessions(filters = {}) {
        state.loading = true;
        emitter.emit('syncSessions:loading', api.getState());
        try {
          const response = await service.list(filters);
          // ...更新 state.sessions / pagination
          emitter.emit('syncSessions:updated', api.getState());
        } catch (error) {
          emitter.emit('syncSessions:error', error);
        } finally {
          state.loading = false;
        }
      },
      async cancelSession(id) {
        await service.cancel(id);
        await api.actions.loadSessions({ ...state.filters });
      },
    },
    destroy() {
      emitter.all.clear?.();
    },
  };

  return api;
}
```

## 7. 验收标准
- 页面脚本中的 `let state = ...`、`currentJobs`, `selectedTags` 等本地状态逐步收敛到 store。
- 视图层通过订阅事件或 `store.getState()` 获取数据，不直接依赖服务层。
- Store 的 action 覆盖原先的网络调用，并在 `docs/refactoring/service_layer_inventory.md` 中同步状态层的完成情况（可新增“Store 进度”列）。
- Mitt 事件命名与 README 一致，`destroy()` 能正确解除订阅，防止内存泄漏。

## 8. 下一步
1. 创建 `modules/stores/README.md` 与首个 store（建议 `sync_sessions_store.js`），提交 PR 验证模式。
2. 在 `frontend_script_refactor_plan.md` 中新增 S1 表格，列出 store 迁移优先级与负责人。
3. 视图层拆解（S2）时可直接依赖 store，避免重复重构。

借助现有服务层与 Mitt 事件总线，状态层可渐进式落地，最终实现“服务层 -> Store -> 视图层”的清晰分层。
