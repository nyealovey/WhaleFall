# TagSelectorFilter Scoped DOM IDs Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/templates/components/filters/macros.html`, `app/static/js/modules/views/components/tags/**`, `app/static/js/modules/views/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P2-01), `docs/standards/halfwidth-character-standards.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `TagSelectorFilter` supports multiple instances on the same page without DOM id collisions. All element queries are scoped to the filter container, not `document.getElementById(...)` with fixed ids.

**Architecture:** Keep `field_id` as the stable scope key, output scoped ids in the Jinja macro, and update JS to query within `[data-tag-selector-scope="<field_id>"]` so the component becomes reusable and collision-free.

**Tech Stack:** Jinja2 macros, vanilla JS modules, Bootstrap modal.

---

## 1. 动机与范围

### 1.1 动机

当前 `tag_selector_filter(...)` 在模板中使用固定 DOM id:

- `open-tag-filter-btn`
- `selected-tags-preview`
- `selected-tags-chips`
- `selected-tag-names`

这会导致同一页面渲染 2 个标签筛选器时发生冲突: label 关联错位, JS 绑定/更新命中错误节点, 进而出现"打开 A 但更新 B"或"只更新第一个"等隐性 bug.

审计报告(P2-01)已给出方向: 将 id 绑定到 `field_id`, 并在 JS 侧按容器 `data-tag-selector-scope` 查询.

### 1.2 范围

In-scope:

- 模板宏: `app/templates/components/filters/macros.html` 的 `tag_selector_filter(...)`.
- JS: `TagSelectorHelper` 及其调用方(实例管理/账户台账/数据库台账等)中对固定 id 的引用.

Out-of-scope(本次不做):

- 重写 TagSelector modal 本体结构(`app/templates/components/tag_selector.html`).
- 新增复杂的组件框架(保持现有 vanilla 模式).

---

## 2. 不变约束(行为/契约/兼容)

- 行为不变: UI 展示与交互不变(打开 modal, 勾选, 确认, 回写 hidden input, 更新 preview chips).
- 表单契约不变: hidden input 的 `name="{{ field_name }}"` 保持不变, 提交值仍为逗号分隔字符串.
- 渐进迁移: 允许先改模板 macro, 再逐页面迁移 JS 调用, 但每个页面完成后必须做到"无固定 id 依赖".

---

## 3. 推荐方案(中期)与可选方案(长期)

### 3.1 Option A(推荐, 中期): scoped ids + scoped query

模板侧:

- `open` button id: `${field_id}-open`
- preview wrapper id: `${field_id}-preview`
- chips container id: `${field_id}-chips`
- hidden input id: `${field_id}-selected`
- label `for` 同步到 `${field_id}-open`
- 保留外层容器:
  - `id="${field_id}-container"`
  - `data-tag-selector-scope="${field_id}"`

JS 侧:

- `TagSelectorHelper` 新增/优先支持 `scope`(field_id) 或 `container`(Element) 入参.
- 所有节点查找必须以 scope container 为起点:
  - `const container = document.querySelector([data-tag-selector-scope="${scope}"])`
  - `container.querySelector(...)`
- 逐步移除调用方中对 `document.getElementById('selected-tag-names')` 等固定 id 的引用.

### 3.2 Option B(长期): 移除 ids, 使用 data-role 作为组件 API

模板侧:

- 内部元素不再暴露 id(避免要求调用方传 `field_id`), 改为 `data-role="tag-filter-open|tag-filter-preview|tag-filter-chips|tag-filter-input"`.

JS 侧:

- `TagSelectorFilterController.create(container, options)` 只接受容器元素, 通过 `data-role` 找内部节点.

优点: 组件更可复用, 更不依赖全局命名.
缺点: 迁移量更大, 需要明确新的组件 API.

推荐结论:

- Phase 1 先落地 Option A(风险低, 改动小, 直接解决冲突).
- Phase 2 评估是否升级到 Option B 以减少调用方配置负担.

---

## 4. 分阶段计划(中期 + 长期)

### Phase 1(中期, 1-2 周): 宏改造 + 调用方迁移

验收口径:

- 任意页面允许渲染 2 个 `tag_selector_filter(...)`(不同 `field_id`), 两者互不干扰.
- 相关 JS 模块不再使用固定 id(例如 `#selected-tag-names`), 改为 scope-based query.

实施步骤:

1. 改造模板宏 `tag_selector_filter(...)`:
   - 将固定 id 替换为 `${field_id}-*`.
   - label `for` 与 open button id 保持一致.
2. 改造 `TagSelectorHelper`:
   - 增加 `scope` 或 `container` 的入口.
   - 在 helper 内部统一派生 open/preview/chips/hidden input 的 selector.
3. 逐页面迁移调用点:
   - `app/static/js/modules/views/instances/list.js`
   - `app/static/js/modules/views/accounts/ledgers.js`
   - `app/static/js/modules/views/databases/ledgers.js`
   - 其他引用固定 id 的页面按 `rg` 命中清单推进.

### Phase 2(长期, 2-4 周): 组件化固化 + 回归门禁

验收口径:

- TagSelectorFilter 的模板与 JS 形成稳定组件 API, 支持多实例且无需全局 id.
- 引入门禁防止新增固定 id 回归.

实施步骤:

1. 标准化:
   - 新增 UI 标准文档: `docs/standards/ui/component-dom-id-scope-guidelines.md`
   - 强约束: 可复用组件不得使用固定全局 id, 必须以 scope 或 data-role 绑定.
2. 门禁(建议先针对 TagSelectorFilter, 再逐步泛化):
   - 新增 `scripts/ci/tag-selector-filter-id-guard.sh`:
     - 禁止出现 `id="open-tag-filter-btn"`/`id="selected-tag-names"` 等固定 id.
     - 或检测 `tag_selector_filter` 宏输出必须包含 `${field_id}` 派生模式.
3. 可选升级到 Option B:
   - 若调用方配置复杂度过高, 将组件 API 切换为纯 container 驱动(data-role).

---

## 5. 风险与回滚

风险:

- 页面仍在引用旧固定 id 时, 改动模板宏会导致 JS 找不到元素.
- 同一页面如果多个筛选器误用相同 `field_id`, 仍可能冲突(需要在调用方代码 review 阶段约束).

回滚:

- 建议按页面拆分 PR: 每个 PR 同时改模板调用与该页面 JS, 保证可回滚且不留下半迁移状态.

---

## 6. 验证与门禁

手工验证:

- 在同一页面渲染两个标签筛选器(不同 `field_id`), 逐个打开, 选择, 确认, 校验 preview 与 hidden input 的值只影响当前筛选器.

静态检查(建议命令):

- `rg -n \"open-tag-filter-btn|selected-tag-names|selected-tags-preview|selected-tags-chips\" app/templates app/static/js`

---

## 7. 清理计划

- Phase 1 完成后: 从代码库中清零上述固定 id 字符串.
- Phase 2 完成后: 将组件规则写入标准并门禁化, 避免未来新增组件重复踩坑.

