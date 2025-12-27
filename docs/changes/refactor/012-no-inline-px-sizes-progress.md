# No Inline PX Sizes(Charts/Tables) Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `012-no-inline-px-sizes-plan.md`
> 关联: `012-no-inline-px-sizes-plan.md`

关联方案: `012-no-inline-px-sizes-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `012-no-inline-px-sizes-plan.md`.

## 2. Checklist

### Phase 1(中期): 清理关键图表 inline px + 引入可复用 class

- [ ] 新增通用 chart 容器 class(支持 `clamp()` 与 variants)
- [ ] capacity:
  - [ ] `app/templates/capacity/databases.html` 清理 canvas inline height/width
  - [ ] `app/templates/capacity/instances.html` 清理 canvas inline height/width
- [ ] partitions:
  - [ ] `app/templates/admin/partitions/charts/partitions-charts.html` 清理容器 inline height
- [ ] 手工回归: 1366x768 与 1440x900 不再首屏挤压

### Phase 2(长期): 标准化 + 门禁 + 扩展到更多 inline px

- [ ] 新增 UI 标准: `docs/standards/ui/layout-sizing-guidelines.md`
- [ ] 新增门禁: `scripts/ci/inline-px-style-guard.sh`(warn -> fail + baseline)
- [ ] 扩展清理: table column inline width(`th style="width: ...px"`) 逐步迁移到 class/colgroup

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-05 为入口推进 inline px 尺寸治理.

