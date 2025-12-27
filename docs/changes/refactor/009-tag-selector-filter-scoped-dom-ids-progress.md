# TagSelectorFilter Scoped DOM IDs Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `009-tag-selector-filter-scoped-dom-ids-plan.md`
> 关联: `009-tag-selector-filter-scoped-dom-ids-plan.md`

关联方案: `009-tag-selector-filter-scoped-dom-ids-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `009-tag-selector-filter-scoped-dom-ids-plan.md`.

## 2. Checklist

### Phase 1(中期): 宏改造 + 调用方迁移

- [ ] 改造 `app/templates/components/filters/macros.html` 的 `tag_selector_filter(...)` 为 `${field_id}-*` ids
- [ ] 改造 `app/static/js/modules/views/components/tags/tag-selector-controller.js` 的 `TagSelectorHelper` 支持 scope/container
- [ ] 迁移固定 id 调用点:
  - [ ] `app/static/js/modules/views/instances/list.js`
  - [ ] `app/static/js/modules/views/accounts/ledgers.js`
  - [ ] `app/static/js/modules/views/databases/ledgers.js`
- [ ] `rg` 清零固定 id: `open-tag-filter-btn/selected-tag-names/selected-tags-preview/selected-tags-chips`
- [ ] 手工回归: 同页 2 个筛选器互不干扰

### Phase 2(长期): 组件化固化 + 回归门禁

- [ ] 新增标准: `docs/standards/ui/component-dom-id-scope-guidelines.md`
- [ ] 新增门禁: `scripts/ci/tag-selector-filter-id-guard.sh`(或更泛化的 DOM id guard)
- [ ] 评估是否升级为 data-role 驱动的组件 API(Option B)

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-01 为入口推进 TagSelectorFilter 多实例可复用治理.

