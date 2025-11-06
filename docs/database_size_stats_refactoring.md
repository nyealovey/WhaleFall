# `database_size_stats` 重构方案

## 1. 背景与现状

当前容量采集体系中，每日写入 `database_size_stats` 记录实例内各数据库的快照，同时在 `instance_databases` 中维护库级生命周期。随着过滤功能、MySQL 采集逻辑等优化落地，暴露出如下问题：

- **状态信息重复**：`database_size_stats` 仍持有 `is_deleted`、`deleted_at` 字段，与 `instance_databases.is_active/deleted_at` 语义重叠，且易出现不一致。
- **事实表语义偏差**：历史容量属于不可篡改的事实数据，事实表不应包含“删除”标记；生命周期判断应该由维表完成。
- **查询复杂度高**：聚合/明细页代码需要反复判断 `is_deleted`，而在新的过滤框架下，库是否展示已经可以由库存过滤直接控制。
- **数据质量隐患**：MySQL 采集已禁止回退到 `information_schema`，若仍依赖 `is_deleted` 兜底，会掩盖库存过滤失效等异常。我们希望当库被过滤或缺失时，通过 `instance_databases` 状态直观体现。

## 2. 重构目标

1. **简化事实表结构**：移除 `database_size_stats` 中的状态字段，仅保留容量相关列。
2. **统一状态来源**：所有“是否在线”判断均以 `instance_databases.is_active` 为准，库存同步负责标记过滤结果。
3. **提升查询一致性**：聚合、API、前端读取时统一通过 JOIN（或缓存视图）获取状态，避免并行条件。
4. **完善监控与排错**：当库存过滤掉某些库时，日志应记录过滤原因，历史容量仍可查询但在 UI 默认隐藏。

## 3. 目标模型

### 3.1 `database_size_stats` 字段保留

| 字段 | 说明 |
| --- | --- |
| `id` | 主键 |
| `instance_id` | 实例 ID |
| `database_name` | 数据库名称 |
| `size_mb` | 总大小（MB） |
| `data_size_mb` | 数据占用（MB） |
| `log_size_mb` | 日志占用（MB，可空） |
| `collected_date` | 采集日期（分区键） |
| `collected_at` | 采集时间 |
| `created_at`/`updated_at` | 元数据 |

> **移除**：`is_deleted`、`deleted_at`

### 3.2 状态来源

`instance_databases` 继续承担库级生命周期字段：

- `is_active`：当前是否展示在容量页
- `deleted_at`：最近一次被库存同步判定为下线的时间
- `last_seen_date`：最后一次被采集到的日期

库存同步通过 `DatabaseSyncFilterManager` 过滤系统库并回写 `filtered_databases`，这些库的 `is_active` 会被设置为 `False`，即使历史容量仍存在也不会在默认视图中显示。

## 4. 实施步骤

### 4.1 数据迁移

1. **生成 Alembic 迁移**：
   ```bash
   alembic revision -m "drop is_deleted columns from database_size_stats"
   ```
2. **迁移脚本**：
   ```python
   def upgrade():
       op.drop_column("database_size_stats", "is_deleted")
       op.drop_column("database_size_stats", "deleted_at")

   def downgrade():
       op.add_column("database_size_stats", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
       op.add_column("database_size_stats", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
   ```
3. **执行迁移**：`alembic upgrade head`

> 迁移前如需保险，可临时备份一份表数据（或通过快照/备份策略保障）。

### 4.2 代码调整

| 模块 | 调整点 |
| --- | --- |
| `app/models/database_size_stat.py` | 删除字段定义与 `to_dict` 输出，更新 `__repr__`。 |
| `app/services/database_sync/persistence.py` | Upsert 逻辑不再写入 `is_deleted`；更新 SQLite fallback 分支。 |
| 查询层 (`aggregation_service`、`routes/instance_detail.py` 等) | 默认查询走 `JOIN instance_databases` 过滤 `is_active = true`，提供“包括已删除”参数时使用 `LEFT JOIN`。 |
| 单测 | 更新模型序列化断言；新增聚合查询覆盖 JOIN 行为。 |

### 4.3 API 与前端

- 容量详情接口增加可选参数 `include_inactive`，默认 `false`。
- 前端容量列表默认只展示 `is_active=true` 的库，提供“显示已删除”开关。
- 历史容量图表读取时若库被过滤，需在 tooltip 中提示“库已移除/过滤”。

### 4.4 日志 & 监控

- 库被过滤时在 `inventory_database_filtered` 日志中记录 `reason`。
- 新增指标：`capacity.filtered_databases_total`（按实例计数）。
- 在聚合任务中若发现数据库从活跃变为非活跃，写一条结构化日志帮助排查。

## 5. 回归验证

1. **数据迁移验证**：
   - `SELECT column_name FROM information_schema.columns` 确认字段已删除。
   - 样例实例中历史数据仍可查询。
2. **采集链路回归**：
   - 对包含系统库的实例触发同步，确认 `instance_databases.filtered_databases` 日志出现，并且 UI 默认隐藏这些库。
   - MySQL 视图不可用时同步应失败（不再回退）。
3. **聚合/报表验证**：
   - 日维容量、实例聚合接口能返回正确数据；“显示已删除”开关开启时可看到历史容量。
4. **性能 & 资源**：
   - 对比修改前后聚合计算耗时；JOIN 引入后如出现性能回退，可考虑物化视图或索引优化。

## 6. 风险与回滚

| 风险 | 缓解策略 |
| --- | --- |
| 查询遗漏 JOIN | 审核涉及 `database_size_stats` 的服务/SQL，提供静态扫描脚本。 |
| 旧数据需要 `is_deleted` | 升级前导出依赖字段的报表，如需回滚可凭备份表恢复。 |
| 聚合缓存 | 如果有基于旧字段的缓存，升级后需刷新或重建。 |

Rollback：保留迁移脚本的 `downgrade`，必要时重新添加字段（注意手动填充值）。

## 7. 里程碑计划

1. **PR1**：新增过滤管理器（已完成）及日志分流。
2. **PR2**：提交迁移 + 模型 & 持久层改造（当前文档对应范围）。
3. **PR3**：逐步改造查询/前端，并补充监控指标。

完成以上步骤后，容量事实表将回归“只存事实”的定位，状态信息由库存维表 + 日志指标统一管理，整体流程更加易懂、易排错。
