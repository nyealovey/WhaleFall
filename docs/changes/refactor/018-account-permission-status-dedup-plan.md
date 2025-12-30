# Account Permission Status And Attributes Dedup Plan

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-30
> 更新: 2025-12-30
> 范围: `account_permission`(schema/model), `accounts_sync`(adapters/manager), `permission_snapshot`/`permission_facts`, instances/accounts APIs, ledger filters, DSL v4
> 关联: `017-account-permissions-refactor-v4-plan.md`, `017-account-permissions-refactor-v4-progress.md`

## 1. 动机与范围

### 1.1 动机

当前 `account_permission` 在 "状态字段(is_superuser/is_locked)" 与 "属性字段(type_specific)" 上存在多处重复表达, 导致:

- 语义漂移: 同一概念在不同 DB/type 的推导规则不一致, 例如锁定态既可能来自 `AccountPermission.is_locked`, 也可能来自 `type_specific.can_login` 或 `type_specific.account_status`.
- 数据漂移: 同步链路中存在多处写入点, 出现 "A 更新了, B 忘了更新" 的风险.
- 维护成本高: UI/API/统计/规则评估在不同模块分别做兜底与推导, 形成隐式耦合.

同时, `permission_facts.capabilities` 已经承担了跨 DB 的语义归一(例如 `SUPERUSER`/`GRANT_ADMIN`) , 继续保留 `account_permission.is_superuser`/`permission_facts.is_superuser` 会形成冗余真源.

本计划目标是把 "超级用户/锁定态" 的真源收敛到 `capabilities`, 并把 `type_specific` 明确为 "账户属性容器", 不再承载权限或状态的重复表达.

### 1.2 范围

In-scope:

- 统一 `is_superuser` 与 `is_locked` 的真源, 收敛为 `permission_facts.capabilities`.
- 规范 `type_specific` 的职责: 仅存放账户属性, 不存放权限, 不存放锁定态等派生状态.
- 移除各模块对 `type_specific` 的锁定态兜底推导, 统一走 `capabilities`.
- 保持 API/UI contract 稳定(迁移期仍对外输出 `is_superuser`/`is_locked`/`type_specific`).

Out-of-scope(本期不做):

- 不修改历史规则数据(例如 `classification_rules.rule_expression` 的存量内容不迁移).
- 不引入新的权限 DSL 语法(仅调整现有 DSL v4 的实现以消除依赖重复字段).
- 不做权限展示信息的扩容(只做字段归一与去重).

### 1.3 现状盘点(重复定义清单)

| 概念 | 当前出现位置(示例) | 问题 |
| --- | --- | --- |
| is_superuser | `RemoteAccount.is_superuser`, `AccountPermission.is_superuser`, `permission_facts.is_superuser`, `permission_facts.capabilities` contains `SUPERUSER` | 多真源. facts 里同时存在 `is_superuser` 与 `capabilities` 冗余表达. |
| is_locked | `RemoteAccount.is_locked`, `AccountPermission.is_locked`, `permission_facts.is_locked`, `type_specific`(MySQL), 各处兜底推导 | 多真源. MySQL/PG/Oracle/SQLServer 的锁定态推导散落在多处, 易漂移. |
| type_specific | `permissions.type_specific`(adapter 输出), `AccountPermission.type_specific`, `permission_snapshot.type_specific` | 同一份属性在写入链路被重复携带与落库, 且混入了权限/状态字段(例如 MySQL `type_specific.is_locked`, PG `type_specific.can_create_role`). |

典型位置(非穷举):

- `app/models/account_permission.py`: 结构化列 `is_superuser`, `is_locked`, `type_specific`.
- `app/services/accounts_permissions/facts_builder.py`: facts 同时写入 `is_superuser`/`is_locked` 与 `capabilities`.
- `app/services/account_classification/dsl_v4.py`: `is_superuser()` 读取 `facts.is_superuser`.
- `app/repositories/account_statistics_repository.py`: 锁定态兜底逻辑读取 `type_specific.*`.
- `app/repositories/ledgers/accounts_ledger_repository.py`: 过滤/排序直接依赖 `AccountPermission.is_superuser/is_locked`.
- `app/services/accounts_sync/adapters/*.py`: adapter 同时输出 `is_locked` 与 `type_specific.is_locked`(MySQL), 或同时输出 `type_specific` 与 `role_attributes`(PostgreSQL).

## 2. 不变约束(行为/契约/性能门槛)

- 行为不变: UI 展示的 "锁定/正常", "超级用户/否" 语义不变.
- 接口契约不破坏: 迁移期 API 仍输出 `is_superuser: bool`, `is_locked: bool`, `type_specific: object`.
- 历史规则数据不动: 不批量修改 `classification_rules.rule_expression`. 规则执行结果语义保持一致.
- 同步稳定性: 不新增额外的 DB round-trip, 不引入额外的远端采集.
- 性能门槛: accounts ledger/instance accounts 列表的过滤与排序不出现数量级退化. 若需要索引支持, 必须在切读前准备好.

## 3. 分层边界(依赖方向/禁止项)

### 3.1 真源分层

定义单一真源与派生层:

- Snapshot layer: `AccountPermission.permission_snapshot`
  - 职责: 存储权限采集结果(可审计), 作为 facts 的输入.
  - 约束: 不在 snapshot 中重复写入可由 facts 推导的状态字段.
- Facts layer: `AccountPermission.permission_facts`
  - 职责: 提供稳定, 可查询的派生视图. `capabilities` 是跨 DB 的语义真源.
  - 约束: 不同时提供 `is_superuser/is_locked` 与 `capabilities` 的重复真源.
- Attributes layer: `AccountPermission.type_specific`
  - 职责: 存放账户属性(非权限, 非锁定态). 为 UI 展示与轻量列表提供数据.
  - 约束: 禁止写入权限类字段(roles, privileges, grant option 等), 禁止写入派生状态(`is_superuser`, `is_locked`).

### 3.2 禁止项(必须删除的重复逻辑)

- 禁止在 repository/service 中通过 `type_specific` 兜底推导锁定态.
- 禁止 adapter 输出 `permissions.type_specific.is_locked` 之类的锁定态重复字段.
- 禁止 facts 同时写 `is_superuser/is_locked` 与 `capabilities` 作为并列真源.

### 3.3 允许项(兼容期)

- 允许 API 继续输出 `is_superuser/is_locked`, 但其值必须由 `capabilities` 推导, 不允许从旧结构化列读取.
- 允许在兼容期保留 `account_permission.is_superuser/is_locked` 结构化列, 但它们只能是派生缓存(最终目标是移除或改为 generated column).

## 4. 目标方案(推荐)

### 4.1 核心决策

1) `capabilities` 作为唯一语义真源:

- `is_superuser := has_capability("SUPERUSER")`
- `is_locked := has_capability("LOCKED")`

2) `permission_facts` 升级为 v2 contract:

- 删除 `permission_facts.is_superuser` 与 `permission_facts.is_locked`.
- 增加 `LOCKED` capability, 并补齐 `capability_reasons` 的推导来源, 用于解释与排障.

3) `type_specific` 仅存账户属性:

- MySQL: `host`, `original_username`, `plugin`, `password_last_changed` 等.
- PostgreSQL: 仅保留非权限类属性(例如 `valid_until`). 角色权限类字段统一落到 `role_attributes` 或其他权限类别.
- Oracle: `account_status`, `default_tablespace` 等.
- SQLServer: `is_disabled` 等.

### 4.2 LOCKED capability 定义(跨 DB 统一语义)

语义: "不可登录/被锁定". 只关心账号是否能在目标 DB 登录, 不关心账号是否在系统内展示(展示由 `InstanceAccount.is_active` 等控制).

建议推导规则(来源只允许来自 snapshot categories 与 type_specific 属性, 不允许读取旧 `is_locked` 列作为真源):

- MySQL: 以 `mysql.user.account_locked` 或等价采集结果为准.
- PostgreSQL: `role_attributes.can_login == false` 或 `valid_until` 已过期(若可用).
- Oracle: `type_specific.account_status != "OPEN"`(注意包含 `LOCKED(TIMED)` 等变体).
- SQLServer: `type_specific.is_disabled == true`.

### 4.3 is_superuser capability 定义(跨 DB 统一语义)

语义: "拥有超级权限". 以各 DB 的官方等价定义为准.

建议推导规则(禁止读取旧 `is_superuser` 列作为真源):

- PostgreSQL: `role_attributes.rolsuper == true` 或等价字段.
- SQLServer: `server_roles` 包含 `sysadmin`.
- Oracle: `oracle_roles` 包含 `DBA`(或同等能力来源).
- MySQL: 以 `mysql.user.Super_priv` 或等价采集结果为准.

## 5. 方案选项(2-3 个)与推荐

### Option A: 保留结构化列, 但统一写入点

做法:

- 仍保留 `account_permission.is_superuser/is_locked`.
- adapter 不再写入派生状态到 `type_specific`.
- manager 在生成 `permission_facts` 后, 用 `capabilities` 反向回填结构化列.

优点:

- 改动小, 读侧与 SQL 查询无需改造.

缺点:

- 仍存在重复存储, 需要持续保证一致性门禁.

### Option B: 移除结构化列, 查询全部基于 JSONB capabilities

做法:

- 删除 `account_permission.is_superuser/is_locked`.
- 过滤条件改为 `permission_facts->'capabilities' ? 'SUPERUSER'` / `'LOCKED'`.
- 建立 GIN index: `gin ((permission_facts->'capabilities'))`.

优点:

- 数据模型最干净, 真源唯一.

缺点:

- 排序需要额外处理(表达式排序/生成列/物化视图), 否则可能带来性能风险.
- ORM 侧需要封装统一的 query helper, 避免散落 JSON 运算.

### Option C: 结构化列保留, 但改为 DB generated column(推荐)

做法:

- `is_superuser`/`is_locked` 不再由应用写入.
- 由 DB 通过表达式从 `permission_facts.capabilities` 生成, 并可继续使用 btree index 支撑排序/过滤.

优点:

- 真源唯一(仍然是 `capabilities`), 同时保留现有查询体验与性能.
- 读侧改动最小, 迁移风险可控.

缺点:

- 需要 DB 支持 generated column, 迁移脚本复杂度略高.

推荐结论:

- 推荐 Option C 作为主路径.
- Option B 作为长期目标备选(当确认不需要对 `is_superuser/is_locked` 做高频排序, 或确认 JSONB index 足够支撑时再切换).

## 6. 分阶段计划(每阶段验收口径)

### Phase 0: Contract 对齐与去重门禁

动作:

- 定义 `permission_facts v2` schema, 引入 `LOCKED` capability.
- `dsl_v4.is_superuser()` 改为 `has_capability("SUPERUSER")`(保持历史规则数据不动).
- 新增门禁: `type_specific` 禁止字段清单校验(至少拦截 `is_superuser`, `is_locked`, `roles`, `privileges`).

验收:

- unit tests 覆盖 facts 构建与 DSL 行为.
- 线上(或本地)对同一账户, `capabilities` 推导与旧字段输出一致(允许极少量例外并有 error codes).

### Phase 1: adapters 输出标准化(type_specific 去权限化, 去锁定态重复)

动作:

- MySQL:
  - 删除 `type_specific.is_locked`, 删除 `type_specific.can_grant`(迁移到权限类别或仅用于 capability reason).
- PostgreSQL:
  - 删除 `type_specific.can_*` 这类权限属性(统一保留在 `role_attributes`).
  - `type_specific` 仅保留非权限属性(例如 `valid_until`, 或为空).
- Oracle/SQLServer:
  - 确保不写入 `type_specific.is_locked/is_superuser`.

验收:

- `AccountPermission.type_specific` 结构稳定, 不包含禁用字段.
- UI 仍能展示需要的属性字段(例如 MySQL `plugin`).

### Phase 2: 读侧切换(从 columns/facts keys 切到 capabilities)

动作:

- API 输出:
  - `is_superuser/is_locked` 从 `capabilities` 推导.
  - `permission_facts` 对外如有暴露, 仅保留 v2 contract.
- Repository filters:
  - ledger/instances list 过滤与排序改为使用 "capabilities -> generated column 或统一 query helper".
- 删除所有 `type_specific` 锁定态兜底推导逻辑.

验收:

- API contract tests 全绿.
- ledger/instances list 的过滤与排序性能满足门槛.

### Phase 3: 数据库结构化列去真源化(Option C 落地)

动作:

- 将 `account_permission.is_superuser/is_locked` 迁移为 generated column(来源 `permission_facts.capabilities`).
- 确保 ORM 写入链路不再设置这两列.

验收:

- 迁移后随机抽样数据一致.
- `EXPLAIN` 显示过滤/排序能命中索引(至少不出现全表扫描退化).

### Phase 4: 清理与收尾

动作:

- 删除 `permission_facts.is_superuser/is_locked` 相关存量兼容代码.
- 更新 reference 文档, 明确 `type_specific` 与 `capabilities` 的职责边界.

验收:

- `rg` 全库无 `type_specific.*is_locked` 等残留写入/兜底.

## 7. 风险与回滚

主要风险:

- facts 推导与旧字段存在差异(例如 MySQL 超管/锁定态的边界定义).
- JSONB/generator 迁移带来索引与查询计划变化, 影响列表性能.

回滚策略(按 Phase):

- Phase 0/1: 仅做校验与输出标准化, 可直接回滚代码.
- Phase 2: 保留 feature flag, 支持回退到旧列读取(仅限迁移期).
- Phase 3: DB 迁移需要提供 downgrade, 或采用 "新增列+切换+保留旧列一段时间" 的安全迁移策略.

## 8. 验证与门禁

建议验证命令:

- 单测: `uv run pytest -m unit`
- 格式化: `make format`
- 类型检查: `make typecheck`

建议新增门禁(脚本或 CI):

- 半角字符检查(文档/注释): `rg -n -P \"[\\\\x{3000}\\\\x{3001}\\\\x{3002}\\\\x{3010}\\\\x{3011}\\\\x{FF01}\\\\x{FF08}\\\\x{FF09}\\\\x{FF0C}\\\\x{FF1A}\\\\x{FF1B}\\\\x{FF1F}\\\\x{2018}\\\\x{2019}\\\\x{201C}\\\\x{201D}\\\\x{2013}\\\\x{2014}\\\\x{2026}]\" docs app scripts tests`
- 禁止 `type_specific` 写入锁定态: `rg -n \"type_specific\\[\\\"is_locked\\\"\\]|type_specific\\.get\\(\\\"is_locked\\\"\" app/services/accounts_sync/adapters`
- facts v2 contract: 针对 `capabilities`/`capability_reasons`/`errors` 的 schema 校验单测.

