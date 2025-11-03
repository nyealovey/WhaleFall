# 容量采集两阶段改造提案

## 背景现状

仓库当前的容量同步逻辑由 `DatabaseSizeCollectorService` 直接执行“连接 → 拉取容量数据 → 写入 `database_size_stats`”。同时，`instance_databases` 表依赖 `database_size_stats` 的 AFTER INSERT 触发器自动新增/刷新 `last_seen_date`，缺失库需要额外调用 `detect_deleted_databases()` 才会被标记为删除。这样带来两个问题：

1. 如果采集流程中出现异常（如数据库权限不足、瞬时故障），`instance_databases` 无法及时更新，“库是否存在”信息不可信。
2. 手动和定时同步都无法在采集前统一校验库列表，新库发现或旧库删除依赖触发器与额外函数，链路过长、难以观察。

## 改造目标

将容量同步拆分成两个明晰的阶段：

1. **数据库列表同步阶段**：先获取远端实例上所有数据库信息，对 `instance_databases` 进行增量维护（新增/更新/标记删除）。
2. **容量采集阶段**：只针对仍处于活跃状态的数据库采集容量数据，写入 `database_size_stats` 并更新实例汇总。

这样可以确保库状态先于容量采集得到矫正，避免“库已删除但仍显示活跃”或“新库迟迟未入库”的问题。

## 调整细节

### 1. 阶段一：同步数据库列表

- 在 `DatabaseSizeCollectorService` 新增 `fetch_databases_metadata()`，仅负责列出实例当前存在的数据库（名称、标识符、可选的连接状态）。
- 应用层比较“采集到的库列表”与 `instance_databases`：
  - 新库：插入记录，补齐 `first_seen_date`、`last_seen_date`、`is_active=TRUE`。
  - 仍存在的库：刷新 `last_seen_date`、清理 `deleted_at`。
  - 基线中有但采集中缺席的库：调用 `InstanceDatabase.mark_as_deleted()` 或专门的检测函数标记 `is_active=FALSE`、写入 `deleted_at`。
- 触发器 `update_instance_database_last_seen` 如保留，应仅负责兜底更新（例如并发场景下更新 `last_seen_date`），不再自动插入新库，以避免与应用逻辑冲突。

### 2. 阶段二：采集活跃库容量

- 读取 `instance_databases` 中 `is_active=TRUE` 的库列表，作为容量采集范围。
- 对每个库调用现有的容量采集逻辑，写入 `database_size_stats` 并更新 `instance_size_stats`。
- 如果某库容量采集失败，仅记录日志或同步会话状态，不影响库的“活跃”标识。

### 3. 触发器与函数调整

- 修改 `update_instance_database_last_seen` 触发器，保留“更新 `last_seen_date`”但去掉自动插入逻辑，将权责放回应用层。
- 保留 `detect_deleted_databases()` 作为辅助函数；在阶段一中执行“同步 + 标记删除”后，可减少额外调度频率。
- `mark_database_as_deleted()` 继续作为应用层调用的工具方法。

## 实施建议

1. 重构 `DatabaseSizeCollectorService`：
   - 新增列表同步能力；
   - 明确 `collect_database_sizes()` 仅处理容量采集。
2. 调整定时任务：
   - 在 `collect_database_sizes()` 里拆分列表同步和容量采集两个阶段。
   - 可选地在列表同步后调用 `InstanceDatabase.detect_deleted_databases()`，确保当天未出现的库立即标记为失活。
   - 根据运行时长考虑将聚合任务安排在容量采集完成之后或隔开调度，避免竞争。
3. 在 `capacity` 手动同步入口与 `capacity_collection_tasks.collect_database_sizes()` 引入阶段一逻辑，确保两阶段顺序执行。
4. 调整触发器与 SQL 脚本，并对 `instance_databases` 做数据迁移（如需移除历史触发器副作用）。

   **参考 SQL 脚本**（以 PostgreSQL 为例，可结合 Alembic/手工执行）：

   ```sql
   -- 1. 修改 update_instance_database_last_seen 触发器：仅更新 last_seen_date，不再插入新库
   DROP TRIGGER IF EXISTS trg_update_instance_database_last_seen ON database_size_stats;
   DROP FUNCTION IF EXISTS update_instance_database_last_seen();

   CREATE OR REPLACE FUNCTION update_instance_database_last_seen()
   RETURNS TRIGGER AS $$
   BEGIN
       UPDATE instance_databases
       SET last_seen_date = NEW.collected_date,
           updated_at = NOW(),
           is_active = TRUE,
           deleted_at = NULL
       WHERE instance_id = NEW.instance_id
         AND database_name = NEW.database_name;

       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER trg_update_instance_database_last_seen
       AFTER INSERT ON database_size_stats
       FOR EACH ROW EXECUTE FUNCTION update_instance_database_last_seen();

   -- 2. 对历史数据执行失活检测（可按需调用）
   -- SELECT detect_deleted_databases(instance_id) FROM instances;

   -- 3. 将历史触发器插入的幽灵记录（无对应 capacity 记录）按业务需要清理
   ```

   如需迁移到 Alembic，可将上述 SQL 拆分到升级/降级脚本中执行。
5. 补充测试覆盖：
   - 新库被发现并写入。
   - 停用库被标记为 `is_active=FALSE`。
   - 采集异常时库状态仍正确。

## 预期收益

- 库状态管理回归应用层，调试与观测更加直观；
- 容量采集故障不会影响库列表的准确性，减少“幽灵库/遗失库”问题；
- 为后续做库级别权限校验、通知等扩展打下基础。
