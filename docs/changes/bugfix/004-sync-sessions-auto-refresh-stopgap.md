# Sync Sessions Auto Refresh Stopgap

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/templates/history/sessions/sync-sessions.html`, `app/static/js/modules/views/history/sessions/sync-sessions.js`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P2-03)

## 1. 症状与影响

会话中心当前默认每 30s 自动刷新(`AUTO_REFRESH_INTERVAL = 30000`), 但缺少:

- 显式开关(用户无法暂停).
- 场景暂停策略(例如打开详情后仍刷新).

影响:

- 用户阅读/复制会话详情时, 列表刷新可能导致焦点与滚动抖动, 产生"我正在看什么"的中断感.
- 用户缺少控制感, 只能被动等待或反复操作, 增加挫败感.

## 2. 复现步骤

1. 打开 "会话中心" 页面.
2. 点击任意会话的 "查看详情", 打开详情模态.
3. 停留 30s 以上, 观察列表刷新带来的页面抖动(滚动位置/焦点/选择状态变化).
4. 在详情中尝试复制内容, 观察是否被刷新打断.

## 3. 根因分析

- `app/static/js/modules/views/history/sessions/sync-sessions.js` 使用 `setInterval(..., 30000)` 周期性 `sessionsGrid.refresh()`.
- 没有 UI 开关控制 `clearInterval`.
- 没有在详情模态打开期间暂停刷新(也没有在关闭后恢复的策略).

## 4. 修复方案(短期止血)

目标: 保证用户在阅读/复制详情时不被刷新打断, 同时保留默认自动刷新能力.

### 4.1 增加 "自动刷新" 开关(默认开启)

改动点:

- 模板 `app/templates/history/sessions/sync-sessions.html` 增加一个 switch/checkbox(建议放在筛选区或列表卡片 header 右侧).
- JS `sync-sessions.js` 读取开关状态, 决定是否启动 `setInterval`.

交互口径:

- 默认开启: 保持现有行为.
- 用户关闭: 立即停止定时器, 不再自动刷新.
- 用户开启: 立即启动定时器, 下次刷新仍按 30s 周期.

可选(短期内建议做):

- 采用 `localStorage` 记住用户选择(例如 key: `syncSessions.autoRefreshEnabled`), 避免每次进入都需要重新关闭.

### 4.2 打开详情模态时自动暂停, 关闭后恢复

改动点:

- 监听 `#sessionDetailModal` 的 Bootstrap 事件:
  - `shown.bs.modal`: 暂停自动刷新(调用 `clearAutoRefresh()`).
  - `hidden.bs.modal`: 若开关为开启状态, 恢复自动刷新(调用 `setupAutoRefresh()`).

口径:

- 暂停仅影响自动刷新, 不影响用户手动触发的刷新(如后续加 "立即刷新" 按钮).
- 关闭详情后是否立刻刷新一次可选:
  - 推荐: 恢复 timer 后立即 `sessionsGrid.refresh()` 一次, 保证用户回到列表看到最新状态.

### 4.3 可选增强: 增加 "立即刷新" 按钮

短期止血阶段, 如果用户关闭自动刷新, 需要一个明确的手动刷新入口.

建议:

- 在列表卡片 header 增加一个 `btn-icon` 刷新按钮.
- 点击后 `sessionsGrid.refresh()`.
- 同时满足 P1-03 的可访问名称要求(aria-label).

## 5. 回归验证

- 桌面端常见分屏宽度(例如 900px)下, 开关可见且可操作.
- 自动刷新开关:
  - 开启: 每 30s 刷新一次.
  - 关闭: 不再自动刷新.
  - 刷新不会产生 console error.
- 详情模态暂停:
  - 打开详情后, 等待超过 30s, 列表不刷新.
  - 关闭详情后, 自动刷新恢复(且可选立即刷新一次).
- 复制体验:
  - 在详情中复制 session id/stack/payload 等内容, 不被刷新打断.

## 6. 风险与回滚

风险:

- 监听 Bootstrap modal 事件依赖 `bootstrap.bundle.min.js` 已加载且 modal id 不变.
- 若页面存在多个 modal, 需确保只绑定到会话详情 modal.

回滚:

- 若出现回归, 可回退到仅提供开关(不做 modal 暂停), 但禁止回退到"无开关且无暂停"的状态.

## 7. 后续事项(不在本次止血内)

- 中期: 仅在存在 running/pending 会话时启用自动刷新, 全部 completed 后停止或降频.
- 长期: 统一后台任务类页面的刷新策略标准(可预测, 可控, 可暂停).
