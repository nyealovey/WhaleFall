# 账户同步两阶段重构提案

## 背景
- 现有账户同步逻辑集中在 `app/services/account_sync/account_sync_service.py` 与遗留的 `account_sync_adapters/`。适配器虽已抽象出“获取账户 → 格式化 → 同步到本地”的流程，但**账户信息与权限同步仍在单个阶段内完成**。
- 最新的容量同步重构已经成功拆分为“库存同步 + 数据采集”两阶段，并迁移到模块化架构（`app/services/database_sync/`）。为了保持架构一致性、提升可维护性，需要将账户同步也改造成两阶段流程。
- 项目未来可能在权限校验、增量同步、外部审计上有更多要求，当前耦合流程不利于扩展和测试。

## 现状痛点
1. **流程耦合**：适配器调用 `sync_accounts` 时同时完成账户存在性更新与权限对比更新，难以独立监控或重试其中一个环节。
2. **异常处理有限**：当权限抓取失败时，很难判定账户信息是否已更新成功，需要更细粒度的状态汇报。
3. **扩展受限**：缺乏统一接口处理“仅同步账户列表”“仅重刷权限”等需求；与容量同步的协调层不一致，增加维护难度。
4. **测试粒度粗**：目前仅能在整体同步层面编写测试，难以针对账户存在性/权限更新做单独验证。
5. **数据模型缺口**：缺少与 `InstanceDatabase` 对应的“实例-账户”关系模型，无法在第一阶段中对账户清单进行持久化、标记新增/删除。需要新增 `InstanceAccount`（暂定名称）模型，并在实例模型中建立关联。
6. **权限快照模型耦合**：`CurrentAccountSyncData` 既承担账户存在性唯一约束，又保存权限快照。两阶段拆分后，应将账户唯一约束迁移到新模型，`CurrentAccountSyncData` 聚焦权限维度。

## 重构目标
1. **两阶段流程**  
   - 阶段一：账户清单同步（Account Inventory）。负责拉取远端账户列表，对 `db_accounts`（假设模型名称）进行增量维护，标记新增、删除、恢复。
   - 阶段二：权限同步（Permission Sync）。在阶段一确认的活跃账户范围内采集权限数据，并与本地权限记录对比更新。
2. **模块分层对齐**  
   - 引入 `app/services/account_sync/` 目录，内含协调器（Coordinator）、适配器（Adapters）、账户库存管理器（AccountInventoryManager）、权限持久化（PermissionPersistence）等，与 `database_sync` 结构一致。
3. **接口兼容**  
   - 保留 `AccountSyncService` 对外接口不变，仅内部委托新的协调器执行两阶段逻辑。
4. **增强可观测性**  
   - 均衡日志、统计、错误返回，清晰描述每个阶段的结果，便于运维监控与手动排查。
5. **更易测试**  
   - 可以分别对账户库存同步与权限同步编写单元测试，模拟各种边界场景。

## 目标架构

```
app/services/
├── account_sync/
│   ├── coordinator.py             # 统一入口，串联两阶段
│   ├── adapters/
│   │   ├── base_adapter.py        # 定义账户与权限抽象接口
│   │   ├── mysql_adapter.py
│   │   ├── postgresql_adapter.py
│   │   ├── sqlserver_adapter.py
│   │   └── oracle_adapter.py
│   ├── inventory_manager.py       # 账户清单同步到本地模型
│   ├── permission_manager.py      # 权限数据比对与持久化
│   └── sync_service.py            # 兼容旧接口的包装器
└── account_sync_service.py        # 过渡：导入新的协调器
```

> 注：若已有权限相关模型/服务（如 `AccountPermission`），需在 `permission_manager.py` 内封装全部增量更新逻辑。

## 两阶段流程描述

### 阶段一：账户清单同步
1. 适配器执行 `fetch_accounts(instance, connection)`，返回包含用户名、标识、锁定状态等信息的列表。
2. `AccountInventoryManager` 对比远端结果与本地记录：
   - 新账户：创建记录，标记 `is_active=True`，填充 `first_seen_at`、`last_seen_at`。
   - 已存在账户：刷新 `last_seen_at`、状态字段，必要时清理删除标记。
   - 缺失账户：标记 `is_active=False`、写入 `deleted_at`。
3. 返回统计信息与活跃账户列表，为权限同步提供输入。

### 阶段二：权限同步
1. 适配器执行 `fetch_permissions(instance, connection, active_accounts)`，返回权限集合（对象-操作列表）。
2. `PermissionManager` 对比本地权限表：
   - 新增/更新权限：插入或更新记录，记录更新时间、变更摘要。
   - 删除权限：标记失效或移除（根据业务要求）。
3. 汇总变更数量，供上层记录。

## 迁移步骤
1. **架构搭建**
   - 新建 `app/services/account_sync/` 目录结构，复制/调整容量同步中的协调器模式。
   - 提取现有 `sync_accounts` 中账户存在性维护逻辑至 `AccountInventoryManager`。
   - 提取权限对比逻辑到 `PermissionManager`。
   - 新增 `app/models/instance_account.py`（命名可调整），结构参考 `InstanceDatabase`，用于记录账户首次/最后出现时间、活跃状态、删除时间等，并在 `Instance` 模型中建立关系字段 `instance_accounts`。
   - 提供轻量级查询辅助模块（如 `account_query_service.py`），供页面/导出场景按实例获取账户数据。

### InstanceAccount 模型草案

Python 模型示例：

```python
class InstanceAccount(db.Model):
    __tablename__ = "instance_accounts"

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False, comment="账户名")
    db_type = db.Column(db.String(50), nullable=False, comment="数据库类型")
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="账户是否活跃")
    first_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    attributes = db.Column(db.JSON, nullable=True, comment="账户补充属性（主机、锁定状态等）")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    instance = db.relationship("Instance", back_populates="instance_accounts")

    __table_args__ = (
        db.UniqueConstraint("instance_id", "db_type", "username", name="uq_instance_account_instance_username"),
        db.Index("ix_instance_accounts_username", "username"),
        db.Index("ix_instance_accounts_active", "is_active"),
        db.Index("ix_instance_accounts_last_seen", "last_seen_at"),
        {"comment": "实例-账户关系表，维护账户存在状态"},
    )
```

对应 PostgreSQL 建表 SQL 参考：

```sql
CREATE TABLE instance_accounts (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    username VARCHAR(255) NOT NULL,
    db_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    attributes JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE instance_accounts
    ADD CONSTRAINT uq_instance_account_instance_username UNIQUE (instance_id, db_type, username);

CREATE INDEX ix_instance_accounts_username ON instance_accounts(username);
CREATE INDEX ix_instance_accounts_active ON instance_accounts(is_active);
CREATE INDEX ix_instance_accounts_last_seen ON instance_accounts(last_seen_at);
```

> 若项目使用 Alembic 迁移，可将上述 SQL 拆分到新迁移脚本中实现。

### CurrentAccountSyncData 调整建议

- 增加 `instance_account_id` 外键，指向 `instance_accounts.id`，以便权限表与库存表解耦。
- 保留 `instance_id + db_type + username` 唯一约束的同时，逐步过渡到以 `instance_account_id` 为主键引用（迁移可分阶段进行：先新增列并回填，再收缩旧约束）。
- 阶段二权限同步完成后，更新 `CurrentAccountSyncData` 相关字段，同时刷新 `InstanceAccount.last_seen_at`、`InstanceAccount.is_active` 等状态，保持两个模型的同步。
- 迁移脚本需要处理现有数据：为每条 `account_permission` 生成对应的 `instance_account` 记录，并填充新外键。
- 精简字段：`is_active`、`is_deleted`、`deleted_time` 等账户存在性相关字段迁移至 `InstanceAccount`；`CurrentAccountSyncData` 可保留权限快照及变更追踪字段（如 `last_sync_time`、`last_change_type`、`last_change_time`），确保职责单一。

参考 PostgreSQL 迁移片段：

```sql
ALTER TABLE account_permission
    ADD COLUMN instance_account_id INTEGER;

UPDATE account_permission AS casd
SET instance_account_id = ia.id
FROM instance_accounts AS ia
WHERE ia.instance_id = casd.instance_id
  AND ia.db_type = casd.db_type
  AND ia.username = casd.username;

ALTER TABLE account_permission
    ALTER COLUMN instance_account_id SET NOT NULL,
    ADD CONSTRAINT fk_current_account_instance_account
        FOREIGN KEY (instance_account_id) REFERENCES instance_accounts(id);

ALTER TABLE account_permission
    DROP COLUMN is_active,
    DROP COLUMN is_deleted,
    DROP COLUMN deleted_time;
```

2. **适配器改造**
   - `BaseSyncAdapter` 拆分为新的 `BaseAccountAdapter`，定义 `fetch_accounts` 与 `fetch_permissions` 两个必须实现的抽象方法。
   - 数据库适配器中拆出“账户列表查询”和“权限查询”两类 SQL/处理逻辑。

3. **协调器实现**
   - `AccountSyncCoordinator` 负责连接管理、顺序执行两阶段，并整合返回结果（新增账户数、删除账户数、权限新增/更新数等）。
   - 对外提供 `synchronize_accounts()`（阶段一）、`synchronize_permissions()`（阶段二）、`sync_all()`（完整流程）等接口。

4. **服务包装**
   - `AccountSyncService` 调整为调用协调器，维持原有 `sync_accounts` 方法签名与返回结构。

5. **日志与监控**
   - 在每个阶段添加结构化日志（如 `account_inventory_sync_completed`、`account_permission_sync_failed`）。
   - 汇总信息中明确区分账户阶段与权限阶段的结果。

6. **测试策略**
   - 为 `AccountInventoryManager` 编写单测覆盖新增/删除/恢复场景。
   - 为 `PermissionManager` 编写单测覆盖权限新增、变更、删除。
   - 适配器层使用假连接对象模拟不同返回值。

## 风险与缓解
- **历史行为变更风险**：通过保留 `AccountSyncService` 旧接口、在协调器内部逐步切换，确保外部调用方不感知。
- **数据一致性风险**：分阶段后需确保权限同步仅针对活跃账户，避免操作已删除账户；通过活跃列表过滤和事务控制缓解。
- **性能影响**：两阶段可能增加数据库交互次数，需要评估权限查询是否可与账户列表联合获取，或在协调器中支持合并模式。
- **开发成本**：适配器改造工作量较大（各数据库类型），需分批执行，可先支持主用数据库，再扩展至其他类型。

## 时间预估
- 架构搭建与协调器实现：2 天
- 适配器拆分（四种数据库）与单测：4 天
- 服务包装、文档更新、回归：1-2 天
- 总计：约 1.5 周（根据实际数据库数量与测试策略调整）

## 后续优化建议
- 支持“仅同步账户”或“仅刷新权限”的手动任务，提升运维灵活性。
- 引入权限差异审计日志，记录每次权限变更详情，支持追踪。
- 与容量同步共享基础设施（连接池、日志、监控指标），降低重复实现。
- 评估是否可以引入异步或分批机制，对大规模账户权限更新进行限速或拆分。

---
该提案最大化复用容量同步的成功经验，为账户同步提供清晰的阶段划分和抽象层次，便于后续扩展、监控及测试。*** End Patch
