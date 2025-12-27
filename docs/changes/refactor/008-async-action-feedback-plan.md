# Async Action Feedback(Sync/Batch) Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/static/js/**`, `app/routes/**`, `app/services/**`, `docs/standards/backend/**`, `docs/standards/ui/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P1-08), `docs/standards/backend/api-response-envelope.md`, `docs/standards/backend/error-message-schema-unification.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Any sync/batch action always yields user-visible feedback. Even if the response schema is unexpected(`success=false` but no `error`, or missing envelope fields), users get a clear "what happened" message and a next-step entry(usually "会话中心").

**Architecture:** Normalize async action results at the boundary(one helper), then make all callers use it. Stabilize backend envelope for async task endpoints so the UI can provide deterministic feedback and CTA.

**Tech Stack:** Vanilla JS modules + Bootstrap toast, Flask JSON envelope, existing "会话中心" pages.

---

## 1. 动机与范围

### 1.1 动机

审计报告 P1-08 指出: 同步/批量动作在 `success=false` 且无 `error` 时可能静默, 用户无法回答"我刚做了什么", 容易重复点击/重复触发任务, 增加系统负载与用户焦虑.

证据(抽样):

- `app/static/js/modules/views/instances/detail.js`(syncCapacity): 仅处理 `data.success` 或 `data.error`, 否则无提示.
- `app/static/js/modules/views/accounts/ledgers.js`(syncAllAccounts): 仅处理 `result.success` 或 `result.error`, 否则无提示.

### 1.2 范围

In-scope:

- 前端: 所有触发"异步任务/批量同步/批量操作"的入口, 统一成功/失败/未知结构的反馈策略.
- 后端: 相关接口返回结构收敛到标准 JSON envelope, 并提供可用于跳转/定位的任务标识(如 `session_id`).

Out-of-scope(本次不做):

- 重构会话中心的列表/详情 UI(仅作为结果入口与 CTA).
- 引入新的 e2e 测试框架(可在长期评估).

---

## 2. 不变约束(行为/契约/性能门槛)

- 行为不变: 不改变同步/批量动作的业务语义, 不改变 API 路径与权限.
- 反馈闭环: 任何情况下必须至少出现一个用户可见反馈(toast/alert), 禁止静默.
- 契约边界: 兼容逻辑只能集中在"边界层"做一次规范化, 业务层禁止扩散 `message || error` 等兜底链(对齐 `error-message-schema-unification.md`).
- 性能门槛: 不引入重型依赖, 新增 helper 必须轻量.

---

## 3. 统一反馈模型(面向异步任务)

对 sync/batch 类动作, UI 需要稳定回答 3 个问题:

1. 动作是否已被接受并开始执行? (started)
2. 如果失败, 用户下一步怎么办? (recoverable + suggestions)
3. 结果在哪里看? (session center entry)

建议定义一个前端统一的 "AsyncActionOutcome":

- `status`: `started | failed | unknown`
- `tone`: `success | error | warning | info`
- `message`: 可展示摘要(单句)
- `resultUrl`: 可选(默认 `/history/sessions`)
- `resultText`: 可选(默认 "前往会话中心查看结果")
- `meta`: 可选(如 `session_id`/`request_id`)

映射规则(推荐最小口径):

- 当响应符合 envelope 且 `success === true`: `status=started`, `tone=success`, `message=resp.message || "任务已启动"`.
- 当响应符合 envelope 且 `error === true` 或 `success === false`: `status=failed`, `tone=error`, `message=resp.message || "操作失败"`, 并尽可能展示 `suggestions`.
- 当响应不符合预期结构: `status=unknown`, `tone=warning`, `message="操作未完成, 请稍后在会话中心确认"`.

---

## 4. 分阶段计划(中期 + 长期)

### Phase 1(中期, 1-2 周): 统一前端规范化 + 覆盖关键入口

验收口径:

- 所有 sync/batch 动作在任何返回结构下都不会静默.
- 所有调用点只依赖统一的 outcome 解析(helper), 不再自行写 `if (success) ... else if (error) ...` 且缺少兜底.
- 至少覆盖审计证据点(实例详情同步容量, 账户台账批量同步).

实施步骤(建议按 PR 拆分):

1. 新增 UI helper(边界层):
   - `app/static/js/modules/ui/async-action-feedback.js`(命名可调整)
   - 输出 `resolveAsyncActionOutcome(response, options)`:
     - 只识别标准字段(`success`, `error`, `message`, `recoverable`, `suggestions`, `data.session_id`).
     - 未识别结构统一走 `unknown` 并给出固定文案.
     - 当命中 `unknown` 时, 记录一次可观测事件(例如 `EventBus.emit("async-action:unknown-response")` 或 console warn), 用于推动后端收敛.
2. 统一 UI 展示策略:
   - 默认用 `toast` 展示 outcome.message.
   - 对于需要强提示/需要入口 CTA 的动作, 使用 `UI.confirmDanger` 的 `resultUrl/resultText` 作为"结果入口"(不依赖 toast HTML).
3. 迁移关键入口:
   - `app/static/js/modules/views/instances/detail.js`:
     - syncAccounts: 移除 `success || Boolean(message)` 成功判定, 改为按 envelope 驱动, 并补齐 unknown fallback(顺带覆盖审计表中的高风险兜底).
     - syncCapacity: 补齐 `else` fallback(unknown)并统一使用 helper.
   - `app/static/js/modules/views/accounts/ledgers.js`:
     - syncAllAccounts: 补齐 unknown fallback 并统一使用 helper.
4. 手工回归:
   - 在 dev 环境模拟 3 类返回(成功/失败/未知结构), 确认 UI 反馈可预测且不静默.

### Phase 2(长期, 2-4 周): 后端契约收敛 + 统一 UI 模式 + 门禁

验收口径:

- 所有 async task 入口 API 返回标准 JSON envelope, 且 `data` 包含可定位的 `session_id`(或等价标识).
- UI 可提供稳定 CTA: "查看会话详情" 或 "会话中心", 不依赖用户猜测.
- 有门禁/清单确保新增 async action 不会回归到静默.

实施步骤:

1. 后端契约收敛:
   - 统一 async task 启动接口返回:
     - `success=true`, `message="任务已启动"`, `data={"session_id": "..."}`
   - 失败统一走 `unified_error_response`(包含 `recoverable/suggestions`), 禁止手写 `{success:false}`.
   - 将 "不稳定结构" 的接口列入清理清单, 以 unknown 命中统计优先级排序.
2. UI 模式沉淀(标准化):
   - 新增 UI 标准: `docs/standards/ui/async-task-feedback-guidelines.md`
   - 内容包括:
     - started/failed/unknown 的统一文案与 tone
     - 何时必须提供 resultUrl(建议默认会话中心)
     - 建议词表(例如 "任务已启动", "操作失败", "请稍后在会话中心确认")
3. 门禁(可选, 迭代推进):
   - 静态扫描:
     - 查找 `if (result?.success) ... else if (result?.error) ...` 且缺少 else 的模式(先 warn 后 fail).
   - 或通过 code review 规则强制: async action 必须调用 helper.

---

## 5. 风险与回滚

风险:

- 部分接口当前不返回 envelope, Phase 1 会触发 `unknown` fallback, 需要同步推动后端修正.
- toast 不支持 HTML/链接, CTA 需要借助页面固定入口(导航栏)或 `UI.confirmDanger` 的 result link.

回滚:

- Phase 1 的变更主要在前端解析与 toast 文案, 可按 PR 回退.
- helper 引入后, 可逐步迁移调用点; 若个别页面回归, 允许暂时保留旧实现但必须补齐 unknown fallback.

---

## 6. 验证与门禁

手工验证(最低覆盖):

- 实例详情页:
  - 同步账户(syncAccounts)
  - 同步容量(syncCapacity)
- 账户台账页:
  - 同步所有账户(syncAllAccounts)

验证口径:

- 无论返回结构如何, 用户都能得到明确反馈, 且知道下一步入口是会话中心.

---

## 7. 清理计划

- 当后端契约稳定后, Phase 1 的 unknown 命中应趋近 0.
- 在 unknown 命中为 0 且保持一段周期后, 可以收紧门禁(禁止新增非 envelope 响应)并清理临时兼容分支.

---

## 8. Open Questions(需要确认)

1. async task 的定位标识以什么为准: `session_id` 还是 `request_id`? 对应的详情页 URL 规则是什么?
2. 对于 "已接受但未开始执行"(排队) 是否需要区分 tone/文案(例如 "任务已排队")?

