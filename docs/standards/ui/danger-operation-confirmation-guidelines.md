# 高风险操作二次确认

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-23  
> 更新：2025-12-25  
> 范围：删除/批量/权限/高资源消耗等高风险操作的确认交互与按钮语义

## 目的

- 统一危险操作确认交互，降低误点与误操作成本。
- 让异步任务提供“结果入口”，用户能找到执行进度与最终结果。

## 适用范围

必须二次确认的典型场景：

- 删除类：删除实例、删除用户、批量删除、清理分区等不可逆操作。
- 全量/批量操作：同步所有账户、重算/重建、批量导入导出（资源消耗大）。
- 权限与安全：移除管理员权限、变更关键权限策略、可能导致“无人可管理”的变更。

## 规则（MUST/SHOULD/MAY）

### 1) 禁止浏览器 `confirm()`

- MUST NOT：使用浏览器 `confirm()` 弹窗（样式不可控且体验不一致）。
- MUST：统一使用 `UI.confirmDanger(options)`（见 `app/static/js/modules/ui/danger-confirm.js`）。

### 2) 影响范围必须可见

- MUST：确认弹窗必须展示影响范围（目标名称/ID 或“已选择 N 条”）。
- SHOULD：补充风险类型（不可撤销/资源消耗/权限风险）与后续查看入口。

### 3) 异步任务必须提供结果入口

- MUST：若操作触发异步任务，弹窗或成功提示必须提供“会话中心”入口（默认指向 `/history/sessions`）。

### 4) 按钮语义与防重复提交

- MUST：删除类最终确认按钮使用 `btn-danger`；资源风险但可恢复的操作使用 `btn-warning`。
- SHOULD：默认焦点放在“取消”，降低误触确认概率。
- MUST：点击确认后进入 loading，并禁用至少一个按钮，防止重复提交。

## 正反例

### 正例：使用统一确认组件

```javascript
UI.confirmDanger({
  title: '确认批量删除实例',
  summary: '该操作不可撤销，请确认影响范围。',
  impacts: ['已选择 3 条实例', '将同时删除关联标签关系'],
  confirmText: '确认删除',
  confirmClass: 'btn-danger',
  sessionLink: '/history/sessions',
});
```

## 门禁/检查方式

- 禁止 `confirm()`：`./scripts/ci/browser-confirm-guard.sh`
- 危险按钮语义：`./scripts/ci/danger-button-semantics-guard.sh`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 补齐标准结构与门禁入口，收敛为可执行的规则。
