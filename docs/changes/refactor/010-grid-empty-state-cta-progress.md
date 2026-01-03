# Grid Empty State CTA Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `010-grid-empty-state-cta-plan.md`
> 关联: `010-grid-empty-state-cta-plan.md`

关联方案: `010-grid-empty-state-cta-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `010-grid-empty-state-cta-plan.md`.

## 2. Checklist

### Phase 1(中期): 统一能力 + 覆盖高频列表页

- [ ] `GridWrapper` 支持 empty state hook/renderer(可注入 CTA)
- [ ] FilterCard 提供可复用的 "clear filters" 能力(方法或 helper)
- [ ] 迁移至少 2-3 个高频列表页:
  - [ ] instances list
  - [ ] accounts ledgers
  - [ ] databases ledgers
- [ ] 手工回归: 无结果 -> CTA 清除筛选 -> 结果恢复

### Phase 2(长期): 空态标准化 + 模板库 + 门禁

- [ ] 新增 UI 标准: `docs/standards/ui/empty-state-guidelines.md`
- [ ] 更新 `docs/standards/ui/gridjs-migration-standard.md` 的 checklist 增加空态要求
- [ ] 评估并落地门禁(先 warn 后 fail)

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-02 为入口推进 Grid 空态可行动性治理.
