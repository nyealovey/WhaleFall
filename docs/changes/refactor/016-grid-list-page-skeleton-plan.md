# Grid List Page Skeleton Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-29
> 更新: 2025-12-29
> 范围: `app/templates/**`(Grid.js list pages), `app/static/js/common/grid-wrapper.js`, `app/static/js/common/table-query-params.js`, `app/static/js/modules/ui/filter-card.js`, `app/static/js/modules/views/**`(grid pages), `app/static/js/modules/views/components/**`, `app/static/css/components/**`, `docs/standards/ui/**`
> 关联: `docs/standards/ui/javascript-module-standards.md`, `docs/standards/ui/gridjs-migration-standard.md`, `docs/standards/ui/grid-wrapper-performance-logging-guidelines.md`, `docs/standards/ui/pagination-sorting-parameter-guidelines.md`, `docs/changes/refactor/010-grid-empty-state-cta-plan.md`, `docs/changes/refactor/015-layout-sizing-system-plan.md`, `docs/standards/halfwidth-character-standards.md`

**Goal:** Extract a single reusable "Grid list page skeleton" so list pages become thin config + domain renderers, eliminating duplicated wiring (filters, URL sync, export, selection, action delegation, error handling).

**Architecture:** Build `Views.GridPage` controller + plugins on top of existing `GridWrapper`, `UI.createFilterCard`, `TableQueryParams`, and existing UI components (toast, confirmDanger, button loading).

**Tech Stack:** Grid.js + `GridWrapper`, vanilla JS modules (no bundler), Bootstrap, Jinja2 templates.

---

## 1. 动机与范围

### 1.1 动机

当前多个 Grid.js 列表页存在大量重复实现, 直接影响"代码唯一性"与"可维护性":

- Grid list view scripts 体积大且重复: 仅以下页面合计约 9.5k LoC
  - `app/static/js/modules/views/instances/list.js`(1514)
  - `app/static/js/modules/views/instances/detail.js`(1816, 含 2+ grids)
  - `app/static/js/modules/views/accounts/ledgers.js`(1156)
  - `app/static/js/modules/views/history/sessions/sync-sessions.js`(1059)
  - `app/static/js/modules/views/credentials/list.js`(976)
  - `app/static/js/modules/views/auth/list.js`(802)
  - `app/static/js/modules/views/tags/index.js`(765)
  - `app/static/js/modules/views/history/logs/logs.js`(735)
  - `app/static/js/modules/views/databases/ledgers.js`(443)
  - `app/static/js/modules/views/admin/partitions/partition-list.js`(315)
- 重复的基础能力在不同页面以不同方式实现, 容易漂移:
  - filter form serialize + debounce + clear
  - URL query params 解析/拼接/兼容字段(page_size vs pageSize/limit)
  - grid row meta 提取(`resolveRowMeta`)
  - `escapeHtml`, `resolveErrorMessage`, chip stack 渲染等工具函数
  - `data-action` click delegation, checkbox selection, batch actions enable/disable

结论: 需要把"列表页骨架"抽为通用组件, 并把可复用能力沉淀为单一真源, 以达到前端代码瘦身与行为一致.

### 1.2 范围

In-scope:

- 抽取 Grid list page skeleton(模板 + JS controller).
- 将重复能力提取到 `modules/views/components/**` 或 `modules/ui/**` 或 `common/**`(按职责划分).
- 以"逐页迁移"方式改造现有 Grid 列表页, 并删除旧实现.
- 补齐必要的 UI 标准与门禁项, 防止新页面回到重复实现.

Out-of-scope(本期不做):

- 替换 Grid.js 或引入前端打包链路.
- 把所有非列表页一次性重构到统一骨架(可在后续独立计划推进).

---

## 2. 不变约束(行为/契约/性能)

- MUST: 列表页仍使用 `GridWrapper`, 不允许页面直接 `new gridjs.Grid`. 参见 `docs/standards/ui/gridjs-migration-standard.md`.
- MUST: 分页参数统一 `page`(1-based) + `page_size`, 仅解析层兼容 `pageSize/limit`. 参见 `docs/standards/ui/pagination-sorting-parameter-guidelines.md`.
- MUST: 不改变现有列表 API 的输入输出契约(仅重构前端组织形式).
- MUST: 迁移过程中允许新旧共存, 但每个页面只能存在一个最终实现(迁移完成必须删除旧实现).
- SHOULD: 不新增高频请求, filter 输入必须 debounce.

---

## 3. 决策(Adopt Option B)

### Decision: Adopt Option B(中期治理)

本计划明确采用 Option B: 引入 `Views.GridPage` controller + plugin 体系, 作为 Grid list page skeleton 的唯一入口.

原因(与目标直接对齐):

- Uniqueness: "骨架"集中到一个入口, 新页面没有理由再复制 wiring.
- Refactor leverage: 通过 plugins 复用 filters/url/export/selection/actions, 能把大文件收敛为"配置 + domain renderers".
- Incremental: 可逐页迁移, 每页可回滚, 风险可控.

### Alternatives(不采用, 仅保留为历史对比)

Option A(抽 helpers, 页面自组装):

- 不满足唯一性约束: wiring 分散在页面, 仍会持续产生重复实现.

Option C(模板宏+数据驱动, JS 变为通用 runtime):

- 价值很高但需要更严格的数据契约与模板抽象, 适合作为 Option B 稳定后的 Phase 3+ 增量优化, 不阻塞当前的瘦身目标.

---

## 4. 统一设计(推荐实现)

### 4.1 单一真源原则(唯一性)

定义强约束: "同一能力只能有一个实现位置", 页面不得复制实现.

建议把常见能力收敛到以下模块, 并在 code review 中强制执行:

- HTML 安全: `UI.escapeHtml(value)`(替换存量 `escapeHtml` 重复函数)
- 统一错误消息: `UI.resolveErrorMessage(error, fallback)`(替换存量重复实现)
- chip stack 渲染: `UI.renderChipStack(values, options)`(替换页面内 `renderChipStack`)
- grid row meta: `GridRowMeta.get(row, { metaColumnId: "__meta__" })`
- filter serialize: `UI.serializeForm(form)`(已存在)
- pagination param normalize: `TableQueryParams.normalizePaginationFilters(filters)`(已存在)

以上能力在迁移完成后应满足:

- `rg -n "function escapeHtml\\(" app/static/js/modules/views` 返回 0
- `rg -n "function resolveErrorMessage\\(" app/static/js/modules/views` 返回 0
- `rg -n "function renderChipStack\\(" app/static/js/modules/views` 返回 0
- `rg -n "function resolveRowMeta\\(" app/static/js/modules/views` 返回 0
- `rg -n "new\\s+GridWrapper\\(" app/static/js/modules/views` 仅命中 grid skeleton 实现(不再命中具体页面脚本)

### 4.2 目录结构与导出约定(Option B 落点)

建议固定目录与全局导出, 防止"又出现一套 grid 封装":

- Create: `app/static/js/modules/views/components/grid/grid-page.js`
  - 导出: `global.Views.GridPage`
- Create: `app/static/js/modules/views/components/grid/plugins/index.js`
  - 导出: `global.Views.GridPlugins`
- Create: `app/static/js/modules/views/components/grid/grid-row-meta.js`(或放到 `common/`)
  - 导出: `global.GridRowMeta`

导出命名约束:

- MUST: 统一挂载在 `window.Views` 命名空间下, 避免散落到 `window.*PageHelper`.
- MUST: plugins 统一从 `window.Views.GridPlugins.*` 暴露, 页面不得自行 new plugin.
- SHOULD: plugins 文件名使用 `kebab-case.js`, 与 view/components 的可读性一致.

### 4.3 `Views.GridPage` 责任边界

`Views.GridPage` 作为唯一入口, 负责:

1. 依赖检测与 fail-fast(缺少 DOMHelpers/GridWrapper/FilterCard 时直接退出).
2. 读取 root dataset 与页面 config(严格 allowlist keys, 防御原型污染).
3. 初始化 FilterCard, 将 form values 规范化为 filters.
4. 初始化 GridWrapper, 并把 filters 统一透传为 query params.
5. 管理生命周期: `mount()` / `destroy()` 负责解绑事件与销毁 plugins.

页面脚本的目标形态:

```js
window.TagsIndexPage = {
  mount: function () {
    window.Views.GridPage.mount({
      root: "#tags-page-root",
      grid: "#tags-grid",
      filterForm: "#tag-filter-form",
      gridOptions: {
        search: false,
        sort: false,
        columns: buildColumns(),
      },
      server: {
        url: "/api/v1/tags",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        then: mapTagsResponse,
        total: mapTagsTotal,
      },
      filters: {
        allowedKeys: ["search", "category", "status", "page", "page_size", "sort", "order"],
        normalize: normalizeTagFilters,
      },
      plugins: [
        window.Views.GridPlugins.urlSync(),
        window.Views.GridPlugins.exportButton({ selector: "[data-action='export']" }),
        window.Views.GridPlugins.actionDelegation({ actions: window.TagsIndexActions }),
      ],
    });
  },
};
```

### 4.4 页面 config contract(建议, 先最小可用)

`Views.GridPage.mount(config)` 的建议入参(最小可用, 可后续扩展):

- `root`: `string | HTMLElement`(page root, 用于 scoped query 与 dataset)
- `grid`: `string | HTMLElement`(Grid container)
- `filterForm`: `string | HTMLFormElement | null`(可选)
- `gridOptions`: `Object`(透传给 `new GridWrapper(..., gridOptions)`, 但禁止覆盖 skeleton 管理的字段)
- `server`:
  - `url`: `string | Function`(required)
  - `headers`: `Object`(optional)
  - `then(response) -> any[]`(required, 由页面提供 domain mapping)
  - `total(response) -> number`(required)
- `filters`:
  - `allowedKeys: string[]`(required, allowlist)
  - `normalize(values) -> Object`(optional, 页面做 domain-specific 清洗)
  - `initial(values) -> Object`(optional, 用于从 URL/dataset 初始化)
- `plugins: Array<plugin>`(optional)

强约束:

- MUST: filters 进入 GridWrapper 前必须经过 `allowedKeys` 过滤, 并调用 `TableQueryParams.normalizePaginationFilters(...)` 统一分页字段.
- MUST NOT: 页面通过 config 绕过 allowlist 或直接透传 `location.search` 原始对象.

### 4.5 Plugin API(建议)

建议 plugin 最小接口:

- `name: string`
- `init(ctx) -> void | { destroy() }`
- 可选 hooks:
  - `onFiltersChanged(ctx, { filters, source })`
  - `onGridReady(ctx)`

`ctx` 建议包含:

- `rootEl`, `gridEl`, `filterFormEl`
- `gridWrapper`, `filterCard`
- `helpers`(`DOMHelpers`), `toast`, `http`
- `config`, `state`, `emit(eventName, payload)`

### 4.6 标准 plugins(建议内置)

P0(迁移必需):

- `filterCard`: 使用 `UI.createFilterCard` 绑定 submit/change/clear, 输出统一 filters.
- `urlSync`: 从 `location.search` 初始化 filters, 在 filters 变化时 `history.replaceState`.
- `actionDelegation`: 基于 `[data-action]` 做 click delegation, 不允许 `onclick="..."`.
- `exportButton`: 基于 `currentFilters` 拼接 export url 并触发下载.

P1(部分页面需要):

- `selection`: checkbox selection + summary + batch buttons enable/disable.
- `toggleControls`: include_deleted switch, db_type buttons, 统一读写 filters.
- `tagSelectorFilter`: 统一接入 Tag selector, 输出 tags filter 值.

P2(与现有计划对齐):

- `emptyState`: 对齐 `docs/changes/refactor/010-grid-empty-state-cta-plan.md`, 统一 no results CTA.

### 4.7 页面脚本的"禁用清单"(迁移完成后的唯一性门槛)

当页面迁移到 `Views.GridPage` 后, 页面脚本不得再做以下事情:

- 自行实现 filter serialize/debounce/clear(必须使用 `UI.createFilterCard` + plugin).
- 自行拼接分页/排序/筛选 query params(必须交给 skeleton + `TableQueryParams`).
- 自行绑定 `data-action` click delegation(必须使用 actionDelegation plugin).
- 定义通用 helper(escapeHtml/resolveErrorMessage/renderChipStack/resolveRowMeta 等).

---

## 5. 除 Grid 骨架外的"其他骨架"提取建议(按收益排序)

### 5.1 CRUD modal skeleton(高收益)

现状: 多个页面存在 create/edit modal controller, 大量重复: 校验, loading, error toast, reset, openEdit fetch.

建议:

- 新增 `UI.CrudModalController`(或 `Views.CrudModal`)统一:
  - `openCreate()`, `openEdit(id)`, `submit()`, `reset()`
  - 与 `FormValidator/ValidationRules` 集成
  - `UI.setButtonLoading` + `UI.resolveErrorMessage` + toast
- 页面只提供 schema(字段映射)与 service 调用函数.

### 5.2 Renderers skeleton(中高收益)

把常用 renderer 从页面中抽出, 形成可复用组件:

- chip stack, status pill, db type badge, timestamp formatter
- 统一 `gridHtml` fallback 行为(无 gridjs.html 时退回纯字符串)

### 5.3 Page action delegation skeleton(中收益)

统一 `[data-action]` 的事件路由与参数解析, 让页面 action 只写一次:

- `UI.ActionRouter` 或 `Views.ActionDelegation`
- 支持从 `data-*` 读取参数并做 allowlist 校验

### 5.4 Charts page skeleton(中收益, 已有基础)

仓库已存在 `modules/views/components/charts/manager.js`, 建议补齐"页面骨架层"以进一步去重:

- 统一 filters + fetch + render lifecycle
- 统一 error/empty/loading 体验

---

## 6. 分阶段计划(逐页迁移, 保持可回滚)

### Phase 0(设计+基建, 1-2 天): 定义 API 与最小可用实现

产出:

- `Views.GridPage`(mount/destroy) + P0 plugins.
- `UI.escapeHtml`, `UI.resolveErrorMessage`, `UI.renderChipStack`, `GridRowMeta.get`.
- 一个示例页面迁移 PR(推荐 tags 或 databases ledgers).

验收口径:

- 新组件可以独立驱动一个列表页完成: filter, grid, export, action delegation.
- 新增代码符合 `docs/standards/ui/javascript-module-standards.md` 分层职责.

### Phase 1(试点迁移, 1 周): 迁移 1-2 个中等复杂页面

推荐试点顺序:

1. `tags/index`(有 CRUD modal + filter card, 但无复杂 selection)
2. `databases/ledgers`(有 tag filter + export + type buttons, 复杂度适中)

验收口径(每页):

- 页面 JS 文件行数下降 >= 50%, 且页面行为不变.
- 不再出现页面内 `escapeHtml/resolveErrorMessage/resolveRowMeta/renderChipStack` 自定义实现.

### Phase 2(规模化迁移, 1-2 周): 覆盖所有 Grid list pages

目标页面(按模板包含 gridjs 统计):

- `app/templates/instances/list.html`
- `app/templates/instances/detail.html`(按 grid 拆分子 controller)
- `app/templates/accounts/ledgers.html`
- `app/templates/history/sessions/sync-sessions.html`
- `app/templates/history/logs/logs.html`
- `app/templates/credentials/list.html`
- `app/templates/auth/list.html`
- `app/templates/admin/partitions/index.html`

验收口径:

- 以上页面全部迁移到 `Views.GridPage` + plugins 体系.
- `rg` 扫描确认 view 层重复 helper 已清零.

### Phase 3(模板宏与 assets 去重, 可选): 抽 Jinja2 list page macro

目标:

- 把重复的 grid assets include 和基础 layout(section/layout-shell/card)收敛到宏.
- 页面模板只保留 slots(filter fields, toolbar buttons, modals include).

验收口径:

- grid list templates 的重复 include 下降明显, 且不影响现有 `page_density/layout-sizing` 规范.

### Phase 4(门禁与标准, 可选): 防止回归到重复实现

建议门禁方向:

- 新增 guard: 检测 view 层新增 `function escapeHtml(` 等重复实现(先 warn, 后 fail).
- 更新标准:
  - 新增 `docs/standards/ui/grid-list-page-skeleton-guidelines.md`, 并在 `gridjs-migration-standard.md` checklist 中引用.

---

## 7. 风险与回滚

风险:

- Plugin API 设计过度或不足: 先以 P0 plugins 覆盖核心路径, 试点后再扩展.
- DOM id/selector 漂移: 统一 root scope 查询, 使用 data-* + allowlist 读取.
- 行为回归难以察觉: 采用"逐页迁移 + 手工回归 checklist", 不做大爆炸式替换.

回滚:

- 单页回滚: 恢复该页旧脚本引用与旧逻辑, 保持新组件不影响其他页面.
- 全量回滚: revert Phase 0-2 引入的组件文件与页面迁移提交.

---

## 8. 验收指标(可量化)

- LoC: Grid list pages 合计从 ~9581 降至 < 4500(Phase 2 目标), 长期目标 < 3000.
- Per-page: grid list page view script <= 300 LoC(不含 domain renderer 可适当放宽).
- Uniqueness: view 层重复 helper definitions 0(见 4.1 的 `rg` 指标).
- DX: 新增一个简单列表页(无 selection)的页面脚本 <= 150 LoC.

---

## 9. Open Questions(需要确认)

1. 你希望 Phase 1 的试点页面选哪个: `tags/index`, `databases/ledgers`, 还是 `credentials/list`?
2. URL sync 的口径是否要在 Phase 0 就强制落地(shareable URL), 还是先保持现状, 后续再开独立计划?
