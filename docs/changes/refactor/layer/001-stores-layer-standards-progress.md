# 前端 Stores layer 标准对齐: 全量审计报告与进度表

> Status: Draft
> Owner: WhaleFall Team
> Created: 2026-01-24
> Updated: 2026-01-24
> Scope: `app/static/js/modules/stores/**`
> Related:
> - `../../../Obsidian/standards/ui/design/layer/stores-layer.md`
> - `state-layer-inventory.md`

## 1. 动机与范围

目标: 对 `app/static/js/modules/stores/**` 做一次全量对照审计, 给出当前不符合项, 并形成可执行的重构进度表.

范围: 仅覆盖 Stores layer, 不包含 views/services/page-entry 的分层问题(分层迁移 SSOT 见 `state-layer-inventory.md`).

## 2. 不变约束(验收口径)

以下口径以 SSOT `../../../Obsidian/standards/ui/design/layer/stores-layer.md` 为准, 本文只摘录用于审计.

- MUST: Store 不得直接操作 DOM, 不得调用 `toast.*`, 不得直连 `window.httpU`.
- MUST: Store 以 `createXStore(options)` 导出, 并挂载 `window.createXStore`.
- MUST: `options.service` 为必填依赖, 且创建时校验必需方法存在.
- MUST: `getState()` 返回快照, 不直接暴露内部 state 引用.
- MUST: 异步 actions 出错时:
  - 记录 `state.lastError`.
  - emit `<domain>:error`(携带 error 与 meta/state).
  - rethrow(上层决定是否 toast/回退).
- MUST: 提供 `subscribe/unsubscribe`, 且提供 `destroy()` 清理 emitter 订阅与内部状态.

## 3. 扫描方法

本次审计使用如下方式组合完成:

- 静态 grep:
  - `rg -n "document\\.|DOMHelpers|toast\\.|\\bhttpU\\." app/static/js/modules/stores`
  - `rg -n "window\\." app/static/js/modules/stores`
  - `rg -n "actions\\s*:\\s*\\{" app/static/js/modules/stores`
  - `rg -n "\\bdestroy\\s*:\\s*function\\b" app/static/js/modules/stores`
- 人工对照:
  - 逐个检查 actions 是否在失败路径统一落到 `lastError + :error + throw`.
  - 逐个检查 `destroy()` 是否有"回到初始态"的清理动作(避免长驻页面内存泄漏/脏状态).

## 4. 现状概览

- Stores 总数: 17
- 结论:
  - PASS: 17
  - NEEDS_FIX: 0

P0(必须修)聚类(已清零):

- 异步 actions 缺少统一错误口径(已修复):
  - `app/static/js/modules/stores/logs_store.js:181` `actions.loadLogDetail()`
  - `app/static/js/modules/stores/account_change_logs_store.js:189` `actions.loadDetail()`
  - `app/static/js/modules/stores/account_classification_store.js:275` `actions.fetchClassificationDetail()`
  - `app/static/js/modules/stores/account_classification_store.js:326` `actions.fetchRuleDetail()`
  - `app/static/js/modules/stores/account_classification_store.js:377` `actions.triggerAutomation()`
  - `app/static/js/modules/stores/account_classification_store.js:383` `actions.fetchPermissions()`
- `destroy()` 清理不完整(已修复):
  - `app/static/js/modules/stores/scheduler_store.js:335`
  - `app/static/js/modules/stores/partition_store.js:460`
  - `app/static/js/modules/stores/instance_store.js:815`
  - `app/static/js/modules/stores/account_classification_store.js:401`
  - `app/static/js/modules/stores/tag_batch_store.js:450`
  - `app/static/js/modules/stores/tag_management_store.js:573`
- `partition_store` refresh 策略B(已落地):
  - `app/static/js/modules/stores/partition_store.js:400`
  - `app/static/js/modules/stores/partition_store.js:428`

## 5. 单点问题清单(按标准条款归类)

### 5.1 MUST: 异步 actions 失败口径缺失

影响: view 无法稳定订阅 `<domain>:error`, `state.lastError` 也不会被更新, 会导致 UI 无提示或状态不同步.

- (已修复) `app/static/js/modules/stores/logs_store.js:181` `actions.loadLogDetail()` 缺 `.catch(...)` 统一错误处理与 rethrow.
- (已修复) `app/static/js/modules/stores/account_change_logs_store.js:189` `actions.loadDetail()` 缺 `.catch(...)` 统一错误处理与 rethrow.
- (已修复) `app/static/js/modules/stores/account_classification_store.js:275` `actions.fetchClassificationDetail()` 缺 `.catch(...)` 统一错误处理与 rethrow.
- (已修复) `app/static/js/modules/stores/account_classification_store.js:326` `actions.fetchRuleDetail()` 缺 `.catch(...)` 统一错误处理与 rethrow.
- (已修复) `app/static/js/modules/stores/account_classification_store.js:377` `actions.triggerAutomation()` 缺 `.catch(...)` 统一错误处理与 rethrow.
- (已修复) `app/static/js/modules/stores/account_classification_store.js:383` `actions.fetchPermissions()` 缺 `.catch(...)` 统一错误处理与 rethrow.

### 5.2 MUST: destroy() 内部状态清理不完整

影响: 页面长驻或多次 init/destroy 时, 可能出现:

- 事件订阅已清但内部状态残留, view 复用 store 时拿到脏数据.
- 大数组/缓存引用未释放, 造成不必要的内存占用.

建议口径: destroy() 至少要做到:

- emitter 订阅清理(当前大多已做).
- 将 state 重置为接近初始态(loading=false, lastError=null, 大数组清空, Set/Map clear).

当前不完整点:

- (已修复) `app/static/js/modules/stores/scheduler_store.js:335` 仅清 `jobs`, 未清 `stats/loading/lastError`.
- (已修复) `app/static/js/modules/stores/partition_store.js:460` 仅清 `partitions`, 未清 `stats/metrics/loading/lastError`.
- (已修复) `app/static/js/modules/stores/instance_store.js:815` 未清 `filters/stats/loading/operations/uploadResult/lastError`.
- (已修复) `app/static/js/modules/stores/account_classification_store.js:401` 未清 `loading/lastError`.
- (已修复) `app/static/js/modules/stores/tag_batch_store.js:450` 未清 `loading/lastError/lastResult/mode`.
- (已修复) `app/static/js/modules/stores/tag_management_store.js:573` 未清 `categories/tags/filteredTags/loading/lastError/filters/stats`.

### 5.3 已决策: refresh 失败允许 resolve, 但必须 emit error(PartitionStore)

现状:

- `createPartition()`/`cleanupPartitions()` 在 service 成功后会触发 `actions.loadInfo({ silent: true })`.
- refresh 失败时被 `.catch(function () { return result; })` 吞掉, action 仍 resolve.

决策结论: 采用 B(宽松).

- 主动作(service.create/service.cleanup)失败: 仍然 reject(保持 "失败即失败" 的口径).
- 后置 refresh(actions.loadInfo)失败: action 允许 resolve(不阻断主动作成功返回), 但必须:
  - 更新 `state.lastError`.
  - emit `partitions:error`(或 `partitions:refreshError`)并在 meta 标记 `nonBlocking: true`/`step: "refreshInfo"`.
  - 禁止 silent swallow(必须对上层可观测: 订阅事件即可感知).

## 6. 进度表(全量)

说明:

- 状态含义:
  - PASS: 无已知 MUST 违例.
  - NEEDS_FIX(P0): 存在 MUST 违例或明确需要对齐的硬约束项.
- 表格内仅列出本次审计发现的缺口, 不代表 store 的全部能力点.

| Store | 状态 | P0: 错误口径 | P0: destroy 清理 | 备注 |
|---|---|---|---|---|
| `account_change_logs_store.js` | PASS | [x] `loadDetail` 补 `lastError + accountChangeLogs:error + throw`(`app/static/js/modules/stores/account_change_logs_store.js:189`) | - | - |
| `account_classification_statistics_store.js` | PASS | - | - | 可选: 对数组元素做更深的 clone, 以防 view 意外修改对象引用. |
| `account_classification_store.js` | PASS | [x] 4 个 actions 补统一错误口径(`app/static/js/modules/stores/account_classification_store.js:275`, `:326`, `:377`, `:383`) | [x] destroy 补齐 `loading/lastError` 等(`app/static/js/modules/stores/account_classification_store.js:401`) | - |
| `accounts_statistics_store.js` | PASS | - | - | - |
| `auth_store.js` | PASS | - | - | - |
| `credentials_store.js` | PASS | - | - | - |
| `dashboard_store.js` | PASS | - | - | - |
| `instance_crud_store.js` | PASS | - | - | - |
| `instance_store.js` | PASS | - | [x] destroy 补齐 `filters/stats/loading/operations/uploadResult/lastError`(`app/static/js/modules/stores/instance_store.js:815`) | - |
| `logs_store.js` | PASS | [x] `loadLogDetail` 补 `lastError + logs:error + throw`(`app/static/js/modules/stores/logs_store.js:181`) | - | - |
| `partition_store.js` | PASS | - | [x] destroy 补齐 `stats/metrics/loading/lastError`(`app/static/js/modules/stores/partition_store.js:460`) | [x] 按策略B实现: refresh 失败 emit error(meta.nonBlocking=true)但 action resolve(`app/static/js/modules/stores/partition_store.js:400`, `:428`). |
| `scheduler_store.js` | PASS | - | [x] destroy 补齐 `stats/loading/lastError`(`app/static/js/modules/stores/scheduler_store.js:335`) | - |
| `tag_batch_store.js` | PASS | - | [x] destroy 补齐 `loading/lastError/lastResult/mode`(`app/static/js/modules/stores/tag_batch_store.js:450`) | - |
| `tag_list_store.js` | PASS | - | - | - |
| `tag_management_store.js` | PASS | - | [x] destroy 补齐 `categories/tags/filteredTags/loading/lastError/filters/stats`(`app/static/js/modules/stores/tag_management_store.js:573`) | - |
| `task_runs_store.js` | PASS | - | - | - |
| `users_store.js` | PASS | - | - | - |

## 7. 分阶段计划(建议)

阶段 1(P0): 先把 MUST 违例清零.

- 修复缺 catch 的 actions, 统一走 `handleError(...)+emit <domain>:error+throw`.
- 补齐 destroy() 重置状态, 避免 store 被复用时残留脏数据.

阶段 2(P1/P2): 再做一致性与可维护性优化(可选).

- 统一 "refresh 失败" 策略(PartitionStore).
- 将事件名常量化(部分 store 已有, 部分仍为字符串散落).
- 对 `getState()` 的数组元素做更彻底的 clone(仅在确有外部误改风险时做, 避免过度 defensive).

## 8. 验收指标与复核命令

### 8.1 验收指标

- 所有 store 的异步 actions: 失败路径必须更新 `lastError`, emit `<domain>:error`, 并 rethrow.
- 所有 store 的 `destroy()`: 必须清理 emitter 订阅, 且 state 进入接近初始态.
- Stores layer 不得出现 DOM/toast/httpU 访问.

### 8.2 复核命令(示例)

```bash
rg -n "document\\.|DOMHelpers|toast\\.|\\bhttpU\\." app/static/js/modules/stores
rg -n "window\\.create[A-Za-z0-9]+Store" app/static/js/modules/stores
rg -n "\\bsubscribe\\s*:\\s*function\\b|\\bunsubscribe\\s*:\\s*function\\b|\\bdestroy\\s*:\\s*function\\b" app/static/js/modules/stores
```
