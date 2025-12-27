# Status Terminology Consistency Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `013-status-terminology-consistency-plan.md`
> 关联: `013-status-terminology-consistency-plan.md`

关联方案: `013-status-terminology-consistency-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `013-status-terminology-consistency-plan.md`.

## 2. Checklist

### Phase 1(中期): 统一 "active/inactive" 状态词

- [x] 决策 canonical 词对: 启用/停用
- [ ] 替换证据点:
  - [ ] `app/static/js/modules/views/instances/list.js`
  - [ ] `app/templates/tags/index.html`
- [ ] 扩展清理统计文案(按 `rg` 命中清单推进)
- [ ] 手工回归: 实例/标签/凭据/用户页面状态文案一致

### Phase 2(长期): 标准化 + 防回归

- [ ] 更新 `docs/standards/terminology.md` 增加 "状态用词" 小节
- [ ] 新增前端 helper(`UI.Terms` 或 `resolveActiveStatusText`)
- [ ] 新增门禁 `scripts/ci/ui-terminology-guard.sh`(限定扫描范围 + baseline)
- [ ] 更新 `.github/pull_request_template.md` 增加 "术语一致性" 自检项

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-06 为入口推进 UI 术语一致性治理.
