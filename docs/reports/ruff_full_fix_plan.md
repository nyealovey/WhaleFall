# Ruff 全量扫描修复计划（更新：2025-12-12 14:39）

> 最新全量报告：`docs/reports/ruff_full_2025-12-12_143953.txt`（293 项告警）。以下计划聚焦本次扫描暴露的问题，替换旧版计划。

## 1. 主要问题分布
| 类型 | 代表规则 | 关键文件 | 行动建议 |
| --- | --- | --- | --- |
| **路由/蓝图导入规范** | `PLC0415` | `app/routes/accounts/sync.py` | 清理函数内导入（例如 `_run_sync_task`），改为惰性 helper 或模块级导入 + 工具函数，确保 Flask 路由模块符合 Ruff 要求。 |
| **账户分类与同步适配器** | `PERF401`、`E501`、`TC003`、`COM812`、`PGH003` | `app/services/account_classification/classifiers/*`、`app/services/accounts_sync/adapters/*`、`account_query_service.py`、`coordinator.py` | 统一导入顺序，将 `collections.abc`/驱动导入移入 `TYPE_CHECKING`，替换长行与缺失逗号，使用推导式/`extend` 取代循环。 |
| **账户同步 SQL Server 适配器** | `TC003`、`PGH003`、`E501`、`COM812` | `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 继续整理导入、`type: ignore` 说明、长 SQL 串以及 trailing comma，保证 JSON/CTE 结构可维护。 |
| **聚合服务与 runner** | `ARG002`、`C901`、`PLR0913`、`ISC001`、`TC003` | `app/services/aggregation/*` | 拆分超长方法、移除未用参数、规整字符串拼接与 typed import。 |
| **通用 utils/logging 模块** | `D205`、`D417`、`I001`、`PLC0415`、`ANN401`、`TRY300` | `app/utils/{decorators,logging*,password_crypto_utils,query_filter_utils,rate_limiter,response_utils,route_safety,safe_query_builder,time_utils,version_parser}.py` | 补 docstring 结构、移动 import、添加类型注解/`ClassVar`，统一日志处理逻辑。 |
| **数据库同步适配器与 migrations** | `TC003`、`D107`、`RUF012`、`G201`、`ANN201`、`INP001` | `app/services/database_sync/adapters/*`、`migrations/env.py`、`nginx/gunicorn/*.conf.py`、`tmp_ble_test.py` | 处理导入/类型注解、增加 `__init__.py` 或重命名配置文件，重构复杂函数并覆盖日志规范。 |

## 2. P0（立即修复）
1. **路由与任务入口导入**  
   - `app/routes/accounts/sync.py:47` 仍在函数体内导入任务导致 `PLC0415`；需要改为模块级或包装 helper。  
   - 验证：`ruff check app/routes/accounts/sync.py --select PLC0415`。
2. **账户分类 classifiers & orchestrator**  
   - 处理 `oracle_classifier.py` 的 `PERF401/E501`，`postgresql/sqlserver` classifier 的 `TC003/E501`，以及 `orchestrator.py:386` 的 `PERF401`。  
   - 验证：`ruff check app/services/account_classification --select PERF401,E501,TC003`。
3. **Accounts Sync 适配器导入与 SQL 规范**  
   - `accounts_sync/adapters/{mysql,oracle,postgresql,sqlserver}.py` 存在 `I001/TC003/PGH003/E501/COM812`；`account_query_service.py` 缺 trailing comma；`coordinator.py` 需要移动 `TracebackType` 导入并补逗号。  
   - 验证：`ruff check app/services/accounts_sync --select I001,TC003,PGH003,E501,COM812`。
4. **聚合服务复杂度与未用参数**  
   - `aggregation_service.py` 中 `_ensure_partition_for_date`、`_commit_with_partition_retry` 需移除未使用参数；`aggregate_current_period` 等需拆分；对应 runner 文件修复 `PLR0913/ISC001`；`calculator.py` 调整 `Callable` 导入。  
   - 验证：`ruff check app/services/aggregation --select ARG002,C901,PLR0913,ISC001,TC003`。
5. **Utils/Logging 模块 docstring 与导入**  
   - `app/utils/decorators.py` 补充 Args 描述、去掉 docstring 后空行；`logging/error_adapter.py` 等移除函数内 import；`password_crypto_utils.py` 校正 docstring、添加 `TRY300` else 块。  
   - 验证：`ruff check app/utils --select D101,D202,D205,D417,I001,PLC0415,TRY300,ANN401,RUF012`。

## 3. P1（结构性工作）
- **数据库同步适配器治理**：`app/services/database_sync/adapters/*` 存在 `TC003/D107/RUF012/G201/C901`，需统一导入模式、增加 docstring 和 `ClassVar`，并分解 `_collect_tablespace_sizes` 等复杂方法。
- **Alembic & Nginx 元数据**：`migrations/env.py` 缺注解且暴露 `INP001`，`nginx/gunicorn*.py` 命名不合法；建议增加 `migrations/__init__.py`、重构函数签名并将 gunicorn 配置改为纯文本或符合 Python 模块命名。
- **辅助脚本清理**：`tmp_ble_test.py`、`app/utils/sqlserver_connection_utils.py` 等需要移除临时代码或统一日志/字符串处理方式。

## 4. 验证建议
1. 每批修改完成后按文件执行 `ruff check <paths> --select <rules>`，确保对应告警清零。  
2. 对账户同步 SQL Server 适配器的 SQL 修改，至少执行一次手动同步或添加单元测试以避免回归。  
3. 聚合服务和 utils 模块属于核心逻辑，建议配合 `pytest -m unit` 验证关键路径。  
4. 全部修复完成后，重新运行 `ruff check --select I001,TC003,E501,PERF401,COM812 app` 及 `docs/reports/ruff_full_*.py` 生成脚本，确认新报告仅包含遗留/待定项。
