# btn-icon Accessible Name(aria-label) Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/templates/**`, `app/static/js/**`, `scripts/ci/**`, `.github/**`, `docs/standards/ui/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P1-03), `docs/standards/ui/close-button-accessible-name-guidelines.md`, `scripts/ci/btn-close-aria-guard.sh`, `docs/standards/halfwidth-character-standards.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** All icon-only action buttons(`.btn-icon`) expose a stable accessible name via `aria-label`(or `aria-labelledby`). Decorative icons use `aria-hidden="true"`. `title` becomes optional UX hint, not the only source of meaning.

**Architecture:** Provide a single source of truth for icon button rendering in both template and JS layers, then enforce via a repo-level guard + standards checklist to prevent regressions.

**Tech Stack:** Jinja2 templates, Bootstrap button styles, Font Awesome, vanilla JS modules, ripgrep-based CI guard scripts.

---

## 1. 动机与范围

### 1.1 动机

- 审计报告(P1-03)指出: 多数 `.btn-icon` 仅依赖 `title`, 缺失 `aria-label`, 导致读屏与键盘体验不达标.
- 代码库内存在局部正确实现(例如 `app/static/js/modules/views/admin/scheduler/index.js` 已同时设置 `title` + `aria-label`, 且 `<i>` 使用 `aria-hidden="true"`), 说明问题根因是缺少统一组件约束与门禁, 而不是实现困难.

### 1.2 范围

In-scope:

- 模板内 icon-only 按钮/链接: `app/templates/**` 中的 `.btn-icon`.
- JS 动态生成的 icon-only 按钮/链接: `app/static/js/**` 中的 formatter/renderer/template string.
- 非 Bootstrap 的 icon-only 按钮(例如 `.btn-icon--sm`).

Out-of-scope(本次不做):

- 建立完整的 i18n 体系(仅要求 aria-label 与当前 UI 语言一致).
- 图标体系从 Font Awesome 迁移到 SVG.
- 将所有 icon-only 交互替换为带文字按钮(属于 UI 改版, 不是本次 refactor 的行为不变目标).

### 1.3 目标与非目标

目标:

- 任何 icon-only 交互, 不依赖 `title` 也能被读屏正确理解.
- 统一产出方式, 避免"手写属性"导致的漏标与回归.
- 引入可自动化门禁, 把问题从"整改一次"变成"不再发生".

非目标:

- 在本 refactor 内调整按钮视觉层级/颜色/尺寸(除非为满足可访问性门槛必须调整).
- 在本 refactor 内重构列表组件(Grid.js 迁移等)或页面信息架构.

---

## 2. 不变约束(行为/契约/性能门槛)

- 行为不变: 仅补齐可访问属性与统一生成方式, 不改变点击行为, 不更改 API 调用, 不更改路由跳转.
- DOM hook 不变: 既有 `data-action`, `data-*-id` 等事件委托选择器保持兼容.
- 视觉不变: `.btn-icon` 的样式与布局不调整, `title` 作为 tooltip 的既有行为保持可用(但不再是唯一语义来源).
- 性能门槛: 不引入重型运行时依赖, 不增加页面首屏 JS 体积(允许新增极小的 helper).

---

## 3. 分层边界(依赖方向/禁止项)

### 3.1 统一规则(对所有 icon-only 按钮成立)

- MUST: 提供可访问名称, 优先使用 `aria-label`, 或使用 `aria-labelledby` 引用可见/不可见文本.
- MUST: 装饰性图标使用 `aria-hidden="true"`.
- SHOULD: `title` 与 `aria-label` 保持一致(默认同值), 避免 tooltip 与读屏描述割裂.
- MUST NOT: 仅依赖 `title` 作为按钮含义来源.

### 3.2 模板层(Jinja2)边界

- 新增/统一模板宏: `app/templates/components/ui/macros.html` 增加 `btn_icon(...)`.
- 模板调用方禁止手写 icon-only 按钮的 `aria-label` 细节, 改为调用宏输出.

建议宏的最小参数口径(可按实际落地调整):

- `label`: 必填, 同时用于 `aria-label` 与默认 `title`.
- `icon_class`: 必填, 例如 `fas fa-eye`.
- `variant_class`: 可选, 默认 `btn-outline-secondary`.
- `size_class`: 可选, 例如 `btn-sm`.
- `href`: 可选, 存在则输出 `<a ...>`, 否则输出 `<button type="button" ...>`.
- `extra_attrs`: 可选, 用于透传 `data-*` 等属性.

### 3.3 JS 层(vanilla modules)边界

- 新增 UI helper: `app/static/js/modules/ui/icon-button.js`(或等价位置), 负责生成 icon-only `<button>/<a>` 的 HTML string.
- JS 业务模块禁止手写 icon-only markup 的 `aria-label`/`aria-hidden` 细节, 改为调用 helper.
- 对于必须手写的遗留模块, 至少满足 3.1 的统一规则, 并纳入后续清理列表.

建议 helper 的最小 API 口径(可按实际落地调整):

- `renderIconButtonHtml({ tag, label, iconClass, title, className, attrs })`.
- 默认策略: `title` 缺省时取 `label`, 并始终输出 `aria-label=label`.

---

## 4. 分阶段计划(中期 + 长期并行推进)

> 说明: P1-03 的短期止血(全站补齐 aria-label)可以作为 Phase 1 的子集完成, 但本计划重点是中期与长期治理, 防止回归.

### Phase 1(中期): 统一产出能力 + 批量迁移(建议 1-2 周)

验收口径:

- `app/templates/**` 与 `app/static/js/**` 中, 所有 `.btn-icon` 均具备 `aria-label` 或 `aria-labelledby`.
- 所有 icon-only `<i>` 均具备 `aria-hidden="true"`.
- 关键样例页通过键盘 Tab 与读屏抽检(见第 6 节).

实施步骤(建议按 PR 拆分):

1. 新增模板宏 `btn_icon(...)`, 并在少量模板页先行替换, 验证样式与事件绑定不回归.
2. 新增 JS helper `renderIconButtonHtml(...)`, 并在一个 Grid.js 列表模块先行替换(例如 credentials), 验证 formatter 输出不回归.
3. 全站迁移剩余 `.btn-icon`:
   - 模板: 实例/账户统计, 历史日志详情, 历史会话详情等.
   - JS: instances list, credentials list, tags index, sessions list, account classification 等.

### Phase 2(长期): 规范化 + 自动化门禁 + 回归机制(建议 2-4 周, 可与 Phase 1 并行启动)

验收口径:

- 新增门禁脚本通过, 且在 CI 作为必跑项(禁止回归).
- UI 标准文档具备明确 MUST/SHOULD/MAY, 包含正反例, 并被 UI README 收录.
- PR 模板包含 a11y checklist, 至少覆盖 icon-only button accessible name.

实施步骤:

1. 新增静态门禁脚本: `scripts/ci/btn-icon-aria-guard.sh`.
   - 扫描目标: `app/templates`, `app/static/js`.
   - 规则: 发现 `.btn-icon` 的 `<button>`/`<a>` 缺失 `aria-label` 且缺失 `aria-labelledby` 时直接 fail.
   - 参考实现: `scripts/ci/btn-close-aria-guard.sh`.
2. 新增 UI 标准: `docs/standards/ui/icon-button-accessible-name-guidelines.md`.
   - 约束 aria-label 使用中文, 与 UI 文案一致, 禁止英文混用(对齐 close button 规则).
   - 明确 title 的定位: tooltip 辅助, 不是可访问名称来源.
3. 更新入口与协作流程:
   - `docs/standards/ui/README.md` 增加索引.
   - `.github/pull_request_template.md` 增加 a11y 检查项(最低覆盖 btn-icon).
4. 可选增强(后续迭代):
   - 引入 `axe` 的自动化扫描到 e2e/回归流程(需要先确认现有测试栈与运行环境).

---

## 5. 风险与回滚

### 5.1 风险

- 门禁误报: 少数 `.btn-icon` 可能通过 `aria-labelledby` 或 `.visually-hidden` 文本提供名称, 需要在门禁规则中明确允许口径.
- 文案漂移: 不同模块对同一动作使用不同 aria-label(例如 "查看详情" vs "详情"), 需要在标准中给出推荐词表.
- 事件委托回归: 迁移到宏/helper 时可能遗漏 `data-action` 或 `data-*-id`, 需要在 Phase 1 的抽检页重点覆盖.

### 5.2 回滚策略

- 本 refactor 主要是属性与渲染方式调整, 回滚策略为逐 PR 回退对应提交即可.
- 门禁脚本可以先以 warn 模式落地, 再切换为 fail(如团队需要缓冲期).

---

## 6. 验证与门禁

### 6.1 静态检查

- 自查扫描(迁移前后对比):
  - `rg -n \"\\bbtn-icon\\b\" app/templates app/static/js`
  - `rg -n \"\\bbtn-icon\\b\" app/templates app/static/js | rg -n \"aria-label|aria-labelledby\"`

### 6.2 手工回归(键盘 + 读屏)

最低抽检路径(覆盖审计证据点):

- instances list: 查看详情, 测试连接.
- credentials list: 编辑, 删除.
- history sessions detail: 复制会话 ID.

抽检口径:

- 键盘 Tab 聚焦到 icon-only 按钮时, 读屏可读出动作含义, 且与视觉 tooltip 一致.
- 同一列多个 icon-only 按钮可被区分, 不出现"按钮, 按钮"无含义的朗读.

### 6.3 自动化门禁(长期)

- 新增 `scripts/ci/btn-icon-aria-guard.sh`, 并纳入 CI/本地检查链路(例如 make target 或 CI workflow).

---

## 7. 清理计划

- Phase 1 完成后: 删除或降级所有"从 title 兜底补 aria-label"的临时代码路径(如存在), 使规则更清晰.
- Phase 2 完成后: 将手写 icon-only markup 的存量点收敛到宏/helper, 仅保留少数经过 review 的例外.

---

## 8. Open Questions(需要确认)

1. aria-label 词表是否需要统一沉淀为常量(例如 JS 内 `UI.A11yLabels`), 还是由各模块按标准自行选择.
2. 对于 row-level 动作, aria-label 是否需要包含上下文(例如 "删除凭据: <name>"), 以提升读屏区分度.
