# Status Terminology Consistency Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/templates/**`, `app/static/js/**`, `docs/standards/terminology.md`, `docs/standards/ui/**`, `scripts/ci/**`, `.github/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P2-06), `docs/standards/terminology.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** For the same "status meaning", UI uses one canonical wording. Remove drift like "禁用" vs "停用" that increases cognitive load and causes users to infer non-existent differences.

**Architecture:** Define a canonical terminology map for common status states, then migrate UI strings to it. Prevent regressions via a lightweight guard and a PR checklist item.

**Tech Stack:** Jinja templates, vanilla JS modules, ripgrep-based CI guards.

---

## 1. 动机与范围

### 1.1 动机

审计报告(P2-06)指出: UI 存在术语漂移, 同一语义状态在不同页面使用不同词, 例如:

- instance status: "禁用"(见 `app/static/js/modules/views/instances/list.js`)
- tag status: "停用标签"(见 `app/templates/tags/index.html`)

影响:

- 用户会推断"禁用"与"停用"是否代表不同机制(权限/软删/不可用), 增加认知负担与误解成本.
- 支持与排障成本增加: 复述问题与检索日志/文档时更难对齐关键词.

### 1.2 范围

In-scope:

- UI 可见文案中的状态词与动作词(按钮, badge, 表格列, 统计卡片, toast).
- 聚焦 "is_active/active/inactive" 一类状态的统一表达, 并扩展到相关页面的统计文案.

Out-of-scope(本次不做):

- 技术语义的 "禁用按钮/disabled" 等描述(属于实现层术语, 不等同于资源状态).
- 建立完整 i18n 体系(仅先统一中文用词).

---

## 2. 不变约束(行为/契约/兼容)

- 行为不变: 仅调整 UI 文案, 不改变状态含义, 不改变接口字段, 不改变权限与业务逻辑.
- 一致性优先: 同一页面内不得混用同义词, 同一语义状态全站优先保持同一对词.
- 可回滚: 变更应按页面/模块拆分 PR, 避免一次性全站替换造成回归难定位.

---

## 3. 方案选项(2-3 个)与推荐

### Option A(中期, 推荐): 选择一组 canonical 状态词, 全站替换

做法:

- 明确 "active/inactive" 的 canonical 词对(例如 "启用/停用" 或 "正常/停用").
- 将现有 UI 中的漂移词统一替换为 canonical 词对.

优点:

- 见效快, 成本低.
- 对用户心智模型提升明显.

缺点:

- 若缺少标准与门禁, 未来仍可能回归.

### Option B(长期): 术语表 + 状态词表 + 统一 helper

做法:

- 在 `docs/standards/terminology.md` 增加 "状态用词" 小节, 固化 canonical 词表与适用范围.
- 在前端增加 `UI.Terms` 或 `UI.resolveStatusText(...)` helper, 页面不再手写状态词.

优点:

- 从源头减少重复与漂移.
- 便于后续扩展到多语言或 UI 统一改版.

缺点:

- 需要迁移调用点, 需要逐步落地.

### Option C(长期): 门禁与字典扫描

做法:

- 增加 `scripts/ci/ui-terminology-guard.sh`, 扫描特定目录中是否出现 "deprecated 词"(例如某一组不再允许的状态词).
- 采用 baseline + 逐步清零策略, 避免一次性阻断存量.

优点:

- 可防止回归, 治理可持续.

缺点:

- 需要精确限定扫描范围, 避免误伤实现层的 "禁用按钮" 等技术描述.

推荐结论:

- Phase 1 先落地 Option A(统一文案).
- Phase 2 结合 Option B/C: 标准化 + helper + 门禁, 让一致性可持续.

---

## 4. 分阶段计划(中期 + 长期)

### Phase 1(中期, 1-2 周): 统一 "active/inactive" 状态词并清理漂移点

验收口径:

- 实例/标签/凭据/用户等页面对 "active/inactive" 使用同一组词.
- 同一页面内不再出现 "禁用/停用" 混用.

建议实施步骤:

1. 决策 canonical 词对: `启用/停用`.
2. 替换证据点:
   - `app/static/js/modules/views/instances/list.js`: status 文案对齐.
   - `app/templates/tags/index.html`: 统计卡片/状态文案对齐.
3. 扩展清理:
   - `app/templates/instances/statistics.html`, `app/templates/accounts/statistics.html` 等统计文案对齐.
   - `app/static/js/modules/views/credentials/list.js`, `app/static/js/modules/views/auth/list.js`, `app/static/js/modules/views/tags/index.js` 等已存在 "启用/停用" 的页面, 确认与 canonical 一致.
4. 手工回归:
   - 关键页面: 实例管理, 标签管理, 凭据管理, 用户管理.
   - 口径: status badge, action button, toast 文案一致.

### Phase 2(长期, 2-4 周): 标准化 + 防回归机制

验收口径:

- `docs/standards/terminology.md` 增加 "状态用词" 条目, 明确:
  - active/inactive 的 canonical 词对
  - 例外场景(例如 "锁定", "暂停", "删除/回收站")
- 新增统一 helper 或至少在关键组件内集中生成状态词, 减少手写.
- 新增门禁或 checklist 防止回归.

建议实施步骤:

1. 更新术语标准:
   - `docs/standards/terminology.md` 增加 "状态用词" 小节, 并给出正反例.
2. 引入统一 helper(建议最小化):
   - `app/static/js/modules/ui/terms.js`:
     - `resolveActiveStatusText(isActive)` -> returns canonical word
     - 可选: `resolveActiveActionText(isActive)` -> for buttons
3. 门禁与协作入口:
   - 增加 `scripts/ci/ui-terminology-guard.sh`(只扫描 UI 文案目录, 且只对已约定 deprecated 词生效).
   - 更新 `.github/pull_request_template.md` 增加 "术语一致性" 自检项(引用 `docs/standards/terminology.md`).

---

## 5. 风险与回滚

风险:

- "禁用" 在代码中同时用于技术语义(按钮 disabled), 门禁需要避免误伤.
- 部分页面的状态语义不完全等价(例如 scheduler 的 "暂停/启用" 与 is_active 不同), 需要明确例外词表.

回滚:

- 文案替换可按页面回退, 但必须保持该页面内用词一致(禁止回到混用状态).

---

## 6. 验证与门禁

静态检查(建议命令):

- `rg -n \"禁用|停用\" app/templates app/static/js/modules/views`

手工验证(最低覆盖):

- 实例管理列表: 状态列与操作文案一致.
- 标签管理页: 统计卡片与状态列一致.

---

## 7. 清理计划

- Phase 1 完成后: 证据点相关页面不再出现漂移词.
- Phase 2 完成后: 新增页面不应再手写状态词, 或手写时必须遵守术语表与门禁.

---

## 8. Open Questions(需要确认)

1. canonical 词对选择: 已确认使用 `启用/停用`.
2. 对 scheduler/job 这类运行态, 是否统一使用 "暂停/启用" 并禁止出现 "禁用任务" 以避免与 active/inactive 混用?
