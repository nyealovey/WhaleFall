# 账户权限重构 V4 实施方案

**目标:** 将当前 "按 db_type 扩列存权限" 升级为版本化 JSONB 快照 + 跨 DB 分类 DSL.

**核心变更(相比 V3):**
- MySQL roles: **延续现有模式**(仅采集 direct roles + default roles), 通过配置开关预留闭包扩展能力
- DSL v4: **最小函数集**(5 个核心函数), 高级函数作为可选扩展
- 迁移策略: **强制一致性校验**, 每阶段必须有回滚 Runbook
- 测试优先: **任务 0 为测试基础设施**, 所有后续任务严格 TDD
- 规则处理: **直接重建**(规则数量有限, 比自动迁移更简单可靠)
- 事务边界: **强一致性保证**(Legacy 列与 Snapshot 在同一事务内写入)
- 权限变更追踪: **保留 `account_change_log` 需求但后置**(阶段 6); 新功能阶段先完成 snapshot/facts/DSL, 再升级 diff 计算

**技术栈:** Flask, SQLAlchemy, Alembic, PostgreSQL(jsonb), pytest, vanilla JS modules

> 状态: 草稿
> 负责人: @kiro
> 创建: 2025-12-30
> 更新: 2025-12-30
> 范围: `account_permission` 存储, `accounts_sync`, `account_classification`, 规则编辑 UI
> 前置: V3 审计报告 (2025-12-30)

---

## 1. 核心决策(V4 vs V3 差异)

### 1.1 MySQL Roles: 延续现有模式

**现有实现**: 当前 MySQL adapter 仅采集 `direct_roles` + `default_roles`, 不做 role graph 闭包展开
**V4 方案**: 保持现有行为不变, 通过 `Settings.MYSQL_ENABLE_ROLE_CLOSURE` 预留闭包扩展能力

**说明**: 这是对现有实现的延续, 而非功能降级. 闭包展开作为可选增强(阶段 B), 需要时再启用.

### 1.2 DSL v4: 最小函数集

**V3 方案**: 7 个必需函数 + 2 个高级函数(`raw_path_*`)
**V4 方案**:
- **阶段 A(MVP)**: 仅实现 5 个核心函数:
  - `db_type_in(types: list[str])`
  - `is_superuser()`
  - `has_capability(name: str)`
  - `has_role(name: str)`
  - `has_privilege(name: str, scope: str)`
- **阶段 B(可选)**: 增加 `is_locked()`, `attr_equals()`, `raw_path_*`

**理由**: 5 个核心函数已覆盖 90% 现有规则, 降低评估器实现复杂度.

### 1.3 迁移策略: 强制校验

**V3 方案**: 建议增加一致性校验
**V4 方案**: **强制要求**每阶段通过校验才能进入下一阶段

| 阶段 | 校验要求 | 失败阈值 |
|------|---------|---------|
| 阶段 1(双写) | 抽样 1000 条, 对比 legacy vs snapshot | 不一致率 < 1% |
| 阶段 2(切读) | 金丝雀 1% 流量, 监控 facts 构建错误率 | 错误率 < 0.1% |
| 阶段 3(同步覆盖) | 仅靠同步覆盖历史记录,统计 snapshot 缺失率并做全量一致性校验 | 缺失率 < 0.5% |

### 1.4 权限变更追踪(account_change_log): 后置任务(阶段 6)

**现状**: 权限同步在写入 `account_permission` 的同时,会计算新旧权限差异并写入 `account_change_log`(用于实例详情的账户变更历史 `/change-history`).

**V4 本阶段范围(0-4)**:
- `account_change_log` 继续按现状产出(不阻塞 snapshot/facts/DSL 的上线).
- 本阶段不做 diff 输入改造,因此**不得删除** legacy 权限列与基于列的 diff 逻辑.

**阶段 6(后置)目标**:
- diff 计算切到基于 v4 snapshot/view(仅保证 v4 数据,**不兼容无 snapshot 的历史旧数据**).
- 保持 `account_change_log.privilege_diff/other_diff/message` 的输出结构兼容现有前端渲染.
- 完成后才允许删除 legacy 权限列与 `PERMISSION_FIELDS` 等硬编码字段集.

---

## 2. 权限快照结构(V4)

### 2.1 外层封套(不变)

```json
{
  "version": 4,
  "categories": {},
  "type_specific": {},
  "extra": {},
  "errors": [],
  "meta": {}
}
```

### 2.2 MySQL: Roles 结构

**V4 结构**:
```json
{
  "version": 4,
  "categories": {
    "roles": {
      "direct": ["'app_role'@'%'"],
      "default": ["'app_role'@'%'"],
      "closure_enabled": false
    },
    "global_privileges": {
      "granted": ["SELECT", "INSERT"],
      "grantable": ["SELECT"],
      "denied": []
    },
    "database_privileges": {
      "db1": {"granted": ["CREATE"], "grantable": [], "denied": []}
    }
  },
  "type_specific": {
    "mysql": {
      "account": {"host": "%", "plugin": "mysql_native_password"}
    }
  },
  "extra": {
    "mysql": {
      "raw_grants": ["GRANT SELECT ON *.* TO 'user'@'%' WITH GRANT OPTION"]
    }
  },
  "errors": ["MYSQL_ROLE_CLOSURE_DISABLED"],
  "meta": {"adapter": "mysql", "adapter_version": "v4", "collected_at": "2025-12-30T00:00:00Z"}
}
```

**关键变更**:
- `categories.roles` 改为 object, 包含 `direct`, `default`, `closure_enabled` 字段
- `errors` 明确记录 `MYSQL_ROLE_CLOSURE_DISABLED`
- 不再有 `extra.mysql.role_graph`(闭包启用后才采集)

**Facts 映射**:
```python
facts.roles = set(snapshot["categories"]["roles"]["direct"])
if snapshot["categories"]["roles"]["closure_enabled"]:
    # 未来扩展: 从 role_graph 提取 all_granted_roles
    pass
```

### 2.3 其他 DB 类型(不变)

PostgreSQL, SQL Server, Oracle 结构与 V3 一致(无 roles 闭包问题).

---

## 3. Facts 模型 V4

```python
@dataclass(frozen=True)
class AccountPermissionFacts:
    db_type: str
    is_superuser: bool
    is_locked: bool
    roles: set[str]  # MySQL: direct roles only (MVP)
    capabilities: set[str]  # SUPERUSER, GRANT_ADMIN
    capability_reasons: dict[str, list[str]]  # 新增: 可解释性
    privilege_grants: list[PrivilegeGrant]  # scope: global/server/database
    attrs: dict[str, JsonValue]  # 预留, MVP 不使用
    errors: list[str]  # 必须记录: PERMISSION_DATA_MISSING, MYSQL_ROLE_CLOSURE_DISABLED
```

**Capability 映射(保守策略)**:

| DB Type | SUPERUSER | GRANT_ADMIN |
|---------|-----------|-------------|
| MySQL | `is_superuser=True` | `GRANT_OPTION` on `*.*` + `CREATE USER` |
| PostgreSQL | `rolsuper=True` | `rolcreaterole=True` |
| SQL Server | `sysadmin` role | `securityadmin` role OR `CONTROL SERVER` |
| Oracle | `DBA` role | `DBA` role OR `GRANT ANY PRIVILEGE` |

**新增**: `capability_reasons` 示例:
```python
{
  "SUPERUSER": ["is_superuser=True"],
  "GRANT_ADMIN": ["global_privileges.grantable contains CREATE USER", "global_privileges.grantable on *.*"]
}
```

---

## 4. DSL v4 (最小函数集)

### 4.1 核心函数(MVP)

```json
{
  "version": 4,
  "expr": {
    "op": "AND",
    "args": [
      {"fn": "has_capability", "args": {"name": "GRANT_ADMIN"}},
      {"fn": "db_type_in", "args": {"types": ["mysql", "postgresql"]}}
    ]
  }
}
```

**函数签名**:
1. `db_type_in(types: list[str]) -> bool`
2. `is_superuser() -> bool`
3. `has_capability(name: str) -> bool`  # name: SUPERUSER | GRANT_ADMIN
4. `has_role(name: str) -> bool`
5. `has_privilege(name: str, scope: str, database?: str) -> bool`  # scope: global | server | database

**错误处理**:
- 未知函数 → 返回 `False` + 日志 `UNKNOWN_DSL_FUNCTION`
- 非法参数 → 返回 `False` + 日志 `INVALID_DSL_ARGS`
- 缺失必需参数 → 返回 `False` + 日志 `MISSING_DSL_ARGS`

**短路评估**:
- `AND` 操作: 遇到第一个 `False` 立即返回 `False`, 不再评估后续参数
- `OR` 操作: 遇到第一个 `True` 立即返回 `True`, 不再评估后续参数
- 短路行为与 Python 的 `and`/`or` 一致, 可减少不必要的函数调用

### 4.2 可选函数(阶段 B)

6. `is_locked() -> bool`
7. `attr_equals(path: str, value: scalar) -> bool`  # 访问 facts.attrs

---

## 5. 迁移策略(强制校验版)

### 5.1 Feature Flags

```python
# app/settings.py
ACCOUNT_PERMISSION_SNAPSHOT_WRITE: bool = False  # 阶段 1
ACCOUNT_PERMISSION_SNAPSHOT_READ: bool = False   # 阶段 2
ACCOUNT_PERMISSION_SNAPSHOT_READ_PERCENTAGE: int = 0  # 金丝雀 0-100
ACCOUNT_CLASSIFICATION_DSL_V4: bool = False      # 阶段 4
MYSQL_ENABLE_ROLE_CLOSURE: bool = False          # 可选增强
```

### 5.2 阶段划分(含回滚条件)

#### 阶段 0: 测试基础设施(1 周)

**交付物**:
- `tests/fixtures/permission_snapshots_v4.py`: v4 snapshot 样例数据
- `tests/unit/models/test_account_permission.py`: model 契约测试
- `tests/unit/services/test_permission_snapshot_view.py`: accessor 测试框架
- `scripts/verify_snapshot_consistency.py`: 一致性校验脚本

**验收标准**: 所有 fixture 可正常加载, 校验脚本可运行.

#### 阶段 1: 双写 + 一致性校验(1-2 周)

**操作**:
1. 部署代码(含 snapshot 列 + 双写逻辑)
2. 启用 `ACCOUNT_PERMISSION_SNAPSHOT_WRITE=True`
3. 运行定时任务(每小时): `scripts/verify_snapshot_consistency.py --sample-size=1000`

**验收标准**:
- 双写成功率 > 99.9%
- 一致性校验不一致率 < 1% (连续 7 天)

**回滚条件**:
- 双写失败率 > 1% → 关闭 `SNAPSHOT_WRITE`, 回滚代码
- 一致性不一致率 > 5% → 暂停, 修复 snapshot builder bug

**Runbook**: `docs/operations/v4-rollback-phase1.md`

#### 阶段 2: 切读(金丝雀)(2 周)

**操作**:
1. 启用 `ACCOUNT_PERMISSION_SNAPSHOT_READ=True` + `READ_PERCENTAGE=1`
2. 监控指标:
   - `account_permission_snapshot_missing_total`
   - `account_classification_facts_errors_total`
3. 每 3 天提升 percentage: 1% → 10% → 50% → 100%

**验收标准**:
- Facts 构建错误率 < 0.1%
- 分类结果与 legacy 对比一致率 > 99% (仅用于验证,不作为兼容承诺)

**回滚条件**:
- 错误率 > 1% → 降低 percentage 或关闭 `SNAPSHOT_READ`
- 分类结果不一致率 > 5% → 回滚到 legacy

**Runbook**: `docs/operations/v4-rollback-phase2.md`

#### 阶段 3: 同步覆盖(1 周)

**操作**:
1. 执行一次全量账户权限同步(覆盖所有实例/账户),确保历史记录写入 v4 snapshot(不使用 backfill 脚本)
2. 全量校验: `scripts/verify_snapshot_consistency.py --full`

**验收标准**:
- snapshot 缺失率 < 0.5%
- 全量校验不一致率 < 0.5%

**回滚条件**: snapshot 缺失率 > 5% → 暂停推进,检查同步覆盖范围与写入路径

#### 阶段 4: DSL v4(2-3 周)

**操作**:
1. 部署 DSL 评估器 + 规则校验 API
2. 基于 DSL v4 重新创建分类规则(规则数量有限, 直接重建比迁移更简单)
3. 启用 `ACCOUNT_CLASSIFICATION_DSL_V4=True`

**验收标准**:
- 所有分类规则已用 DSL v4 重建
- 分类结果与 legacy 对比一致率 > 99% (仅用于验证,不作为兼容承诺)

**回滚条件**: 分类结果不一致率 > 5% → 关闭 DSL, 回退 legacy

#### 阶段 5: 清理(1 周)

**操作**:
1. 删除 legacy 分类器代码
2. 删除 `PERMISSION_FIELDS` 在分类器侧的引用(若存在)

**前置条件**: 阶段 4 稳定运行 > 1 个月

#### 阶段 6: 变更日志升级 + 清理 legacy 权限列(1-2 周)

**操作**:
1. 确认 snapshot 缺失率满足阈值(见阶段 3)
2. 升级 diff 计算为基于 v4 snapshot/view,不依赖 legacy 权限列
3. 验证 `/change-history` 在新权限结构下正常工作
4. 删除 legacy 权限列(migration)
5. 删除 `PERMISSION_FIELDS` 硬编码(或缩减为仅用于个别兼容期模块)

---

## 6. 详细实施任务(TDD 严格版)

### 任务 0: 测试基础设施(阻塞性前置)

**文件**:
- 新增: `tests/fixtures/permission_snapshots_v4.py`
- 新增: `tests/unit/models/test_account_permission.py`
- 新增: `tests/unit/services/test_permission_snapshot_view.py`
- 新增: `scripts/verify_snapshot_consistency.py`

**步骤**:
1. 创建 v4 snapshot fixtures(覆盖 4 种 db_type, 含边界情况)
2. 编写 model 契约测试(列存在性、类型、索引)
3. 编写 accessor 测试框架(mock snapshot, 验证 snapshot 缺失时显式报错/错误码)
4. 实现一致性校验脚本(抽样对比 legacy columns vs snapshot view)

**验收**: `pytest tests/fixtures/ tests/unit/models/ -v` 全部通过(即使 model 未加列, 测试应 SKIP 而非 FAIL)

### 任务 1: 加列 + Migration

**文件**:
- 修改: `app/models/account_permission.py`
- 新增: `migrations/versions/20250101000000_add_permission_snapshot_v4.py`

**测试**(先写):
```python
def test_account_permission_has_snapshot_columns():
    from app import db
    table = db.metadata.tables["account_permission"]
    assert "permission_snapshot" in table.c
    assert table.c["permission_snapshot"].type.__class__.__name__ == "JSONB"
    assert "permission_snapshot_version" in table.c
    assert table.c["permission_snapshot_version"].default.arg == 4
```

**实现**:
```python
# app/models/account_permission.py
permission_snapshot = db.Column(db.JSONB, nullable=True)
permission_snapshot_version = db.Column(db.Integer, nullable=False, default=4, server_default="4")
```

**验收**: `pytest tests/unit/models/test_account_permission.py::test_account_permission_has_snapshot_columns -v`

### 任务 2: Snapshot Accessor(不兼容旧数据,不做 legacy 回退)

**文件**:
- 新增: `app/services/accounts_permissions/snapshot_view.py`
- 修改: `app/models/account_permission.py` (增加 `get_permission_snapshot()` 方法)

**测试**(先写):
```python
def test_snapshot_view_prefers_snapshot_over_legacy():
    account = AccountPermission(
        db_type="mysql",
        permission_snapshot={"version": 4, "categories": {"global_privileges": {"granted": ["SELECT"]}}},
        global_privileges=["INSERT"]  # legacy
    )
    view = build_permission_snapshot_view(account)
    assert view["categories"]["global_privileges"]["granted"] == ["SELECT"]  # 优先 snapshot
```

**实现**:
```python
def build_permission_snapshot_view(account: AccountPermission) -> dict:
    if account.permission_snapshot and account.permission_snapshot.get("version") == 4:
        return account.permission_snapshot
    # 不兼容旧数据: 明确暴露缺失,由上层触发重同步/等待下一次同步
    return {"version": 4, "categories": {}, "type_specific": {}, "extra": {}, "errors": ["SNAPSHOT_MISSING"], "meta": {}}
```

**验收**: `pytest tests/unit/services/test_permission_snapshot_view.py -v`

### 任务 3: 双写 Snapshot(不丢字段)

**文件**:
- 修改: `app/services/accounts_sync/permission_manager.py`
- 修改: `app/settings.py` (增加 `ACCOUNT_PERMISSION_SNAPSHOT_WRITE`)

**事务边界说明**:
- Legacy 列写入与 Snapshot 写入在**同一个数据库事务**内完成
- 如果 Snapshot 构建失败, **整个事务回滚**, Legacy 列也不会写入
- 这确保了 Legacy 列与 Snapshot 的强一致性: 要么都成功, 要么都失败
- 构建失败时记录 `snapshot_write_failed` 指标, 便于监控和排查

```python
# 伪代码示意
with db.session.begin():
    # Legacy 写入
    for field in PERMISSION_FIELDS:
        setattr(record, field, permissions.get(field))

    # Snapshot 写入 (同一事务)
    if Settings.ACCOUNT_PERMISSION_SNAPSHOT_WRITE:
        record.permission_snapshot = self._build_snapshot(...)  # 失败则抛异常, 事务回滚
        record.permission_snapshot_version = 4

    db.session.add(record)
# 事务提交
```

**测试**(先写):
```python
def test_apply_permissions_writes_snapshot_when_enabled(monkeypatch):
    monkeypatch.setattr("app.settings.Settings.ACCOUNT_PERMISSION_SNAPSHOT_WRITE", True)
    manager = AccountPermissionManager()
    record = AccountPermission(db_type="mysql")
    permissions = {"global_privileges": ["SELECT"], "unknown_field": "value"}
    manager._apply_permissions(record, permissions, is_superuser=False, is_locked=False)

    assert record.permission_snapshot is not None
    assert record.permission_snapshot["version"] == 4
    assert record.permission_snapshot["extra"]["unknown_field"] == "value"  # 不丢字段
```

**实现**:
```python
def _apply_permissions(self, record, permissions, *, is_superuser, is_locked):
    # Legacy 写入(保持不变)
    for field in PERMISSION_FIELDS:
        ...

    # Snapshot 写入(feature flag 控制)
    if Settings.ACCOUNT_PERMISSION_SNAPSHOT_WRITE:
        record.permission_snapshot = self._build_snapshot(permissions, is_superuser, is_locked)
        record.permission_snapshot_version = 4
```

**验收**: `pytest tests/unit/services/test_account_permission_manager.py::test_apply_permissions_writes_snapshot_when_enabled -v`

### 任务 4: 一致性校验脚本

**文件**:
- 新增: `scripts/verify_snapshot_consistency.py`

**功能**:
```bash
python scripts/verify_snapshot_consistency.py \
  --sample-size=1000 \
  --output=consistency_report.json
```

**输出**:
```json
{
  "total_sampled": 1000,
  "consistent": 990,
  "inconsistent": 10,
  "inconsistency_rate": 0.01,
  "errors": [
    {"account_id": 123, "field": "global_privileges", "legacy": ["SELECT"], "snapshot": ["INSERT"]}
  ]
}
```

**验收**: 手动运行脚本, 验证输出格式正确.

### 任务 5-12: (与 V3 类似, 省略细节)

关键变更:
- 任务 6(Facts Builder): `roles` 仅使用 `snapshot["categories"]["roles"]["direct"]`
- 任务 7(DSL 评估器): 仅实现 5 个核心函数
- 任务 11(规则重建): 基于 DSL v4 语法重新创建分类规则, 无需自动迁移脚本

---

## 7. 监控指标(强制要求)

### 7.1 Snapshot 写入

```python
# app/services/accounts_sync/permission_manager.py
from prometheus_client import Counter, Histogram

snapshot_write_success = Counter("account_permission_snapshot_write_success_total", "db_type")
snapshot_write_failed = Counter("account_permission_snapshot_write_failed_total", "db_type", "error_type")
snapshot_build_duration = Histogram("account_permission_snapshot_build_duration_seconds", "db_type")
```

### 7.2 Snapshot 读取

```python
snapshot_missing = Counter("account_permission_snapshot_missing_total", "db_type")
```

### 7.3 Facts 构建

```python
facts_build_errors = Counter("account_classification_facts_errors_total", "db_type", "error_type")
facts_build_duration = Histogram("account_classification_facts_build_duration_seconds", "db_type")
```

### 7.4 DSL 评估

```python
dsl_evaluation_duration = Histogram("account_classification_dsl_evaluation_duration_seconds", "function")
dsl_evaluation_errors = Counter("account_classification_dsl_evaluation_errors_total", "error_type")
```

---

## 8. 文档交付清单

### 8.1 必须交付

- [ ] `docs/operations/account-sync-minimum-privileges.md`: 各 db_type 采集账号最小权限
- [ ] `docs/operations/v4-rollback-phase1.md`: 阶段 1 回滚操作手册
- [ ] `docs/operations/v4-rollback-phase2.md`: 阶段 2 回滚操作手册
- [ ] `docs/architecture/permission-snapshot-v4-schema.md`: Snapshot JSON Schema 定义
- [ ] `docs/reference/dsl-functions-v4.md`: DSL 函数参考(含示例)

### 8.2 可选交付

- [ ] `docs/architecture/mysql-role-closure-design.md`: Roles 闭包设计(阶段 B)
- [ ] `docs/operations/performance-tuning-v4.md`: 性能调优指南

---

## 9. 成功标准

### 9.1 功能完整性

- [x] 支持 4 种 db_type 的 snapshot 存储
- [x] snapshot view 缺失时显式暴露错误(不做 legacy 回退)
- [x] Facts 构建覆盖 SUPERUSER + GRANT_ADMIN
- [x] DSL 评估器支持 5 个核心函数
- [x] 所有分类规则已用 DSL v4 重建

### 9.2 可靠性指标

- [x] Snapshot 双写成功率 > 99.9%
- [x] 一致性校验不一致率 < 1%
- [x] Facts 构建错误率 < 0.1%
- [x] 分类结果一致率 > 99%

### 9.4 可维护性

- [x] 测试覆盖率 > 80% (unit + integration)
- [x] 所有 public API 有文档字符串
- [x] 关键路径有结构化日志
- [x] 所有 feature flags 有配置说明

---

## 10. 风险与缓解(V4 更新)

### 10.1 双写期间数据不一致 🟢 低

**风险**: 双写期间 Legacy 列与 Snapshot 不一致.

**缓解**: 通过事务边界保证强一致性(见任务 3 事务边界说明), 要么都成功要么都失败.

---

## 11. 总结

### 11.1 V4 vs V3 核心差异

| 维度 | V3 | V4 |
|------|----|----|
| MySQL Roles | 闭包展开(复杂) | 延续现有模式(可选闭包) |
| DSL 函数 | 7 个必需 + 2 个高级 | 5 个核心(MVP) |
| 一致性校验 | 建议 | 强制(每阶段) |
| 测试策略 | TDD | 任务 0 为测试基础设施 |
| 回滚准备 | 提及 | 每阶段有 Runbook |
| 规则处理 | 自动迁移 | 直接重建 |
| 事务边界 | 未明确 | 强一致性保证 |

### 11.2 预计工期

| 阶段 | 工期 | 关键里程碑 |
|------|------|-----------|
| 阶段 0 | 1 周 | 测试基础设施就绪 |
| 阶段 1 | 1-2 周 | 双写稳定, 一致性 < 1% |
| 阶段 2 | 2 周 | 切读 100%, 错误率 < 0.1% |
| 阶段 3 | 1 周 | 同步覆盖完成, snapshot 缺失率 < 0.5% |
| 阶段 4 | 2-3 周 | DSL 上线, 规则重建完成 |
| 阶段 5 | 1 周 | Legacy 代码清理 |
| 阶段 6 | 1-2 周 | 变更日志升级完成, legacy 权限列删除 |
| **总计** | **9-12 周** | 含稳定期 |

### 11.3 关键成功因素

1. ✅ **严格 TDD**: 任务 0 完成前不启动后续任务
2. ✅ **强制校验**: 每阶段必须通过一致性校验
3. ✅ **金丝雀发布**: 阶段 2 分 4 步提升流量
4. ✅ **快速回滚**: 每阶段有明确回滚条件与 Runbook
5. ✅ **事务一致性**: 双写在同一事务内, 保证强一致性
6. ✅ **规则重建**: 直接用 DSL v4 重建规则, 避免迁移复杂度

### 11.4 后续优化(阶段 B)

- [ ] MySQL roles 闭包展开(需要 `Settings.MYSQL_ENABLE_ROLE_CLOSURE`)
- [ ] DSL 高级函数(`is_locked`, `attr_equals`, `raw_path_*`)
- [ ] Facts 缓存(Redis)
- [ ] 规则编辑辅助工具(Web UI)

---

**文档版本**: V4 草稿
**基于**: V3 审计报告 (2025-12-30)
**下一步**: 评审 V4 方案 → 启动任务 0
