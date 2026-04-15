# Instance Detail Tabs Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复实例详情页切换到“备份信息”时出现空白和串位的问题，并把数据标签页区域重构为更易维护的模板结构。

**Architecture:** 先用路由级结构测试锁定 `#databaseInfoTabContent` 的一级子节点契约，再将详情页 tab content 拆分为独立局部模板，最后验证前端契约与路由渲染结果。核心思路是不改备份数据接口，只收敛模板层结构和可维护性。

**Tech Stack:** Flask, Jinja2, pytest

### Task 1: 锁定 tab-content 结构契约

**Files:**
- Modify: `tests/unit/routes/test_instances_detail_audit_tab.py`

**Step 1: 写失败测试**

- 解析实例详情页 HTML。
- 断言 `#databaseInfoTabContent` 下的一级 `pane` 顺序固定为 `capacity-pane`、`accounts-pane`、`audit-pane`、`backup-pane`。

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/routes/test_instances_detail_audit_tab.py -q`

Expected: 因当前模板层级错误导致新结构断言失败。

### Task 2: 拆分实例详情页数据标签模板

**Files:**
- Create: `app/templates/instances/partials/detail/_data_tabs_card.html`
- Create: `app/templates/instances/partials/detail/_accounts_pane.html`
- Create: `app/templates/instances/partials/detail/_capacity_pane.html`
- Create: `app/templates/instances/partials/detail/_audit_pane.html`
- Create: `app/templates/instances/partials/detail/_backup_pane.html`
- Modify: `app/templates/instances/detail.html`

**Step 1: 提取 tab card 与各 pane 局部模板**

- 保持现有 DOM id、class、数据挂载点不变。
- 删除手工拼接导致的多余闭合标签。

**Step 2: 最小化修改主模板**

- 主模板只保留 include 入口。
- 确保备份 pane 继续使用 `#backupInfoContent` 作为 JS 渲染挂载点。

### Task 3: 验证契约与页面行为

**Files:**
- Modify: `tests/unit/test_frontend_veeam_source_contract.py`

**Step 1: 补充模板引用契约**

- 断言详情页主模板已引用新的 tab 局部模板。
- 维持已有 CSS / JS 备份契约断言。

**Step 2: 运行相关测试**

Run: `uv run pytest tests/unit/routes/test_instances_detail_audit_tab.py tests/unit/test_frontend_veeam_source_contract.py -q`

Expected: 全部通过。
