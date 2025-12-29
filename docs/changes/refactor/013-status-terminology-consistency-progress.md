# Status Terminology Consistency Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-29
> 范围: 同 `013-status-terminology-consistency-plan.md`
> 关联: `013-status-terminology-consistency-plan.md`

关联方案: `013-status-terminology-consistency-plan.md`

---

## 1. 当前状态(摘要)

- 已开始落地:
  - 运行态口径已确认: running=`运行中`, pending=`等待中`.
  - 已修复表格状态 pill 对齐/抖动问题(通过“列宽 + pill 填充”策略，避免全局 `min-width` 撑开表格导致页面溢出).
  - 已对齐“同步会话”相关页面的 running/pending 文案.
  - 已对齐常见启用态文案: 启用/停用(含筛选项/统计卡片/导出/登录提示等触点).
  - plan 已补齐“全量状态词表(v1)”, 覆盖运行态/终态、锁定、删除、调度器 job、健康状态等常见语义.
- 剩余工作见第 2 节 checklist.

## 2. Checklist

### Phase 1(中期): 统一常见状态词(v1)并清理漂移点

- [x] 决策 canonical 词表(v1): 启用/停用、运行中、等待中(等)（见 plan 第 1.3 节与第 8 节确认项）
- [x] 解决对齐问题(基础样式): 通过 status/布尔列固定列宽 + `.status-pill` 填充居中，避免 1/2/3 字状态在居中列中不对齐/抖动
- [x] 对齐同步会话 running/pending 文案:
  - [x] `app/static/js/modules/views/history/sessions/sync-sessions.js`
  - [x] `app/static/js/modules/views/history/sessions/session-detail.js`
  - [x] `app/templates/history/sessions/sync-sessions.html`
- [x] 对齐调度器“运行中”分组文案:
  - [x] `app/templates/admin/scheduler/index.html`
  - [x] `app/static/js/modules/views/admin/scheduler/index.js`
- [x] 替换证据点(激活状态 `is_active`):
  - [x] `app/static/js/modules/views/instances/list.js`
  - [x] `app/templates/tags/index.html`
- [x] 扩展清理统计/提示/导出文案(按 `rg` 命中清单推进)
- [ ] 手工回归: 实例/标签/凭据/用户/会话/调度器页面状态文案一致 + 表格对齐

### Phase 2(长期): 标准化 + 防回归

- [x] 更新 `docs/standards/terminology.md` 增加 "状态用词" 小节
- [x] 新增前端 helper(`UI.Terms` / `resolveActiveStatusText` / `resolveRunStatusText`)
- [x] 新增门禁 `scripts/ci/ui-terminology-guard.sh`(限定扫描范围 + baseline)
- [x] 更新 `.github/pull_request_template.md` 增加 "术语一致性" 自检项

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-06 为入口推进 UI 术语一致性治理.
- 2025-12-28: 补齐全量状态词表(v1); 确认 running/pending canonical 文案(运行中/等待中); 修复表格状态 pill 对齐; 对齐同步会话、调度器、启用态相关页面的状态文案; 落地术语标准/前端 helper/门禁/PR checklist 防回归.
