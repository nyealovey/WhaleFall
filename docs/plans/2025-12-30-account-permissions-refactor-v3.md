# 账户权限重构 V3 (存储 + 结构 + 跨 DB 分类 DSL) 实施方案

**目标:** 将当前 "按 db_type 扩列存权限" + "按 db_type 分流评估规则" 的模式升级为: 版本化权限快照(JSONB)作为单一真源 + 跨 DB Facts 层 + 版本化 DSL, 同时保证可灰度发布(双写/切读回退/回填/可回滚).

**架构:** 引入 `AccountPermission.permission_snapshot`(JSONB) 与 `permission_snapshot_version` 作为权限快照真源. 基于 snapshot + 结构化列构建 `AccountPermissionFacts`. 新规则以 `dsl_expression`(JSONB) + `dsl_version` + `applies_to_db_types` 存储并优先评估(严格失败关闭, fail-closed), 在规则迁移完成前保留 legacy `rule_expression` + 旧分类器的回退链路.

**技术栈:** Flask, SQLAlchemy, Alembic, PostgreSQL(jsonb), pytest, vanilla JS modules, Jinja2 templates

> 状态: 草稿
> 负责人: @kiro
> 创建: 2025-12-30
> 更新: 2025-12-30
> 范围: `account_permission` 存储, `accounts_sync`, `account_classification`, instances/ledgers 权限详情, 规则编辑 UI
> 关联: `docs/plans/2025-12-29-account-permissions-refactor-v2-overview.md`, `docs/plans/2025-12-29-account-permission-storage-v2.md`, `docs/plans/2025-12-29-account-classification-dsl-v2.md`, (input) `account-classification-v2-design`

---

## 1. 摘要(V3 决策)

### 1.1 存储(单一真源)

- 在 `account_permission` 表新增 2 列:
  - `permission_snapshot`(jsonb, nullable): 权限快照真源载荷(payload).
  - `permission_snapshot_version`(int, not null, default=3): 快照结构版本.
- 分阶段发布:
  - 阶段 A: 双写(legacy columns + snapshot).
  - 阶段 B: 切读(snapshot 优先, 缺失回退 legacy columns).
  - 阶段 C: 回填历史数据.
  - 阶段 D: 删除 legacy 权限列 + 硬编码字段清单.

### 1.2 权限结构与 UI 可选项(避免 "UI 能选但后端无法评估")

- 将 `permission_configs` 作为 UI 与校验的 "可选项真源"(选项注册表).
- 为 snapshot 建立 V3 的 "分类维度契约"(category contract):
  - facts 评估消费归一化 categories(示例): `roles`, `global_privileges`, `server_roles`, `server_permissions`, `database_roles`, `database_privileges`, `database_permissions`.
  - db-specific payload 进入 `type_specific` 与 `extra` (保留用于原始视图/审计).

### 1.3 分类(facts + DSL, legacy 回退)

- Facts 是评估器(evaluator)的唯一稳定输入:
  - `capabilities`(最小集合: `SUPERUSER`, `GRANT_ADMIN`), `roles`, `privilege_grants`(scope 仅 `global/server/database`), `attrs`, `errors`.
- DSL v3:
  - 以 JSON AST + version 存储.
- 未知函数/非法参数必须失败关闭(fail-closed).
  - 规则通过 `applies_to_db_types` 支持多 db_type(支持 `*`).
- 评估链路:
  - 若 `dsl_expression` 存在且版本受支持: 评估 DSL.
  - 否则: 回退 legacy `rule_expression` + 现有分类器(迁移期临时存在).

### 1.4 前端(两种视图)

- 原始视图(raw view): 展示 `permission_snapshot`(含 `extra`), 用于审计/排障.
- 归一化视图(normalized view): 展示 facts + capability 原因(reasons), 用于可解释性与排障.

---

## 2. 目标 / 非目标

### 2.1 目标

- 可扩展存储: 新增 db_type 不应再需要加列.
- 向后/向前兼容: 历史无 snapshot 的行仍可读; snapshot 新增 key 不应破坏旧 reader.
- 安全发布: feature-flag 控制双写/切读回退/一致性验证/回滚.
- 统一分类: 新 db_type 不需要为常见规则复制一套 per-db 分类器.
- 禁止 "静默漂移": 避免 `or []` / `or {}` 兜底把缺失数据掩盖成默认值, 导致规则语义悄然改变.

### 2.2 非目标(本 V3 不做)

- 不做全库权限项搜索/聚合引擎(可为后续可选的扁平化索引表预留空间).
- DSL 评估器(evaluator)不做 object-level(schema/table/object) 粒度(raw snapshot 仍保留明细用于展示).
- 不追求所有 db_type 语义完全对齐(facts mapping 采取保守策略, 失败安全 fail-safe).

---

## 3. 现状热点(兼容/防御/回退/适配)

> 输出格式遵循仓库约定: 位置 / 类型 / 描述 / 建议. 重点关注: `or` 兜底, 字段别名, 迁移/版本化, 结构漂移(schema drift).

- 位置: `app/models/account_permission.py:129`
  - 类型: 适配(字段别名 / 按 db_type 分支)
  - 描述: `get_permissions_by_db_type()` 通过 db_type 分支做字段映射与别名(例如 PostgreSQL 用 `database_privileges_pg` 映射为返回值里的 `database_privileges`, Oracle 返回 `oracle_system_privileges` 等 key).
  - 建议: 改为 `get_permission_snapshot()` + `get_permission_view()` 统一入口: snapshot 优先, 缺失回退旧列, 并在迁移期给 legacy 分类器输出一份稳定的规范化视图(canonical view).

- 位置: `app/services/accounts_sync/permission_manager.py:43`
  - 类型: 兼容 / 防御(硬编码字段集, 破坏性清空)
  - 描述: `PERMISSION_FIELDS` 是固定白名单. `_apply_permissions()` 会把未出现的字段置为 `None`(除 `type_specific` 保留), 导致适配器采集到但未建列的数据被静默丢弃.
  - 建议: 以 `permission_snapshot` 存整份载荷(payload)(不丢字段). 旧列写入只作为明确范围的双写阶段存在.

- 位置: `app/services/accounts_sync/adapters/oracle_adapter.py:91`
  - 类型: 兼容 / 缺陷(结构不匹配 -> 数据丢失)
  - 描述: Oracle adapter 曾产出 `tablespace_quotas`(已决策: V3 不再采集), 但 `AccountPermission`/`PERMISSION_FIELDS` 不持久化该字段, 暴露了 "采集输出与落库结构不一致" 的系统性风险(新增字段会被静默丢弃).
  - 建议: 以 `permission_snapshot` 为真源持久化整份快照, 并将 raw-only 字段放入 `permission_snapshot.extra` 且显式标注, 避免 UI/评估器(evaluator)产生漂移.

- 位置: `app/types/accounts.py:15`
  - 类型: 兼容(类型契约 vs 持久化契约漂移)
  - 描述: `PermissionSnapshot` TypedDict 含有一些 key(例如 `tablespace_quotas`), 但当前结构并不落库, 容易让人误以为 "我们存了". 且 `tablespace_quotas` 已决策在 V3 不再采集, 需要同步更新类型契约避免误导.
  - 建议: 明确并版本化 snapshot 结构. 要么让持久化与类型契约一致, 要么调整类型契约对齐真实落库行为(含删除/废弃不再采集的字段).

- 位置: `app/services/accounts_sync/adapters/factory.py:46`
  - 类型: 防御(回退归一化)
  - 描述: `(db_type or "").lower()` 用于避免 null/empty 输入导致崩溃.
  - 建议: 保留该防御写法. V3 更推荐引入携带 schema/version 元信息的注册表(registry).

- 位置: `app/models/account_classification.py:183`
  - 类型: 防御(JSON 解析失败关闭, fail-closed)
  - 描述: `ClassificationRule.get_rule_expression()` JSON 解析失败会返回 `{}`, 导致评估直接 `False`.
  - 建议: 保留失败关闭(fail-closed), 但在保存规则时增加结构化校验错误并反馈到 UI, 避免出现 "规则静默失效".

- 位置: `app/services/account_classification/orchestrator.py:391`
  - 类型: 适配(单 db_type 规则限制)
  - 描述: 账户先按 `acc.instance.db_type.lower() == db_type` 过滤, 评估又依赖 `classifier_factory.get(rule.db_type)`, 导致 "单条规则无法覆盖多 db_type".
  - 建议: 增加 `applies_to_db_types` 并支持 `*`. DSL v3 里也可以显式 `db_type_in()` 约束.

- 位置: `app/services/account_classification/classifiers/sqlserver_classifier.py:81`
  - 类型: 兼容(legacy alias)
  - 描述: SQL Server 分类器兼容 legacy `database_privileges` 作为 `database_permissions` 的别名并做 merge.
  - 建议: 将 alias 收敛到单一归一化(canonicalization)层(事实提取层或 snapshot view builder), 待迁移完成后删除各分类器里的 alias.

- 位置: `app/services/account_classification/classifiers/mysql_classifier.py:68`
  - 类型: 防御(or fallback)
  - 描述: `permissions = account.get_permissions_by_db_type() or {}` 防崩溃, 但也会掩盖 "快照缺失" 的问题.
  - 建议: 通过 facts.errors / 指标把 "快照缺失" 显式暴露出来, 防止规则语义漂移而无人察觉.

- 位置: `app/services/instances/instance_accounts_service.py:43`
  - 类型: 适配 / 防御(per-db branching + `or` fallback)
  - 描述: 权限 DTO 构造依赖 `instance.db_type` 的固定分支, 并大量使用 `getattr(..., None) or []/{}` 兜底, 新 db_type 难以扩展.
  - 建议: 用 `permission_snapshot` + `permission_configs` 生成通用 `PermissionCategoriesDTO`, 每个 db_type 的旧字段只保留兼容视图.

- 位置: `app/services/ledgers/accounts_ledger_permissions_service.py:62`
  - 类型: 适配 / 防御(shape coercion)
  - 描述: SQL Server 的 db permissions 在服务层被二次简化为 `dict[str, list[str]]`, 并用 `or {}` 兜底.
  - 建议: 将 "简化视图" 下沉到 snapshot 归一化(canonicalization), service 只消费稳定 DTO.

- 位置: `app/templates/accounts/account-classification/rules_form.html:59`
  - 类型: 防御(template fallback)
  - 描述: `db_type_options or []` / `operator_options or []` 防止模板报错, 但也可能导致 UI 静默空白.
  - 建议: 保留兜底, 但当 options 为空时在页面显式提示错误状态.

---

## 4. V3 架构

### 4.1 权限快照结构(版本化)

本节定义 `account_permission.permission_snapshot` 的 v3 结构. 这是权限链路的单一真源, 该结构一旦设计错误, 后续会出现大量 "静默丢数/语义漂移/规则永不命中" 的隐藏问题. 因此本节明确:

- 哪些字段属于 "归一化有效视图"(categories).
- 哪些字段属于 "raw/明细"(extra, raw-only).
- MySQL roles 如何表达并纳入有效权限.
- Oracle tablespace 相关权限如何归属到 system privileges.
- PostgreSQL 取消 tablespace privileges.
- SQL Server roles 如何区分服务器级与数据库级.

#### 4.1.1 外层封套(通用外层)

`permission_snapshot` 必须是一个 dict, 最外层字段固定如下(顺序不重要, 但 key 必须稳定):

```json
{
  "version": 3,
  "categories": {},
  "type_specific": {},
  "extra": {},
  "errors": [],
  "meta": {}
}
```

字段语义:

- `version`: int, 固定为 3, 用于 reader 判定语义与兼容逻辑.
- `categories`: PermissionCategoriesV3, "归一化有效视图", 用于 UI(归一化视图) + Facts + DSL.
- `type_specific`: dict, db 专有的结构化属性(例如 host/plugin/role attributes). 禁止存敏感信息(例如口令/口令 hash).
- `extra`: dict, raw/明细/审计/排障信息(raw-only). 默认不参与 Facts/DSL 评估, 但允许 UI(原始视图) 展示.
- `errors`: list[object|str], 采集与归一化过程中的错误. 必须可观测, 禁止静默吞掉导致 "空权限" 假象.
- `meta`: dict, collector 元信息(adapter, collected_at, source queries, etc).

兼容性规则(强约束):

- reader 必须忽略未知 key(向前兼容).
- writer 必须保留未知 key(read-modify-write 不可丢字段).
- categories 必须是 deterministic 的归一化结果, 禁止 "靠 `or {}`/`or []` 填默认值" 的静默重写(silent rewrite).

#### 4.1.2 PermissionCategoriesV3(归一化有效视图)

核心原则: `categories` 表达的是账号在 "最大权限视角" 下的有效权限. 即:

- 对 MySQL: 必须在采集侧做 roles 闭包展开(role closure, 含角色嵌套), 把 role 带来的权限并入有效权限.
- 对 SQL Server: 必须同时表达服务器级与数据库级 roles; permissions 必须区分 `granted/denied/grantable`.
- 对 Oracle: 表空间相关权限归入 `system_privileges`(server scope), 例如 `UNLIMITED TABLESPACE`, `DROP TABLESPACE`. 本期不采集 tablespace quota(配额), 因此 snapshot 不再出现 `tablespace_quotas`.
- 对 PostgreSQL: V3 不再提供 `tablespace_privileges`(不采集, 不展示, 不评估). 表空间管理相关能力如果要纳入, 必须映射到 server scope facts/capabilities, 而不是单独 category.

通用类型(用于后续各 db_type 的结构定义):

```json
{
  "PrivilegeSetV3": {
    "granted": ["..."],
    "grantable": ["..."],
    "denied": ["..."]
  },
  "PermissionSetV3": {
    "granted": ["..."],
    "denied": ["..."],
    "grantable": ["..."]
  }
}
```

说明:

- `grantable`: 对应 "WITH GRANT OPTION" 或等价能力(Oracle admin option 见专有结构).
- `denied`: 仅适用于存在显式 deny 语义的引擎(主要是 SQL Server). 其他 db_type 可省略或置空数组.

#### 4.1.3 MySQL: 最大权限结构(最大权限快照)

要求: MySQL 角色必须 "带权限" 表达. V3 将其拆为 2 层:

- `categories`: 存有效权限(已合并 roles 闭包展开).
- `extra.mysql.role_graph`: 存 roles 图与 role 定义(包含 role 自身 privileges), 用于解释与排障.

MySQL roles 的关键语义(必须明确, 否则会出现严重的规则语义漂移):

- direct roles: "授予给该用户的角色集合"(用户可用的角色), 通常来自 `GRANT 'role'@'host' TO 'user'@'host'`.
- default roles: "用户登录时默认激活的角色集合", 通常来自 `SET DEFAULT ROLE ... TO user` 或 `ALTER USER ... DEFAULT ROLE ...`.
- all granted roles: direct roles 的传递闭包(transitive closure), 即包含 "角色嵌套授予" 后用户可获得的全部角色集合.

V3 约定:

- `categories.*` 表达 "最大权限视角": direct user grants + all granted roles 的闭包展开后合并得到的有效权限.
- default roles 仅用于辅助展示/排障, 不作为分类评估口径, 避免出现 "非 default 的高权限 role 让账号可升级, 但分类却漏标" 的风险.

##### 4.1.3.1 统计口径(选用方案 1: 三集合 + 传递闭包)

你担心的复杂度点主要在这里: 如果我们只存 default roles, 很容易漏掉 "可手动激活的高权限 role"; 但如果把 roles 做得过度复杂, 采集/存储/解释又会失控. 方案 1 的目标是: **最小复杂度 + 最大正确性**.

结论(本 V3 选用):

- `direct_roles`: 该用户被授予的 roles(不区分是否 default).
- `default_roles`: 登录默认激活的 roles(仅用于 UI/解释, 不参与分类口径).
- `all_granted_roles`: 从 `direct_roles` 出发, 按 role->role 授予边做传递闭包, 得到用户 "最大可获得/可激活" 的 roles.

你问的关键点: MySQL 默认会嵌套 role -> role 吗?

- MySQL **支持** role 嵌套(`GRANT role_a TO role_b`), 但**不会自动生成**嵌套; 只有管理员显式做了 role->role 授予时才会出现.
- 一旦存在嵌套, 激活某个 role 时, 其下游 role 的权限会一并生效. 因此在 "最大权限视角" 下必须做闭包, 否则会漏掉通过嵌套获得的高危权限.

##### 4.1.3.2 采集与计算(最小可实现, 推荐)

采集侧需要同时满足两件事:

1) 能算出 `categories`(最大权限视角).
2) 能解释 "这条权限从哪来"(user direct / 哪个 role / role 嵌套链路).

推荐实现(保持简单且版本稳定): **用 `SHOW GRANTS` 做 DFS/BFS 展开**.

- 第 1 步: 对用户执行 `SHOW GRANTS FOR 'user'@'host'`.
  - 解析出用户的 direct privileges(含 `WITH GRANT OPTION`).
  - 解析出 `direct_roles`(匹配 `GRANT <role> TO <user>`).
  - 解析出 `default_roles`(如果输出里包含 `SET DEFAULT ROLE ...`); 如果采集账号不具备读取 default roles 的能力, 必须在 `errors` 记录 `DEFAULT_ROLES_UNKNOWN`, 严禁默认为 `[]` 造成 silent drift.
- 第 2 步: role 闭包展开(队列初始化为 `direct_roles`).
  - 每出队一个 role, 执行 `SHOW GRANTS FOR <role>`, 得到:
    - role 自身 privileges(写入 `extra.mysql.role_graph.role_definitions[role]`).
    - role->role 授予边(写入 `extra.mysql.role_graph.edges`, 并把新 role 入队).
  - 用 `visited` 做环路保护(允许 role grants 存在环, 不能死循环).
  - 展开结束后, `all_granted_roles = visited_roles`(按字典序排序以保持 deterministic).
- 第 3 步: 计算最大权限视角的有效权限:
  - `effective = user_direct_privileges ∪ (⋃ role_privileges for role in all_granted_roles)`.
  - MySQL 无显式 deny 语义, `denied` 维度保持 `[]`.
- 第 4 步: 落库:
  - `categories.roles = all_granted_roles`(用于 facts/DSL).
  - `extra.mysql.role_graph` 保留三集合 + edges + role_definitions, 用于解释与排障.

示例(结构示意, privileges 列表仅举例, 不枚举全部名称):

```json
{
  "version": 3,
  "categories": {
    "roles": ["'nested_role'@'%'", "'read_only'@'%'"],
    "global_privileges": {
      "granted": ["SELECT", "INSERT", "CREATE USER"],
      "grantable": ["SELECT"],
      "denied": []
    },
    "dynamic_privileges": {
      "granted": ["BACKUP_ADMIN"],
      "grantable": [],
      "denied": []
    },
    "database_privileges": {
      "db1": {"granted": ["CREATE", "DROP"], "grantable": [], "denied": []}
    },
    "table_privileges": {
      "db1": {
        "t1": {"granted": ["SELECT"], "grantable": [], "denied": []}
      }
    }
  },
  "type_specific": {
    "mysql": {
      "account": {
        "host": "%",
        "original_username": "app_user",
        "plugin": "mysql_native_password",
        "account_locked": false,
        "password_last_changed": "2025-12-30T00:00:00Z"
      }
    }
  },
  "extra": {
    "mysql": {
      "raw_grants": {
        "user": ["GRANT SELECT ON *.* TO 'app_user'@'%' WITH GRANT OPTION"],
        "roles": {
          "'read_only'@'%'": ["GRANT SELECT ON *.* TO 'read_only'@'%'"],
          "'nested_role'@'%'": ["GRANT CREATE USER ON *.* TO 'nested_role'@'%'"]
        }
      },
      "role_graph": {
        "direct_roles": ["'read_only'@'%'"],
        "default_roles": ["'read_only'@'%'"],
        "all_granted_roles": ["'nested_role'@'%'", "'read_only'@'%'"],
        "edges": [
          {"from": "'read_only'@'%'", "to": "'nested_role'@'%'", "with_admin_option": false}
        ],
        "role_definitions": {
          "'read_only'@'%'" : {
            "global_privileges": {"granted": ["SELECT"], "grantable": [], "denied": []},
            "dynamic_privileges": {"granted": [], "grantable": [], "denied": []},
            "database_privileges": {},
            "table_privileges": {},
            "granted_roles": ["'nested_role'@'%'"]
          },
          "'nested_role'@'%'" : {
            "global_privileges": {"granted": ["CREATE USER"], "grantable": [], "denied": []},
            "dynamic_privileges": {"granted": [], "grantable": [], "denied": []},
            "database_privileges": {},
            "table_privileges": {},
            "granted_roles": []
          }
        }
      }
    }
  },
  "errors": [],
  "meta": {
    "adapter": "mysql",
    "adapter_version": "v3",
    "collected_at": "2025-12-30T00:00:00Z"
  }
}
```

关键约束:

- Facts/DSL 读取 `categories.*` 时, 视为 "最大权限视角" 下的有效权限.
- MySQL 采集必须提供 role definitions, 否则 roles closure 无法正确计算, 会导致严重漏标(例如 `GRANT_ADMIN`).

#### 4.1.4 SQL Server: 最大权限结构(最大权限快照)

要求: SQL Server roles 必须区分服务器级与数据库级. permissions 必须保留 deny, 否则会产生 "看起来有权限但实际被 deny" 的隐藏误判.

示例:

```json
{
  "version": 3,
  "categories": {
    "server_roles": ["sysadmin", "securityadmin"],
    "server_permissions": {
      "granted": ["CONTROL SERVER", "ALTER ANY LOGIN"],
      "denied": [],
      "grantable": []
    },
    "database_roles": {
      "db1": ["db_owner", "db_securityadmin"]
    },
    "database_permissions": {
      "db1": {
        "granted": ["CONNECT", "CREATE TABLE"],
        "denied": ["DROP TABLE"],
        "grantable": []
      }
    }
  },
  "type_specific": {
    "sqlserver": {
      "login_name": "app_user",
      "default_database": "master"
    }
  },
  "extra": {
    "sqlserver": {
      "raw_server_permissions": [
        {"permission": "CONTROL SERVER", "state": "GRANT"}
      ],
      "raw_database_permissions": {
        "db1": [
          {"permission": "CREATE TABLE", "state": "GRANT"},
          {"permission": "DROP TABLE", "state": "DENY"}
        ]
      },
      "object_permissions": {
        "db1": {
          "schemas": {
            "dbo": {
              "tables": {
                "t1": {"granted": ["SELECT"], "denied": [], "grantable": []}
              }
            }
          }
        }
      }
    }
  },
  "errors": [],
  "meta": {"adapter": "sqlserver", "adapter_version": "v3", "collected_at": "2025-12-30T00:00:00Z"}
}
```

#### 4.1.5 Oracle: 最大权限结构(最大权限快照)

要求:

- tablespace 相关权限归入 `system_privileges`(而不是单独 tablespace category).
- 本期不采集 tablespace quota(配额), 因此 snapshot 不再出现 `tablespace_quotas`.

示例:

```json
{
  "version": 3,
  "categories": {
    "oracle_roles": {
      "granted": ["DBA", "RESOURCE"],
      "admin_option": ["DBA"],
      "default": ["RESOURCE"]
    },
    "system_privileges": {
      "granted": ["CREATE USER", "DROP USER", "UNLIMITED TABLESPACE", "DROP TABLESPACE"],
      "admin_option": ["CREATE USER"],
      "denied": []
    }
  },
  "type_specific": {
    "oracle": {
      "account_status": "OPEN",
      "default_tablespace": "USERS",
      "temporary_tablespace": "TEMP"
    }
  },
  "extra": {
    "oracle": {
      "object_privileges": {
        "HR.EMPLOYEES": {"granted": ["SELECT"], "grantable": [], "denied": []}
      }
    }
  },
  "errors": [],
  "meta": {"adapter": "oracle", "adapter_version": "v3", "collected_at": "2025-12-30T00:00:00Z"}
}
```

#### 4.1.6 PostgreSQL: 最大权限结构(最大权限快照, 无 tablespace)

要求: PostgreSQL 在 V3 不再提供 `tablespace_privileges`. role 属性(role attributes)与成员关系(membership)才是服务器级(server scope)的核心.

示例:

```json
{
  "version": 3,
  "categories": {
    "predefined_roles": ["pg_read_all_data", "pg_write_all_data"],
    "role_attributes": {
      "rolsuper": false,
      "rolcreaterole": true,
      "rolcreatedb": false,
      "rolreplication": false,
      "rolbypassrls": false
    },
    "database_privileges": {
      "db1": {"granted": ["CONNECT", "CREATE"], "grantable": [], "denied": []}
    }
  },
  "type_specific": {
    "postgresql": {
      "connlimit": 10,
      "valid_until": null
    }
  },
  "extra": {
    "postgresql": {
      "object_privileges": {
        "db1": {
          "schemas": {
            "public": {
              "tables": {
                "t1": {"granted": ["SELECT"], "grantable": [], "denied": []}
              }
            }
          }
        }
      }
    }
  },
  "errors": [],
  "meta": {"adapter": "postgresql", "adapter_version": "v3", "collected_at": "2025-12-30T00:00:00Z"}
}
```

#### 4.1.7 归一化规则(legacy -> v3)

当 snapshot 缺失时, 需要基于 legacy 列合成 v3 snapshot, 并使用显式映射(禁止隐式 `or` 兜底):

- MySQL: legacy 列 `global_privileges`(list[str]) 映射到 `categories.global_privileges.granted`.
- MySQL: legacy 列 `database_privileges`(dict[str, list[str]]) 映射到 `categories.database_privileges[db].granted`.
- MySQL: legacy 列无法表达 roles/dynamic/table 等维度; 合成 snapshot 时必须在 `errors` 标记缺失原因(例如 `MYSQL_ROLES_UNKNOWN_FROM_LEGACY`), 禁止静默置空导致 "最大权限视角" 漂移.
- PostgreSQL: legacy 列 `database_privileges_pg` 映射到 `categories.database_privileges`.
- PostgreSQL: legacy 列 `tablespace_privileges` 不再进入 v3 categories(可以选择落到 `extra.postgresql.legacy_tablespace_privileges` 供审计, 但默认 UI 不展示).
- Oracle: legacy 的 `tablespace_quotas` 不再采集, 因此不再进入 v3 snapshot; system privileges 进入 `categories.system_privileges`.
- SQL Server: legacy `database_privileges` 视为 `categories.database_permissions.*.granted` 的 alias, 并在归一化阶段统一.

### 4.2 结构注册表(schema registry): 以 `permission_configs` 作为 "可选项真源"

V3 规则 UI 与校验必须依赖 `permission_configs`:

- UI 只能提供后端能归一化(canonicalize)并可评估的选项.
- 如果某权限项存在于 `permission_configs`, 但 adapter 永远采集不到, 视为 bug(可用测试 + CI 约束).

可选后续扩展(非 V3 最小可用(MVP)必需):

- 引入 `permission_schema_definitions`(per db_type) 描述:
  - dimension 类型(`list/object/nested`) 与 JSON shape.
  - UI 的 enums.
  - 可用于分类的字段集合.

### 4.3 Adapter 契约 v3

Adapters 必须输出完整 snapshot 载荷(payload), 并保证落库时不丢 key:

```python
class RemoteAccountV3(TypedDict):
    username: str
    db_type: str
    is_superuser: bool
    is_locked: bool
    permissions: dict[str, Any]  # permission_snapshot payload
```

Adapter registry 选型:

- 方案 A(最小改动): 保留 `adapters/factory.py` 的 dict, 但为每个 adapter 增加 `get_permission_schema()` 供校验.
- 方案 B(推荐): 引入 `AdapterRegistry` 装饰器注册(参考 `account-classification-v2-design`), 并支持结构(schema)自动注册.

### 4.4 Facts 模型 v3

Facts 是评估器(evaluator)的唯一输入, 由 snapshot 推导:

```python
@dataclass(frozen=True)
class AccountPermissionFacts:
    db_type: str
    is_superuser: bool
    is_locked: bool
    roles: set[str]
    capabilities: set[str]
    privilege_grants: list[PrivilegeGrant]
    attrs: dict[str, JsonValue]
    errors: list[str]
```

Capability 最小集合(沿用 v2 已确认决策):

- `SUPERUSER`
- `GRANT_ADMIN`(严格口径: 实例级/广泛授予能力, 不等同于单对象 owner)

映射(mapping)必须满足:

- 保守(conservative): 避免误报(false positive).
- 可解释(explainable): 可输出原因(reasons)供 UI 展示.
- 集中维护(centralized): 单模块 + 单测.

### 4.5 DSL v3

#### 4.5.1 AST 存储(JSONB)

```json
{
  "version": 3,
  "expr": {
    "op": "AND",
    "args": [
      {"fn": "has_capability", "args": {"name": "GRANT_ADMIN"}},
      {"fn": "db_type_in", "args": ["mysql", "postgresql", "sqlserver", "oracle"]}
    ]
  }
}
```

#### 4.5.2 必需函数(最小可用, MVP)

- `db_type_in(types: list[str])`
- `is_superuser()`
- `is_locked()`
- `has_role(name: str)`
- `has_capability(name: str)`
- `has_privilege(name: str, scope: "global" | "server" | "database", database?: str)`
- `attr_equals(path: str, value: scalar)`

错误处理:

- 未知函数(fn) / 非法参数(args) / 非法 AST: 必须失败关闭(fail-closed)(返回 `False`), 并输出结构化日志.

#### 4.5.3 高级模式(可选)

如果必须支持 db-specific 条件(数据库专有条件), 但又不希望扩充 facts:

- 增加 `raw_path_exists(path: str)` / `raw_path_equals(path: str, value: scalar)`, 并限制只能访问 `permission_snapshot.extra` 与 `type_specific`.
- 必须显式启用(opt-in), 并在 UI 明确标注为 "数据库专有(db-specific)/易碎(brittle)".

### 4.6 规则存储与评估链路

扩展 `classification_rules`:

- `dsl_expression`(jsonb, nullable)
- `dsl_version`(int, nullable or default 3)
- `applies_to_db_types`(text[] or jsonb array, nullable, 支持 `*`)
- 迁移期间保留 legacy `rule_expression`(text)

评估顺序:

1. 若 `dsl_expression` 存在: 校验(validate) + 评估(evaluate) DSL(基于 facts).
2. 否则: 解析(parse) legacy JSON, 用 legacy 分类器(classifier, per-db)评估.

### 4.7 APIs(V3)

- `GET /api/v3/permission-options/{db_type}`: 返回 `permission_configs`(按 category 分组).
- `POST /api/v3/classification-rules/validate`: 校验 DSL AST(针对选定 db_types, 可选样例 snapshot).
- `GET /api/v3/accounts/{account_id}/permissions`: 返回原始 snapshot + 归一化 facts.

---

## 5. 迁移与回滚

### 5.1 特性开关(feature flags)(推荐)

- `ACCOUNT_PERMISSION_SNAPSHOT_WRITE`: 开启 snapshot 双写.
- `ACCOUNT_PERMISSION_SNAPSHOT_READ`: 读取侧 snapshot 优先(缺失回退 legacy).
- `ACCOUNT_CLASSIFICATION_DSL_V3`: 开启 DSL v3 评估(缺失回退 legacy classifiers).

### 5.2 发布阶段

- 阶段 0: 加列 + 结构类型(schema types) + 最小 DTO 访问器(accessors).
- 阶段 1: 全 db_type 双写 snapshot, 保持 legacy 行为不变.
- 阶段 2: 读取侧切到 snapshot(缺失回退), 同步改造 UI 原始/归一化视图(raw/normalized view).
- 阶段 3: 增加 DSL 列, 实现 facts + DSL 评估器(evaluator), 增加规则校验 API.
- 阶段 4: 迁移规则(脚本 script), 开关(flag)控制启用 DSL, 监控不一致(mismatch).
- 阶段 5: 回填历史 snapshot, 并在稳定窗口后删除 legacy 列/分类器.

回滚约定:

- 若某阶段失败, 回滚优先采用 "代码回滚" + "flag 回滚".
- 双写阶段保留 legacy 列, 因此通常不需要数据回滚.

---

## 6. 详细实现计划(可执行的小任务)

### 任务 1: 为 `account_permission` 增加 snapshot 列

**文件:**
- 修改: `app/models/account_permission.py`
- 新增: `migrations/versions/20XXXXXXXXXX_add_permission_snapshot_v3_to_account_permission.py`
- 测试: `tests/unit/routes/test_api_v1_instances_contract.py`

**步骤 1: 先写一个会失败的测试**

增加断言, 确认 SQLAlchemy table 存在新列:

```python
def test_account_permission_has_snapshot_columns() -> None:
    from app import db
    table = db.metadata.tables["account_permission"]
    assert "permission_snapshot" in table.c
    assert "permission_snapshot_version" in table.c
```

**步骤 2: 运行测试, 确认它会失败**

运行: `pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -k snapshot_columns -v`
预期: FAIL (columns not found).

**步骤 3: 写最小实现让测试通过**

- 在 model 与 migration 中增加 nullable `permission_snapshot`(JSONB) + `permission_snapshot_version`(int, default 3).

**步骤 4: 再运行测试, 确认通过**

运行: `pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -k snapshot_columns -v`
预期: PASS.

### 任务 2: 增加 snapshot accessor 与 legacy 回退映射

**文件:**
- 修改: `app/models/account_permission.py`
- 新增: `app/services/accounts_permissions/snapshot_view.py`
- 测试: `tests/unit/services/test_account_permission_snapshot_view.py`

**步骤 1: 先写一个会失败的测试**

```python
@pytest.mark.unit
def test_snapshot_view_falls_back_to_legacy_columns() -> None:
    account = AccountPermission(db_type="postgresql", database_privileges_pg={"db1": ["CREATE"]})
    view = build_permission_snapshot_view(account)
    assert view["categories"]["database_privileges"]["db1"]["granted"] == ["CREATE"]
```

**步骤 2: 运行测试, 确认它会失败**

运行: `pytest -m unit tests/unit/services/test_account_permission_snapshot_view.py -v`
预期: FAIL (builder not implemented).

**步骤 3: 写最小实现让测试通过**

- 实现 `build_permission_snapshot_view(account)`:
  - 若 `account.permission_snapshot` 存在且版本受支持, 直接返回.
  - 否则从 legacy columns 合成 snapshot, 并使用显式 alias mapping.

**步骤 4: 再运行测试, 确认通过**

运行: `pytest -m unit tests/unit/services/test_account_permission_snapshot_view.py -v`
预期: PASS.

### 任务 3: 同步阶段双写 snapshot(不丢未知字段)

**文件:**
- 修改: `app/services/accounts_sync/permission_manager.py`
- 测试: `tests/unit/services/test_account_permission_manager_snapshot_dual_write.py`

**步骤 1: 先写一个会失败的测试**

```python
@pytest.mark.unit
def test_apply_permissions_persists_full_snapshot() -> None:
    manager = AccountPermissionManager()
    record = AccountPermission(db_type="oracle")
    permissions = {"object_privileges": {"HR.EMPLOYEES": {"granted": ["SELECT"]}}}
    manager._apply_permissions(record, permissions, is_superuser=False, is_locked=False)
    assert record.permission_snapshot["extra"]["oracle"]["object_privileges"]["HR.EMPLOYEES"]["granted"] == ["SELECT"]
```

**步骤 2: 运行测试, 确认它会失败**

运行: `pytest -m unit tests/unit/services/test_account_permission_manager_snapshot_dual_write.py -v`
预期: FAIL (snapshot column missing / data dropped).

**步骤 3: 写最小实现让测试通过**

- 增加 feature flag 控制的 `record.permission_snapshot` 写入.
- 将 adapter 的未知 key 存到 snapshot(若非 canonical, 优先放 `extra`).
- 阶段 1 保持 legacy 列写入逻辑不变.

**步骤 4: 再运行测试, 确认通过**

运行: `pytest -m unit tests/unit/services/test_account_permission_manager_snapshot_dual_write.py -v`
预期: PASS.

### 任务 4: 读取侧切换为 snapshot-first(缺失回退 legacy)

**文件:**
- 修改: `app/services/instances/instance_accounts_service.py`
- 修改: `app/services/ledgers/accounts_ledger_permissions_service.py`
- 测试: `tests/unit/routes/test_api_v1_instances_contract.py`
- 测试: `tests/unit/routes/test_api_v1_accounts_ledgers_contract.py`

**步骤 1: 先写一个会失败的测试**

- 添加单测: 构造只有 snapshot(不填 legacy fields) 的行, 验证 APIs 仍返回正确的 permission DTOs.

**步骤 2: 运行测试, 确认它会失败**

运行: `pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -k snapshot_only -v`
预期: FAIL (APIs read legacy columns only).

**步骤 3: 实现 snapshot-first 读取**

- 使用 `build_permission_snapshot_view(account)` 填充 DTO fields.
- 保留现有 API 契约(contract)的 legacy DTO 字段, 但尽量从 snapshot 读取.

**步骤 4: 再运行测试, 确认通过**

运行: `pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -k snapshot_only -v`
预期: PASS.

### 任务 5: 增加回填与一致性验证脚本

**文件:**
- 新增: `scripts/backfill_account_permission_snapshot_v3.py`
- 新增: `scripts/verify_account_permission_snapshot_v3.py`
- 测试: `tests/unit/services/test_snapshot_backfill_helpers.py`

**步骤 1: 先写一个会失败的测试**

为 "从 legacy columns 构造 snapshot" 的 helper 补齐测试.

**步骤 2: 实现 scripts**

- 回填仅针对 snapshot 为空的行.
- 做抽样一致性校验: legacy view vs snapshot view.

**步骤 3: 运行单测**

运行: `pytest -m unit tests/unit/services/test_snapshot_backfill_helpers.py -v`
预期: PASS.

### 任务 6: 实现 facts builder + capability mapping(最小集合)

**文件:**
- 新增: `app/services/account_classification/facts.py`
- 新增: `app/services/account_classification/capabilities.py`
- 测试: `tests/unit/services/account_classification/test_facts_builder_v3.py`

**步骤 1: 先写会失败的测试**

覆盖:

- MySQL: `is_superuser` -> `SUPERUSER`.
- SQL Server: `server_roles` 包含 `sysadmin` -> `SUPERUSER`.
- Oracle: role `DBA` -> `SUPERUSER` (是否作为兜底由你们决策).
- `GRANT_ADMIN` 严格映射(strict mapping, per db_type).

**步骤 2: 实现构建器(builder)**

- 解析 snapshot categories, 产出 `roles` 与 `privilege_grants`.
- 产出 `capabilities` + `capability_reasons`(原因列表).
- 若必需 categories 缺失, 记录到 `errors`.

**步骤 3: 运行测试**

运行: `pytest -m unit tests/unit/services/account_classification/test_facts_builder_v3.py -v`
预期: PASS.

### 任务 7: 实现 DSL v3 评估器(evaluator)(失败关闭, fail-closed)

**文件:**
- 新增: `app/services/account_classification/dsl/ast.py`
- 新增: `app/services/account_classification/dsl/evaluator.py`
- 新增: `app/services/account_classification/dsl/functions.py`
- 测试: `tests/unit/services/account_classification/test_dsl_evaluator_v3.py`

**步骤 1: 先写会失败的测试**

- 未知函数 -> 返回 `False`.
- `AND` / `OR` semantics 正确.
- `has_capability` 与 `db_type_in` 能基于 facts 工作.

**步骤 2: 实现最小评估器(evaluator)**

- 校验 AST 结构(shape).
- 从白名单分发函数.
- 对非法输入输出结构化日志.

**步骤 3: 运行测试**

运行: `pytest -m unit tests/unit/services/account_classification/test_dsl_evaluator_v3.py -v`
预期: PASS.

### 任务 8: 扩展 classification_rules 存储(DSL v3 + 多 db_type 适用范围)

**文件:**
- 修改: `app/models/account_classification.py`
- 新增: `migrations/versions/20XXXXXXXXXX_add_dsl_columns_to_classification_rules.py`
- 修改: `app/services/accounts/account_classifications_write_service.py`
- 测试: `tests/unit/services/test_classification_rule_write_service.py`

**步骤 1: 先写会失败的测试**

- 保存带 `dsl_expression` 的规则, 能持久化 JSONB.
- `applies_to_db_types` 能持久化且默认值正确.

**步骤 2: 实现 DB + model 变更**

- 增加列.
- 确保 write service 校验 DSL, 且在有输入时能同时存 DSL 与 legacy.

**步骤 3: 运行测试**

运行: `pytest -m unit tests/unit/services/test_classification_rule_write_service.py -v`
预期: PASS.

### 任务 9: 改造 orchestrator: DSL 优先, legacy 回退

**文件:**
- 修改: `app/services/account_classification/orchestrator.py`
- 修改: `app/services/account_classification/repositories.py`
- 测试: `tests/unit/services/account_classification/test_orchestrator_dsl_v3.py`

**步骤 1: 先写会失败的测试**

- 创建一条适用于多 db_type 的 DSL 规则, 验证它能跨类型匹配账户.

**步骤 2: 实现**

- 为每个 account 构建 facts.
- 若 DSL 存在, 用 DSL engine 评估; 否则走 legacy 分支.
- 将 "按 db_type 单一过滤" 替换为 applies-to 逻辑.

**步骤 3: 运行测试**

运行: `pytest -m unit tests/unit/services/account_classification/test_orchestrator_dsl_v3.py -v`
预期: PASS.

### 任务 10: 增加规则校验 API, 并让 UI 输出 DSL payload

**文件:**
- 修改: `app/routes/api/v3/...` (新的 route 模块)
- 修改: `app/templates/accounts/account-classification/rules_form.html`
- 修改: `app/static/js/modules/views/accounts/account-classification/...`
- 测试: `tests/unit/routes/test_api_v3_classification_rules_validate_contract.py`

**步骤 1: 先写会失败的契约测试(contract test)**

- 校验 endpoint 返回 `success: true` 以及 `valid: true/false`, 并包含错误明细.

**步骤 2: 实现**

- Backend: validate AST + selected db types + optional sample snapshot.
- Frontend: rule builder 产出 `dsl_expression` JSON 并提交.

**步骤 3: 运行测试**

运行: `pytest -m unit tests/unit/routes/test_api_v3_classification_rules_validate_contract.py -v`
预期: PASS.

### 任务 11: 规则迁移脚本(legacy -> DSL v3) + 一致性检查

**文件:**
- 新增: `scripts/migrate_classification_rules_legacy_to_dsl_v3.py`
- 新增: `app/services/account_classification/dsl/legacy_converter.py`
- 测试: `tests/unit/services/account_classification/test_legacy_converter_v3.py`

**步骤 1: 先写会失败的测试**

- 将一个最小 legacy MySQL rule 转换为 DSL v3(能用 capability 的优先用 capability).
- 对不支持的 shape, converter 返回结构化错误, 且保留 legacy 不变.

**步骤 2: 实现**

- Converter 只做确定性映射(deterministic mapping), 不引入启发式.
- Script 对可转换的规则写入 `dsl_expression`.
- Script 输出 report(计数, 失败原因, 示例).

**步骤 3: 运行测试**

运行: `pytest -m unit tests/unit/services/account_classification/test_legacy_converter_v3.py -v`
预期: PASS.

### 任务 12: 稳定后的清理计划

**文件:**
- 修改: `app/services/account_classification/classifiers/*`
- 修改: `app/models/account_permission.py`
- 修改: `app/services/accounts_sync/permission_manager.py`
- 修改: `permission_configs` 的 SQL 种子数据

Checklist:

- 规则全量迁移后, 删除各 classifier 的 alias 兼容逻辑.
- 回填完成并稳定后, 删除 legacy permission columns.
- 增加 CI guardrails, 防止新增 per-db hardcoding 回归.
