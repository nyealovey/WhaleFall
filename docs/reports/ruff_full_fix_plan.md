# Ruff 全量扫描修复计划（更新：2025-12-12 16:45）

> 最新全量报告：`docs/reports/ruff_full_2025-12-12_164042.txt`（240 项告警）。下方计划基于本次扫描结果，替换旧版计划。

## 1. 主要问题分布
| 类型 | 代表规则 | 关键文件 | 行动建议 |
| --- | --- | --- | --- |
| **必修 F821 逻辑错误** | `F821` | `app/services/aggregation/database_aggregation_runner.py`、`app/utils/data_validator.py` | 多处引用未定义变量（`start_date`、`instance_id` 等）或未使用 `cls`，将导致运行时报错。需补充正确的参数/属性引用或改成实例属性。 |
| **类型提示与导入整理** | `TC006`、`TC003`、`I001` | 账户分类器、database_sync 系列适配器、`sqlserver_adapter.py` 等 | - `cast(Sequence[str] | None, ...)` 需加引号；<br> - 多个模块要把 `collections.abc` 放入 `TYPE_CHECKING`；<br> - 新增 dataclass 后的 import block 需重新 isort。 |
| **文档/注释缺失** | `D417`、`D107`、`D102` | 聚合 Runner、`database_sync/*`、`app/types/sync.py` | 公共方法缺少 docstring 或参数说明，按中文 Google 模板补齐，特别是 Runner `aggregate_period` 的 `callbacks`。 |
| **日志规则与可读性** | `G201`、`COM812`、`E501` | database_sync 模块、`cache_service.py`、`sqlserver_connection_utils.py` | 按要求改用 `logger.exception`；行尾缺逗号、字符串超长需拆分。 |
| **工具/类型定义问题** | `ANN401`、`RUF012`、`F821` | `oracle_adapter.py`、`database_sync/adapters/mysql_adapter.py`、`app/utils/cache_utils.py` | 为公共 API 补全类型、把可变 class attr 标记为 `ClassVar`，并补全缺失的别名（如 `TypingCallable`）。 |

## 2. P0（立即修复）
1. **Aggregation Runner 未定义变量**  
   - `app/services/aggregation/database_aggregation_runner.py` 的 `_persist_database_aggregation`、`_persist_instance_aggregation` 中引用 `start_date`、`instance_id`、`database_name`、`period_type` 但未声明，导致 `F821`。需通过 `context.start_date` 等对象提供或补全参数。  
   - 验证：`ruff check app/services/aggregation/database_aggregation_runner.py --select F821`。
2. **数据校验器 `cls` 使用错误**  
   - `app/utils/data_validator.py` 的多处静态函数在方法内部引用 `cls.PASSWORD_MIN_LENGTH` 等，导致 `F821`。改为 `self`/类方法或改用常量。  
   - 验证：`ruff check app/utils/data_validator.py --select F821`。
3. **账户分类器类型转换（TC006）**  
   - `app/services/account_classification/classifiers/postgresql_classifier.py` 与 `sqlserver_classifier.py` 在 `cast(Sequence[str] | None, …)` 中需改为 `cast("Sequence[str] | None", …)`，避免运行期评估。  
   - 验证：`ruff check app/services/account_classification/classifiers --select TC006`。
4. **SQL Server 适配器导入顺序（I001/TC003）**  
   - 最新改动引入 `dataclasses` 后 import 块未排序，且 `Sequence` 应仅在 type-check 时导入。整理 `from __future__ import annotations` 下方导入。  
   - 验证：`ruff check app/services/accounts_sync/adapters/sqlserver_adapter.py --select I001,TC003`。

## 3. P1（结构性/批量工作）
- **Database Sync 模块治理**：`app/services/database_sync/*`、`database_type_service.py` 等存在 docstring 缺失、日志 API、复杂度 (`C901/PLR0912/PLR0915`)。建议分批添加文档、拆解函数，逐步压降复杂度。
- **类型/协议文件统一**：`app/types/sync.py` / `app/types/structures.py` 缺少方法 docstring、尾逗号与 import 顺序，需要一轮集中修复，确保协议与 typed dict 都遵循 ANN/COM 规则。
- **缓存与日志工具**：`app/utils/cache_utils.py` 缺 `TypingCallable` 定义、第三方导入需移至 `TYPE_CHECKING`，`app/utils/logging/*` 存在未使用参数与外部依赖导入问题，宜一并处理。
- **配置/脚本文件**：`migrations/env.py`、`nginx/gunicorn-*.conf.py`、`tmp_ble_test.py` 等存在命名或模块级 docstring 问题，可安排在工具/脚本治理阶段统一整改。

## 4. 验证建议
1. P0 修复完成后，分别对聚合 runner、data_validator、account_classification、sqlserver_adapter 执行针对性 `ruff check --select <rules>`，避免通用扫描耗时。  
2. Database Sync 系列涉及数据库访问，重构前先添加单元/集成测试 stub，防止 `_collect_tablespace_sizes`、`inventory_manager.synchronize` 行为回归。  
3. Utils 和 types 模块修改类型定义后，执行 `ruff check <files> --select ANN,TC,COM` 以及 `pyright`，确保类型治理符合仓库规则。  
4. 所有问题清零后，重新生成 `docs/reports/ruff_full_YYYY-MM-DD_hhmmss.txt` 并更新本计划。
