# Ruff 全量扫描修复计划（更新：2025-12-13 13:58）

> 最新全量报告：`docs/reports/ruff_full_2025-12-13_135811.txt`（生成于 2025-12-13 13:58:11）。以下计划全面替换旧版修复计划。

## 1. 规则匹配数量（按出现次数降序）
| 规则 | 数量 | 典型文件（示例） |
| --- | --- | --- |
| COM812 | 27 | `app/services/form_service/scheduler_job_service.py` |
| D102 | 18 | `app/types/query_protocols.py` |
| TRY300 | 17 | `app/tasks/capacity_collection_tasks.py` |
| I001 | 11 | `app/services/form_service/classification_rule_service.py` |
| TC003 | 11 | `app/services/database_sync/adapters/base_adapter.py` |
| PLC0415 | 10 | `app/tasks/accounts_sync_tasks.py` |
| D107 | 8 | `app/services/database_sync/inventory_manager.py` |
| TC002 | 8 | `app/services/form_service/scheduler_job_service.py` |
| PLR0913 | 7 | `app/services/statistics/database_statistics_service.py` |
| D205 | 7 | `app/services/partition_management_service.py` |
| INP001 | 6 | `app/services/statistics/account_statistics_service.py` |
| C901 | 6 | `app/tasks/capacity_aggregation_tasks.py` |
| D103 | 6 | `app/types/converters.py` |
| ANN001 | 3 | `migrations/env.py` |
| ANN201 | 3 | `migrations/env.py` |
| D417 | 3 | `app/services/aggregation/database_aggregation_runner.py` |
| G201 | 3 | `app/tasks/log_cleanup_tasks.py` |
| PLR0911 | 3 | `app/services/form_service/classification_service.py` |
| PLR0915 | 3 | `app/tasks/accounts_sync_tasks.py` |
| TC001 | 3 | `app/utils/route_safety.py` |
| ARG002 | 4 | `app/utils/logging/handlers.py` |
| D100 | 1 | `tmp_ble_test.py` |
| D105 | 1 | `app/services/form_service/scheduler_job_service.py` |
| ANN401 | 1 | `app/services/connection_adapters/adapters/oracle_adapter.py` |
| FBT001 | 1 | `app/services/form_service/credential_service.py` |
| N806 | 1 | `app/utils/logging/queue_worker.py` |
| SLF001 | 1 | `app/tasks/accounts_sync_tasks.py` |
| E501 | 2 | `app/utils/sqlserver_connection_utils.py` |
| N999 | 2 | `nginx/gunicorn/gunicorn-dev.conf.py` |
| PLR0912 | 2 | `app/tasks/capacity_aggregation_tasks.py` |

## 2. P0（立即处理，影响稳定性/可读性）
- **TRY300（17）**：多处在 `except` 后直接 `return`，需改为 `else`/`finally` 确保异常路径清晰（`app/tasks/capacity_collection_tasks.py`、`sync_session_service.py` 等）。  
- **G201（3）**：将 `logger.error(..., exc_info=True)` 改为 `logger.exception`（`app/tasks/accounts_sync_tasks.py`、`log_cleanup_tasks.py`）。  
- **PLC0415（10）**：函数体内延迟导入应移到顶部或封装懒加载 helper，避免隐藏依赖（`app/tasks/accounts_sync_tasks.py` 等）。  
- **INP001（6）/N999（2）**：补充缺失的 `__init__.py`（statistics、migrations 等目录），并重命名 `nginx/gunicorn-*.conf.py` 以满足模块命名规范。  
- **E501（2）**：`app/utils/sqlserver_connection_utils.py` 的长行按 120 列折行并补尾逗号。

## 3. P1（批量快捷修复）
- **导入/类型块（I001/TC002/TC003/TC001，合计 33 条）**  
  - 统一将 `collections.abc`、第三方依赖放入 `TYPE_CHECKING`，整理 import 顺序（database_sync 适配器、form_service、types 包）。  
  - 验证命令：`ruff check app/services app/types app/utils --select I001,TC001,TC002,TC003`.
- **格式/文档（COM812/D205/D107/D417，45 条）**  
  - 补尾逗号、摘要与描述间空行、构造函数/参数 docstring（中文 Google 模板），优先处理表单服务与聚合 Runner。  
  - 验证命令：`ruff check app/services app/types --select COM812,D205,D107,D417`.

## 4. P2（复杂度与参数治理）
- **复杂度/分支（C901/PLR0911/0912/0913/0915，21 条）**  
  - 拆分 `capacity_aggregation_tasks.py` 与 `capacity_collection_tasks.py` 大函数；表单校验与统计服务函数按职责分解，减少返回/分支数量。  
  - 建议先抽取参数校验与数据库交互小函数，再补对应单测（`pytest -k capacity_collection_tasks`）。
- **布尔位置参数（FBT001 1条）**  
  - `credential_service.validate` 的 `require_password` 改为关键字参数或枚举。

## 5. P3（类型与日志细节）
- **类型精确化（ANN001/ANN201/ANN401，共7条）**：为 Alembic helper 补返回类型，Oracle 适配器避免 `Any`。  
- **未使用参数（ARG002 4条/N806 1条/SLF001 1条）**：使用下划线前缀或删除未用参数；`queue_worker` 中局部变量改小写；避免访问 Flask 私有属性。  
- **文档缺失（D100/D105/D103/D102）**：公共协议与工具函数补 docstring，解释用途与参数（中文）。

## 6. 验证顺序
1) 先执行 P0 定向规则：`ruff check app/tasks app/services --select TRY300,G201,PLC0415,E501`；补 `__init__.py` 后重跑 `ruff check app/services/statistics migrations`.  
2) 批量导入与格式：`ruff check app --select I001,TC001,TC002,TC003,COM812,D205,D107,D417`.  
3) 复杂度与参数治理：`ruff check app --select C901,PLR0911,PLR0912,PLR0913,PLR0915,FBT001`; 对改动函数补/更新单测。  
4) 收尾类型与文档：`ruff check app migrations nginx tmp_ble_test.py --select ANN,ARG,N806,SLF001,D100,D102,D103,D105`.  
5) 全量验证：`ruff check` + `pyright`；必要时 `pytest -m unit -k capacity_collection_tasks or scheduler_job_service`.

## 7. 输出与跟踪
- 修复完成后生成新报告 `docs/reports/ruff_full_<日期>_<时间>.txt` 并同步此计划。  
- PR 需说明：已清零的规则列表、仍存在的遗留告警及原因（如待重构或外部依赖），并附运行命令记录。
