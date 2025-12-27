# Async Action Feedback(Sync/Batch) Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `008-async-action-feedback-plan.md`
> 关联: `008-async-action-feedback-plan.md`

关联方案: `008-async-action-feedback-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `008-async-action-feedback-plan.md`.

## 2. Checklist

### Phase 1(中期): 统一前端规范化 + 覆盖关键入口

- [ ] 新增 helper: `app/static/js/modules/ui/async-action-feedback.js`
- [ ] 迁移 `app/static/js/modules/views/instances/detail.js`:
  - [ ] syncAccounts: 移除 `success || Boolean(message)` 成功判定, 改为 envelope 驱动 + unknown fallback
  - [ ] syncCapacity: 增加 unknown fallback, 统一使用 helper
- [ ] 迁移 `app/static/js/modules/views/accounts/ledgers.js`:
  - [ ] syncAllAccounts: 增加 unknown fallback, 统一使用 helper
- [ ] 手工回归: 成功/失败/未知结构均不静默

### Phase 2(长期): 后端契约收敛 + 统一 UI 模式 + 门禁

- [ ] 后端 async task 启动接口统一返回 envelope + `data.session_id`(或等价标识)
- [ ] 新增 UI 标准: `docs/standards/ui/async-task-feedback-guidelines.md`
- [ ] `docs/standards/ui/README.md` 增加索引
- [ ] 评估并落地静态门禁(先 warn 后 fail)

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P1-08 为入口推进同步/批量动作反馈闭环治理.

