# Grid List Page Skeleton Refactor Progress

> 状态: In Progress
> 负责人: WhaleFall FE
> 创建: 2025-12-29
> 更新: 2025-12-30
> 范围: 同 `016-grid-list-page-skeleton-plan.md`
> 关联: `016-grid-list-page-skeleton-plan.md`

关联方案: `016-grid-list-page-skeleton-plan.md`

---

## 1. 当前状态(摘要)

- Phase 0 已落地 skeleton + plugins，并以 `instances/list` 作为试点页完成迁移（保持现有 URL sync 行为，不额外强化 shareable URL 口径），且已完成手工回归验收。
- Phase 1 已迁移 `tags/index` 与 `databases/ledgers` 到 `Views.GridPage` + plugins。
- Phase 2 已继续推进，并完成 `auth/list`、`admin/partitions/index`、`credentials/list`、`history/sessions/sync-sessions`、`history/logs/logs`、`accounts/ledgers`、`instances/detail` 迁移。
- 已完成 `rg` 指标验收（迁移页脚本不再直接 `new GridWrapper`，且不再在页面内定义重复 helper）。
- 下一步：进入 Phase 3/4（可选）。

## 2. Checklist

### Phase 0(设计+基建, 1-2 天): 定义 API 与最小可用实现

- [x] 确认试点页面：`instances/list`
- [x] 确认 URL sync 口径：保持现状（不额外强化 shareable URL 口径）
- [x] 新增 `Views.GridPage`(mount/destroy) 并明确 config contract(allowlist + root scope query)
- [x] 新增 P0 plugins: `filterCard` / `urlSync` / `actionDelegation` / `exportButton`
- [x] 抽出单一真源 helpers: `UI.escapeHtml`, `UI.resolveErrorMessage`, `UI.renderChipStack`, `GridRowMeta.get`
- [x] 迁移一个示例页面到 skeleton, 并删除旧 wiring(保证“每页最终只有一个实现”)
- [x] 验收: 试点页行为不变(筛选/URL/导出/action delegation/错误处理/selection)

### Phase 1(试点迁移, 1 周): 迁移 1-2 个中等复杂页面

- [x] `tags/index` 迁移到 `Views.GridPage` + plugins, 页面脚本收敛为“配置 + domain renderers”
- [x] `databases/ledgers` 迁移到 `Views.GridPage` + plugins
- [ ] 验收: 每页 JS 行数下降 >= 50%, 且页面行为不变
- [ ] 验收: view 层不再出现页面内 `escapeHtml/resolveErrorMessage/resolveRowMeta/renderChipStack` 重复实现

### Phase 2(规模化迁移, 1-2 周): 覆盖所有 Grid list pages

- [x] `app/templates/instances/list.html` 对应页面迁移
- [x] `app/templates/instances/detail.html` 对应页面迁移(按 grid 拆分子 controller)
- [x] `app/templates/accounts/ledgers.html` 对应页面迁移
- [x] `app/templates/history/sessions/sync-sessions.html` 对应页面迁移
- [x] `app/templates/history/logs/logs.html` 对应页面迁移
- [x] `app/templates/credentials/list.html` 对应页面迁移
- [x] `app/templates/auth/list.html` 对应页面迁移
- [x] `app/templates/admin/partitions/index.html` 对应页面迁移
- [x] 验收: `rg` 指标(重复 helper / `new GridWrapper` 命中)达标

### Phase 3(可选): 模板宏与 assets 去重

- [ ] 抽 Jinja2 list page macro, 收敛 grid assets include 与基础 layout(shell/card)
- [ ] 验收: list templates 重复 include 显著下降且不影响 `page_density/layout-sizing`

### Phase 4(可选): 门禁与标准

- [ ] 新增 UI 标准: `docs/standards/ui/grid-list-page-skeleton-guidelines.md`
- [ ] 更新 `docs/standards/ui/gridjs-migration-standard.md` checklist 引用 skeleton 标准
- [ ] 新增 guard: 检测 view 层新增 `function escapeHtml(` 等重复实现(先 warn 后 fail)

## 3. 变更记录

- 2025-12-29: 初始化 progress 文档, 待开始推进.
- 2025-12-29: Phase 0 落地：新增 `Views.GridPage` + P0 plugins + shared helpers，并迁移 `instances/list` 到 skeleton.
- 2025-12-29: Phase 0 试点页验收通过，并完成 Phase 1 页面迁移：`tags/index` + `databases/ledgers`.
- 2025-12-29: Phase 2 批量迁移开始：`auth/list` + `admin/partitions/index`.
- 2025-12-29: Phase 2 继续推进：完成 `credentials/list` + `history/sessions/sync-sessions` + `history/logs/logs` + `accounts/ledgers` 迁移。
- 2025-12-30: Phase 2 继续推进：完成 `instances/detail`（accounts/databases 两个 grids）迁移到 `Views.GridPage` + plugins，并补齐 `rg` 指标验收。
