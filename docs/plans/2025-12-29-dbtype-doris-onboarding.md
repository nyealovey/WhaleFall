# Doris DB Type Onboarding Design (Permission Snapshot + Classification DSL v2)

> 状态: Backlog (Not in scope for current refactor)
> 创建: 2025-12-29
> 更新: 2025-12-29
> 依赖:
> - `docs/plans/2025-12-29-account-permission-storage-v2.md`
> - `docs/plans/2025-12-29-account-classification-dsl-v2.md`

## 1. 目标

把 **Apache Doris** 作为一个“新 db_type”接入鲸落的账户/权限/分类体系，并遵循新架构：

- 权限以 `account_permission.permission_snapshot`(jsonb) 为真源落库，可扩展、可版本化
- 展示侧优先读快照（缺失回退旧列仅用于历史数据）
- 分类侧优先使用 **DSL v2**（Facts 层 + capabilities + privileges/roles/attributes）

> 说明：Doris 目前仅在规划中，本期重构不纳入实现范围；本文档保留为后续接入草案。

---

## 2. Doris 接入原则(与“隐藏问题治理”强相关)

1) **不要再为新 DB 扩列**  
所有 Doris 专有字段进入 `permission_snapshot.extra` 或作为 `PrivilegeGrant.name` 原样保留，避免再出现类似 Oracle `tablespace_quotas`“采集了但落库丢失”的问题。

2) **规则/展示/采集必须同源**  
规则 UI 能选到的项，必须来自 Doris 的 `permission_configs(db_type='doris', ...)`；后端 Facts 提取与 evaluator 必须能消费同一份 snapshot/category；避免“UI 可配但后端永不命中”。

3) **capabilities 优先解决“跨 DB 通用分类”**  
对 Doris 的精细权限分类可以后补，但第一阶段必须能通过 capabilities 解决“高风险账号/运维账号/只读账号/写入账号”等核心分类。

4) **新增 db_type 必须同步补齐高级模式(已确认)**  
你已选择“不接受先只支持通用能力分类，后补高级权限分类 UI/映射”。因此 Doris 上线时必须同时具备：

- PermissionConfig（用于 UI 权限选择器的“可选项真源”）
- Doris 权限选择器策略（高级模式 UI）
- `SHOW GRANTS` 解析与 Facts extractor（后端评估与展示）

---

## 3. Doris 权限快照约定(permission_snapshot)

### 3.1 建议的 snapshot shape

优先复用 MySQL-like 的 category 命名（便于 UI 与规则理解）：

```json
{
  "global_privileges": ["SELECT", "CREATE USER", "GRANT", "..."],
  "database_privileges": {
    "db1": ["SELECT", "LOAD", "..."],
    "db2": ["SELECT"]
  },
  "roles": ["role_a", "role_b"],
  "type_specific": {
    "host": "%",
    "is_locked": false,
    "source": "doris"
  },
  "errors": [],
  "extra": {
    "raw_grants": ["GRANT ...", "GRANT ..."],
    "cluster": "xxx"
  }
}
```

说明：

- `global_privileges/database_privileges/roles` 这些字段是否能全部采集到，取决于你们 Doris 的实际授权模型与可用系统表/命令；采集不到的字段允许为空，但必须把原始输出放入 `extra.raw_grants`，保证可追溯。
- Doris 专有概念（如资源组/权限域等）短期可进入 `extra.*`，后续稳定后再提升为顶层 category。

### 3.2 PermissionConfig(展示/规则构建的“可选项真源”)

为 Doris 新增 `permission_configs` 数据（UI 权限选择器与规则构建应读取这里）：

- `db_type='doris'`
- `category` 建议至少包含：
  - `global_privileges`
  - `database_privileges`
  - （可选）`roles`
  - （可选）`capabilities`（若 UI 需要展示通用能力而非 DB 原子权限）

> Doris 的“权限名全集”建议不要硬编码到代码里；以你们生产 Doris 的真实导出为准（类似 `sql/seed/postgresql/permission_configs.sql` 的生成方式）。

---

## 4. Doris Facts 提取与 capabilities 映射

### 4.1 Facts 提取目标

从 `permission_snapshot` + 结构化列推导：

- `roles: set[str]`（来自 snapshot.roles 或从 raw_grants 解析）
- `privileges: list[PrivilegeGrant]`（至少 global/database 两种 scope）
- `attributes: dict[str, JsonValue]`（host、锁定状态、额外元信息）
- `capabilities: set[str]`（跨 DB 的安全能力标签）

### 4.2 Doris capabilities(第一阶段建议覆盖)

建议先覆盖“最常用、最能解决跨 DB 分类”的能力集合（名字与 `docs/plans/2025-12-29-account-classification-dsl-v2.md` 保持一致）：

- `SUPERUSER`
- `USER_ADMIN`
- `GRANT_ADMIN`
- `DDL_ADMIN`
- `DML_WRITE`
- `DML_READ`
- `SECURITY_ADMIN`（可选，取决于 Doris 是否暴露审计/安全相关权限项）

### 4.3 映射策略(保守 + 可解释)

由于 Doris 的权限名/语义可能与 MySQL 不完全一致，建议采用两段式策略：

1) **显式映射表(优先)**：对你们确定语义的权限名做精确映射  
例如（示意，实际以你们 Doris 权限名为准）：
`CREATE USER` -> `USER_ADMIN`  
`GRANT`/`GRANT OPTION` -> `GRANT_ADMIN`  
`CREATE`/`DROP`/`ALTER` -> `DDL_ADMIN`  
`INSERT`/`UPDATE`/`DELETE`/`LOAD` -> `DML_WRITE`  
`SELECT` -> `DML_READ`

2) **受控的模式匹配(兜底)**：仅用于减少漏标，不用于高风险标签  
例如：包含 `ADMIN` 的权限名可以映射到 `SECURITY_ADMIN` 或 `DDL_ADMIN` 的候选集合，但 **不得直接映射为 `SUPERUSER`**，避免误判。

补充约束(已确认)：

- capabilities 映射由**代码常量**维护（不由后台表配置），并配套单测，确保 Doris 版本升级/语法变化时不会静默改变分类结果。

---

## 5. Doris 规则 DSL 的写法建议(给使用方的“第一感”)

### 5.1 通用分类(推荐优先用 capabilities)

- 高风险账号：`has_capability("USER_ADMIN") OR has_capability("GRANT_ADMIN") OR has_capability("SUPERUSER")`
- 只读账号：`has_capability("DML_READ") AND NOT has_capability("DML_WRITE") AND NOT has_capability("DDL_ADMIN")`
- 写入账号：`has_capability("DML_WRITE")`

### 5.2 Doris 专有精细规则(用 has_privilege/attr)

当需要精确到某个库/对象时：

- `has_privilege("SELECT", scope="database", database="db1")`
- `attr_equals("type_specific.host", "%")`（如你们把 host/来源等写入 type_specific）

---

## 6. 接入步骤(设计层面)

> 仅描述“需要做什么”，不落地实现。

1) 定义 `db_type='doris'` 的全链路规范化（写入/校验/展示 options）
2) Doris 账户与授权采集：产出 `PermissionSnapshot`，落库到 `permission_snapshot`
3) Doris PermissionConfig 数据：用于 UI 展示与规则构建
4) Doris Facts extractor + capabilities mapping：让 DSL v2 能工作
5) UI：db_type 下拉支持 Doris；规则编辑器支持 Doris（通用模式 + 高级模式均为上线必需）

高级模式最小要求：

- 至少支持 `global_privileges` 与 `database_privileges` 的选择与展示（与快照解析能力对齐）
- 若能从 `SHOW GRANTS` 稳定解析 role，则补齐 `roles` 的选择与展示
- `table_privileges` 可作为第二期增强（除非你们强依赖表级分类）

---

## 7. Doris 权限采集策略(已确认：SHOW GRANTS 解析文本)

已确认：Doris 的授权信息以 `SHOW GRANTS` 输出为权威来源（文本解析）。

### 7.1 采集流程(建议)

1) **获取账号清单**（来源可选其一，按你们现网可用能力确定）
   - A. Doris 支持的“列出所有用户”的命令/视图（优先，避免依赖内部表结构）
   - B. MySQL 兼容系统表（若你们允许；例如按 MySQL adapter 的模式查询 user/host）
   - C. 由现有 `instance_accounts` 增量维护（首次需要一次全量拉取）

2) **逐账号执行 `SHOW GRANTS`**  
   - 对每个 `user@host` 拉取完整授权语句列表
   - 原样保存到 `permission_snapshot.extra.raw_grants`
   - 解析失败/权限不足等错误写入 `permission_snapshot.errors`（不要吞掉）

3) **解析授权语句 -> 快照结构**（只做“最小可用 + 可追溯”）
   - 能解析的部分写入：
     - `global_privileges: list[str]`
     - `database_privileges: dict[str, list[str]]`
     - （可选）`table_privileges: dict[str, dict[str, list[str]]]`（先放快照里，不扩列）
     - `roles: list[str]`（若 `SHOW GRANTS` 包含 role 授予）
     - `type_specific`: `{host, original_username, ...}`
   - 不能解析的语句写入 `permission_snapshot.extra.unparsed_grants`，并记录原因

4) **落库与可观测性**
   - `permission_snapshot` 必须包含 `extra.raw_grants`（强约束，保证可追溯）
   - 记录“解析覆盖率”(parsed/total)，用于发现 Doris 新语法导致的静默丢数风险

### 7.2 解析规则(最小可用，不绑定 Doris 版本细节)

> 原则：宁可“解析少一些 + 全量保留 raw_grants”，也不要“误解析导致错分类”。

建议的解析分层：

- **Layer 0：存原始**  
  不做任何假设，先把每条 `SHOW GRANTS` 返回行原样写入 `extra.raw_grants`。

- **Layer 1：解析 GRANT 的核心骨架（尽量兼容 MySQL-like 语法）**
  - 识别：
    - `GRANT <priv_list> ON *.* ...` => `global_privileges`
    - `GRANT <priv_list> ON <db>.* ...` => `database_privileges[db]`
    - `GRANT <priv_list> ON <db>.<table> ...` => `table_privileges[db][table]`
  - `<priv_list>` 支持：
    - 逗号分隔的权限名（原样记录为字符串，大小写统一为大写/原样二选一）
    - `WITH GRANT OPTION`：建议额外记录 `GRANT OPTION`（或写入 `type_specific.can_grant=true`）

- **Layer 2：解析角色授予（若输出包含）**
  - 识别 `GRANT <role> TO ...` => `roles.append(role)`

- **Layer 3：兜底**
  - 不符合以上模式的行：进入 `extra.unparsed_grants`，并附带 `reason`（例如 `unknown_format`）

### 7.3 与 capabilities/Facts 的对齐方式

在 “跨 DB 通用分类” 场景下，Doris 优先通过 capabilities 解决：

- `global_privileges/database_privileges/table_privileges` => 映射到 `DML_READ/DML_WRITE/DDL_ADMIN/...`
- `roles` => 可直接用于 `has_role()`，也可作为 capabilities 的触发条件（需明确语义）

关键约束：

- `SUPERUSER/USER_ADMIN/GRANT_ADMIN` 这类高风险 capability 必须 **保守映射**，仅在权限名语义明确时触发，避免误判。

### 7.4 性能与限流建议

`SHOW GRANTS` 往往是 “N 个用户 = N 次查询”，建议在设计里明确：

- 分批执行（batch size）与超时
- 并发上限（避免 FE 压力过大）
- 失败重试策略（可重试的错误才重试）

---

## 8. 后续落地前需要的样本(用于定稿解析器与 PermissionConfig)

当后续进入 Doris 实施阶段时，为避免“误解析导致错分类”，需要提供 2 份 Doris 的真实 `SHOW GRANTS` 输出（脱敏即可）：

1) 高权限账号（包含用户管理/授权/DDL 等）
2) 只读账号（仅 SELECT）

每个账号 3–10 行足够。拿到样本后，我会把：

- `raw_grants` 的解析规则（正则/分支）
- `permission_configs(db_type='doris')` 的类别与权限名集合
- capabilities 映射表（精确触发条件）

补齐到可直接落地的程度。
