# Db Type Single Source Of Truth Refactor Plan (Option A)

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-28
> 更新: 2025-12-28
> 范围: 实例创建/更新, 凭据, 筛选下拉选项, API options, 连接测试, db_type 校验
> 关联: `app/constants/database_types.py`, `app/utils/data_validator.py`, `app/services/database_type_service.py`

## 1. 背景与问题

当前仓库内的 `db_type`(数据库类型)存在多套"真源"并存, 导致行为不一致与维护成本上升:

- DB 配置表: `database_type_configs`(model: `app/models/database_type_config.py`) + `DatabaseTypeService.get_active_types()`(`app/services/database_type_service.py`)
- 页面/筛选静态常量: `DATABASE_TYPES`(`app/constants/filter_options.py`)
- 另一份表单常量: `DB_TYPE_OPTIONS`(`app/forms/definitions/account_classification_rule_constants.py`)
- 连接能力边界映射: `ConnectionFactory.CONNECTION_CLASSES`(`app/services/connection_adapters/connection_factory.py`)

现象与风险(已在代码中出现/可推导):

- UI 可选项与后端校验集合不一致(页面能选但后端不认, 或页面不能选但后端允许)
- 校验通过但落库不规范化: `DataValidator` 只校验 `lower()` 后的值, 但写入层未统一 `normalize()`(`app/services/instances/instance_write_service.py`, `app/services/credentials/credential_write_service.py`), 可能导致 `MYSQL` 这类值落库, 进而让 `instance.db_type == DatabaseType.MYSQL` 的分支失效
- 多处动态读 DB 配置带来不必要的 query 与故障耦合(例如 DB 配置表为空时, 下拉可能为空)

结论: `db_type` 不是高频变化配置, 适合采用"纯代码常量"作为单一真源, 以换取一致性与稳定性.

## 2. 目标 / 非目标

### 2.1 目标

- 单一真源: 任何"允许的 db_type 集合"与"下拉选项"只来自代码常量
- 一致性: UI/校验/API/连接能力边界对齐, 且写入前统一规范化
- 稳定性: 不依赖 `database_type_configs` 表是否存在/是否有数据
- 可演进: 未来若需要再引入 DB 配置, 以"覆盖 UI 展示"方式增量引入, 不影响核心校验与能力边界

### 2.2 非目标(本期不做)

- 不删除/迁移 `database_type_configs` 表与历史数据(先停止依赖, 后续再讨论清理策略)
- 不引入"可新增自定义 db_type"能力(Option A 明确不支持)
- 不重构权限配置与权限数据模型(仅保证 `db_type` 值集合一致)

## 3. 统一设计(Option A)

### 3.1 唯一真源

以 `app/constants/database_types.py::DatabaseType` 作为唯一真源, 并补齐/固化以下信息:

- 允许集合: "实例域"(Instance DB types)只允许 `mysql/postgresql/sqlserver/oracle`
- 展示信息: display name, icon, color
- 默认值: default port, default schema(如需要)
- 规范化: `normalize()`(包含别名如 `pg -> postgresql`, `mssql -> sqlserver`)

建议在 `app/constants/database_types.py` 内新增派生常量与 helper:

- `INSTANCE_DB_TYPES: tuple[str, ...] = DatabaseType.RELATIONAL`
- `DATABASE_TYPE_OPTIONS: list[dict[str, str]]` 统一输出 `value/label/icon/color`
- `get_default_schema(db_type: str) -> str` 与 `get_default_port(db_type: str) -> int | None` 统一从常量映射读取

### 3.2 统一输出形态(兼容现有调用方)

仓库中存在多种 option shape, 需要兼容并逐步统一:

- 页面/Jinja 下拉常见: `{ "value": "...", "label": "..." }`
- RESTX options API: `{ "value": "...", "text": "...", "icon": "...", "color": "..." }`
- 旧静态常量 `DATABASE_TYPES`: `{ "name": "...", "display_name": "...", "icon": "...", "color": "..." }`

策略:

- 内部统一用 `value/label/icon/color`, 并提供轻量转换函数以兼容旧字段(例如在 `FilterOptionsService`/routes 层做一次转换)
- 逐步移除 `DATABASE_TYPES` 与 `DB_TYPE_OPTIONS` 的手写列表, 改为引用唯一真源生成

### 3.3 校验与写入规范化(必须修复)

把"校验允许集合"与"落库值规范化"拆开, 但都只依赖代码常量:

- `DataValidator.validate_db_type()` 与 `validate_instance_data()`:
  - allowed set 固定为 `INSTANCE_DB_TYPES`
  - 不再读取 `DatabaseTypeService.get_active_types()`(去掉动态 DB 依赖)
- `InstanceWriteService`/`CredentialWriteService`:
  - 在赋值前调用 `DatabaseType.normalize()`并写回, 保证落库永远是标准小写值

## 4. 影响面清单(当前实现盘点)

### 4.1 当前从 DB 动态读取 db_type 的位置(将移除)

- `app/utils/data_validator.py`:
  - `_resolve_allowed_db_types()` 当前优先读取 `DatabaseTypeService.get_active_types()`后回退静态白名单
- `app/services/common/filter_options_service.py` + `app/repositories/filter_options_repository.py`:
  - `get_common_database_types_options()` 当前从 `database_type_configs` 表读取
- 多处页面/表单 context:
  - `app/forms/handlers/instance_form_handler.py`
  - `app/routes/instances/manage.py`
  - `app/routes/capacity/instances.py`
  - `app/services/capacity/capacity_databases_page_service.py`
  - `app/services/connection_adapters/adapters/base.py::get_default_schema()`

### 4.2 当前使用静态列表/重复定义的位置(将统一引用真源)

- `app/constants/filter_options.py::DATABASE_TYPES`
- `app/forms/definitions/account_classification_rule_constants.py::DB_TYPE_OPTIONS`
- 页面路由:
  - `app/routes/credentials.py`, `app/routes/accounts/ledgers.py`, `app/routes/databases/ledgers.py`

### 4.3 能力边界(保持但对齐真源)

- `app/services/connection_adapters/connection_factory.py::CONNECTION_CLASSES`
- `app/services/database_sync/adapters/factory.py::_ADAPTERS`

上述映射应改为使用 `DatabaseType.*` 常量作为 key, 并与 `INSTANCE_DB_TYPES` 保持一致.

## 5. 分阶段落地计划

### Phase 1: 引入唯一真源与 option 生成

- 扩展 `app/constants/database_types.py` 以覆盖 icon/color/default schema 等信息
- 提供 `DATABASE_TYPE_OPTIONS`(或等价函数)作为唯一 options 来源
- 保持现有 `app/constants/filter_options.py::DATABASE_TYPES` 不变, 但逐步改为由真源生成(避免破坏性改动)

验收:

- 不依赖 DB, 任何页面仍能渲染 db_type 下拉
- `rg -n \"DatabaseTypeService.get_active_types\\(\" app` 的调用仅保留"未来可配置"相关代码, 不再影响核心流程

### Phase 2: 全量替换调用方, 移除 DB 读取

- 替换所有页面/表单/API options 的 db_type 来源为真源 options
- 替换 `DataValidator` 的 allowed set 为真源常量
- 替换 `get_default_schema()` 等 helper 不再查 DB

验收:

- `/api/v1/common/database-types/options` 不需要创建 `database_type_configs` 表即可返回数据
- `DataValidator` 的 db_type 校验不触发任何 DB query

### Phase 3: 写入规范化 + 测试与清理

- `InstanceWriteService` 与 `CredentialWriteService` 落库前统一 `normalize()`
- 将 `DB_TYPE_OPTIONS`/`DATABASE_TYPES` 的手写重复定义删除或改为从真源生成
- 更新单测, 覆盖:
  - options API 无 DB 表/无数据仍可返回
  - 输入 `MYSQL/pg/mssql` 等别名可被 normalize 并落库为标准值

验收:

- `pytest -m unit` 通过
- 新增/修改的 docstring 与 docs 内容符合半角字符规范

## 6. 兼容性, 回滚, 风险

### 6.1 兼容性

- 保持现有 API schema 不变(仅数据来源变为常量)
- 保持页面展示字段兼容(如果仍需旧 shape, 通过转换函数适配)

### 6.2 风险

- 若当前生产环境依赖 `database_type_configs` 自定义 display/icon, 将在 Option A 中失效
- 若存在历史数据 `db_type` 为非标准大小写或别名, 将在 Phase 3 统一规范化后改变表现(属于修复, 但需注意回归)

### 6.3 回滚

- 回滚策略为代码回滚: 恢复 `DatabaseTypeService.get_active_types()` 的读取路径与旧 options 生成逻辑
- 数据回滚一般不需要, 因为 normalize 只会把值收敛到标准集合(可通过脚本将标准值映射回旧值, 但不建议)
