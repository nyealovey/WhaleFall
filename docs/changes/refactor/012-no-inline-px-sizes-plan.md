# No Inline PX Sizes(Charts/Tables) Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/templates/**`, `app/static/css/**`, `scripts/ci/**`, `docs/standards/ui/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P2-05), `docs/standards/ui/design-token-governance-guidelines.md`, `docs/standards/halfwidth-character-standards.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove fixed inline `style="height: Npx"` / `style="width: Npx"` from key chart/table layouts. Replace with reusable CSS classes + responsive sizing rules(clamp/viewport-based) so 1920x1080 and 2560x1440 have predictable, adjustable information density.

**Architecture:** Move layout sizing from templates(inline styles) into CSS tokens + component classes. Introduce a small "chart container sizing" contract and enforce it via standards + a guard script that blocks new inline px sizing.

**Tech Stack:** Jinja templates, CSS variables, Chart.js containers, ripgrep-based CI guards.

---

## 1. 动机与范围

### 1.1 动机

审计报告(P2-05)指出: 多个图表/表格容器使用 inline style 固定 px 高度, 例如:

- `app/templates/capacity/databases.html`: `<canvas style="height: 550px; width: 100%;">`
- `app/templates/admin/partitions/charts/partitions-charts.html`: `<div style="height: 400px;">`

影响:

- 在 1920x1080 等常见桌面分辨率下, 首屏被固定高度挤压, 需要更多滚动.
- 页面节奏不可调: 后续想调整密度/引入主题/做一致化时, inline style 成为治理死角.

### 1.2 范围

In-scope:

- templates 中的 inline px sizing(主要针对 chart/table 容器).
- 为图表容器提供可复用的 CSS class + token 化尺寸策略.
- 建立门禁防止新增 inline px sizing 回归.

Out-of-scope(本计划不做):

- 改造图表库或重写图表渲染逻辑.
- 将所有 table column width inline style 一次性清零(先聚焦"首屏挤压"的高度问题, 宽度作为后续扩展).

---

## 2. 不变约束(行为/视觉/性能门槛)

- 行为不变: 图表数据/交互不变(切换折线/柱状, TOPN, 周期选择不变).
- 视觉门槛: 默认主题下, 图表可读性不下降; 关键图表不应变得过矮导致不可用.
- 响应式门槛: 在 1920x1080 与 2560x1440 下, 首屏信息密度可控且滚动次数减少或不增加.
- 性能门槛: 不新增运行时依赖, 仅通过 CSS 改善布局.

---

## 3. 方案选项(2-3 个)与推荐

### Option A(中期, 推荐): CSS class + `clamp()`/viewport-based height

做法:

- 为图表容器增加 class(例如 `.chart-stage`), 在 CSS 中统一定义高度:
  - `height: clamp(22rem, 50vh, 44rem);`
- 将模板中的 inline `style="height: 550px"` 替换为 class.
- 对不同密度的图表提供 size variants:
  - `.chart-stage--lg`, `.chart-stage--md`, `.chart-stage--sm`

优点:

- 落地快, 改动小, 直接解决首屏挤压.
- 规则集中, 后续可统一调整.

缺点:

- 需要为各页面选择合适的 variant, 需要少量视觉回归.

### Option B(长期): Token 化图表尺寸 + 标准化 chart container contract

做法:

- 在 `variables.css` 增加 chart height tokens(例如 `--chart-height-lg`), 并在页面 CSS 里用 `clamp()` 组合 token.
- 建立标准文档定义:
  - 哪些页面使用哪种 chart height tier
  - 何时允许例外

优点:

- 与现有 token 治理体系一致, 可控可审查.

缺点:

- 需要更系统的设计决策(高度分层与默认值).

### Option C(长期扩展): 彻底禁止 inline style(门禁) + 迁移 width/column sizing

做法:

- 增加门禁: 扫描 templates 中 `style="...px"` 并阻断(允许极少数白名单例外).
- 将 table column width 从 inline 改为 class 或 colgroup 定义(按组件规范化).

优点:

- 从机制上减少布局漂移.

缺点:

- 一刀切可能影响历史页面, 需要渐进策略与白名单机制.

推荐结论:

- Phase 1 采用 Option A 解决最影响体验的 chart height inline px.
- Phase 2 采用 Option B/C: token+标准+门禁, 并逐步扩展覆盖面.

---

## 4. 分阶段计划(中期 + 长期)

### Phase 1(中期, 1-2 周): 清理关键图表 inline px + 引入可复用 class

验收口径:

- capacity 页面所有 `<canvas style="height: 550px">` 改为 class 驱动.
- partitions charts 的 `<div style="height: 400px">` 改为 class 驱动.
- 在 1920x1080 与 2560x1440 下确认首屏挤压明显缓解(至少不劣化).

实施步骤:

1. 新增通用 chart 容器 class:
   - 位置建议: `app/static/css/components/charts.css`(若已有 charts 相关 CSS, 则复用现有组件文件夹)
   - 提供 `.chart-stage` + variants(`--lg/--md/--sm`), 采用 `clamp()` 定义高度.
2. 迁移容量统计页面:
   - `app/templates/capacity/databases.html` & `app/templates/capacity/instances.html`:
     - 移除 canvas inline height/width, 改为 `class="chart-stage chart-stage--lg"`(或合适 variant).
3. 迁移分区图表:
   - `app/templates/admin/partitions/charts/partitions-charts.html`:
     - 移除 inline height, 改为 `class="chart-stage chart-stage--md"`(或合适 variant).
4. 手工回归:
   - 1920x1080 与 2560x1440 截图对比(首屏可见信息量与滚动次数).

### Phase 2(长期, 2-4 周): 标准化 + 门禁 + 扩展到更多 inline px

验收口径:

- UI 标准中明确: 禁止关键布局使用 inline px 高度, 给出可选 class/tokens 与例外流程.
- 门禁阻止新增 `style="height: Npx"`/`style="width: Npx"` 在 templates 中出现(或限定在 allowlist 中).

实施步骤:

1. 新增 UI 标准:
   - `docs/standards/ui/layout-sizing-guidelines.md`
   - 内容包含:
     - MUST: 禁止在 templates 中新增 `style="...px"` 用于关键布局(尤其 height).
     - SHOULD: 使用 `clamp()` + token + class 管理尺寸.
     - 例外: 必须走评审并记录原因与清理计划.
2. 新增门禁脚本:
   - `scripts/ci/inline-px-style-guard.sh`
   - 初期策略(推荐渐进):
     - Phase 2.1: warn 模式输出命中清单(便于存量清理计划)
     - Phase 2.2: fail 模式阻止新增命中(允许 baseline 文件做存量豁免, 逐步清零)
3. 扩展清理范围:
   - 除 chart 外, 逐步处理 table column inline width(例如 `<th style="width: 220px">`)并沉淀为 class/colgroup.

---

## 5. 风险与回滚

风险:

- 图表容器高度变化可能影响 Chart.js canvas 自适应逻辑, 需要确认 resize 行为正常(可能需要触发 chart.resize()).
- `clamp()` 的默认值不合适会导致图表过矮/过高, 需要按页面调参.

回滚:

- 允许按页面回滚 variant 参数(仍使用 class, 不回退到 inline px).
- 门禁如影响存量合并, 先以 warn + baseline 方式落地, 再逐步收紧.

---

## 6. 验证与门禁

手工验证(最低覆盖):

- 1920x1080: capacity 页面 3 张图表首屏不再过度挤压, 用户能看到更多筛选/统计信息.
- 2560x1440: 图表仍清晰可读, 不出现过小导致的标签重叠.

静态检查(建议命令):

- `rg -n \"style=\\\"[^\\\"]*(height|width)\\s*:\\s*\\d+px\" app/templates`

自动化门禁(长期):

- `scripts/ci/inline-px-style-guard.sh`

---

## 7. 清理计划

- Phase 1 后: capacity + partitions charts 的 inline height px 应清零.
- Phase 2 后: 新增 inline px 在 templates 中应被门禁阻断, 存量逐步清零.

---

## 8. Open Questions(需要确认)

1. chart 容器的默认高度 tier 你希望偏 "信息密度优先"(更矮) 还是 "可读性优先"(更高)?
2. 门禁是否只针对 `height: Npx`(先解决首屏挤压)还是同时覆盖 `width: Npx`?
