# Ruff 全量扫描修复计划（更新：2025-12-11 15:35）

> 最新全量报告：`docs/reports/ruff_full_2025-12-11_153511.txt`（上一版 14:15 计划聚焦 BLE001、Docstring 与复杂度治理。本次扫描显示 BLE001 已清零，但 `TC001/D413/PLR0913/E501/C901` 仍为主要阻断，需要重新排序优先级）。

## 1. 最新扫描概览

### 1.1 主要规则分布
| 规则 | 命中数（约） | 代表文件 | 治理建议 |
| --- | --- | --- | --- |
| **D413/D205/D202** Docstring 段落空行 | 120+ | `app/errors/__init__.py`、`app/models/database_*`、`app/routes/capacity/*` | 全量套用“摘要 + 空行 + Args/Returns + 结尾空行”模板，写完立即 `ruff --select D202,D205,D413` 自检。 |
| **PLR0913/PLR0915/PLR0911** 参数/分支过多 | 30+ | `app/models/credential.py`、`app/models/instance.py`、`app/models/unified_log.py`、`app/routes/*` | 引入 dataclass/辅助 builder，或拆分 helper；路由函数用局部 `_execute`/`safe_route_call` 承载参数。 |
| **BLE001** 捕获裸 `Exception` | 0 | —— | 已于 15:35 前全部替换为白名单异常；后续扫描若新增需立即补充。 |
| **PLC0415/TC00x/UP035** 导入层级 | 20+ | `app/routes/files.py`、`app/utils/time_utils.py`、`app/utils/query_filter_utils.py`、`app/utils/structlog_config.py` | 运行期不用的类型移入 `TYPE_CHECKING`，循环导入改为模块顶部 import；统一 `collections.abc`。 |
| **E501** 长行 | 15 | `app/models/instance_account.py`、`app/models/instance_size_stat.py`、`app/utils/sqlserver_connection_utils.py` | 采用多行参数/常量抽取，或者使用 `textwrap.dedent` 对长字符串分段。 |
| **C901/TRY300** 复杂度与 try/else | 10+ | `app/routes/capacity/aggregations.py`、`app/routes/capacity/instances.py`、`app/utils/version_parser.py` | 拆分 `_execute` 子函数或复用 service 层；`try` 分支内直接 `return` 的改为 `else` 或提前赋值。 |
| **ANN/INP/N999** 类型与命名 | 5+ | `migrations/env.py`、`nginx/gunicorn-*.conf.py` | 为 Alembic 辅助函数补返回类型，gunicorn 配置重命名/迁移出 Python 模块路径。 |

### 1.2 阻断主题
1. **`app/errors/__init__.py` 文档与导入回归**：仍存在 `TC001`（LoggerExtra 应转入 `TYPE_CHECKING`）与大批 `D413`。需在 P0 一次性修复 docstring 模版并补空行。  
2. **模型/日志 Docstring & 长行**：`database_size_*`、`database_type_config.py`、`unified_log.py` 仍有 `D413/D205/E501`。集中通过脚本或批量 `apply_patch` 处理。  
3. **PLR0913 热点**：`Credential.__init__`、`Instance.__init__`、`UnifiedLog.create_log_entry`、`_build_accounts_json_response` 等函数入参仍超 5 个，需要 dataclass/options object 或局部 context。  
4. **导入层级/循环依赖**：`app/routes/files.py`、`app/utils/structlog_config.py`、`app/utils/query_filter_utils.py` 和 `app/utils/time_utils.py` 仍有 `PLC0415/TC003`，应纳入 P1 集中治理。  
5. **配置/脚本质量**：`migrations/env.py` 缺少类型注解、`nginx/gunicorn-*.conf.py` 命名不合法，需要纳入 P2 清理。  

### 1.3 本次 BLE001 治理进展（12-11 15:35）
- **accounts + adapters**：`app/services/accounts_sync/**`、`connection_adapters/**`、`connection_test_service.py` 均使用统一异常元组（含驱动异常 + `ConnectionAdapterError`），同步链路再无裸捕。  
- **tasks**：`app/tasks/capacity_*`、`app/tasks/partition_management_tasks.py`、`log_cleanup_tasks.py`、`accounts_sync_tasks.py` 均定义独立异常集合（`CAPACITY_TASK_EXCEPTIONS` 等），保证重试/回滚逻辑清晰。  
- **database_sync**：协调器、Collector 及 MySQL adapter 全面接入 `DATABASE_SYNC_EXCEPTIONS`/`MYSQL_CAPACITY_EXCEPTIONS`，BLE001 在 database_sync 模块归零。  

### 1.4 15:35 报告新增 / 仍未关闭的重点
- **TC001/D413**：`app/errors/__init__.py` 仍是顶级阻断（LoggerExtra import + 10+ docstring 空行问题）。需使用 `TYPE_CHECKING` 并改写所有 docstring。  
- **D205/D202**：`app/routes/cache.py`、`app/routes/capacity/databases.py`、`app/routes/capacity/instances.py` 等文件存在模块 docstring 首行空行缺失、函数 docstring 后多余空行，建议脚本化修复。  
- **PLR0913/PLR0915**：`app/models/credential.py`、`app/models/instance.py`、`app/models/unified_log.py` 及 `app/routes/accounts/ledgers.py::_build_accounts_json_response`，需要 dataclass/options 拆分。  
- **E501**：`app/models/instance_account.py`、`app/models/instance_size_stat.py` 超长 Column 定义仍在；建议改用多行或抽常量。  
- **C901**：`app/routes/capacity/aggregations.py` 与 `app/routes/capacity/instances.py` 的 `aggregate_current`、`_execute`、`fetch_instance_summary` 复杂度持续超标，需借助 service 分层或拆子函数。  

## 2. 优先修复清单

### P0（立即处理，解掉基础规则）
1. **`app/errors/__init__.py`**  
   - 目标：`TC001/D202/D413`。  
   - 动作：把 `LoggerExtra` 改为 `TYPE_CHECKING` 导入；所有类/函数 docstring 按“摘要句号 + 空行 + Args/Returns + 结尾空行”重写。  
   - 验证：`ruff check app/errors/__init__.py --select TC001,D202,D413`。

2. **模型 Docstring & 长行批 1**  
   - 范围：`app/models/database_size_aggregation.py`、`database_size_stat.py`、`database_type_config.py`、`unified_log.py`。  
   - 动作：统一 docstring 模板，拆分超过 120 字的 Column 描述；必要时抽常量。  
   - 验证：`ruff check app/models --select D205,D413,E501`。

3. **PLR0913 核心构造函数**  
   - 文件：`app/models/credential.py`、`app/models/instance.py`、`app/models/unified_log.py`。  
   - 动作：引入 Options dataclass 或分拆 helper，减少 `__init__` 位置参数；`UnifiedLog.create_log_entry` 引入载荷对象。  
   - 验证：`ruff check app/models --select PLR0913`。

4. **Docstring 模块空行治理**  
   - 范围：`app/routes/cache.py`、`app/routes/capacity/databases.py`、`app/routes/capacity/instances.py`、`app/routes/common.py`。  
   - 动作：模块 docstring 前后补单空行；函数 docstring 移除多余空行或补缺失空行。  
   - 验证：`ruff check app/routes/cache.py app/routes/capacity --select D202,D205`。

### P1（本迭代后半）
1. **导入层级 / isort**：`app/routes/files.py`、`app/utils/structlog_config.py`、`app/utils/query_filter_utils.py`、`app/utils/time_utils.py`、`app/utils/response_utils.py`。整理 import 顺序，类型导入移入 `TYPE_CHECKING`，同时解决 `UP035/TC002/TC003/PLC0415`。  
2. **Docstring 批 2 & D205**：完成 capacity、common、databases 路由剩余 docstring 的摘要/段落空行，必要时脚本化。  
3. **Scheduler/Response 工具**：`app/services/form_service/scheduler_job_service.py` 拆分 Cron 字段校验；`app/routes/accounts/ledgers.py::_build_accounts_json_response` 引入响应 builder，继续压缩 `PLR0913/PLR0915`。  
4. **Version / SQLServer 工具**：`app/utils/version_parser.py` 标注 `ClassVar`、降低 `_extract_main_version` 复杂度；`app/utils/sqlserver_connection_utils.py` 拆分长字符串、处理 `TRY300`。  

### P2（滚动缓解）
- `migrations/env.py`：补全返回类型 (`Engine`, `str`, `MetaData`) 及 `process_revision_directives` 参数注解，若需多模块引用可抽到 `scripts/alembic_helpers.py`。  
- `nginx/gunicorn/*.conf.py`：按 pep8 命名（如 `gunicorn_dev_conf.py`）或移动到 `nginx/gunicorn/conf/` 并在 tox/ruff exclude。  
- `app/routes/capacity/aggregations.py`、`app/routes/capacity/instances.py`、`app/routes/credentials.py`：拆分 C901 复杂函数（`aggregate_current`、`fetch_instance_summary`、`list_credentials` 等），引入 service 层组合。  

## 3. 批量治理策略
1. **Docstring 脚本化**：维护 `scripts/tools/add_cn_docstrings.py`，支持 `D205/D413` 自动修复；大批模型/路由可以批量套用。  
2. **异常模板**：在 `app/utils/route_safety.py` 增强 `safe_route_call`（允许统一兜底 `AppError`），并在贡献指南追加“不得裸捕获 `Exception`”示例。  
3. **Cron/Scheduler 工具化**：整理 Cron 解析逻辑进入 `app/utils/cron_expression.py`，避免 `PLR0913` 在多处重复。  
4. **Import Guard**：补 `scripts/tools/fix_typing_imports.py` + `poetry run python -m automate.disable_runtime_types`（若已有），CI 中增加 `ruff --select UP035,TC001,TC002,TC003,PLC0415`。  

## 4. 验证清单（提交前）
- `./scripts/refactor_naming.sh --dry-run`。  
- `ruff check <touched files> --select BLE,G,TRY,TC,UP,PLR09x,D,E,RUF012`。  
- `npx pyright app`。  
- `pytest -m unit`。  
- Scheduler 或同步相关改动需在 `make dev start` 后跑一次 smoke（scheduler reload + account sync）。  

## 5. 里程碑
1. **12-11 下午**：关闭本次报告中的 P0（`app/errors/__init__.py`、模型 docstring、核心 PLR0913、BLE001 热点），复跑 `ruff_full` 期待 D 类下降 50%。  
2. **12-11 晚间**：完成导入层级/P1 Docstring，以及 `version_parser`/`sqlserver_connection_utils` 长行治理，输出阶段性总结。  
3. **12-12 上午**：集中处理 C901/TRY300、migrations/nginx 命名及脚本化工具，确保 `ruff_full` 仅剩低优先级告警。  
