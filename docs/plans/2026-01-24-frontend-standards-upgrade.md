# Frontend Standards Upgrade (Flask + Jinja) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 将 `docs/Obsidian/standards/ui/**` 升级为一套“SSR(Jinja) + Progressive Enhancement + 少量模块化 JS”的前端最佳实践（参考 Vercel React Best Practices 的核心思想：少发 JS、避免瀑布、以可维护/可审查为先），并给出可执行的迁移清单，方便后续逐页改造模板与静态资源。

**Architecture:** SSR 优先（Jinja 输出首屏/表格/表单），前端只做增强（交互、校验、异步局部刷新）。资源加载遵循“全站最小核心 + 页面按需加载”。JS 延续现有 `Page Entry -> Views -> Stores -> Services` 分层，减少全局依赖与重复实现。

**Tech Stack:** Flask + Jinja2、Bootstrap、Vanilla JS（IIFE/UMD 风格 + `page_id` 入口）、ESLint、现有 vendor 封装（`httpU/DOMHelpers/timeUtils/NumberFormat/EventBus/UI` 等）。

---

## Phase 0: 基线与对照（1 次性）

### Task 0: 提炼 Vercel Best Practices 的“可迁移核心”

**Files:**
- Create: `docs/Obsidian/standards/ui/vercel-react-best-practices-mapping.md`

**Step 1: 拉取并阅读引用文档**

Run: `curl -fsSI https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices | head -n 1`
Expected: 包含 `200`

**Step 2: 写“概念映射表”（React/Next -> Flask/Jinja）**

- 输出一页表格：原则、在 React 的落点、在 Jinja 的等价落点、适用范围/反例。

**Step 3: 设定本项目“性能预算/目标”（可度量）**

- 目标示例：`base.html` 全站必需脚本不超过 N 个、非必需 vendor 必须按页引入；首屏不依赖 JS 才能看见关键数据；页面脚本不得产生串行瀑布请求（除非有依赖关系并说明）。

**Step 4: Commit**

Run:
```bash
git add docs/Obsidian/standards/ui/vercel-react-best-practices-mapping.md
git commit -m "docs: map vercel react best practices to flask+jinja ui"
```

### Task 1: 建立“资源与入口”现状清单（为标准落地提供事实）

**Files:**
- Create: `docs/Obsidian/standards/ui/resource-loading-inventory.md`

**Step 1: 统计 `base.html` 引入的 CSS/JS 列表并分组**

Run: `rg -n "<link |<script " app/templates/base.html`
Expected: 输出 link/script 列表

**Step 2: 统计页面级 `extra_js/extra_css` 使用现状**

Run: `rg -n "\\{%\\s*block\\s+extra_(js|css)\\s*%\\}" -S app/templates`
Expected: 输出使用位置

**Step 3: 产出“核心资源 vs 页面资源”的初版建议表**

- 以“是否全站都需要/是否可延后加载/是否仅特定页面使用”为维度。

**Step 4: Commit**

Run:
```bash
git add docs/Obsidian/standards/ui/resource-loading-inventory.md
git commit -m "docs: add ui resource loading inventory"
```

---

## Phase 1: 性能标准（少发 JS + 按需加载 + 避免瀑布）

### Task 2: 新增“SSR + Progressive Enhancement 性能标准”

**Files:**
- Create: `docs/Obsidian/standards/ui/performance-standards.md`
- Modify: `docs/Obsidian/standards/ui/README.md`

**Step 1: 写标准文档骨架（MUST/SHOULD/MAY + 正反例 + 门禁/自查）**

文档至少包含：
- 资源加载：`base.html` 只放“全站必需”资源；其余必须在页面 `extra_js/extra_css` 按需引入
- 交互增强：功能必须“无 JS 可用仍可完成核心操作”（允许体验降级，但不能不可用）
- 异步请求：禁止串行瀑布（能并行就并行）；必须缓存/复用页面数据，避免重复请求
- 表格/列表：优先 SSR 渲染首屏，必要时再用 JS 做分页/筛选增强

**Step 2: 把新文档加入 UI 标准索引**

- 在 `docs/Obsidian/standards/ui/README.md` 的“关键入口”里新增链接。

**Step 3: 自查命令补齐**

- 至少提供：定位 `base.html` 全站引入、定位重复引入、定位页面脚本里的串行请求（以 `await` 链/then 链为启发式）。

**Step 4: Commit**

Run:
```bash
git add docs/Obsidian/standards/ui/performance-standards.md docs/Obsidian/standards/ui/README.md
git commit -m "docs: add ui performance standards for ssr + progressive enhancement"
```

### Task 3: 把“按需加载”规则融入现有 vendor 标准与 Page Entry 标准

**Files:**
- Modify: `docs/Obsidian/standards/ui/vendor-library-usage-standards.md`
- Modify: `docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md`

**Step 1: vendor 标准补齐“引入策略”**

- 明确：新增 vendor 时必须回答“是否全站必需”；默认按页引入；禁止把 page-only vendor 放进 `base.html`。

**Step 2: Page Entry 标准补齐“数据/资源下发契约”**

- 强化：page entry 只做 wiring；页面脚本必须支持缺失依赖时快速失败且不半初始化。

**Step 3: Commit**

Run:
```bash
git add docs/Obsidian/standards/ui/vendor-library-usage-standards.md docs/Obsidian/standards/ui/layer/page-entry-layer-standards.md
git commit -m "docs: enforce per-page loading and ssr-first entry wiring"
```

---

## Phase 2: 可维护性标准（模板组件化 + 分层推进 + 统一数据下发）

### Task 4: 新增“模板组件化/复用”标准（Jinja 视角的 maintainability）

**Files:**
- Create: `docs/Obsidian/standards/ui/jinja-template-composition-standards.md`
- Modify: `docs/Obsidian/standards/ui/README.md`

**Step 1: 明确模板结构与复用策略**

- 页面：`extends base.html` + `page_id` + 按需 `extra_css/extra_js`
- 可复用 UI：优先 `templates/components/ui/*.html` 宏/组件；禁止在页面里复制粘贴大段卡片/表格结构
- 数据下发：页面使用“单一根节点 dataset 契约”（引用 Page Entry 标准），禁止散落多处 `data-*` 与隐式全局

**Step 2: 增加“何时抽组件/何时别抽”的边界（YAGNI）**

- 以“复用次数/变体复杂度/是否跨页面”为判断标准，提供正反例。

**Step 3: 在 UI 标准索引加入链接**

**Step 4: Commit**

Run:
```bash
git add docs/Obsidian/standards/ui/jinja-template-composition-standards.md docs/Obsidian/standards/ui/README.md
git commit -m "docs: add jinja template composition standards"
```

### Task 5: 收敛 JS 分层的“落地检查清单”

**Files:**
- Modify: `docs/Obsidian/standards/ui/javascript-module-standards.md`
- Modify: `docs/Obsidian/standards/ui/layer/views-layer-standards.md`
- Modify: `docs/Obsidian/standards/ui/layer/stores-layer-standards.md`
- Modify: `docs/Obsidian/standards/ui/layer/services-layer-standards.md`

**Step 1: 给每层补“页面改造时的最小套路”**

- Service：只做 API 封装/参数序列化/错误转换；不碰 DOM
- Store：状态 + actions + emitter；不碰 `window.httpU`（通过注入）
- View：DOM 渲染 + 事件绑定；业务动作通过 store actions
- Page Entry：读 dataset + 组装依赖 + mount + 首屏 load

**Step 2: 给出迁移示例（短）**

- 一个“旧页面脚本 -> 4 层拆分”的最小示例（只写结构，不引入构建工具）。

**Step 3: Commit**

Run:
```bash
git add docs/Obsidian/standards/ui/javascript-module-standards.md \
  docs/Obsidian/standards/ui/layer/views-layer-standards.md \
  docs/Obsidian/standards/ui/layer/stores-layer-standards.md \
  docs/Obsidian/standards/ui/layer/services-layer-standards.md
git commit -m "docs: add js layering migration checklists"
```

---

## Phase 3: 一致性与可访问性（统一交互、按钮层级、可访问名称、可键盘操作）

### Task 6: 新增“可访问性(A11y) 基线”标准

**Files:**
- Create: `docs/Obsidian/standards/ui/accessibility-baseline-standards.md`
- Modify: `docs/Obsidian/standards/ui/README.md`
- Modify (可选): `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md`
- Modify (可选): `docs/Obsidian/standards/ui/button-hierarchy-guidelines.md`

**Step 1: 定义 MUST 的 A11y 基线**

- 图标按钮必须有可访问名称（`aria-label` 等）
- Modal：可聚焦、可 ESC 关闭、打开/关闭焦点管理（引用现有 `UI.createModal` 规则）
- 表单：`label for`、错误提示与输入关联、`required` 与校验提示一致
- 键盘：关键操作必须可 Tab 到达并触发（不依赖仅 mouse）

**Step 2: 统一“状态反馈”口径**

- loading/disabled、danger 二次确认、toast/alert 的使用边界（引用既有标准并补齐交叉链接）。

**Step 3: 在 UI 标准索引加入链接**

**Step 4: Commit**

Run:
```bash
git add docs/Obsidian/standards/ui/accessibility-baseline-standards.md docs/Obsidian/standards/ui/README.md
git commit -m "docs: add ui accessibility baseline standards"
```

---

## Deliverables（交付物）

- SSOT 标准文档新增：性能 / 模板组件化 / A11y 基线 / Vercel 映射 / 资源盘点
- 现有标准文档补强：vendor 使用、page entry、modules 分层落地清单、UI 标准索引
- 给页面改造的“执行清单”：用户可按清单逐页迁移，不需要一次性重写
