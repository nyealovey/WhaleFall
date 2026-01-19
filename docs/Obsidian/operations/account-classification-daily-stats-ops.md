# 账户分类每日统计（每日留痕）运维指南

> 目的：补齐“自动分类”的**每日留痕**与**趋势分析**能力，支持按「分类 / 规则 / db_type / instance」组合查询。

## 1. 口径定义（务必对齐）

### 1.1 规则日统计（B 口径）
- **含义**：对每条规则（`rule_id`），统计当日评估命中的**账号数**。
- **注意**：规则之间允许重叠，同一账号可同时被多条规则计数，因此“各规则之和”不等于分类去重总数。

### 1.2 分类日统计（去重口径）
- **含义**：对每个分类（`classification_id`），统计当日命中该分类任意规则的账号**去重数**。
- **去重范围**：按 `instance_id + account_id` 维度天然去重（不同实例的同名账号视为不同账号记录）。

### 1.3 周/月/季聚合展示（均值 + 缺失策略）
- 当 `period_type != daily` 时，趋势图以**均值**展示：
  - `value_avg = SUM(周期内每日值) / coverage_days`
  - `coverage_days`：该周期内实际存在统计记录的天数（缺失天不计入分母）。
  - `expected_days`：该周期自然天数（周=7，月/季按自然日计算）。

### 1.4 日期切分与“同一天只留最后一次”
- **日期切分**：以 `Asia/Shanghai` 的“当天日期”为准。
- **同一天多次执行**：两张日表均按唯一键 `upsert` 覆盖，实现“当天只保留最后一次统计结果”。

## 2. 数据模型与稳定口径

### 2.1 分类：`account_classifications`
- `name`：语义升级为 **code（不可变）**，用于稳定口径。
- `display_name`：展示名（允许调整，不影响统计语义锚点）。

### 2.2 规则：`classification_rules`（不可变版本化）
- 更新规则不再 UPDATE 原记录；改为**创建新版本**（新 `rule_id`）。
- 字段：
  - `rule_group_id`：同一规则的版本组标识
  - `rule_version`：版本号递增
  - `superseded_at`：被替代时间
  - `is_active`：当前是否启用（旧版本会被归档为 `false`）

### 2.3 每日统计表

1) `account_classification_daily_rule_match_stats`
- 维度：`(stat_date, rule_id, db_type, instance_id)`
- 指标：`matched_accounts_count`

2) `account_classification_daily_classification_match_stats`
- 维度：`(stat_date, classification_id, db_type, instance_id)`
- 指标：`matched_accounts_distinct_count`

## 3. 调度任务

### 3.1 任务 ID 与默认时间
- 任务 ID：`calculate_account_classification_daily_stats`
- 默认 cron：每日 `02:00`（`Asia/Shanghai`）
- 配置文件：`app/config/scheduler_tasks.yaml`

> 提示：调度时间不是强约束，可按环境需要调整。

### 3.2 手动触发
可在“定时任务管理”中手动执行该任务；当日重复执行会覆盖当天统计结果。

## 4. 对外接口（API）

### 4.1 分类趋势
- `GET /api/v1/accounts/statistics/classifications/trend`
- query：
  - `classification_id`（必填）
  - `period_type`：`daily|weekly|monthly|quarterly`（`yearly` 会返回 400）
  - `periods`：回溯周期数（默认 7）
  - `db_type`（可选）
  - `instance_id`（可选）

### 4.2 单规则趋势
- `GET /api/v1/accounts/statistics/rules/trend`
- query：
  - `rule_id`（必填）
  - 其余同上

### 4.3 规则贡献（当前周期 TopN）
- `GET /api/v1/accounts/statistics/rules/contributions`
- query：
  - `classification_id`（必填）
  - `period_type`：`daily|weekly|monthly|quarterly`
  - `db_type` / `instance_id`（可选）
  - `limit`（默认 10，最大 50）

### 4.4 规则列表（窗口累计，用于左侧排序/展示）
- `GET /api/v1/accounts/statistics/rules/overview`
- query：
  - `classification_id`（必填）
  - `period_type` / `periods` / `db_type` / `instance_id`（同趋势）
  - `status`：`active|archived|all`（默认 `active`）

## 5. SQL 示例（常用排查/统计）

> 下方以 PostgreSQL 为例；`stat_date` 为 DATE。

### 5.1 某分类：按日去重账号数（全量实例）
```sql
select
  stat_date,
  sum(matched_accounts_distinct_count) as accounts_distinct
from account_classification_daily_classification_match_stats
where classification_id = :classification_id
group by stat_date
order by stat_date;
```

### 5.2 某分类 + 某规则：按日命中账号数（可继续加 db_type/instance）
```sql
select
  stat_date,
  sum(matched_accounts_count) as matched_accounts
from account_classification_daily_rule_match_stats
where classification_id = :classification_id
  and rule_id = :rule_id
  and (:db_type is null or db_type = :db_type)
  and (:instance_id is null or instance_id = :instance_id)
group by stat_date
order by stat_date;
```

### 5.3 某分类 + 某规则 + db_type + instance：单维度日统计
```sql
select
  stat_date,
  matched_accounts_count
from account_classification_daily_rule_match_stats
where rule_id = :rule_id
  and db_type = :db_type
  and instance_id = :instance_id
order by stat_date;
```

## 6. 回滚/降级策略

### 6.1 快速降级（推荐）
- 仅禁用任务：在调度器配置/管理页禁用 `calculate_account_classification_daily_stats`，保留数据表不影响线上运行。

### 6.2 数据库回滚（高风险）
- 若必须回退表结构，可通过 Alembic downgrade 回退到对应 revision（涉及：
  - `20260119132000_add_account_classification_daily_stats_tables.py`
  - `20260119131000_add_classification_rule_versioning.py`
  - `20260119130000_add_account_classification_display_name.py`
）
- 注意：规则版本化属于写路径语义变更，回滚前需评估前端/调用方是否仍依赖 `new_rule_id` 返回与旧规则归档逻辑。

