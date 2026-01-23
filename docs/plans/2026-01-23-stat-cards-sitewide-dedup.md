# Stat Cards Sitewide Dedup + Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 全站所有“统计数字卡片/统计块”（含 `metric_card`、`instance-stat-card`、分区页 `setStatCard`、各页面 JS 更新的统计值）统一重构：每张卡更“丰富”（主值 + 二级维度），且同一行/同一组统计块中不出现“重复含义的数字”。

**Architecture:**
- 以页面为单位建立“统计组（Stat Group）”概念：同一行 3-4 张卡、或同一区块内的一组统计展示。
- 为每个统计组定义一组“语义键（semantic key）”，例如 `logs.error_count`、`instances.total`。
- **硬约束：同一统计组内，每个 semantic key 只能出现一次**（只允许作为某张卡的主值或某个 meta item 之一）。
- 允许使用“派生指标”作为主值或 meta：比例（%）、速率（/h）、均值（/account）、Top1（name/占比）等，因为语义不同，不算重复。
- UI 表达风格：meta 统一用 **图标 + 数字/短文本**，不放冗余文字；文字放到 `title` / `aria-label`。

**Tech Stack:** Jinja2 templates, existing `metric_card` macro (`app/templates/components/ui/metric_card.html`), existing components (`status-pill`, `chip-outline`), page JS.

---

## 0) 统一定义

### 0.1 统计组（Stat Group）
- 例：日志中心页顶部 4 张卡是一个统计组。
- 例：实例详情页“数据库统计”3 张 `instance-stat-card` 是一个统计组；“账户统计”3 张也是一个统计组。

### 0.2 semantic key
- 每个“绝对数量”必须有唯一语义键：例如 `account_change.total_changes`。
- 派生指标用不同键：例如 `account_change.success_rate`。

### 0.3 去重规则（Hard Rule）
- 同一统计组内：**同一个 semantic key 的数字只允许出现一次。**
- 计数（count）不允许重复；但派生值（rate/per_xxx/top share）允许出现。

---

## 1) Inventory（全站统计组清单）

### 1.1 `metric_card` 页面清单
`metric_card` 出现于：
- `app/templates/dashboard/overview.html`
- `app/templates/accounts/statistics.html`
- `app/templates/instances/statistics.html`
- `app/templates/tags/index.html`
- `app/templates/admin/partitions/index.html`
- `app/templates/capacity/instances.html`
- `app/templates/capacity/databases.html`
- `app/templates/history/logs/logs.html`
- `app/templates/history/account_change_logs/account-change-logs.html`

### 1.2 非 `metric_card` 的统计块
- 实例详情页：`app/templates/instances/detail.html` 使用 `instance-stat-card`（两组）
- 分区页：`app/static/js/modules/views/admin/partitions/index.js` 的 `setStatCard()` 写入 `[data-role="metric-value"]` 与 `[data-role="metric-meta"]`

---

## 2) 各页面“最终卡片方案”（避免重复含义数字）

下面每个页面都给出：主值（Primary）+ meta（Secondary），并标注 semantic key，确保组内不重复。

### 2.1 日志中心（`LogsPage`）
**现状问题：** 总日志卡 meta 重复展示错误/告警（其它卡主值）；且“模块数量”卡主值缺后端字段导致恒为 0。

**统计组：LogsCards**
- 卡 A：总日志数（primary: `logs.total_logs`）
  - meta: Top 模块名（`logs.top_module_name`，文本）
  - meta: Top 模块量（`logs.top_module_count`）
  - meta: 时间窗口（`logs.window_hours`，如 24h）

- 卡 B：错误日志（primary: `logs.error_count`）
  - meta: 错误率（`logs.error_rate`，%）
  - meta: 严重（`logs.critical_count`）
  - meta: 错误速率（`logs.error_per_hour`）

- 卡 C：警告日志（primary: `logs.warning_count`）
  - meta: 告警占比（`logs.warning_rate`，%）
  - meta: 告警速率（`logs.warning_per_hour`）

- 卡 D：信息日志（primary: `logs.info_count`）【替换旧“模块数量”】
  - meta: 调试（`logs.debug_count`）

> 如果必须保留“模块数量”，则追加后端字段 `module_count`（见 Task 6）。


### 2.2 账户变更历史（`AccountChangeLogsPage`）
**现状问题：** 当 failed=0 时 success_count == total_changes，导致两张卡重复同一个大数字。

**统计组：AccountChangeCards**
- 卡 A：变更总数（primary: `account_change.total_changes`）
  - meta: 人均变更（`account_change.avg_changes_per_account`）
  - meta: 时间窗口（`account_change.window_hours`）

- 卡 B：失败变更（primary: `account_change.failed_count`）
  - meta: 失败率（`account_change.failed_rate`，%）
  - meta: 失败/账号（`account_change.failed_per_account`）

- 卡 C：成功率（primary: `account_change.success_rate`，%）【替换旧“成功变更”主值】
  - meta: 成功/账号（`account_change.success_per_account`）

- 卡 D：影响账号数（primary: `account_change.affected_accounts`）
  - meta: 每账号变更（`account_change.changes_per_account`）【如与卡 A 重复则只保留一处】


### 2.3 标签管理（`TagsIndexPage`）
**现状问题：** “全部标签”卡 meta 展示 `category_count`，但 `category_count` 同时是“标签分类”卡主值 → 重复。

**统计组：TagCards**
- 卡 A：全部标签（primary: `tags.total`）
  - meta: 启用率（`tags.active_rate`，%）
  - meta: 停用率（`tags.inactive_rate`，%）

- 卡 B：启用标签（primary: `tags.active`）
  - meta: 启用占比（`tags.active_rate`，%）【若已在卡 A 使用，则此处只保留 1 处】

- 卡 C：停用标签（primary: `tags.inactive`）
  - meta: 停用占比（`tags.inactive_rate`，%）【同上】

- 卡 D：标签分类（primary: `tags.category_count`）
  - meta: Top 分类名（`tags.top_category_name`）【需要后端/页面数据支持，否则省略】


### 2.4 实例统计（`InstanceStatisticsPage`）
**目标：** 保留关键维度且不重复。

**统计组：InstanceCards**（建议改为：总数 + 在线/删除 + 类型覆盖）
- 卡 A：实例总数（primary: `instances.total`）【新增】
  - meta: 在线率（`instances.active_rate`，%）
  - meta: 删除率（`instances.deleted_rate`，%）

- 卡 B：在线实例（primary: `instances.active`）
  - meta: 在线占比（`instances.active_rate`，%）【若已在卡 A 使用则只保留一处】

- 卡 C：已删除实例（primary: `instances.deleted`）
  - meta: 删除占比（`instances.deleted_rate`，%）【同上】

- 卡 D：数据库类型（primary: `instances.db_types_count`）
  - meta: Top 类型（`instances.top_db_type`）+ 占比（`instances.top_db_type_share`）【可由页面 table 推导】

> “停用实例”可以不再作为卡片主值，留在明细表/列表中。


### 2.5 账户统计（`AccountsStatisticsPage`）
**统计组：AccountCards**（保持 4 张卡，但 meta 只放派生值）
- 卡 A：总账户数（primary: `accounts.total`）
  - meta: 活跃率（`accounts.active_rate`，%）
  - meta: 锁定率（`accounts.locked_rate`，%）

- 卡 B：活跃账户（primary: `accounts.active`）
  - meta: 活跃占比（`accounts.active_rate`，%）【组内只保留一处】

- 卡 C：锁定账户（primary: `accounts.locked`）
  - meta: 锁定占比（`accounts.locked_rate`，%）【组内只保留一处】

- 卡 D：在线实例（primary: `accounts.instances`）
  - meta: 账户/实例均值（`accounts.avg_per_instance`）


### 2.6 分区管理（`AdminPartitionsPage`）
**统计组：PartitionCards**
- 卡 A：分区总数（primary: `partitions.total_partitions`）
  - meta: 平均记录/分区（`partitions.avg_records_per_partition`）

- 卡 B：总大小（primary: `partitions.total_size`）
  - meta: （可选）需要后端补充 `total_size_bytes` 才能做派生（否则只放数据来源/窗口）

- 卡 C：总记录数（primary: `partitions.total_records`）
  - meta: 平均记录/分区（同卡 A 不重复，仅保留一处）

- 卡 D：健康状态（primary: `partitions.health`）
  - meta: 数据库组件状态（`partitions.db_component_status`）


### 2.7 容量统计（实例/数据库）
**容量(实例)统计组：CapacityInstanceCards**
- 卡 A：在线实例数（primary: `capacity.instances.total_instances`）
  - meta: 平均容量（`capacity.instances.avg_size_mb` 格式化）【若卡 C 已作为主值则此处只保留一处】

- 卡 B：总容量（primary: `capacity.instances.total_size_mb`）
  - meta: 人均容量（`capacity.instances.total_per_instance`）

- 卡 C：平均容量（primary: `capacity.instances.avg_size_mb`）
  - meta: 最大/平均比（`capacity.instances.max_to_avg_ratio`）

- 卡 D：最大容量（primary: `capacity.instances.max_size_mb`）
  - meta: （可选）来源/周期（`capacity.instances.period_type`）

**容量(数据库)统计组：CapacityDatabaseCards**
- 卡 A：总数据库数（primary: `capacity.databases.total_databases`）
  - meta: 实例数（`capacity.databases.total_instances`）

- 卡 B：总容量（primary: `capacity.databases.total_size_mb`）
  - meta: 增长率（`capacity.databases.growth_rate`，%）

- 卡 C：平均容量（primary: `capacity.databases.avg_size_mb`）
  - meta: （可选）P95/最大比（若后端无数据则省略）

- 卡 D：最大容量（primary: `capacity.databases.max_size_mb`）


### 2.8 实例详情页（`InstancesDetailPage`）
现有两组 `instance-stat-card` 都是“单一数字”，需要升级为：每组 1 张“总数卡” + 2-3 个子维度（作为 meta）。

**统计组：InstanceDetailDatabaseCards**（数据库）
- 卡 A：数据库总数（primary: `instance_detail.db_total`）【新增，需要后端/JS 提供 total】
  - meta: 在线（`instance_detail.db_online`）
  - meta: 已删除（`instance_detail.db_deleted`）
  - meta: 总容量（`instance_detail.db_total_capacity`）【单位不同，允许】

**统计组：InstanceDetailAccountCards**（账户）
- 卡 A：账户总数（primary: `instance_detail.account_total`）【新增，需要后端/JS 提供 total】
  - meta: 活跃（`instance_detail.account_active`）
  - meta: 已删除（`instance_detail.account_deleted`）
  - meta: 超管（`instance_detail.account_superuser`）

实现方式：将 `instance-stat-card` 迁移为 `metric_card`（统一样式），或保留结构但增加 meta 区。

---

## 3) 实施步骤（按风险从低到高）

### Task 1: 输出“去重对照表”到代码旁注释（可选）
**Files:**
- Modify: `docs/plans/2026-01-23-stat-cards-sitewide-dedup.md`

将每个页面的统计组 semantic key 固化成表格，作为后续 review 的检查项。


### Task 2: 修复已引入的重复（Logs + AccountChangeLogs）
**Files:**
- Modify: `app/templates/history/logs/logs.html`
- Modify: `app/static/js/modules/views/history/logs/logs.js`
- Modify: `app/templates/history/account_change_logs/account-change-logs.html`
- Modify: `app/static/js/modules/views/history/account-change-logs/account-change-logs.js`

目标：立即消除重复含义数字；并把“模块数量”卡替换为“信息日志”或走后端补齐。


### Task 3: TagsIndexPage 去重（移除 total 卡里对 category_count 的重复）
**Files:**
- Modify: `app/templates/tags/index.html`
- Modify: `app/static/js/modules/views/tags/index.js`（如需要动态更新派生 meta）


### Task 4: AccountsStatisticsPage 丰富化但不重复
**Files:**
- Modify: `app/templates/accounts/statistics.html`
- Modify: `app/static/js/modules/views/accounts/statistics.js`

添加派生 meta（率/均值），不重复展示其它卡主值。


### Task 5: InstanceStatisticsPage 结构调整（引入 total + 派生卡）
**Files:**
- Modify: `app/templates/instances/statistics.html`
- Modify: `app/static/js/modules/views/instances/statistics.js`

将 4 卡改为：总数、在线、已删、类型覆盖（停用移出卡片）。


### Task 6: 容量统计页 meta 扩展（纯前端派生）
**Files:**
- Modify: `app/templates/capacity/instances.html`
- Modify: `app/static/js/modules/views/capacity/instances.js`
- Modify: `app/static/js/modules/views/components/charts/summary-cards.js`（若要支持更新 meta）
- Modify: `app/templates/capacity/databases.html`
- Modify: `app/static/js/modules/views/capacity/databases.js`


### Task 7: 分区管理页 meta 扩展（records/partition 等）
**Files:**
- Modify: `app/static/js/modules/views/admin/partitions/index.js`
- Optional backend: 如果要 size 派生，增加 bytes 字段。


### Task 8: 实例详情页两组统计升级为“总数 + meta”
**Files:**
- Modify: `app/templates/instances/detail.html`
- Modify: `app/static/js/modules/views/instances/detail.js`
- Optional backend: 若缺少 total 字段，补接口返回。


### Verification
- JS 语法检查：`node -e "new Function(require('fs').readFileSync(PATH,'utf8'));"` 对所有改动 JS 文件执行。
- 手工 smoke：打开各页面确认卡片无重复含义数字、meta 图标+数字显示正确。

---

## 4) 风险与策略
- 统计接口字段不足（例如 logs 的 module_count、分区 size_bytes、实例详情 totals）：优先用前端派生；无法派生时才加后端字段。
- 避免过度“设计化”：先保证语义正确和去重；视觉增强不引入复杂动画。
