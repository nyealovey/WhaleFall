# Navbar Toggler(Desktop Narrow) Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/templates/base.html`, `app/static/css/**`, `scripts/ci/**`, `.github/**`, `docs/standards/ui/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P1-04), `docs/standards/halfwidth-character-standards.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When viewport width is <992px(e.g. desktop split view), the navbar remains reachable via a visible, keyboard-accessible `navbar-toggler` that correctly controls `#navbarNav` and exposes an accessible name.

**Architecture:** Follow Bootstrap navbar canonical structure(brand + toggler + collapse). Define a desktop-narrow strategy(breakpoint and overflow), then enforce it via a UI standard + static guard to prevent regressions.

**Tech Stack:** Jinja2 templates, Bootstrap 5(bundled JS), custom CSS.

---

## 1. 动机与范围

### 1.1 动机

- 审计报告(P1-04)指出: Navbar 在 <992px 会折叠, 但缺少 `navbar-toggler`, 导致导航不可达.
- 当前实现中存在 `#navbarNav` 的 `collapse navbar-collapse`, 但无任何触发器可以展开(桌面分屏场景会踩坑).

### 1.2 范围

In-scope:

- `app/templates/base.html` Navbar DOM 结构补齐 `navbar-toggler`.
- 如主题覆盖导致 toggler icon 不可见, 增加最小 CSS 修复(不改变视觉体系).

Out-of-scope(本次不做):

- 重做导航信息架构(菜单分组/命名/权限体系).
- 引入全量 e2e/可视化回归框架(可在长期阶段评估).

---

## 2. 不变约束(行为/性能门槛)

- 行为不变: 不调整各导航链接的路径与权限逻辑, 不改变 dropdown 行为.
- 可用性提升: 在 <992px 时, 导航必须可打开并可访问全部菜单项.
- 性能门槛: 不新增运行时依赖, 继续使用现有 Bootstrap bundle.

---

## 3. 可选方案(2-3 个)与推荐

### Option A(推荐, 中期落地): 补齐 `navbar-toggler`, 保持 `navbar-expand-lg`

做法:

- 在 `navbar-brand` 与 `#navbarNav` 之间新增 `<button class="navbar-toggler" ...>`.
- 绑定 `data-bs-toggle="collapse"` 与 `data-bs-target="#navbarNav"`.
- 补齐 `aria-controls="navbarNav" aria-expanded="false" aria-label="切换导航"`.
- 使用 `<span class="navbar-toggler-icon" aria-hidden="true"></span>`(或 Font Awesome icon)保证视觉可见.

优点:

- 最小改动, 与 Bootstrap 习惯一致, 风险低.
- 直接解决"导航不可达"的根问题.

缺点:

- <992px 时导航进入折叠态, 桌面窄宽度下需要额外点击一次才能访问菜单(但可用性显著优于当前不可达).

### Option B(补充策略): 调整折叠断点以降低桌面分屏折叠概率

做法:

- 将 `navbar-expand-lg` 调整为 `navbar-expand-md`(或其他断点), 使 900px 等桌面分屏宽度仍保持展开.

优点:

- 桌面分屏时更接近"桌面体验", 减少折叠带来的额外交互.

缺点:

- 可能引入单行溢出/换行, 需要配套 overflow 策略与视觉验收.

### Option C(长期治理): Desktop narrow "优先级 + more 菜单"或 overflow 策略

做法:

- 在桌面窄宽度下, 将低频入口折叠到 "更多" dropdown, 保持主要入口可见.
- 或提供水平滚动/overflow 的视觉策略, 避免主导航完全折叠.

优点:

- 兼顾桌面窄宽度效率与可达性, 形成可持续演进的导航策略.

缺点:

- 需要产品/设计决策与更多回归验证, 不适合当作中期的最小修复.

推荐结论:

- Phase 1 采用 Option A 保证可达性.
- Phase 2 评估是否引入 Option B/C 作为桌面窄宽度的体验增强.

---

## 4. 分阶段计划(中期 + 长期)

### Phase 1(中期): 可达性修复 + 桌面分屏回归(建议 0.5-2 天)

验收口径:

- 在宽度约 900px(桌面分屏)下, `navbar-toggler` 可见且可点击/可键盘触发.
- 点击/触发后, `#navbarNav` 展开并可访问全部一级菜单与 dropdown.
- `aria-expanded` 状态随展开/收起更新, 读屏可理解其用途.

实施步骤:

1. 在 `app/templates/base.html` 增加 `navbar-toggler` 并正确关联 `#navbarNav`.
2. 如 toggler icon 不可见, 增加最小 CSS 修复(优先使用 Bootstrap 默认 `navbar-toggler-icon`).
3. 手工回归:
   - 桌面宽度 900px, 展开/收起正常.
   - 键盘 Tab 可聚焦 toggler, Enter/Space 可展开.
   - dropdown 在展开态下可打开并可达.

### Phase 2(长期): 规范化 + 门禁 + 策略沉淀(建议 1-2 周)

验收口径:

- UI 标准中明确 Navbar 的响应式结构与 a11y 要求(MUST/SHOULD/MAY).
- 新增静态门禁脚本, 防止再次出现"有 collapse 无 toggler".
- PR 模板包含导航回归点(桌面窄宽度 900px).

实施步骤:

1. 新增 UI 标准:
   - `docs/standards/ui/navbar-responsive-guidelines.md`
   - 内容包含: canonical DOM 结构, aria 约束, 断点策略建议, 正反例, 手工回归清单.
2. 新增门禁脚本:
   - `scripts/ci/navbar-toggler-guard.sh`
   - 扫描 `app/templates/base.html`(或 `app/templates/**`)中:
     - 存在 `collapse navbar-collapse` 且包含 `id="navbarNav"` 时
     - 必须存在 `.navbar-toggler` 且 `data-bs-target="#navbarNav"` 且 `aria-controls="navbarNav"` 且存在 `aria-label`.
3. 更新入口与协作流程:
   - `docs/standards/ui/README.md` 增加索引.
   - `.github/pull_request_template.md` 增加桌面分屏回归项.
4. 评估体验增强(Option B/C):
   - 需要明确目标: 保持展开 vs 保持单行 vs 优先级菜单.

---

## 5. 风险与回滚

风险:

- 主题覆盖导致 toggler icon 对比度不足或不可见(需要 CSS 兜底).
- DOM 结构调整可能影响现有 navbar 自定义布局(`navbar-container` flex).

回滚:

- 若出现布局回归, 可先保留 toggler 并调整其位置/样式, 不回退到"无 toggler"状态.
- 若 Phase 2 门禁误报, 先放宽规则(允许 `aria-labelledby`)再逐步收紧.

---

## 6. 验证与门禁

手工验证:

- 桌面分屏宽度约 900px: toggler 可见, 可展开, 菜单可达.
- 键盘: Tab -> toggler -> Enter/Space 展开, 再 Tab 遍历导航项与用户菜单.

静态门禁(长期):

- `scripts/ci/navbar-toggler-guard.sh`

---

## 7. 清理计划

- 将 Navbar 响应式结构写入标准后, 后续所有导航相关改动必须引用标准并通过门禁.
- 若后续决定调整断点或引入优先级菜单, 将方案沉淀为独立变更文档并记录到 progress.

---

## 8. Open Questions(需要确认)

1. 是否需要调整折叠断点(保留 `navbar-expand-lg` vs 改为 `navbar-expand-md`)?
2. 用户菜单是否需要在折叠态下保持更易达(例如放到 brand 旁边而不是进入 collapse)?
