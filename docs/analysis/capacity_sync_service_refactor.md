# 容量同步适配层重构方案

## 背景
- `app/services/database_sync/database_sync_service.py` 将**连接管理、库存同步、容量采集、数据持久化、日志**等职责集中在一个类内，文件超过 900 行，难以扩展与测试。
- 最新的“两阶段同步”改造已引入“数据库清单同步 + 容量采集”流程，但实现仍是巨型类内的条件分支，与账户同步（`app/services/account_sync/account_sync_service.py` + `account_sync/adapters/`）相比欠缺清晰的适配层结构。
- 即将支持更多数据库类型、权限差异以及可能的异步化需求，需要可拔插、易测试、可复用的架构。

## 重构目标
1. **拆分职责**：将通用流程抽象为同步基类，具体数据库逻辑下沉至独立适配器。
2. **统一接口**：对外保留 `DatabaseSizeCollectorService`（或改名为 Coordinator），内部委托给适配器执行库存与容量采集。
3. **易扩展与可测试**：适配器遵循统一协议，可单独编写单元测试；协调层聚焦应用交互和事务管理。
4. **保持现有行为兼容**：API、定时任务、触发器更新逻辑与数据模型保持不变，仅内部实现替换。

## 现状痛点
- **巨型类耦合**：`DatabaseSizeCollectorService` 同时承担连接管理、SQL 执行、数据归集、ORM 写入，导致修改任何环节都要回归整体。
- **数据库分支散落**：MySQL/PostgreSQL/SQLServer/Oracle 的查询语句、数据转换交织在类内部，不利于对单个数据库做增强或调试。
- **库存/容量混杂**：虽然已分为两阶段，但在代码层面仍由同一类负责，难以在不同数据库上复用或单独调整。
- **测试覆盖不足**：目前仅有库存同步的单测，容量采集和持久化逻辑难以隔离验证。

## 目标架构

```
app/services/
├── database_sync/
│   ├── coordinator.py         # 统一入口，负责调度、事务、日志
│   ├── adapters/
│   │   ├── base_adapter.py    # 抽象基类，定义库存与容量采集接口
│   │   ├── mysql_adapter.py
│   │   ├── postgresql_adapter.py
│   │   ├── sqlserver_adapter.py
│   │   └── oracle_adapter.py
│   ├── inventory_manager.py   # 公共库存落库逻辑（现有 sync_instance_databases 抽象）
│   └── persistence.py         # DatabaseSizeStat / InstanceSizeStat 写入封装
└── database_sync_service.py   # 过渡：导入 coordinator 对外暴露旧接口
```

### 基类职责（`BaseCapacitySyncAdapter`）
- `fetch_inventory(connection) -> list[InventoryRow]`：返回实例当前数据库/表空间元数据。
- `fetch_capacity(connection, inventory: list[str]) -> list[CapacityRow]`：采集容量数据，仅关注业务数据组装。
- `normalize_inventory` / `normalize_capacity`：按需清洗字段、标记系统库。
- 提供错误信息标准化，区分权限错误、网络错误等。

### 适配器职责
- 实现各自数据库的 SQL/命令。
- 处理数据库特有的数据结构（如 MySQL 表空间、Oracle tablespace、PostgreSQL 模板库过滤）。
- 只处理“读”操作，不涉及 ORM。

### 协调器职责（`CapacitySyncCoordinator`）
- 管理连接生命周期（沿用 `ConnectionFactory`）。
- 调用适配器完成库存 → 调用 `InventoryManager` 落库 → 根据活跃库调用适配器采集容量 → 调用 `CapacityPersistence` 写入。
- 统一日志、异常包装、统计汇总。
- 对外暴露与现有 `DatabaseSizeCollectorService` 等价的 `synchronize_inventory`、`collect_capacity`、`collect_and_save` 等接口。

### 存储层封装
- `InventoryManager`：封装当前 `sync_instance_databases` 的逻辑，对 `InstanceDatabase` 的增删改统一管理，便于单测。
- `CapacityPersistence`：封装 `DatabaseSizeStat` 与 `InstanceSizeStat`、聚合调用等写入操作，可注入事务或批量处理策略。

## 迁移步骤
1. **准备阶段**
   - 新建 `app/services/database_sync/` 目录结构与骨架文件。
   - 提取 `sync_instance_databases` 与持久化逻辑到独立模块，保持旧类调用路径不变（减少一次性 diff）。

2. **适配器迁移**
   - 按数据库类型逐个迁移现有 `_collect_*` 和 `_fetch_*` 方法至新适配器。
   - 适配器内保留原 SQL/处理逻辑，协调器负责调用。
   - 为每个适配器编写单元测试（可通过模拟连接对象返回查询结果）。

3. **协调器替换**
   - 实现 `CapacitySyncCoordinator`，将现有 `collect_database_sizes`、`synchronize_database_inventory`、`collect_and_save` 改为委托协调器。
   - 验证路由与任务层调用无感知变更。

4. **移除遗留代码**
   - 当所有功能迁移至新结构并通过测试后，将旧类裁剪为薄包装或直接弃用，确保外部导入路径不破坏。
   - 更新文档、开发指南，通知团队新的扩展点。

5. **测试与回归**
   - 扩充现有单测，覆盖：
     - 适配器 inventory/capacity 正常路径与权限异常。
     - InventoryManager 的新增/停用/恢复流程。
     - Coordinator 在“无活跃库”“容量采集失败”场景下的行为。
   - 回归 `app/tasks/capacity_collection_tasks.py`、`app/routes/capacity.py`、聚合任务路径。

## 风险与缓解
- **行为偏差风险**：通过保留现有对外接口 + 增加快照测试（确保关键 SQL/字段一致）减少差异。
- **事务一致性风险**：协调器需严格控制事务边界，库存持久化与容量写入分阶段提交；必要时引入 `Session` 上下文管理工具。
- **测试环境缺乏真实数据库**：适配器测试将使用假连接对象返回固定结果；集成测试继续依赖当前模拟/fixture。

## 时间与资源预估
- 适配器抽取：每个数据库类型 ~0.5-1 天（含测试）。
- 协调器与管理器封装：1.5 天。
- 回归测试与文档更新：1 天。
- 合计：约 4-5 个工作日，视环境差异调整。

## 后续可选优化
- 引入策略：按数据库类型读取配置驱动 SQL 片段，减少硬编码。
- 支持增量采集：适配器记录上次成功时间，协调器可选择仅采集新增/活跃库。
- 提供异步模式或批处理：在协调器层加入任务队列，按实例或库并发处理。
- 结合 metrics/Tracing：在协调器中统一埋点，便于运维监控。

---
此重构方案与账户同步架构保持一致，有助于未来在容量与账户之间共享连接策略、监控、错误处理等基础能力。下一步可按“准备阶段”开始拆分，以渐进方式落地。*** End Patch
