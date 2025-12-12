# Ruff 全量扫描修复计划（更新：2025-12-12 12:29）

> 最新全量报告：`docs/reports/ruff_full_2025-12-12_122910.txt`（共 397 条告警，涉及 40 个规则 ID，带 `[*]` 的可通过 `ruff --fix` 自动处理）。以下计划以本次扫描为唯一基准。

## 1. 主要问题分布
| 类型 | 命中数（约） | 代表文件 | 行动建议 |
| --- | --- | --- | --- |
| **结构复杂度（C901/PLR091x）** | ~50 | `app/routes/instances/manage.py`、`app/routes/partition.py`、`app/routes/instances/detail.py` | 拆分 `_execute`、查询 + 序列化逻辑，下沉批量计算，必要时引入 service/helper。|
| **导入与 TYPE_CHECKING（TC003/TC002/I001）** | ~57 | `app/models/instance.py`、`app/routes/scheduler.py`、`app/routes/instances/detail.py`、`app/routes/users.py` | 将 `collections.abc`/第三方导入移入 `TYPE_CHECKING`，使用 `typing` stub，运行 isort/ruff 校验。|
| **Docstring 规范（D202/D205/D102/D107）** | ~54 | `app/models/{credential,instance}.py`、`app/routes/history/logs.py`、`app/scheduler.py` | Docstring 采用“摘要+空行+详情+Args”等中文模板，移除 docstring 与函数体之间空行。|
| **类型注解与 Any（ANN401/ANN201/ANN001）** | ~9 | `app/models/{credential,instance,unified_log}.py`、部分 helper | 为 `**kwargs` / `**entry_fields` 定义 TypedDict 或显式参数对象，去除 Any。|
| **格式化问题（COM812/E501/TRY300 等）** | ~90 | `app/routes/partition.py`、`app/routes/tags/manage.py`、`app/routes/users.py` | 自动补拖尾逗号、控制行宽，统一 `try` 结构，`ruff --fix --select COM812,E501` 可批量处理。|
| **安全及敏感项（S105/S608）** | 9 | `app/constants/http_headers.py`、`app/routes/accounts/*` | 用配置驱动常量或 `noqa` 注释说明用途，检查 SQL 拼接参数化。|

## 2. P0（立即修复）
1. **CSRF 头部常量 S105（app/constants/http_headers.py）**：调整为通过集中元组或 `typing.Final` 暴露，并在注释中解释“header key only”，必要时将值放入配置后再引用。验证：`ruff check app/constants/http_headers.py --select S105`。
2. **模型构造与日志参数（app/models/{credential,instance,unified_log}.py）**：
   - 为 `**kwargs`/`**entry_fields` 创建 TypedDict（如 `CredentialOrmFields`、`LogEntryKwargs`），或在 `TYPE_CHECKING` 中声明 SQLAlchemy Base mixin，消除 `ANN401`；
   - 将 dataclass/构造 docstring 后空行移除，并依据 `AGENTS.md` 补完中文说明；
   - `Instance` 中的 `Sequence` 引入移动至 `TYPE_CHECKING`，防止 `TC003`。验证：`ruff check app/models -n --select ANN401,D202,TC003`。
3. **历史日志与调度模块 Docstring（app/routes/history/logs.py、app/scheduler.py）**：移除内部空行，确保 helper docstring 完成度，并复用 `_determine_per_page` 等新 helper；`app/scheduler.py` 同时需要将 `Flask`/`apscheduler` 放入 `TYPE_CHECKING` 并消除 D202。验证：`ruff check app/routes/history/logs.py app/scheduler.py --select D202,TC002`。
4. **实例/分区路由复杂度（app/routes/instances/{manage,detail}.py、app/routes/partition.py）**：
   - 将 `_execute`/`list_instances_data`/`get_core_aggregation_metrics` 拆分为过滤、分页、序列化、响应四段 helper，结合服务层减少 `C901`/`PLR091x`；
   - 同步修复同文件中的 `COM812` 与导入顺序问题。验证：`ruff check app/routes/instances app/routes/partition.py --select C901,PLR0912,PLR0913,COM812`。
5. **Scheduler/Users 路由导入治理（app/routes/scheduler.py、app/routes/users.py、app/scheduler.py）**：
   - 将 `apscheduler` 与 `flask.Flask` 导入移动到 `TYPE_CHECKING`，运行 isort；
   - `_load_tasks_from_config` 等 docstring 去掉多余空行；
   - 用户路由需重新排序导入块，保证 `app.types` 放在内部导入之后。验证：`ruff check app/routes/scheduler.py app/routes/users.py app/scheduler.py --select I001,TC002,D202`。

## 3. P1（结构性 / 中期优化）
- **批量格式化（COM812/E501）**：对 `app/routes/partition.py`、`app/routes/tags/manage.py`、`app/routes/accounts/*` 执行 `ruff --fix --select COM812,E501`，并人工复核多行表达式尾逗号。
- **TRY300/PLC0415 清理**：审查长 `try` 块与函数体内导入（`app/routes/accounts/*`、`app/routes/partition.py`），将导入提升或封装 helper，确保 `try` 中不直接 `return`。
- **数据库/实例视图复杂度**：在 `app/routes/instances/detail.py` 中为 `_fetch_latest_database_sizes`、`_fetch_historical_database_sizes` 引入参数对象或 dataclass，减少位置参数超过 5 的问题。 
- **安全扫描（S608/PGH003）**：针对报告中的 SQL/模板字符串，统一使用参数化查询或 `text()` + 绑定变量，并在必要位置添加注释说明数据来源。 

## 4. 验证建议
- 每完成一个模块，运行 `ruff check <files> --select <相关规则>` 进行增量验证；
- 导入/排序修改后执行 `ruff check <files> --select I001,TC00?`；
- 对结构拆分模块补充单元测试或至少通过 `make test` 验证关键路径；
- 所有改动提交前再跑一次 `ruff check --preview` 以确认告警数量下降。 
