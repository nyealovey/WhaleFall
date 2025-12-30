# Account Permission Storage v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将当前 `account_permission` “按数据库类型拆列存权限”的模式升级为“可扩展的 JSONB 权限快照(版本化)”存储, 在不频繁改表的前提下支持新增数据库类型, 且不破坏既有的账户分类管理能力(规则评估/分配/台账与实例详情权限展示)。

**Architecture:** 在 `account_permission` 表新增 `permission_snapshot`(jsonb) 与 `permission_snapshot_version`(int) 作为权限真源, 通过兼容层实现“优先读新字段, 缺失回退读旧字段”, 同步阶段先双写(新字段 + 旧列), 完成切读与回填后再删除旧列与硬编码字段清单。

**Tech Stack:** Flask, SQLAlchemy, Alembic, PostgreSQL(jsonb), pytest

> 状态: Draft
> 创建: 2025-12-29
> 更新: 2025-12-29
> 范围: `account_permission` 存储结构, 账户同步(accounts_sync), 账户分类(account_classification), 权限详情(实例详情/台账)
> 关联: `app/models/account_permission.py`, `app/services/accounts_sync/permission_manager.py`, `app/services/account_classification/**`, `app/services/instances/instance_accounts_service.py`, `app/services/ledgers/accounts_ledger_permissions_service.py`

---

## 1. 背景与问题

当前 `AccountPermission` 采用“按 db_type 固定列”存储权限(例如 MySQL 用 `global_privileges/database_privileges`, PostgreSQL 用 `predefined_roles/database_privileges_pg`, SQLServer 用 `server_roles/database_permissions`, Oracle 用 `oracle_roles/system_privileges` 等)。该方案在扩展性和一致性上存在明显问题:

- **新增数据库类型成本高**: 新增一种 DB(例如 MongoDB/Redis/ClickHouse)需要改表 + 增加列 + 更新 `PERMISSION_FIELDS` 等硬编码清单 + 更新多处 service/DTO/页面逻辑, 扩展路径不闭环。
- **权限结构割裂**: 同一语义(例如“数据库级权限”)在不同 DB 中落到不同列名(`database_privileges` vs `database_privileges_pg`), 需要额外适配层, 进一步增加维护成本。
- **表结构稀疏**: 单行只使用其 db_type 对应少量字段, 其余列常为 NULL, 既增加理解成本也增加数据迁移与演进成本。
- **分类功能强依赖固定字段**: 账户分类的规则表达式与分类器实现基于当前固定字段/固定 key, 若引入新 DB 类型, 需要新增分类器与 UI 配置并同步演进存储结构。

结论: 权限快照属于“结构随 DB 类型变化/随版本变化”的半结构化数据, 更适合以 **JSONB 真源 + 版本化 + 兼容读取** 的方式存储, 而不是持续扩列。

---

## 2. 目标 / 非目标

### 2.1 目标

- **可扩展存储**: 新增 DB 类型时不需要改 `account_permission` 表结构即可落库权限快照。
- **版本化**: 权限快照 schema 可演进, 支持向前/向后兼容读取与逐步迁移。
- **账户分类不破坏**: 现有分类规则表达式与分类器可继续工作(至少通过兼容层过渡)。
- **灰度迁移**: 支持双写、回填、切读、回滚, 不中断同步与页面展示。

### 2.2 非目标(本期不做)

- 不重写账户分类规则 DSL(仍沿用现有 `rule_expression` 结构, 后续可另起计划统一为跨 DB 通用 DSL)。
- 不引入“权限项搜索/统计引擎”(如按权限名全库检索)；仅预留索引/扁平化表的扩展点。
- 不一次性删除旧列(先保证可回滚, 再逐步收敛)。

---

## 3. 现状代码盘点(兼容/防御/回退/适配)

> 说明: 本节按仓库约定输出“位置/类型/描述/建议”, 重点关注 `or` 兜底与字段适配逻辑。

- 位置：`app/models/account_permission.py:51`
  - 类型：兼容(legacy 存储形态固化)
  - 描述：按 db_type 拆分固定 JSON 列存权限, 扩展新 DB 类型需要新增列并同步修改多处代码。
  - 建议：新增 `permission_snapshot`(jsonb) 作为真源, 固定列变为“可选缓存/过渡字段”, 最终删除。

- 位置：`app/services/accounts_sync/permission_manager.py:43`
  - 类型：兼容/防御
  - 描述：`PERMISSION_FIELDS` 硬编码列清单, `_apply_permissions()`(`app/services/accounts_sync/permission_manager.py:415`) 逐字段写入/清空, 未出现的字段会被置为 None(除 `type_specific` 保留原值)。
  - 建议：改为写入 `permission_snapshot` 一次性落库; 旧字段仅在过渡期双写或由快照派生。

- 位置：`app/models/account_permission.py:129`
  - 类型：适配(字段别名/形态统一)
  - 描述：`get_permissions_by_db_type()` 对不同 DB 做 key 适配, 例如 PostgreSQL 将 `database_privileges_pg` 映射为返回值中的 `database_privileges`(`app/models/account_permission.py:142`)。
  - 建议：将“适配层”从“列名适配”升级为“快照 schema 适配”(优先读 `permission_snapshot`, 缺失回退旧列)；明确版本字段, 避免跨 DB 复用同名列造成语义漂移。

- 位置：`app/services/account_classification/classifiers/mysql_classifier.py:68`
  - 类型：防御(兜底/容错)
  - 描述：分类器通过 `permissions = account.get_permissions_by_db_type() or {}` 做空值兜底, 避免权限快照缺失时报错。
  - 建议：在 `AccountPermission` 层提供 `get_permission_snapshot()`/`get_permissions_view()` 统一兜底, 分类器无需关注新旧来源。

- 位置：`app/services/instances/instance_accounts_service.py:43`
  - 类型：防御(兜底) / 适配(按 db_type 分支)
  - 描述：大量 `getattr(..., None) or []/{}` 用于空值兜底, 且权限详情/列表输出通过 `instance.db_type == ...` 进行固定分支映射, 新 DB 类型无法无痛扩展。
  - 建议：引入“按 PermissionConfig 分组渲染”的通用权限输出结构(例如 `categories: dict[str, Any]`), 对已支持 DB 保持兼容字段, 对新 DB 走通用结构。

- 位置：`app/services/ledgers/accounts_ledger_permissions_service.py:62`
  - 类型：适配/防御
  - 描述：SQL Server 权限详情对 `database_permissions` 进行二次“简化提取”(将复杂结构提取为 `dict[str, list[str]]`), 同时使用 `or {}` 兜底。
  - 建议：把“权限快照规范化(含简化视图)”下沉到统一的快照适配层, Service 层只消费稳定 DTO。

---

## 4. 方案选型

### Option A(推荐): JSONB 权限快照作为真源 + 版本化 + 兼容层

- **存储**: 新增 `permission_snapshot`(jsonb) 存整份权限快照, `permission_snapshot_version` 表示 schema 版本。
- **演进**: 新 DB 类型新增适配器输出结构即可(不改表), 可通过版本字段做迁移/兼容。
- **分类**: `AccountPermission.get_permissions_by_db_type()` 改为“从快照读取 + 旧列回退”, 现有分类器/规则表达式不需要立刻变更。
- **风险**: 若未来需要大量基于权限项的 DB 侧检索/聚合, 纯 JSONB 可能需要额外索引或扁平化表。

### Option B: 权限项扁平化(EAV/Grant 表)

- **存储**: 新建 `account_permission_grants` 以行形式存每条授权/角色等。
- **优点**: 更易 SQL 查询/统计。
- **缺点**: 设计与迁移成本高; 各 DB 权限模型差异大, 需要定义复杂的通用范式。

### Option C: Hybrid(JSONB 真源 + 可选扁平化索引表)

- 在 Option A 基础上, 为“常用筛选/统计”维护一张可选索引表(或数组字段)。
- 适合后期出现明确查询诉求后再做。

本次重构推荐 **Option A**, 并在设计中为 Option C 预留扩展点。

---

## 5. 新数据模型(AccountPermission v2)

### 5.1 表结构增量

在 `account_permission` 表新增字段:

- `permission_snapshot` (jsonb, nullable): 权限快照真源, 存储 `PermissionSnapshot` 字典。
- `permission_snapshot_version` (int, not null, default=1): 快照 schema 版本。

说明:

- `is_superuser/is_locked/last_sync_time/last_change_*` 继续保留为结构化列, 便于筛选/排序与兼容现有逻辑。
- 旧的权限列(`global_privileges` 等)在 Phase 1/2 继续保留用于双写与回滚, Phase 3 再删除。

### 5.2 快照内容约定

`permission_snapshot` 推荐直接复用 `app/types/accounts.py::PermissionSnapshot` 作为“快照 payload”, 允许额外 key(向前兼容), 关键点:

- `type_specific`: 存账户属性/元信息(例如 MySQL host/plugin, Oracle created/lock_date 等)。
- `errors`: 采集过程中出现的错误列表(若有)。
- `extra`: 预留扩展字段, 新 DB 类型或新版本优先落到这里, 再逐步标准化为顶层 category。
- **展示明细**：展示页需要呈现 schema/table/object 明细时，允许在快照中保留更细粒度的 raw grants（例如 `table_privileges/object_privileges` 等，或落入 `extra.raw_*`）；但分类/DSL v2 不直接消费这些明细（仅消费 Facts）。

**新增 DB 类型的约束建议:**

- category 命名尽量与 `permission_configs.category` 对齐, 便于 UI 展示与规则构建。
- 不要复用已有 category 但语义不一致(避免类似 “system_privileges 在不同 DB 下含义漂移” 的问题)。

---

## 6. 与“账户分类管理”的关系与改造点

### 6.1 现状依赖

- 分类规则实体: `ClassificationRule.rule_expression`(JSON text)。
- 分类器: `app/services/account_classification/classifiers/*` 通过 `account.get_permissions_by_db_type()` 获取权限视图进行评估。
- 分配关系: `AccountClassificationAssignment.account_id` 外键指向 `account_permission.id`(`migrations/versions/20251219161048_baseline_production_schema.py` 中可见)。

### 6.2 兼容策略(保证“不破坏”)

在 Phase 2 之前, **不改规则表达式结构**, 仅调整权限读取来源:

- `AccountPermission.get_permissions_by_db_type()`:
  - 若 `permission_snapshot` 存在, 从快照中取所需 category, 并保持返回 dict 的 key 与当前分类器预期一致。
  - 若快照缺失, 回退旧列逻辑(当前实现)。

这样可以保证:

- 历史规则表达式不需要迁移即可继续使用。
- 分类器实现无需立刻修改, 仅底层数据来源切换。

### 6.3 后续演进(可选)

当新增 DB 类型数量变多后, 建议另起计划将分类规则 DSL 统一为“跨 DB 通用表达式”, 并提供:

- 通用谓词: `has_privilege(name, scope=...)`, `has_role(name)`, `is_superuser`, `is_locked`, `attr_equals(key, value)` 等。
- DB 特性谓词走 `type_specific`/`extra` 的命名空间。

---

## 7. 分阶段落地计划(推荐)

### Phase 1: 增字段 + 双写(最小改动, 可回滚)

目标: 不影响线上行为的前提下, 将快照落库并开始积累数据。

关键动作:

- Alembic 增加 `permission_snapshot/permission_snapshot_version` 两列。
- `AccountPermissionManager._apply_permissions()` 额外写入 `permission_snapshot`(仍保持旧列写入不变)。

验收:

- 同步流程正常, `account_permission.permission_snapshot` 开始有数据。
- UI/分类/台账行为不变。

### Phase 2: 切读(服务/分类优先读快照, 缺失回退旧列)

目标: 将读取侧从“固定列”迁移到“快照”, 同时保持兼容回退。

关键动作:

- `AccountPermission.get_permissions_by_db_type()` 改为优先读快照。
- 权限详情相关 Service(`InstanceAccountsService`, `AccountsLedgerPermissionsService`) 使用统一 accessor 从快照取值(缺失回退)。
- 若存在 “快照缺失” 的历史数据, 仍能通过旧列展示。

验收:

- 在有快照/无快照两类数据下, API contract 均稳定。

### Phase 3: 回填 + 删除旧列(收敛技术债)

目标: 快照成为唯一真源, 移除固定列与硬编码字段清单。

关键动作:

- 一次性回填脚本: 将旧列组合写入 `permission_snapshot`(仅针对快照为空的记录)。
- 删除旧列与 `PERMISSION_FIELDS` 相关写入/清空逻辑; diff/日志改为基于快照对比。

验收:

- `account_permission` 表不再随 DB 类型扩列。
- 新 DB 类型仅需: 新适配器输出 + PermissionConfig 配置 + (可选)分类器/规则 UI 支持。

---

## 8. 回滚策略

在 Phase 1/2 保留旧列的前提下:

- 回滚为“代码回滚”: 读取侧恢复使用旧列; `permission_snapshot` 可忽略。
- 数据无需回滚: 双写期间旧列仍是可用数据源。

仅在 Phase 3 删除旧列前需要明确回滚窗口与备份策略。

---

## 9. 测试策略(建议最小覆盖)

- 单元测试:
  - `AccountPermission.get_permissions_by_db_type()` 在以下场景返回一致:
    - 仅旧列有值
    - `permission_snapshot` 有值(优先读)
    - 两者都有值(快照优先)
  - `AccountPermissionManager._apply_permissions()` 会写入 `permission_snapshot`。
- API contract:
  - 现有 `tests/unit/routes/test_api_v1_instances_contract.py` 与 `tests/unit/routes/test_api_v1_accounts_ledgers_contract.py` 不应因新增列而破坏。

推荐命令:

- `pytest -m unit`

---

## 10. Implementation Tasks(按执行顺序)

> 说明: 这里给出可执行的落地任务清单(偏工程执行), 具体实现可在执行阶段再细化。

### Task 1: 增加 `permission_snapshot` 字段(模型 + 迁移)

**Files:**
- Modify: `app/models/account_permission.py:46`
- Create: `migrations/versions/20XXXXXXXXXX_add_permission_snapshot_to_account_permission.py`

**Steps:**
1. 为 `AccountPermission` 增加:
   - `permission_snapshot = db.Column(db.JSON, nullable=True)`
   - `permission_snapshot_version = db.Column(db.Integer, nullable=False, default=1)`
2. Alembic 迁移创建上述字段(生产库为 PostgreSQL 时建议使用 `sa.dialects.postgresql.JSONB`)。

**Test:**
- Run: `pytest -m unit`
  - Expected: PASS

### Task 2: 同步流程双写快照(不改读取侧)

**Files:**
- Modify: `app/services/accounts_sync/permission_manager.py:415`

**Steps:**
1. 在 `_apply_permissions()` 中新增写入 `record.permission_snapshot = permissions`。
2. 保持旧列写入逻辑不变(Phase 1 仅做双写)。

**Test:**
- Add: `tests/unit/services/test_permission_manager_snapshot_write.py`
- Run: `pytest -m unit -k permission_manager_snapshot_write`
  - Expected: PASS

### Task 3: 提供统一读取适配层(快照优先 + 回退旧列)

**Files:**
- Modify: `app/models/account_permission.py:129`

**Steps:**
1. 新增方法:
   - `get_permission_snapshot() -> dict` (快照优先, 缺失返回由旧列拼装的 dict)
   - `get_permission_category(name: str, default: object) -> object`
2. 重写 `get_permissions_by_db_type()` 以使用 `get_permission_snapshot()` 提供的数据来源, 且保持返回 key 不变(保证分类规则与分类器不变)。

**Test:**
- Add: `tests/unit/models/test_account_permission_snapshot_compat.py`
- Run: `pytest -m unit -k account_permission_snapshot_compat`
  - Expected: PASS

### Task 4: 权限详情 Service 切读快照(保留兼容回退)

**Files:**
- Modify: `app/services/instances/instance_accounts_service.py:90`
- Modify: `app/services/ledgers/accounts_ledger_permissions_service.py:28`
- (Optional) Modify: `app/types/instance_accounts.py:84`, `app/types/accounts_permissions.py:1`

**Steps:**
1. 从 `AccountPermission.get_permission_snapshot()`/`get_permission_category()` 读取对应 category, 替换 `getattr(account, "global_privileges", None) or []` 等读取方式。
2. SQL Server 的“简化视图”逻辑保持, 但输入改为快照中的 `database_permissions`。

**Test:**
- Run: `pytest -m unit`
  - Expected: PASS

### Task 5(可选): Phase 3 回填与删列计划(另起迁移)

**Files:**
- Create: `scripts/backfill_account_permission_snapshot.py`
- Create: `migrations/versions/20XXXXXXXXXX_drop_legacy_permission_columns.py`

**Steps:**
1. 回填脚本仅更新 `permission_snapshot is null` 的记录, 从旧列拼装写入快照。
2. 删除旧列与 `PERMISSION_FIELDS` 相关逻辑, 将 diff/日志改为快照 diff。

**Test:**
- Run: `pytest -m unit`
  - Expected: PASS

---

## 11. 决策与后续计划

已确认：**存储 + 展示 + 跨 DB 通用分类 DSL(另起一期做规则统一)**。

已确认(更新)：分类/规则编辑器**不做表/对象级**；统一建模到 `global/server/database`。Oracle 表空间“删除/管理”属于 **server scope 系统权限**（例如 `DROP TABLESPACE`），必须纳入可配置/可评估范围。

已确认：展示页需要展示 schema/table/object 明细（来自 raw snapshot）；`tablespace_quotas` 不用于规则评估，也不用于页面展示。

后续计划文档：`docs/plans/2025-12-29-account-classification-dsl-v2.md`

> 依赖关系: DSL v2 推荐基于 `permission_snapshot` + `AccountPermissionFacts`(从快照提取的跨 DB 统一事实)评估, 从而避免继续扩散“按 db_type 拆列/拆逻辑”的技术债。

---

## 12. 已发现的隐藏问题(建议随本次重构一并修复)

> 说明: 本节按仓库约定输出“位置/类型/描述/建议”, 重点关注 `or` 兜底与字段/结构不一致导致的数据丢失或规则失效。

- 位置：`app/services/accounts_sync/adapters/oracle_adapter.py:91`
  - 类型：兼容/缺陷(数据结构不一致导致丢数)
  - 描述：Oracle 适配器产出权限快照使用 `tablespace_quotas` key，但 `PERMISSION_FIELDS`/`AccountPermission` 未包含对应列；当前同步写入会忽略该字段，导致表空间配额信息落地丢失。
  - 建议：在 Phase 1 双写时把整份 `permissions` 写入 `permission_snapshot`，作为该类字段的长期真源；后续展示/分类基于快照读取。

- 位置：`app/services/account_classification/classifiers/oracle_classifier.py:31`
  - 类型：适配/缺陷(规则可配置但评估不生效)
  - 描述：前端规则构建支持 `tablespace_quotas`(见 `permission-policy-center.js`)，但后端 Oracle 分类器不评估该字段；且表空间权限/配额的命名在 UI/采集/落库间存在漂移(quotas vs privileges)。
  - 建议：表空间属于高风险域（例如 `DROP TABLESPACE` 可能造成重大数据删除），不应简单移除：
    - 存储侧：以 `permission_snapshot` 为真源保留 `tablespace_quotas/system_privileges`，修复 quotas 落库丢失与字段命名漂移。
    - 分类/DSL v2：Oracle 的“表空间权限”本质上是 system privileges 的一个 UI 分组（`PermissionConfig.category='tablespace_privileges'`），评估侧应统一落到 `has_privilege(..., scope="server")` 的同一条链路（避免“选了但永远匹配不到”）。
    - `tablespace_quotas`：已确认 **不参与规则评估，也不用于页面展示**；如需保留仅作为 raw 审计/排障证据，建议落入 `permission_snapshot.extra` 并在 UI 隐藏（避免产生“可配置/可展示”的错觉）。

- 位置：`app/templates/accounts/account-classification/rules_form.html:65`
  - 类型：兼容/防御(回退导致错误默认值)
  - 描述：表单默认值使用 `resource.operator or 'OR'` 回退，但 `operator` 并未持久化到 `classification_rules` 表；刷新编辑页可能错误回退到 OR，与 `rule_expression.operator` 不一致。
  - 建议：统一以 `rule_expression.operator` 作为单一真源；DSL v2 迁移后移除“独立 operator 表单字段/非持久化属性”的双源设计。
