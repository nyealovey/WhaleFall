# Ruff 全量扫描修复计划（更新：2025-12-13 18:58）

> 最新全量报告：`docs/reports/ruff_full_2025-12-13_185806.txt`（生成于 2025-12-13 18:58:06）。以下计划全面替换旧版修复计划。

## 1. 规则匹配数量（按出现次数降序）
| 规则 | 数量 | 典型文件（示例） |
| --- | --- | --- |
| D400 | 6 | `app/services/database_type_service.py` |
| D415 | 6 | `app/services/partition_management_service.py` |
| D417 | 5 | `app/services/sync_session_service.py` |
| F821 | 4 | `app/services/sync_session_service.py` |
| ANN001 | 4 | `app/tasks/accounts_sync_tasks.py` |
| PLC0415 | 3 | `app/services/form_service/scheduler_job_service.py` |
| TRY003 | 3 | `app/tasks/capacity_collection_tasks.py` |
| EM102 | 3 | `app/tasks/capacity_collection_tasks.py` |
| UP037 | 2 | `app/services/form_service/scheduler_job_service.py` |
| ANN202 | 2 | `app/services/statistics/database_statistics_service.py` |
| E501 | 2 | `app/tasks/accounts_sync_tasks.py` |
| I001 | 2 | `migrations/env.py` |
| UP035 | 1 | `app/services/connection_adapters/adapters/oracle_adapter.py` |
| TC004 | 1 | `app/tasks/accounts_sync_tasks.py` |
| TC006 | 1 | `app/tasks/accounts_sync_tasks.py` |
| TRY300 | 1 | `app/tasks/accounts_sync_tasks.py` |
| FBT001 | 1 | `app/tasks/capacity_aggregation_tasks.py` |
| B905 | 1 | `app/tasks/capacity_collection_tasks.py` |
| RUF100 | 1 | `app/utils/version_parser.py` |
| TC002 | 1 | `migrations/env.py` |

## 2. P0（立即处理，影响稳定性/可读性）
- **TRY003/EM102（各3）**：`capacity_collection_tasks.py` 中直接用 f-string 抛出 `AppError`，需先赋值再抛出，避免重复长消息。  
- **F821（4）**：`sync_session_service.py` 未定义的 `items_*` 变量，补默认值或从上下文传入，防止运行期异常。  
- **PLC0415（3）/UP035（1）**：移除函数内延迟导入（scheduler_job_service）并改用 `collections.abc` 导入接口类型。  
- **TRY300（1）/B905（1）**：`accounts_sync_tasks.py` 的 try-return、`zip` 未显式 strict，按建议调整控制流与 strict 参数。  
- **RUF100（1）**：移除 `version_parser.py` 的无效 `noqa`，确保告警可见。

## 3. P1（批量快捷修复）
- **文档/格式（D400/D415/D417，17 条）**：补首行句号及参数描述，覆盖 database_type_service、partition_management_service、sync_session_service。  
- **类型/注解（ANN001/ANN202 6 条）**：accounts_sync_tasks 私有函数补参数/返回类型；统计服务私有方法补返回类型。  
- **导入/typing（I001/TC002/TC004/TC006 5 条）**：migrations/env.py 及 accounts_sync_tasks 调整导入顺序与 TYPE_CHECKING 位置，`typing.cast` 使用字符串类型。  
- **样式（UP037/UP035/E501 5 条）**：scheduler_job_service 去掉引号注解，Oracle 适配器改用 collections.abc，超长行折行。  
- **布尔位置参数（FBT001 1 条）**：`_init_aggregation_session` 改为关键字参数或枚举标志。

## 4. P2（复杂度与参数治理）
- 当前报告未出现复杂度告警，保持近期重构成果；关注修复过程中避免新增 C901/PLR09xx。

## 5. 收尾与遗留
- **E501（2）**：accounts_sync_tasks 中超长行随同本轮一起折行。  
- **TC002（1）**：`migrations/env.py` 需将 `MigrationContext` 放入 TYPE_CHECKING，配合 I001 调整。  
- 修复完成后再确认无新增告警，并更新计划。

## 6. 验证顺序
1) 定向 P0：`ruff check app/tasks app/services --select TRY003,EM102,PLC0415,UP035,F821,TRY300,B905,RUF100`.  
2) 导入与 typing：`ruff check app migrations --select I001,TC002,TC004,TC006,UP037`.  
3) 文档/格式与类型：`ruff check app --select D400,D415,D417,ANN001,ANN202,E501,FBT001`.  
4) 全量回归：`ruff check` + `pyright`；必要时 `pytest -m unit -k accounts_sync_tasks capacity_collection_tasks`。

## 7. 输出与跟踪
- 修复完成后生成新报告 `docs/reports/ruff_full_<日期>_<时间>.txt` 并同步此计划。  
- PR 需说明：已清零的规则列表、仍存在的遗留告警及原因（如待重构或外部依赖），并附运行命令记录。
