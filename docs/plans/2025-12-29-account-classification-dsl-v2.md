# Account Classification DSL v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不再为每种数据库写一套分类器/规则结构的前提下，实现“跨 DB 通用的账户分类规则 DSL”，并与 `account_permission.permission_snapshot`(权限快照真源)对齐，修复当前分类链路里“UI 能配但后端不生效 / 采集数据丢失 / 双真源回退错误”的隐藏问题。

**Architecture:** 新增“统一事实层”(AccountPermissionFacts) + “统一规则 DSL(AST, 版本化)” + “规则评估引擎(可编译/可缓存/可回退)”三层：采集仍存 raw 快照用于展示与追溯；分类引擎只消费 facts；规则存储从 text JSON 升级为 JSONB + version，并保留 legacy 规则兼容直到全部迁移完成。

**Tech Stack:** Flask, SQLAlchemy, Alembic, PostgreSQL(jsonb), pytest, (frontend) vanilla JS modules

> 状态: Draft
> 创建: 2025-12-29
> 更新: 2025-12-29
> 范围: 账户分类管理(规则/评估/缓存/自动分类), 规则 UI, 与权限快照对齐
> 依赖: `docs/plans/2025-12-29-account-permission-storage-v2.md`

---

## 1. 背景与问题

当前“账户分类”以 `db_type` 为分界，形成了多套规则表达式与评估逻辑：

- 前端：`PermissionPolicyCenter` 为 MySQL/PostgreSQL/SQLServer/Oracle 各自生成不同 shape 的 `rule_expression`。
- 后端：`ClassifierFactory` 固定注册 4 个分类器，按 `rule.db_type` 分流评估。
- 存储：`ClassificationRule.rule_expression` 为 text(JSON)，没有 schema/version；`operator` 字段在 UI 与后端存在双源。

这一架构导致：

- **新增 DB 类型基本等于重写一条链路**：新策略 JS + 新后端分类器 + 新权限采集/展示/规则验证。
- **隐藏的数据/规则失效**：存在 key 漂移/字段缺失导致的“采集了但没落库/没参与评估/只在某处生效”。
- **难以治理与演进**：规则表达式缺乏版本化与统一语义层，一旦要修复/统一会影响面巨大。

目标是把分类规则从“按 DB 拼凑字段”升级为“统一 DSL + 统一事实模型”，并保持迁移过程可回滚、可灰度。

---

## 2. 目标 / 非目标

### 2.1 目标

- **统一 DSL**：同一套表达式语义可应用于多种 db_type(可选限定适用范围)。
- **统一事实层**：把各 DB 的权限/角色/属性归一为一套 facts，使规则评估不再关心快照字段名差异。
- **版本化与迁移**：规则表达式与权限快照都具备版本字段，支持逐步迁移与兼容回退。
- **修复隐藏问题**：UI 可配项必须被后端评估；采集到的数据必须可落库可展示；避免“回退导致错误默认值”。

### 2.2 非目标(本期不做)

- 不做完整“自然语言/文本 DSL 编辑器”(先以 JSON AST 为主，UI 用可视化构建器输出 AST)。
- 不追求所有 DB 权限模型的完全等价映射(先覆盖安全/分类最常用的能力集合，保留 raw 查询接口与高级模式扩展)。

---

## 3. 现状盘点(隐藏问题清单)

> 按仓库要求输出：位置 / 类型 / 描述 / 建议，重点关注 `or` 兜底与字段漂移。

- 位置：`app/templates/accounts/account-classification/rules_form.html:65`
  - 类型：防御/缺陷(回退默认值错误)
  - 描述：`selected_operator` 回退到 `resource.operator or 'OR'`，但 `operator` 并未持久化到 DB；导致刷新编辑页可能错误默认 OR，与 `rule_expression.operator` 不一致。
  - 建议：短期统一读取 `rule_expression.operator`；长期在 DSL v2 中移除“operator 双源”(表单字段与表达式)。

- 位置：`app/services/accounts_sync/adapters/oracle_adapter.py:91`
  - 类型：兼容/缺陷(数据结构不一致导致丢数)
  - 描述：Oracle 快照使用 `tablespace_quotas`，但 `AccountPermission`/`PERMISSION_FIELDS` 没有对应列；当前同步落库会忽略该字段，且后端分类器也不评估 quotas。
  - 建议：以 `permission_snapshot` 为真源保存整份快照，修复 `tablespace_quotas` 落库丢失；并在 DSL v2 中纳入“表空间相关高危能力”：
    - Oracle 的“删除/管理表空间”能力来自 `system_privileges`（例如 `DROP TABLESPACE` / `UNLIMITED TABLESPACE`），应能通过 `has_privilege(..., scope="server")` 命中（避免 UI 可选但后端永远不命中）。
    - `tablespace_quotas`：已确认 **不参与规则评估，也不用于页面展示**；如需保留仅作为 raw 审计/排障证据，建议落入 `permission_snapshot.extra` 并在 UI 隐藏（避免产生“可配置/可展示”的错觉）。

- 位置：`app/services/accounts_sync/adapters/postgresql_adapter.py:506`
  - 类型：兼容/缺陷(UI/后端不一致导致规则永不命中)
  - 描述：PostgreSQL 采集 `tablespace_privileges` 目前只判断 `CREATE`；但 `permission_configs` 里存在 `tablespace_privileges` 的 `USAGE` 选项（见 `sql/seed/postgresql/permission_configs.sql:453`），会导致 UI 可选但后端永远匹配不到。
  - 建议：采集侧补齐 `USAGE`（以及你们实际使用到的 tablespace 权限集合）；Facts/DSL v2 侧统一归入 `server` scope，并保证 UI 可选项与 evaluator 可命中项同源。

- 位置：`app/services/account_classification/classifiers/factory.py:25`
  - 类型：兼容/适配(固定注册表)
  - 描述：分类器工厂硬编码支持的 db_type，新 DB 类型必须改代码新增分类器。
  - 建议：DSL v2 引入统一评估引擎 + db_type facts extractor；新增 DB 类型最小化为“采集适配器 + facts mapping +（可选）UI 配置”。

- 位置：`app/services/account_classification/orchestrator.py:392`
  - 类型：适配(按 db_type 分流)
  - 描述：规则评估前按 `rule.db_type` 过滤账户列表；无法支持“一个规则适配多个 db_type”。
  - 建议：规则模型改为 `applies_to_db_types`(list) + 可选 `*`；评估时按范围过滤，或在 DSL 中显式用 `db_type_in()` 谓词约束。

- 位置：`app/services/account_classification/classifiers/sqlserver_classifier.py:82`
  - 类型：兼容(字段别名)
  - 描述：SQLServer 规则兼容 `database_privileges` 作为 `database_permissions` 的 legacy alias(merge 去重)。
  - 建议：DSL v2 明确 canonical 名称与 alias 层，避免每个分类器各自维护兼容逻辑；迁移完成后删除 alias。

---

## 4. DSL v2 总体设计

### 4.1 三层模型：Raw Snapshot / Facts / DSL

1) **Raw Snapshot**：来自采集适配器的原始权限结构，落库到 `AccountPermission.permission_snapshot`，用于展示、追溯、debug。

2) **Facts(统一事实层)**：从 snapshot + 结构化列(`is_superuser/is_locked/db_type/type_specific`)推导出的统一事实对象：

- `db_type: str`
- `is_superuser: bool`
- `is_locked: bool`
- `roles: set[str]`
- `privileges: list[PrivilegeGrant]`（统一结构，见 4.2）
- `attributes: dict[str, JsonValue]`（来自 type_specific + 允许的衍生字段）
- `capabilities: set[str]`（跨 DB 风险能力集合，见 4.3）

3) **DSL(AST)**：规则表达式以 JSON AST 存储/传输，评估引擎只依赖 Facts，不直接读 snapshot 细节。

### 4.2 PrivilegeGrant 统一结构(建议最小字段集)

统一 privilege 的表达，避免“同一权限在不同 DB 结构完全不同”。

> 决策(更新)：本项目分类/DSL/规则编辑器**不细化到表/对象级**；统一建模到 `global/server/database` 三层。  
> 说明：Oracle 的表空间“删除/管理”（`DROP TABLESPACE` 等）属于 **system privilege**，归入 `server` scope 并纳入评估；表空间配额(quotas)默认只用于展示/追溯，若要纳入规则需另行定义明确语义。

```json
{
  "name": "SELECT",
  "scope": "global|server|database",
  "database": "db1",
  "granted": true
}
```

各 DB 的映射策略：

- MySQL：`global_privileges` -> scope=global；`database_privileges`(按 db) -> scope=database。
- PostgreSQL：
  - `predefined_roles` -> roles
  - `database_privileges_pg` -> scope=database
  - `tablespace_privileges` -> scope=server（表空间管理/使用类权限；不在规则中细化到具体表空间名）
- SQL Server：`server_permissions` -> scope=server；`database_permissions` -> scope=database；角色落入 roles 并同时映射 capabilities(如 sysadmin)。
- Oracle：`system_privileges` -> scope=server（包含 `DROP TABLESPACE/UNLIMITED TABLESPACE/...` 等表空间管理类系统权限）；`oracle_roles` -> roles。

### 4.3 Capabilities(跨 DB 通用能力集合)

**Capabilities 是“跨 DB 的能力标签”**：它不是数据库原生的 `privilege/role`，而是产品层定义的一组“安全/风险视角的能力”(power)。

目的：让你能写出**不绑定某个 DB 细节**的规则（例如“能管理用户/能授权/能改表结构/能写数据”），并让同一条规则可覆盖 MySQL/PostgreSQL/SQLServer/Oracle 以及未来新增的 db_type。

与 `privilege`/`role` 的区别：

- **Privilege(原子权限)**：DB 原生授权项可以非常细；本项目 DSL 仅建模到 `global/server/database`（如 MySQL `SELECT`、SQL Server `ALTER ANY LOGIN`）。
- **Role(角色)**：DB 原生权限包（如 Oracle `DBA`、SQL Server `sysadmin`）。
- **Capability(能力标签)**：把多个 privilege/role/属性归并成“业务关心的能力”，用于分类，不用于精确授权审计（精确审计应使用 `has_privilege`/`has_role`）。

Facts 层产出 `capabilities: set[str]`，DSL 侧用 `has_capability(name)` 进行判断。

#### 4.3.1 MVP(本期必须有)

你已确认本期 capabilities **最小集合**为：

- `SUPERUSER`：数据库最高权限（在该实例维度可视为“管理员/最高权限账号”）
- `GRANT_ADMIN`：可以给其他账户授权（实例级/广义授权能力；排除仅对象 owner 范围内的 grant）

其余能力标签(如 `DDL_ADMIN/DML_READ/DML_WRITE/...`) 先作为后续扩展，不作为本期必须项。

#### 4.3.2 映射规则(按 db_type，保守且可解释)

capabilities 映射由代码常量维护（已决策：A），并要求“可解释”(能输出触发原因)。

> 说明：这里给出“判定依据”的设计约定；实际落地时应写成明确的匹配集合与单测，避免因权限名差异导致误判。

- MySQL:
  - `SUPERUSER`: `AccountPermission.is_superuser == True`
  - `GRANT_ADMIN`(严格口径 A：实例级/广义)：命中任一条件
    - `GRANT OPTION` 出现在 `global_privileges`（仅全局；忽略单库/单对象范围的 grant option）
    - 或 `type_specific.can_grant == True` 且该字段语义明确为“全局可授权”（建议用 `type_specific.can_grant_scope="global"` 约束）

- PostgreSQL:
  - `SUPERUSER`: `AccountPermission.is_superuser == True`（`pg_roles.rolsuper`）
  - `GRANT_ADMIN`(严格口径 A：实例级/广义)：命中任一条件
    - `type_specific.can_create_role == True`（`pg_roles.rolcreaterole`，用于角色授予/管理的保守 proxy）
    - 或存在明确的“可授予权限/角色”的系统权限/属性（若后续补齐）

- SQL Server:
  - `SUPERUSER`: 命中任一条件
    - `AccountPermission.is_superuser == True`（采集侧若有）
    - 或 `server_roles` 包含 `sysadmin`
  - `GRANT_ADMIN`(严格口径 A：实例级/广义)：命中任一条件（保守集合，后续按你们生产实际补齐）
    - `server_roles` 包含 `securityadmin` 或 `sysadmin`
    - 或 `server_permissions` 命中如 `CONTROL SERVER` / `ALTER ANY LOGIN` / `ALTER ANY SERVER ROLE` 等授予/安全管理类权限

- Oracle:
  - `SUPERUSER`: 命中任一条件（建议至少覆盖）
    - `AccountPermission.is_superuser == True`（例如 `SYS`）
    - 或 `oracle_roles` 包含 `DBA`（避免仅 SYS 被标为 superuser 的漏标）
  - `GRANT_ADMIN`(严格口径 A：实例级/广义)：命中任一条件
    - `system_privileges` 包含 `GRANT ANY PRIVILEGE` 或 `GRANT ANY ROLE`（或你们认可的等价集合）
    - （可选兜底）`oracle_roles` 包含 `DBA`（是否作为兜底取决于你们对 DBA 语义的严格程度）

#### 4.3.3 后续扩展(暂不纳入本期)

后续若要扩展更多 capabilities，建议按“需求驱动”的顺序引入，并明确每个标签的安全语义与触发条件（含回归样本）。

建议后续候选集合(示例)：

- `SUPERUSER`
  - `USER_ADMIN`（创建/删除/修改用户、登录、角色）
  - `DDL_ADMIN`（建库/建表/改表/删除）
  - `DML_WRITE`（INSERT/UPDATE/DELETE）
  - `DML_READ`（SELECT/READ）
  - `EXECUTE`（执行存储过程/函数/作业）
  - `SECURITY_ADMIN`（安全策略/审计/加密相关）
  - `REPLICATION_ADMIN`
  - `BACKUP_RESTORE`

映射原则(重要)：

- **保守映射(避免误判)**：宁可漏标也不要错标，尤其是 `SUPERUSER/USER_ADMIN/GRANT_ADMIN` 这类高风险标签。
- **可解释**：每个 capability 必须能追溯到“哪些 roles/privileges/attributes 触发了它”，便于 UI 展示与调试。
- **集中维护**：不要让 mapping 分散到各处分类器；统一放在 Facts 提取层，并以**代码常量**维护（已决策：A）+ 单测。

以“新增 db_type”为例(写规则时的直觉)：

- 若账号具备“管理用户/授权/全局管理”等权限 => 标 `USER_ADMIN/GRANT_ADMIN/SUPERUSER`（具体匹配的权限名需根据该 db_type 的实际语义与部署约定确定）。
- 若账号具备 `CREATE/DROP/ALTER` 等 DDL 权限 => 标 `DDL_ADMIN`。
- 若账号具备 `INSERT/UPDATE/DELETE/LOAD` 等写入相关权限 => 标 `DML_WRITE`。
- 若账号具备 `SELECT` 等读取权限 => 标 `DML_READ`。

### 4.4 DSL AST 结构(版本化)

存储形态建议：

```json
{
  "version": 2,
  "expr": {
    "op": "AND",
    "args": [
      { "fn": "has_capability", "args": {"name": "USER_ADMIN"} },
      { "fn": "db_type_in", "args": ["mysql", "postgresql", "sqlserver", "oracle"] }
    ]
  }
}
```

支持的节点类型(最小集)：

- Boolean 组合：`{op: "AND"|"OR", args: [expr...]}`（短路）
- Not：`{op: "NOT", arg: expr}`
- Function：`{fn: str, args: object|list}`（白名单函数，纯解释执行）
- Compare：`{op: "EQ"|"NE"|"IN"|"CONTAINS"|"GT"|"GTE"|"LT"|"LTE", left: valueExpr, right: valueExpr}`
- Value：`{"var": "is_superuser"}` / `{"attr": "type_specific.host"}` / 常量

内置函数(第一期必须)：

- `db_type_in(types: list[str])`
- `is_superuser()` / 或 `var: is_superuser`
- `is_locked()`
- `has_role(name: str)`
- `has_capability(name: str)`
- `has_privilege(name: str, scope?: str, database?: str)`（scope 仅允许 global/server/database）
- `attr_equals(path: str, value: scalar)`

错误处理策略：

- 解析失败 / 未知 fn / 参数非法：**fail-closed**(该条规则返回 False) + 记录结构化日志，避免误分类。

---

## 5. 存储与兼容策略(规则模型升级)

### 5.1 数据库字段扩展(推荐在 `classification_rules` 表增量)

新增字段：

- `dsl_expression` (jsonb, nullable)：DSL v2 AST
- `dsl_version` (int, not null, default=2)
- `applies_to_db_types` (jsonb/array, nullable)：为空表示沿用旧 `db_type`；非空表示多 db_type（或 `["*"]` 表示全量）
- (可选) `legacy_expression`：保留旧 text 字段作为回退，或继续用现有 `rule_expression`

读取/评估优先级：

1. `dsl_expression` 存在 => 用 DSL v2 评估
2. 否则 => 用 legacy 分类器评估 `rule_expression`（完全兼容现有规则）

### 5.2 迁移策略

- **自动迁移**：将现有 per-db `rule_expression` 转换为等价的 DSL AST（能转则转）。
- **无法自动迁移**：保留 legacy 表达式继续评估，并在 UI 标注“需升级”。
- **双跑验证**(可选)：对可转换规则，迁移后在后台任务中对同一账户集同时跑 legacy 与 DSL，若差异过大报警。

---

## 6. 展示与规则 UI 设计(可分两步)

### 6.1 展示侧(规则详情/预览)

- 规则详情优先渲染 DSL（以“通用条件 + 适用 db_types + 关键能力/权限”展示）。
- legacy 规则保持现有渲染逻辑。

### 6.2 规则编辑 UI(推荐两种模式并存)

1) **通用模式(推荐)**：

- 选择适用 db_types（多选，可选“全部”）
- 勾选 capabilities（跨 DB）
- 可选增加属性条件（如 host、账号状态）

2) **高级模式(按 DB 精细化)**：

- 复用现有 `PermissionPolicyCenter` 每 DB 的权限选择器
- 产出 DSL 子表达式：`(db_type == 'mysql' AND <mysql conditions>) OR (db_type == 'oracle' AND <oracle conditions>) ...`
- 粒度约束：高级模式同样不做表/对象级；统一只允许 `global/server/database` 三层条件。  
  - PostgreSQL/Oracle 的“表空间权限”在 UI 中可以继续作为分组（`PermissionConfig.category='tablespace_privileges'`），但**评估侧统一视为 server scope 的系统/实例级权限子集**（避免再出现“选了但永远匹配不到”）。
  - `tablespace_quotas`：已确认不用于规则评估/页面展示，规则 UI 不应提供该分组选项。

这样可以同时满足：

- 业务侧“写一次规则覆盖多 DB”（通用能力）
- 运维侧“对某 DB 精细授权细节分类”（高级模式）

约束(已决策：B)：

- **新增 db_type 接入时，不接受“只做通用能力分类、后补高级模式”**。
- 新 db_type 上线时必须同时具备：
  - 采集并落库 `permission_snapshot`（raw 可追溯）
  - Facts extractor + capabilities 映射（通用模式）
  - PermissionConfig + 规则 UI 高级模式（可选择/可生成精细权限 DSL 子表达式）

---

## 7. 分阶段落地计划

### Phase A: 引入 DSL 存储 + Facts 层(不改 UI, 仅后端可评估)

- 新增 `dsl_expression/dsl_version/applies_to_db_types`
- 引入 `AccountPermissionFacts` 提取器（MySQL/Postgres/SQLServer/Oracle）
- 新增 DSL evaluator（白名单函数 + fail-closed）
- API 读取侧透出 `dsl_expression`（可先隐藏在 admin 视图）

### Phase B: 规则迁移(可回滚)

- 写转换器：legacy -> DSL（覆盖当前 4 个 DB 的主流字段）
- 为可转换规则写入 `dsl_expression`，保留 legacy 字段
- 引入双跑校验/差异统计（可选，避免静默改变分类结果）

### Phase C: UI 改造与默认切换

- 规则创建默认产出 DSL（通用模式）
- legacy 编辑入口保留，但默认提示升级
- 修复 operator 双源；移除/禁用表/对象级（schema/table/object）等超出粒度的规则项，确保 UI/评估一致（Oracle 表空间管理类权限保留，归入 server scope）

### Phase D: 收敛技术债

- 迁移完成后逐步删除 legacy 分类器与相关缓存结构
- cache 从“按 db_type 缓存规则文本”升级为“按适用范围缓存已编译 DSL”

---

## 8. Implementation Tasks(按执行顺序)

### Task 1: 扩展规则表结构(DSL 字段)

**Files:**
- Modify: `app/models/account_classification.py:98`
- Create: `migrations/versions/20XXXXXXXXXX_add_dsl_fields_to_classification_rules.py`

**Steps:**
1. 为 `ClassificationRule` 增加 `dsl_expression/dsl_version/applies_to_db_types` 字段映射。
2. Alembic 迁移创建字段（PostgreSQL 推荐 JSONB）。

**Test:**
- Run: `pytest -m unit`
  - Expected: PASS

### Task 2: 引入 Facts 提取器与 DSL evaluator(最小可用)

**Files:**
- Create: `app/services/account_classification/dsl/facts.py`
- Create: `app/services/account_classification/dsl/evaluator.py`
- Create: `app/services/account_classification/dsl/functions.py`
- Test: `tests/unit/services/account_classification/test_dsl_evaluator.py`

**Steps:**
1. 定义 `AccountPermissionFacts` 与最小字段集(capabilities/roles/privileges/attributes)。
2. 为 4 个 db_type 实现 facts extractor（先覆盖当前已采集字段）。
3. 实现 evaluator（支持 AND/OR/NOT + 关键函数，fail-closed）。

**Test:**
- Run: `pytest -m unit -k dsl_evaluator`
  - Expected: PASS

### Task 3: 分类引擎接入 DSL(优先 DSL, 否则 legacy)

**Files:**
- Modify: `app/services/account_classification/orchestrator.py:380`
- Modify: `app/services/account_classification/repositories.py:199`
- Modify: `app/services/account_classification/cache.py:1`

**Steps:**
1. 评估时：若 `dsl_expression` 存在，用 DSL evaluator；否则走现有 classifier。
2. cache 里序列化/反序列化规则时带上 dsl 字段。
3. 支持 `applies_to_db_types`：过滤候选账户集（或在 DSL 中显式约束）。

**Test:**
- Run: `pytest -m unit`
  - Expected: PASS

### Task 4: legacy -> DSL 转换器与迁移脚本(可选灰度)

**Files:**
- Create: `app/services/account_classification/dsl/legacy_converter.py`
- Create: `scripts/migrate_classification_rules_to_dsl.py`
- Test: `tests/unit/services/account_classification/test_legacy_converter.py`

**Steps:**
1. 为 MySQL/Postgres/SQLServer/Oracle 的主流字段做等价转换。
2. 对无法转换的结构打标并跳过（保持 legacy 评估）。
3. 提供 dry-run 输出差异统计。

**Test:**
- Run: `pytest -m unit -k legacy_converter`
  - Expected: PASS

### Task 5: UI 修复与 DSL 创建入口(通用模式优先)

**Files:**
- Modify: `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:1`
- Modify: `app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js:1`
- Modify: `app/templates/accounts/account-classification/rules_form.html:65`

**Steps:**
1. 修复 operator 默认值来源：以 `rule_expression.operator` 或 DSL 中的 op 为真源。
2. 新增“通用模式”能力选择器（capabilities）。
3. 创建规则时产出 `dsl_expression`；保留高级模式可生成 per-db 子表达式。

**Test:**
- Run: `pytest -m unit`
  - Expected: PASS

---

## 9. Decisions(已确认)

1) “通用分类能力(capabilities)”维护方式：**A. 代码常量维护**

2) 新 DB 类型接入策略：**B. 不接受只做通用能力分类，必须同步补齐高级模式**

3) DSL 表达方式：对通用能力采用标签式谓词 `has_capability("<CAPABILITY>")`（例如 `has_capability("GRANT_ADMIN")`）

4) 权限细化粒度(更新)：分类/DSL/规则 UI **不做表/对象级**；统一建模到 `global/server/database`。Oracle 表空间“删除/管理”类能力属于 **server scope 系统权限**（例如 `DROP TABLESPACE`），必须纳入可配置/可评估范围

5) 展示页：需要展示 schema/table/object 明细（来源为 raw snapshot，不参与 DSL 评估）

6) `tablespace_quotas`：不参与规则评估，也不用于页面展示

7) PostgreSQL 表空间管理/使用类权限：保留，并归入 `server` scope（参考 Oracle 处理方式）
