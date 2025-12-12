# Ruff 全量扫描修复计划（更新：2025-12-12 13:22）

> 最新全量报告：`docs/reports/ruff_full_2025-12-12_132156.txt`（仍有多项规则命中，重点集中在导入治理、格式规范与账户分类/同步相关服务的复杂度）。以下计划覆盖本次扫描暴露的剩余问题，替换上一版计划。

## 1. 主要问题分布
| 类型 | 代表规则 | 关键文件 | 行动建议 |
| --- | --- | --- | --- |
| **格式与文档（E501/D202/D205/RUF002）** | `E501`、`D202`、`D205`、`RUF002` | `app/routes/accounts/{classifications,ledgers}.py`、`app/routes/partition.py`、`app/scheduler.py` | 控制行宽≤120，移除 docstring 后空行，中文 Docstring 避免全角符号。|
| **TYPE_CHECKING 与导入排序（I001/TC002/TC003/PLC0415）** | `TC002/TC003/I001/PLC0415` | `app/routes/instances/manage.py`、`app/services/account_classification/cache.py`、账户同步/连接适配器模块 | 将第三方与 `collections.abc` 导入移入 `TYPE_CHECKING`，保持 import block 排序，禁止函数内 `import`。|
| **账户分类/同步复杂度（C901/PLR091x/TRY300/FBT001）** | `C901`、`PLR0911/12/13/15`、`TRY300`、`FBT001` | `app/services/account_classification/classifiers/*`、`orchestrator.py`、`permission_manager.py`、`accounts_sync` 适配器 | 拆分 `evaluate`/`synchronize` 等超长方法，引入 helper 处理条件分支；`safe_route_call` 周边按 `try/else` 结构。|
| **安全与类型（S608/PGH003/F821/RUF012）** | `S608`、`PGH003`、`F821`、`RUF012` | `app/services/accounts_sync/adapters/sqlserver_adapter.py`、`connection_adapters/*`、`app/routes/partition.py`、`connection_factory.py` | 对 SQL Server 构造 SQL 的位置添加参数化或显式安全说明，补充缺失的 `Any` 导入与 `ClassVar`。|
| **缓存/聚合服务风格（COM812/ISC001/ARG002）** | `COM812`、`ISC001`、`ARG002` | `app/services/accounts_sync/account_query_service.py`、`cache_service.py`、聚合 runners | 添加缺失的 trailing comma，合并字符串字面量，移除未使用参数或转为 `*_`。|

## 2. P0（立即修复）
1. **行宽与 docstring 规范（accounts routes + partition）**  
   - 处理 `app/routes/accounts/classifications.py:159`、`app/routes/accounts/ledgers.py:526` 的 `E501`，必要时拆分推导式；  
   - 清理 `app/routes/partition.py` 多个 helper 的 `D202` 与缺失的 `Any` 导入；  
   - 验证：`ruff check app/routes/accounts/classifications.py app/routes/accounts/ledgers.py app/routes/partition.py --select E501,D202,F821`.
2. **TYPE_CHECKING 导入与布尔参数（instances/manage + scheduler + cache）**  
   - 将 `sqlalchemy.orm.Query`/`Subquery`、`collections.abc.*` 等搬入 `if TYPE_CHECKING`;  
   - `app/scheduler.py` 的 `_build_cron_trigger` docstring 更换半角逗号，`_log_task_creation_failure` 使用关键字/Enum 替代布尔参数；  
   - `app/services/account_classification/cache.py`、`accounts_sync/adapters/base_adapter.py` 等整理 import 顺序；  
   - 验证：`ruff check app/routes/instances/manage.py app/scheduler.py app/services/account_classification/cache.py app/services/accounts_sync/adapters/base_adapter.py --select TC002,TC003,I001,FBT001,RUF002`.
3. **SQL Server adapter 安全注释与 S608**  
   - 为 `_get_server_roles_bulk` 及批量权限查询补充参数化策略（或重构为 `text()`+`bindparam`）；`S608` 重复位置需统一处理；  
   - 若继续使用字符串模板，提供 `SafeQueryBuilder` 或将查询拆分到存储过程；  
   - 验证：`ruff check app/services/accounts_sync/adapters/sqlserver_adapter.py --select S608,E501`.
4. **账户分类/连接适配器 import & docstring**  
   - `app/services/account_classification/classifiers/*`、`connection_adapters/*` 统一 `TYPE_CHECKING` 导入、driver `type: ignore` 加上 `PGH003` 具体代码；  
   - 为 BaseAdapter/ConnectionAdapter `__init__` 添加中文 docstring，去掉函数体内动态 import（或以懒加载 helper 包装）；  
   - 验证：`ruff check app/services/account_classification app/services/connection_adapters --select I001,TC003,PLC0415,D107,PGH003,E501`.
5. **高复杂度 classifier/permission manager**  
   - 拆分 `mysql_classifier.evaluate`、`permission_manager.synchronize/_calculate_diff/_build_change_summary`，将规则解析、权限归并、错误处理独立为 helper；  
   - `TRY300` 报警点（orchestrator/repositories/coordinator 等）使用 `else` 或 context manager；  
   - 验证：`ruff check app/services/account_classification app/services/accounts_sync --select C901,PLR091x,TRY300`.

## 3. P1（结构性工作）
- 设计统一的账户分类表达式解析器，供各 `evaluate` 函数调用，减少分支并解耦数据库差异。
- 将 SQL Server 批量权限查询迁移至存储过程或视图，避免在 Python 层拼接长 SQL，同时消化 `S608` 与 `E501`。
- 聚合 runner (`aggregation_service`, `database_aggregation_runner`) 内部的多参数函数可拆成数据类 + pipeline，降低 `PLR0913`/`ISC001`。

## 4. 验证建议
1. 针对每个修复批次运行 `ruff check <files> --select <rules>`，控制回归范围；  
2. 对涉及 driver import 的模块补充最小化单元测试（可使用 stub/mock）；  
3. S608/SQL 相关修改后建议执行 `make test` 或最小化集成测试确保查询功能正常；  
4. 结构性调整完成后再跑一次 `ruff check --preview app/services/account_classification app/services/accounts_sync app/services/connection_adapters`.
