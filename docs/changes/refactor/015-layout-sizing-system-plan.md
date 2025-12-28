# Layout Sizing System (Page Frame) Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-28
> 更新: 2025-12-28
> 范围: `app/templates/**`, `app/static/css/**`, `scripts/ci/**`, `docs/standards/ui/**`
> 关联: `docs/standards/ui/layout-sizing-guidelines.md`, `docs/changes/refactor/012-no-inline-px-sizes-plan.md`, `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provide a complete, reusable sizing system for page frame, controls, tables, and charts. Remove ad-hoc sizing and make information density adjustable and reviewable.

**Architecture:** Define sizing contract in `docs/standards/ui/layout-sizing-guidelines.md`, then implement via CSS Tokens (`app/static/css/variables.css`) + reusable component classes (`app/static/css/**`). Migrate templates to classes (no inline width/height px), and add CI guards to prevent regression.

**Tech Stack:** Bootstrap 5 (Flatly), Jinja templates, CSS variables, Grid.js, Chart.js, ripgrep-based CI guards.

---

## 1. 动机与范围

### 1.1 动机

当前 UI 的"尺寸决策"存在以下问题:

- 页面框架: navbar height, main content offset, max width tier 的约束不成体系, 页面之间易漂移.
- 控件: button/input 的高度, padding, icon button hit area 在不同页面不一致, 影响可用性与密度可调.
- 列表/表格: Grid.js 与传统 table 的行高, 操作区宽度, 列宽策略缺少统一约束.
- 图表: 存在模板 inline `style="height: Npx"`/`style="width: Npx"` (见审计 P2-05), 在 1920x1080 与 2560x1440 下首屏信息密度不可调, 且后续难以统一治理.

本计划目标是补齐"页面框架大小规范", 并为后续 012 的 inline px 清理提供完整的 sizing contract.

### 1.2 范围

In-scope:

- 建立并落地 `docs/standards/ui/layout-sizing-guidelines.md` (single source of truth).
- 引入一组可复用的 sizing tokens 与组件 classes, 覆盖:
  - page frame (navbar, main content, footer spacing)
  - controls (buttons, icon buttons, inputs/selects)
  - tables/lists (row density, action column width policy)
  - charts (chart stage height tiers)
  - modals (dialog width tiers)
- 渐进迁移关键页面与组件, 并新增门禁脚本阻止回归.

Out-of-scope (本计划不做):

- 重新设计视觉风格或大规模改版布局.
- 更换 Bootstrap, Grid.js, Chart.js 等基础技术栈.
- 移动端优先适配 (本计划只覆盖桌面端 1920x1080 与 2560x1440).

---

## 2. 不变约束 (行为/契约/性能门槛)

- 行为不变: 不改业务流程与数据交互, 仅收敛布局尺寸表达方式.
- 可用性门槛: click target 不得缩小到不可点击 (尤其是表格行内操作与 icon button).
- 响应式门槛: 1920x1080 与 2560x1440 下, 首屏密度不劣化, 且关键操作可见.
- 性能门槛: 不新增运行时依赖, 优先通过 CSS Tokens 与 class 落地.

---

## 3. 方案选项 (2-3 个) 与推荐

### Option A: 只补文档 (不改代码)

优点: 快.

缺点: 无法阻止漂移与回归, 012 等后续重构缺少可执行落点.

### Option B (推荐): 先立标准 + Token + class, 再渐进迁移

优点: 规则可执行, 可以分阶段迁移, 可通过门禁守住新增代码质量.

缺点: 需要维护过渡期 (旧页面与新规范并存).

### Option C: 一次性全站迁移

优点: 最终状态一致, 历史债一次性清理.

缺点: 风险高, 回归成本大, 不利于拆分 PR.

推荐结论:

- Adopt Option B, 并把 012 计划作为 charts/tables 的子任务阶段推进.

---

## 4. 分阶段计划 (每阶段验收口径)

### Phase 0: 标准落地 (Docs)

目标:

- `docs/standards/ui/layout-sizing-guidelines.md` 达到可执行的 sizing contract (page frame, controls, tables, charts, modals).
- UI 标准索引新增入口, 变更可检索.

验收:

- UI README 已链接该标准.

### Phase 1: Token 化 page frame (CSS)

目标:

- 把 navbar height, main content offset 等关键 page frame 尺寸收敛到 Token, 禁止散落 magic number.

建议修改:

- Modify: `app/static/css/variables.css` (新增 `--layout-navbar-height` 等 tokens, 并把 `--layout-max-width*` 对齐 1920x1080/2560x1440: 1440/1920/1200)
- Modify: `app/static/css/global.css` (用 Token 替换 navbar/main-content 的硬编码高度)

验收:

- 1920x1080 与 2560x1440 下, navbar 与 main content 对齐无跳动, 无额外空白.

### Phase 2: Controls size tiers (Buttons, Inputs)

目标:

- 明确 regular/compact 两档控件密度, 并能被页面复用 (避免页面私有 padding).

建议修改:

- Modify: `app/static/css/components/buttons.css`
- Modify: `app/static/css/components/filters/filter-common.css`
- Optional: 新增 `app/static/css/components/forms.css` (如现有结构不适合继续堆在 global.css)

验收:

- icon button, filter controls 的高度与 hit area 在关键页面一致.
- 不出现 "按钮视觉变小但点击热区也变小" 的回归.

### Phase 3: Tables and lists density (Grid.js, table)

目标:

- 表格行高, action column width, badge/button 的尺寸策略可复用, 并在 compact 模式下仍保持可用.

建议修改:

- Modify: `app/static/css/components/table.css`
- Optional: 引入 `data-density="compact"` 对表格容器生效的规则 (避免多处 copy/paste).

验收:

- 列表页在 1920x1080 下首屏可见行数不减少, 且操作按钮可点击.

### Phase 4: Charts stage tiers + 移除模板 inline px (与 012 联动)

目标:

- 引入 `.chart-stage` + height tiers, 并迁移关键页面移除 inline px sizing.

建议修改:

- Create: `app/static/css/components/charts.css`
- Modify: `app/templates/**` (按 012 的 in-scope 页面迁移)
- Create: `scripts/ci/inline-px-style-guard.sh` (或在 012 中实现)

验收:

- `rg -n \"style=\\\"[^\\\"]*(height|width)\\s*:\\s*\\d+px\" app/templates` 对关键页面不再命中.
- 1920x1080 与 2560x1440 下图表可读, 且首屏信息密度不劣化.

---

## 5. 风险与回滚

风险:

- 统一控件高度可能影响部分页面的对齐与换行, 需要逐页回归.
- chart container 高度变化可能触发 Chart.js resize 行为差异, 需要观察渲染是否溢出或模糊.

回滚策略:

- 允许按组件回滚到旧 class, 但不回退到模板 inline px.
- 如门禁阻塞存量页面, 先以 baseline 方式允许存量命中, 再逐步清零.

---

## 6. 验收指标

- 在 1920x1080 与 2560x1440 下, 关键页面 (列表, 图表, 表单) 的首屏信息密度可控.
- 仓库内新增代码不再引入模板 inline `height/width: Npx` 用于布局.
- sizing 决策可追溯: 新增尺寸 tier 必须先改 Token/标准, 再改页面.

---

## 7. 清理计划

- 随 Phase 推进, 逐步删除页面私有的 magic number 与重复样式.
- 在 012 完成后, 将 charts/tables inline px sizing 的 allowlist/baseline 逐步清零.
