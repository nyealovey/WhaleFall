# Grid List Page Skeleton Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-29
> 更新: 2025-12-29
> 范围: 同 `016-grid-list-page-skeleton-plan.md`
> 关联: `016-grid-list-page-skeleton-plan.md`

关联方案: `016-grid-list-page-skeleton-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `016-grid-list-page-skeleton-plan.md`.

## 2. Checklist

### Phase 0(设计+基建, 1-2 天): 定义 API 与最小可用实现

- [ ] 确认试点页面(建议: `tags/index` 或 `databases/ledgers`)
- [ ] 确认 URL sync 口径(Phase 0 强制 shareable URL, 或保持现状后置)
- [ ] 新增 `Views.GridPage`(mount/destroy) 并明确 config contract(allowlist + root scope query)
- [ ] 新增 P0 plugins: `filterCard` / `urlSync` / `actionDelegation` / `exportButton`
- [ ] 抽出单一真源 helpers: `UI.escapeHtml`, `UI.resolveErrorMessage`, `UI.renderChipStack`, `GridRowMeta.get`
- [ ] 迁移一个示例页面到 skeleton, 并删除旧 wiring(保证“每页最终只有一个实现”)
- [ ] 验收: 试点页行为不变(筛选/URL/导出/action delegation/错误处理)

### Phase 1(试点迁移, 1 周): 迁移 1-2 个中等复杂页面

- [ ] `tags/index` 迁移到 `Views.GridPage` + plugins, 页面脚本收敛为“配置 + domain renderers”
- [ ] `databases/ledgers` 迁移到 `Views.GridPage` + plugins
- [ ] 验收: 每页 JS 行数下降 >= 50%, 且页面行为不变
- [ ] 验收: view 层不再出现页面内 `escapeHtml/resolveErrorMessage/resolveRowMeta/renderChipStack` 重复实现

### Phase 2(规模化迁移, 1-2 周): 覆盖所有 Grid list pages

- [ ] `app/templates/instances/list.html` 对应页面迁移
- [ ] `app/templates/instances/detail.html` 对应页面迁移(按 grid 拆分子 controller)
- [ ] `app/templates/accounts/ledgers.html` 对应页面迁移
- [ ] `app/templates/history/sessions/sync-sessions.html` 对应页面迁移
- [ ] `app/templates/history/logs/logs.html` 对应页面迁移
- [ ] `app/templates/credentials/list.html` 对应页面迁移
- [ ] `app/templates/auth/list.html` 对应页面迁移
- [ ] `app/templates/admin/partitions/index.html` 对应页面迁移
- [ ] 验收: `rg` 指标(重复 helper / `new GridWrapper` 命中)达标

### Phase 3(可选): 模板宏与 assets 去重

- [ ] 抽 Jinja2 list page macro, 收敛 grid assets include 与基础 layout(shell/card)
- [ ] 验收: list templates 重复 include 显著下降且不影响 `page_density/layout-sizing`

### Phase 4(可选): 门禁与标准

- [ ] 新增 UI 标准: `docs/standards/ui/grid-list-page-skeleton-guidelines.md`
- [ ] 更新 `docs/standards/ui/gridjs-migration-standard.md` checklist 引用 skeleton 标准
- [ ] 新增 guard: 检测 view 层新增 `function escapeHtml(` 等重复实现(先 warn 后 fail)

## 3. 变更记录

- 2025-12-29: 初始化 progress 文档, 待开始推进.

