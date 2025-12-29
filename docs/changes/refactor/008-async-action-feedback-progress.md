# Async Action Feedback(Sync/Batch) Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-29
> 范围: 同 `008-async-action-feedback-plan.md`
> 关联: `008-async-action-feedback-plan.md`

关联方案: `008-async-action-feedback-plan.md`

---

## 1. 当前状态(摘要)

- Phase 1 已完成关键入口迁移（除手工回归项），同步/批量动作在未知结构下不再静默。
- Phase 2 已推进：后端启动接口开始返回 `data.session_id`，新增 UI 标准与（warn-first）静态门禁脚本。

## 2. Checklist

### Phase 1(中期): 统一前端规范化 + 覆盖关键入口

- [x] 新增 helper: `app/static/js/modules/ui/async-action-feedback.js`
- [x] 迁移 `app/static/js/modules/views/instances/detail.js`:
  - [x] syncAccounts: 移除 `success || Boolean(message)` 成功判定, 改为 envelope 驱动 + unknown fallback
  - [x] syncCapacity: 增加 unknown fallback, 统一使用 helper
- [x] 迁移 `app/static/js/modules/views/accounts/ledgers.js`:
  - [x] syncAllAccounts: 增加 unknown fallback, 统一使用 helper
- [ ] 手工回归: 成功/失败/未知结构均不静默

### Phase 2(长期): 后端契约收敛 + 统一 UI 模式 + 门禁

- [x] 后端 async task 启动接口统一返回 envelope + `data.session_id`(或等价标识)
- [x] 新增 UI 标准: `docs/standards/ui/async-task-feedback-guidelines.md`
- [x] `docs/standards/ui/README.md` 增加索引
- [x] 评估并落地静态门禁(先 warn 后 fail)

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P1-08 为入口推进同步/批量动作反馈闭环治理.
- 2025-12-29: 落地 Phase 1 核心入口：新增 async-action-feedback helper，并迁移实例详情/账户台账的同步动作以补齐 unknown fallback.
- 2025-12-29: 推进 Phase 2：`/api/v1/accounts/actions/sync-all` 返回 `data.session_id`，新增 UI 标准与 warn-first 静态门禁脚本.
