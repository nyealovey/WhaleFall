# PostgreSQL 账户同步问题分析报告

## 现象与影响
- 所有 PostgreSQL 账户在控制台均标记为“已锁定”。
- 账户详情缺少预定义角色、角色属性、数据库/表空间权限等关键信息。
- 同步记录表 `account_permission` 中，PostgreSQL 的 `database_privileges_pg`、`tablespace_privileges` 为 `NULL`，前端展示受到影响。

## 根因快照
1. **锁定状态误判**：`AccountPermission.is_locked_display` 依赖 `type_specific.can_login`，但同步链路没有确保 `type_specific` 被填充。
2. **权限 JSON 字段名错误**：适配器返回键为 `database_privileges`，模型字段是 `database_privileges_pg`，写入时数据被丢弃。
3. **权限 SQL 取数不对**：
   - 数据库权限查询误用 `information_schema.role_table_grants`，该视图只包含表级权限。
   - 表空间权限查询误用 `information_schema.role_usage_grants`，不含 tablespace 信息。
4. **权限数据流不一致**：`_fetch_raw_accounts()` 将角色属性放在 `account["attributes"]`，`_normalize_account()` 却从 `permissions.type_specific` 读取，导致值始终为空；当前版本已淘汰 `account["attributes"]` 字段，所有残留引用都应移除。

## 详细分析

### 1. 锁定状态始终为真
`AccountPermission.is_locked_display`：
```python
if self.db_type == DatabaseType.POSTGRESQL:
    return not self.type_specific.get("can_login", True)
```
- 当 `type_specific` 为 `{}` 或 `None` 时默认返回 `False`，但同步结束后数据库中的 `type_specific` 实际为 `NULL`，原因是旧逻辑只把登录状态写入已废弃的 `account["attributes"]`，未同步到 `type_specific`。
- 结果：展示层读不到 `can_login`，统一显示“已锁定”。

### 2. 权限字段写入失败
`AccountPermission` 模型字段是 `database_privileges_pg`，适配器 `_get_role_permissions()` 返回：
```python
permissions = {
    "database_privileges": {},  # ❌ 字段名不匹配
}
```
ORM 在 `AccountPermissionManager._save_permission()` 内使用 `permissions.get("database_privileges_pg")`，拿不到值，最终写入 `NULL`。

### 3. 权限 SQL 不覆盖数据库级与表空间级
- `_get_database_privileges()` 查询 `information_schema.role_table_grants`，只能拿到表级 `SELECT/INSERT` 等权限，数据库级 CONNECT/CREATE/TEMP 永远缺失。
- `_get_tablespace_privileges()` 查询 `information_schema.role_usage_grants`，与表空间无关，返回空集。
- 正确方式：使用 `has_database_privilege()`、`has_tablespace_privilege()`，或结合 `pg_database` 与 `aclexplode(datacl)` 读取 ACL。

### 4. 属性来源不一致
- 历史实现中 `_fetch_raw_accounts()` 曾把角色属性写入 `account["attributes"]` 并在 `_normalize_account()` 中读取，但当前数据结构已完全移除该字段。
- 代码仍然引用 `account["attributes"]` 会导致 KeyError 或空值逻辑，必须改为只依赖 `permissions.type_specific`。
- 同时，`type_specific` 未填充时仍无法判定 `can_login`，需要在同步链路中统一来源。

## 修复建议

### 阶段 1：数据结构修复（优先级 P0）
- `enrich_permissions()`：不要再构造或依赖 `account["attributes"]`，直接在 `permissions.type_specific` 与 `permissions.role_attributes` 中填充 `can_login` 等字段。
- `_get_role_permissions()`：返回字典键改为 `database_privileges_pg`。
- `_normalize_account()`：彻底移除对 `account["attributes"]` 的访问，仅从 `permissions.type_specific` 读取；同步清理旧字段的传参和测试依赖。

### 阶段 2：权限查询纠偏（P1）
- 重写 `_get_database_privileges()`：
  - 通过 `has_database_privilege(username, datname, 'CONNECT/CREATE/TEMP')` 判断；
  - 或使用 `pg_database` + `aclexplode(datacl)` 过滤目标角色 OID。
- 重写 `_get_tablespace_privileges()`：使用 `has_tablespace_privilege(username, spcname, 'CREATE')`。
- 增加异常日志，区分“查询为空”与“SQL 失败”。

### 阶段 3：验证与回归（P1）
- 针对普通用户、只读用户、superuser 同步验证：
  - `type_specific.can_login` 与 `AccountPermission.is_locked_display` 行为正确；
  - `database_privileges_pg`、`tablespace_privileges` 数据完整；
  - 前端展示的角色属性、预定义角色与数据库一致。
- 新增测试用例覆盖：
  1. `enrich_permissions()` 会把 `can_login` 等字段填入 `permissions.type_specific`。
  2. `_normalize_account()` 全程不访问 `account["attributes"]`，并在 `type_specific` 缺失时提供安全默认值。
  3. `_get_database_privileges()` 解析 CONNECT/CREATE/TEMP 场景。

## 风险与注意事项
- `has_*_privilege` 查询需在主库执行；若走只读副本可能权限不足，需确认连接配置。
- 实例库较多时逐库调用 `has_database_privilege` 可能影响性能，可考虑批量查询或缓存角色 OID。
- 若历史存在正确的 `database_privileges_pg` 数据，部署前需评估是否补偿迁移。

## 后续动作清单
1. 完成阶段 1 修复后立即执行一次账户同步，确认锁定状态恢复正常。
2. 实现 SQL 调整后，在测试环境跑 `make test` 并人工对比权限结果。
3. 输出回归报告，列出修改模块、SQL 与验证步骤，为正式修复铺路。
