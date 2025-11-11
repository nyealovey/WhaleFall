# 账户锁定字段结构化重构方案

> 背景：`account_permission` 表当前仅依赖 `type_specific -> is_locked/is_disabled/...` 推导锁定状态。不同数据库字段含义不一，导致查询、统计、导出场景都需要解析 JSON，且当 `type_specific` 缺失或失真时 UI 会回退到 `InstanceAccount.is_active`，出现“真实已锁定但页面显示正常”的问题。为降低耦合，需要新增显式字段统一存储锁定状态。

## 1. 目标

1. 在 `account_permission` 表新增布尔字段 `is_locked`，表示“该账户是否处于锁定/禁用状态”。  
2. 同步链路与统计服务优先读写该字段；`type_specific` 仍可保留各数据库的详细信息（如 `account_status`、`locked_reason`）。  
3. 对外 API、列表、导出、报表统一使用 `AccountPermission.is_locked`，避免重复解析。

## 2. 数据模型改动

| 项目 | 说明 |
| --- | --- |
| 新增列 | `account_permission.is_locked BOOLEAN DEFAULT FALSE NOT NULL`（带索引 `idx_account_permission_locked` 以便筛选） |
| ORM 更新 | `AccountPermission` 模型新增 `is_locked = db.Column(db.Boolean, default=False, nullable=False, index=True)`；`is_locked_display` 属性改为优先返回该字段，若为 `None` 再回退到 `type_specific` |
| 兼容策略 | 迁移脚本在新增列后执行回填：根据现有 `type_specific` 推导锁定状态（同 `is_locked_display` 逻辑），并写入 `is_locked` |

## 3. 同步链路调整

1. **适配器** (`app/services/account_sync/adapters/*.py`)  
   - `_fetch_raw_accounts` / `_get_user_permissions` 的返回结构中新增顶层 `is_locked`。  
   - 在 `_normalize_account` 中设置：`account["is_locked"] = computed_value`，并写入 `permissions["type_specific"]` 供详情展示。  
2. **AccountPermissionManager**  
   - `remote` 数据中的 `is_locked` 直接传入 `AccountPermission.is_locked`（在 `_apply_permissions` 前处理）。  
   - diff 逻辑 (`_calculate_diff`) 纳入 `is_locked`，记录锁定状态变更。  
3. **InventoryManager / InstanceAccount**  
   - 仍以 `is_active` 区分“是否存在”。`is_locked` 不再反向影响 `is_active`，避免误判删除。  

## 4. API 与前端联动

| 模块 | 修改点 |
| --- | --- |
| `app/routes/account.py`, `app/routes/files.py` | 筛选条件新增对 `AccountPermission.is_locked` 的直接过滤；导出时不再解析 JSON。 |
| `app/routes/instance.py` | `/api/<id>/accounts` 的响应字段 `is_locked` 直接返回模型字段；仍保留 `type_specific` 细节。 |
| `templates/accounts/list.html` 等 | 模板与前端 JS 改为读取 `account.is_locked`（或 `is_locked_display` 兼容），保证 UI 一致。 |
| 统计服务 | `account_statistics_service` 直接基于 `is_locked` 计算锁定占比，减少多次解析。 |

## 5. 迁移计划

1. **数据库迁移**  
   - Alembic 迁移脚本：  
     1. `op.add_column('account_permission', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.false()))`  
     2. `op.create_index('idx_account_permission_locked', 'account_permission', ['is_locked'])`  
     3. 数据回填 SQL（分 DB 类型）：  
        ```sql
        UPDATE account_permission
        SET is_locked = TRUE
        WHERE (db_type = 'mysql' AND (type_specific->>'is_locked')::boolean IS TRUE)
           OR (db_type = 'postgresql' AND (type_specific->>'can_login')::boolean IS FALSE)
           OR (db_type = 'sqlserver' AND (type_specific->>'is_disabled')::boolean IS TRUE)
           OR (db_type = 'oracle' AND upper(type_specific->>'account_status') <> 'OPEN');
        ```  
     4. 移除 `server_default`，保持显式写入。
2. **回归验证**  
   - 各数据库实例分别同步一次，确认 `AccountPermission.is_locked` 符合原始数据。  
   - UI 列表、实例详情、导出 CSV 的锁定列与数据库对比。  
   - 统计报表（锁定/正常占比）与旧版本一致。

## 6. 风险与缓解

| 风险 | 缓解策略 |
| --- | --- |
| JSON 字段与新字段不一致 | 同步链路以 `is_locked` 为准，同时在调试日志中输出 `type_specific` 与 `is_locked`，发现差异立即报警。 |
| 旧代码仍引用 `type_specific.is_locked` | 搜索代码库并替换；在 `AccountPermission.is_locked_display` 中打印 deprecation warning（开发期使用）。 |
| 迁移回填耗时 | 批量更新可按数据库类型分批执行，并在低流量窗口进行；必要时写脚本分块处理。 |

## 7. 时间线

1. D1：完成 schema + ORM + 同步链路改造，本地回填验证。  
2. D2：联调前端、API，确保 UI 读取新字段。  
3. D3：灰度环境运行一次完整同步 + 对比报表；若无异常，合并进入 `main`。  
4. D4：生产执行迁移，并在 `make quality` 中增加检查（例如同步输出 `is_locked` 缺失报警）。

## 8. 追加优化：剥离 `grant_statements`

- MySQL 适配器仍使用 `SHOW GRANTS` 解析权限，保证 `global_privileges` / `database_privileges` 的准确性；  
- 但不再把原始 `grant_statements` 字符串数组写入 `type_specific`，避免 JSON 体膨胀及敏感信息泄漏；  
- 如需排查授权，可在同步日志中单次打印或让 DBA 手动 `SHOW GRANTS`，而不是长期保存在快照里。

通过此次重构，可以将“账户锁定”作为一等字段管理，消除跨数据库字段名差异带来的逻辑分叉，提升同步准确性和调试效率。***
