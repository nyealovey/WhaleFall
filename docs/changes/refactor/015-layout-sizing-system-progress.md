# Layout Sizing System (Page Frame) Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-29
> 更新: 2025-12-29
> 范围: 同 `015-layout-sizing-system-plan.md`
> 关联: `015-layout-sizing-system-plan.md`

关联方案: `015-layout-sizing-system-plan.md`

---

## 1. 当前状态(摘要)

- Phase 0 已完成: sizing contract 标准 `docs/standards/ui/layout-sizing-guidelines.md` 已落地并在 UI README 中可检索.
- Phase 1 部分已完成: page frame tokens 已补齐并应用于 `.navbar`/`.main-content`, 清理 `.main-content` 的 hardcode offset.
- 剩余工作见第 2 节 checklist.

## 2. Checklist

### Phase 0: 标准落地 (Docs)

- [x] `docs/standards/ui/layout-sizing-guidelines.md` 草案达到可执行的 sizing contract
- [x] UI 标准索引新增入口: `docs/standards/ui/README.md`

### Phase 1: Token 化 page frame (CSS)

- [x] `app/static/css/variables.css` 的 layout max width tiers 对齐 1920x1080/2560x1440 推荐值(1440/1920/1200)
- [x] `app/static/css/variables.css` 新增 page frame tokens(例如 `--layout-navbar-height`), 并收敛 navbar/main content 占位策略
- [x] `app/static/css/global.css` 用 Token 替换 `.main-content` 的 hardcode `76px`(margin-top/min-height) 并保持行为不变
- [ ] 手工回归: 1920x1080 与 2560x1440 下 navbar 与 main content 对齐无跳动/无额外空白

### Phase 2: Controls size tiers (Buttons, Inputs, Filters)

- [x] 明确 regular/compact 两档密度并提供统一入口(优先 `data-density="regular|compact"`)
- [x] `app/static/css/components/buttons.css` 增加 density-aware 规则(按钮/btn-icon hit area 不缩小)
- [x] `app/static/css/components/filters/filter-common.css` 对齐 filter controls 高度/padding 并提供 compact overrides
- [x] (可选) 新增 `app/static/css/components/forms.css` 承载通用表单控件 sizing(避免继续堆在 `global.css`)
- [ ] 手工回归: icon button 与 filter controls 在关键页面高度一致, 不出现“视觉变小但可点击热区也变小”的回归

### Phase 3: Tables and lists density (Grid.js, table)

- [x] `app/static/css/components/table.css` 收敛行高/单元格 padding/行内操作尺寸策略
- [x] (可选) 引入对表格容器生效的 `data-density="compact"` 规则, 避免多处 copy/paste
- [x] 明确 action column width policy(可复用 class/列规则, 避免页面私有 magic number)
- [ ] 手工回归: 列表页在 1920x1080 下首屏可见行数不减少, 且操作按钮可点击

### Phase 4: Charts stage tiers + 移除模板 inline px (与 012 联动)

- [x] 新增 `app/static/css/components/charts.css` 提供 `.chart-stage` + height tiers(`--lg/--md/--sm`) 与 `.chart-canvas`
- [x] 迁移关键页面移除 inline px:
  - [x] `app/templates/capacity/databases.html`
  - [x] `app/templates/capacity/instances.html`
  - [x] `app/templates/admin/partitions/charts/partitions-charts.html`
- [x] 新增/对齐门禁: `scripts/ci/inline-px-style-guard.sh`(baseline: `scripts/ci/baselines/inline-px-style-guard.txt`)
- [x] 验收: `rg -n \"style=\\\"[^\\\"]*(height|width)\\s*:\\s*\\d+px\" app/templates/capacity app/templates/admin/partitions/charts/partitions-charts.html` 对 in-scope 页面不再命中
- [ ] 手工回归: 1920x1080 与 2560x1440 下图表可读且首屏密度不劣化

### Phase 5(可选): Modals (Dialog width tiers)

- [x] 定义 modal width tiers 并提供可复用 class(与 `layout-sizing-guidelines.md` 保持一致)
- [x] 渐进迁移关键 modal, 禁止模板 inline `style="width: ..."` 作为布局手段
- [ ] 手工回归: 1920x1080 与 2560x1440 下 modal 不遮挡关键操作

## 3. 变更记录

- 2025-12-29: 初始化 progress 文档; Phase 0(Docs) 已落地, 其余阶段待推进.
- 2025-12-29: Phase 1(部分): 新增 page frame tokens(`--layout-navbar-height` 等), `.main-content` 去除 hardcode `76px` 并改为 token 驱动.
- 2025-12-29: Phase 2(部分): 新增 control sizing tokens + forms.css; `.btn`/filter controls 由 `data-density` 驱动 regular/compact 尺寸 tier.
- 2025-12-29: Phase 2(应用): 数据密集页面默认启用 `page_density='compact'`(实例/账户/数据库/凭据/标签/用户/日志/会话/容量统计等列表页).
- 2025-12-29: Phase 3(部分): Grid.js/Bootstrap table 的 row density/操作区尺寸由 `data-density` 驱动, 并收敛到 `app/static/css/components/table.css`.
- 2025-12-29: Phase 4(部分): 新增 `.chart-stage` + height tiers, capacity/partitions charts 移除模板 inline px(height/width) 并改为 class 驱动.
- 2025-12-29: Phase 4(门禁): 新增 `scripts/ci/inline-px-style-guard.sh`，并以 baseline 方式禁止新增 templates inline px layout sizing.
- 2025-12-29: Phase 4(扩展): 迁移统计页 table column width 的 inline px 为 CSS class, `inline-px-style-guard` baseline 清零.
- 2025-12-29: Phase 5(可选): 新增 modal width tiers tokens + `modals.css`, 并迁移关键 modal 使用 `size`/`scrollable` 参数统一宽度与滚动策略.
