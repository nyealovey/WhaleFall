# Grid Empty State CTA Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/static/js/common/grid-wrapper.js`, `app/static/js/modules/ui/filter-card.js`, `app/static/js/modules/views/**`, `docs/standards/ui/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P2-02), `docs/standards/ui/gridjs-migration-standard.md`, `docs/standards/halfwidth-character-standards.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Grid empty states are actionable. When the grid has no results, the UI provides a next step (clear filters, create entry, or navigate to the right place) instead of only showing "未找到记录".

**Architecture:** Extend `GridWrapper` to expose empty state signals and allow per-page empty state config. Integrate with `FilterCard` so "清除筛选" works reliably. Then standardize copy and patterns via UI standards + optional guard.

**Tech Stack:** Grid.js + `GridWrapper`, FilterCard, Bootstrap, vanilla JS modules.

---

## 1. 动机与范围

### 1.1 动机

当前 `GridWrapper` 的默认空态文案为 `noRecordsFound: "未找到记录"`(`app/static/js/common/grid-wrapper.js`). 空态过于终止式, 用户不知道下一步应该做什么(清除筛选? 创建数据? 调整时间范围?), 导致反复试错与学习成本上升.

审计报告(P2-02)建议: 空态应提供 CTA, 至少包含 "清除筛选" 的快速入口.

### 1.2 范围

In-scope:

- Grid.js 列表页空态: no results / no data 的可行动提示与 CTA.
- 与 FilterCard 联动: 空结果时提供一键清除筛选并触发刷新.
- 逐页支持可选的 "创建入口" CTA(由页面决定链接与权限).

Out-of-scope(本次不做):

- 重写 Grid.js 渲染机制或替换表格组件.
- 引入完整 e2e 回归框架(长期可评估).

---

## 2. 不变约束(行为/性能门槛)

- 行为不变: 列表 API 请求/分页/排序/筛选逻辑保持不变, 仅增强 empty state 的 UI 引导.
- 性能门槛: 不引入重型依赖, 空态渲染不应增加额外请求.
- 兼容约束: 存量页面可逐步迁移, 不要求一次性全站改完.

---

## 3. 术语与空态分类(建议口径)

为避免"同一个空态文案覆盖所有情况", 推荐区分以下场景:

1. No results(有筛选, 结果为空): "未找到符合当前筛选条件的记录" + CTA: 清除筛选.
2. No data(无筛选, 数据为空): "暂无数据" + CTA: 创建入口/查看指引(按页面定义).
3. Error(加载失败): "加载数据失败" + CTA: 重试(可选) + 查看详情(可选).

本变更优先解决 #1, 并为 #2/#3 提供可扩展接口.

---

## 4. 方案选项(2-3 个)与推荐

### Option A(低成本, 中期可用): 页面级补丁

做法:

- 各列表页在拿到 `items=[]` 时, 在 FilterCard 下方插入一行提示 + "清除筛选"按钮.

优点:

- 落地快, 无需修改 GridWrapper.

缺点:

- 逻辑分散, 文案与样式难以统一, 长期容易回归.

### Option B(推荐, 中期落地): GridWrapper 支持 empty state hook + 可注入 CTA

做法:

- 在 `GridWrapper` 中新增可选配置:
  - `emptyState`: `{ mode, message, actions, filterCard }`
  - `onEmptyStateChange`: `(state) => void`
- `GridWrapper` 包装 `server.then/total`:
  - 解析响应中的 `items` 数量(或允许页面提供 `getItemsCount(response)`).
  - 当 `itemsCount === 0` 时触发 empty state 渲染或回调.
- 提供默认 empty state renderer(轻量 DOM), 支持:
  - 当存在 active filters -> 显示 "清除筛选" CTA
  - 当存在 `createUrl` -> 显示 "创建" CTA

优点:

- 逻辑集中, 可复用, 更容易统一文案与样式.

缺点:

- 需要谨慎处理不同页面的 response shape(支持页面自定义 extractor).

### Option C(长期治理): EmptyState 组件化 + UI 标准 + 门禁

做法:

- 新增 `UI.EmptyState`(或等价模块), 统一渲染 "空结果/无数据/错误/无权限".
- 将空态模板与 CTA 规则写入 UI 标准, 并在 PR 模板与门禁中约束.

优点:

- 形成一致的可行动空态体验, 减少长期漂移.

缺点:

- 需要更完整的组件 API 设计与迁移投入.

推荐结论:

- Phase 1 采用 Option B 解决主问题并建立可扩展接口.
- Phase 2 逐步升级到 Option C, 沉淀标准与门禁.

---

## 5. 分阶段计划(中期 + 长期)

### Phase 1(中期, 1-2 周): 统一能力 + 覆盖高频列表页

验收口径:

- 当筛选导致空结果时, 页面不再只有 "未找到记录", 而是出现 "清除筛选" CTA.
- 点击 "清除筛选" 后, 过滤条件被重置并触发刷新, 结果可恢复.
- 至少覆盖 2-3 个高频列表页(例如 instances/accounts/databases ledgers).

实施步骤(建议按 PR 拆分):

1. `GridWrapper` 增强:
   - 支持 `emptyState` 配置与渲染占位容器(例如 `data-grid-empty-state`).
   - 支持 `getItemsCount(response)` 或 `extractItems(response)` 以兼容不同接口 shape.
2. FilterCard 联动:
   - 为 FilterCard 增加 `clear()` 或提供一个最小 "reset + submit" helper, 供 empty state CTA 调用.
3. 页面迁移:
   - 为各目标列表页补充 empty state 配置:
     - 文案: "未找到符合当前筛选条件的记录"
     - CTA: "清除筛选"(绑定 FilterCard 清空)
     - 可选 CTA: "创建"(按页面能力提供)
4. 手工回归:
   - 设置筛选为无结果 -> 显示 CTA -> 清除筛选 -> 结果恢复.

### Phase 2(长期, 2-4 周): 空态标准化 + 可扩展模板库 + 门禁

验收口径:

- UI 标准中定义空态类型与 CTA 规则(至少覆盖 grid list).
- 新增空态相关门禁(或 code review 规则)防止新增列表页回到终止式空态.

实施步骤:

1. 新增 UI 标准:
   - `docs/standards/ui/empty-state-guidelines.md`
   - 内容包含:
     - 空态分类(no results/no data/error/no permission)
     - 推荐文案与 CTA
     - 何时必须提供 "清除筛选" 与 "创建入口"
2. 更新 Grid.js 标准入口:
   - 在 `docs/standards/ui/gridjs-migration-standard.md` 的 checklist 中补充 empty state 要求.
3. 门禁(可选, 迭代推进):
   - 静态扫描:
     - 检测 `GridWrapper` 使用点是否提供 empty state 配置(先 warn 后 fail).
   - 或在 PR 模板自检项中加入 "空态可行动性" 检查.

---

## 6. 风险与回滚

风险:

- 不同列表 API 的 response shape 不一致, 可能导致 itemsCount 解析错误(需 extractor).
- 清除筛选涉及表单控件与 URL 同步, 需要确保 FilterCard/页面逻辑不会出现双重提交或状态漂移.

回滚:

- Phase 1 可按页面逐步迁移, 出现问题可回退到页面级方案(Option A), 但必须保留 CTA(禁止回到纯文案空态).

---

## 7. 验证与门禁

手工验证(最低覆盖):

- 找到一个存在 FilterCard 的 Grid 列表页, 设定筛选无结果.
- 确认空态出现 "清除筛选" CTA.
- 点击 CTA 后筛选被清空, 列表刷新并恢复结果.

静态检查(建议命令):

- `rg -n \"noRecordsFound:\\s*\\\"未找到记录\\\"\" app/static/js/common/grid-wrapper.js`
- `rg -n \"GridWrapper\\(\" app/static/js/modules/views`

---

## 8. Open Questions(需要确认)

1. 空态文案是否需要区分 "无筛选无数据"(暂无数据) 与 "有筛选无结果"(未找到符合条件的记录), 还是统一文案?

