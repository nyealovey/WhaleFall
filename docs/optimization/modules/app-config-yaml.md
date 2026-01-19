# Module: `app/config/*.yaml`（account_filters/database_filters/scheduler_tasks）

## Simplification Analysis

### Core Purpose

- `app/config/account_filters.yaml`：账户同步的过滤规则默认配置（由 `AccountFiltersConfigFile` 校验/规整后消费）
- `app/config/database_filters.yaml`：容量同步的数据库过滤规则默认配置（由 `DatabaseFiltersConfigFile` 校验/规整后消费）
- `app/config/scheduler_tasks.yaml`：默认调度任务列表（由 `SchedulerTasksConfigFile` 校验后用于初始化 jobstore）

### Unnecessary Complexity Found

- `app/config/account_filters.yaml`：存在大量“说明/占位字段”（`version/description/description/exclude_roles/include_only/custom_rules` 等），但 schema 明确只消费 `exclude_users/exclude_patterns`，其余字段会被忽略（`app/schemas/base.py:13`、`app/schemas/yaml_configs.py:63`）。
- `app/config/database_filters.yaml`：同样存在 `version/description/description` 等元数据字段，且 schema 只消费 `exclude_databases/exclude_patterns`（`app/schemas/base.py:13`、`app/schemas/yaml_configs.py:125`）。
- `app/config/scheduler_tasks.yaml`：cron 触发器参数中显式写入 `day/month/day_of_week='*'` 属于冗余噪音；调度器只取存在的字段并交给 `CronTrigger`（`app/scheduler.py:667`），省略这些字段不会改变当前默认任务的触发语义。
- `app/config/account_filters.yaml:26`：Oracle 的 `exclude_users` 里存在重复项（如 `ORDPLUGINS`）——不会改变过滤语义，但会让参数列表/SQL 生成更啰嗦。

### Code to Remove

- `app/config/account_filters.yaml`（已删除）- root 与 rule 内的元数据/未实现字段；并去掉重复的 `ORDPLUGINS`
- `app/config/database_filters.yaml`（已删除）- root 与 rule 内的元数据字段
- `app/config/scheduler_tasks.yaml`（已删除）- cron 的冗余 `'*'` 字段与 `enabled: true`（schema 默认即为 true：`app/schemas/yaml_configs.py:19`）
- Estimated LOC reduction: ~56 LOC（净删；仅删除“无消费字段/重复项/冗余默认值”）

### Simplification Recommendations

1. 配置文件只保留 schema 固化的字段
   - Current: “工具箱式” YAML（包含大量未来可能用到的字段）
   - Proposed: 只保留当前代码确实消费的字段，避免误导与维护负担
   - Impact: 更少配置噪音；更清晰的真实生效面

2. cron 触发器配置只写“需要非默认值”的字段
   - Current: 充满 `'*'` 的显式默认值
   - Proposed: 保留 `second/minute/hour` 等关键字段，其余交给 CronTrigger 默认
   - Impact: 配置更短、更易读；不改变任务触发语义

### YAGNI Violations

- `exclude_roles/include_only/custom_rules` 等“看起来可扩展但当前未实现/未消费”的字段
- `version/description/description` 等对运行逻辑无影响的元数据（如果需要说明，应转为文档而非运行配置）

### Final Assessment

Total potential LOC reduction: ~56 LOC（已落地）
Complexity score: Low
Recommended action: 后续若要新增配置字段，先在 schema 与消费侧落地，再写入 YAML（避免“写了但不生效”的配置幻觉）

