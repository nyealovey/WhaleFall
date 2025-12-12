# Ruff 全量扫描修复计划（更新：2025-12-12 14:05）

> 最新全量报告：`docs/reports/ruff_full_2025-12-12_140554.txt`（共 282 项告警）。以下计划仅反映本次扫描结果，用于指导后续 P0/P1 修复。

## 1. 主要问题分布
| 类型 | 代表规则 | 关键文件 | 行动建议 |
| --- | --- | --- | --- |
| **账户分类/同步导入与性能** | `TC003`、`PERF401`、`E501` | `app/services/account_classification/classifiers/*`、`orchestrator.py` | 将 `collections.abc`/TypedDict 导入移入 `TYPE_CHECKING`，压缩长推导，使用列表推导或 `extend` 替换循环。 |
| **Accounts Sync 适配器与协调层** | `I001`、`PGH003`、`COM812`、`TC003`、`E501` | `app/services/accounts_sync/adapters/*`、`account_query_service.py`、`coordinator.py`、`permission_manager.py` | 统一 import block、`type: ignore`，补 trailing comma，拆分 SQL Server 拼接块并消除长行。 |
| **聚合服务与 runner 复杂度** | `ARG002`、`C901`、`PLR0913`、`ISC001` | `app/services/aggregation/{aggregation_service,database_aggregation_runner,instance_aggregation_runner}.py`、`calculator.py` | 拆 helper、提取数据类，消除未用参数和隐式拼接。 |
| **实用工具与日志模块** | `D205`、`D417`、`I001`、`PLC0415`、`ANN401`、`TRY300` | `app/utils/{decorators,logging*,password_crypto_utils,query_filter_utils,rate_limiter,safe_query_builder,time_utils,version_parser}.py` | 补中文 docstring、完善 Args 描述，移出函数内 import，补类型注解与 `ClassVar`。 |
| **数据库同步适配器与基础设施** | `TC003`、`D107`、`RUF012`、`G201`、`C901` | `app/services/database_sync/adapters/*`、`migrations/env.py`、`nginx/gunicorn-*.conf.py`、`tmp_ble_test.py` | 整理导入、补 docstring/类型、重构高复杂度采集函数，按 Alembic 要求补注解或 `__init__.py`。 |

## 2. P0（立即修复）
1. **账户分类 classifiers 与 orchestrator**  
   - 处理 `oracle/postgresql/sqlserver` classifier 的 `PERF401/E501/TC003`；`orchestrator.py:386` 改为列表推导。  
   - 命令：`ruff check app/services/account_classification/classifiers app/services/account_classification/orchestrator.py --select PERF401,E501,TC003`.
2. **Accounts Sync 适配器导入与 SQL 拼接**  
   - 整理 `accounts_sync/adapters/*` 的 import、`type: ignore`、长行与 trailing comma；修正 `account_query_service.py`、`coordinator.py`、`permission_manager.py` 的 `COM812/TC003`。  
   - 命令：`ruff check app/services/accounts_sync --select I001,PGH003,COM812,TC003,E501`.
3. **聚合服务与 runners 复杂度**  
   - `aggregation_service.py` 清理未用参数与 `C901` 方法，`database_aggregation_runner.py`/`instance_aggregation_runner.py` 降低 `PLR0913` 并合并字符串；`calculator.py` 导入放入 `TYPE_CHECKING`。  
   - 命令：`ruff check app/services/aggregation --select ARG002,C901,PLR0913,ISC001,TC003`.
4. **核心工具与日志体系文档/导入**  
   - `app/utils/decorators.py` 增补 Args 说明、调整 docstring 空行；`logging/*`、`password_crypto_utils.py`、`query_filter_utils.py`、`rate_limiter.py`、`safe_query_builder.py`、`time_utils.py` 全量清理 `PLC0415/TRY300/RUF012`。  
   - 命令：`ruff check app/utils --select D205,D417,I001,PLC0415,TRY300,RUF012,ANN401`.
5. **数据库同步适配器与基础设施文件**  
   - `database_sync/adapters/*` 调整 `TYPE_CHECKING` 导入、`ClassVar`、logging 规范与复杂度；`migrations/env.py`、`nginx/gunicorn-*.conf.py`、`tmp_ble_test.py` 补模块/函数注解及命名。  
   - 命令：`ruff check app/services/database_sync migrations nginx tmp_ble_test.py --select TC003,D107,RUF012,G201,C901,ANN201,N999`.

## 3. P1（结构性工作）
- 为账户分类与账户同步共享一套 `Sequence`/TypedDict 类型定义，减少跨模块 `TYPE_CHECKING` 重复。
- 聚合 runner 与 version parser 的长逻辑拆分为 `@dataclass` Pipeline，逐步压低 `C901/PLR0911`。
- 日志队列、rate limiter、SQL Server connection utils 引入统一 helper 以避免重复 `TRY300/PLC0415` 模式。

## 4. 验证建议
1. 每个批次完成后执行对应 `ruff check` 子集，必要时附 `--fix`。  
2. 涉及数据库/驱动导入的模块在 CI 中使用 stub 或 mock，确保缺少驱动时也能通过。  
3. 聚合与 accounts sync 结构调整后，至少跑 `pytest -m unit` 与 `ruff check --select C901,PLR0913 app/services/aggregation app/services/accounts_sync`.  
4. 全量修复完成后，复跑最新 `docs/reports/ruff_full_*.txt` 生成脚本，确保计划项全部消化。
