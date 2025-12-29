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

- [x] 新增通用 chart 容器 class(支持 `clamp()` 与 variants)
- [ ] capacity:
  - [x] `app/templates/capacity/databases.html` 清理 canvas inline height/width
  - [x] `app/templates/capacity/instances.html` 清理 canvas inline height/width
- [ ] partitions:
  - [x] `app/templates/admin/partitions/charts/partitions-charts.html` 清理容器 inline height
- [ ] 手工回归: 1366x768 与 1440x900 不再首屏挤压

### Phase 2(长期): 标准化 + 门禁 + 扩展到更多 inline px

- [x] 新增 UI 标准: `docs/standards/ui/layout-sizing-guidelines.md`
- [x] 新增门禁: `scripts/ci/inline-px-style-guard.sh`(fail + baseline)
- [x] 扩展清理: table column inline width(`th style="width: ...px"`) 逐步迁移到 class/colgroup

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-05 为入口推进 inline px 尺寸治理.
- 2025-12-29: 新增 `.chart-stage` 高度 tiers(`clamp()`), capacity/partitions charts 清理 inline px; 新增门禁 `scripts/ci/inline-px-style-guard.sh` 防止回归.
- 2025-12-29: 迁移统计页 table column width inline px 为 CSS class, 更新 baseline 至 0 命中.
