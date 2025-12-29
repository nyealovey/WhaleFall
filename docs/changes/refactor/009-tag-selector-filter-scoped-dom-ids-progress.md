# TagSelectorFilter Scoped DOM IDs Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-29
> 范围: 同 `009-tag-selector-filter-scoped-dom-ids-plan.md`
> 关联: `009-tag-selector-filter-scoped-dom-ids-plan.md`

关联方案: `009-tag-selector-filter-scoped-dom-ids-plan.md`

---

## 1. 当前状态(摘要)

- Phase 1/2(Option A) 已落地:
  - `tag_selector_filter(...)` 已改为 `${field_id}-*` scoped ids，避免同页多实例冲突.
  - `TagSelectorHelper` 已支持 `scope/container`，并修复同一 modal root 重复构造 controller 的问题.
  - 3 个页面调用点已迁移，固定 id 字符串已清零，并新增门禁防回归.
- 已通过静态验证：`rg` 清零固定 id；`./scripts/ci/tag-selector-filter-id-guard.sh` 通过；`uv run pytest -m unit` 通过.
- 剩余：手工回归“同页 2 个筛选器互不干扰”。
- Option B：按本次约束不执行。

## 2. Checklist

### Phase 1(中期): 宏改造 + 调用方迁移

- [x] 改造 `app/templates/components/filters/macros.html` 的 `tag_selector_filter(...)` 为 `${field_id}-*` ids
- [x] 改造 `app/static/js/modules/views/components/tags/tag-selector-controller.js` 的 `TagSelectorHelper` 支持 scope/container
- [x] 迁移固定 id 调用点:
  - [x] `app/static/js/modules/views/instances/list.js`
  - [x] `app/static/js/modules/views/accounts/ledgers.js`
  - [x] `app/static/js/modules/views/databases/ledgers.js`
- [x] `rg` 清零固定 id: `open-tag-filter-btn/selected-tag-names/selected-tags-preview/selected-tags-chips`
- [ ] 手工回归: 同页 2 个筛选器互不干扰

### Phase 2(长期): 组件化固化 + 回归门禁

- [x] 新增标准: `docs/standards/ui/component-dom-id-scope-guidelines.md`
- [x] 新增门禁: `scripts/ci/tag-selector-filter-id-guard.sh`(或更泛化的 DOM id guard)
- [ ] 评估是否升级为 data-role 驱动的组件 API(Option B)（按本次约束不执行）

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-01 为入口推进 TagSelectorFilter 多实例可复用治理.
- 2025-12-29: 落地 Option A(宏 scoped ids + JS scope/container 绑定); 迁移 instances/accounts/databases 调用点; 清零固定 id 并新增标准与门禁防回归.
