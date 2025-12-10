# Ruff 全量扫描修复计划（更新：2025-12-10 11:30）

## 1. 最新扫描概览

### 1.0 今日修复进展（2025-12-10 上午）
- **账户域路由拆分完成**：`app/routes/accounts/ledgers.py` 引入 `AccountFilters` 等 helper，将「解析 → 查询 → 序列化」分层，`PLR0915/PLR0912/PLC0415` 在该文件已归零，同时补上 `app/routes/accounts/__init__.py` 解决 INP001。
- **文件导出/日志路由收敛**：`app/routes/files.py` 新增 `_parse_account_export_filters`、`_build_log_query` 等工具，所有函数内 import 移至文件顶部，导出逻辑复用统一入口，`PERF401/PLC0415/TRY301` 告警在该模块清零。
- **调度器与表单服务治理**：`app/routes/scheduler.py` 的 `get_jobs`/`run_job` 拆分为 `_build_job_payload` 等小函数，清理 TRY301/PLC0415；`SchedulerJobFormView`、`classification_rule_service`、`credential_service` 引入 helper，`ANN002/003/PLR0911` 告警清除。
- **工具层基线**：`cache_utils`、`data_validator`、`structlog_config`、`scheduler_forms` 等模块补 `ClassVar`、`TypedDict`/`Any` 注解与 `try/else` 结构，`ANN00x + TRY300` 在相关文件已通过 `ruff check`。
- **验证**：对上述触达文件执行 `ruff check`（命令见工作日志）全部通过，待晚上运行 `./scripts/ruff_report.sh full` 复核全仓指标。
- **扫描命令**：`./scripts/ruff_report.sh full`（禁用 `--fix/--unsafe-fixes`，Python 3.12 + uv 环境）。
- **报告文件**：`docs/reports/ruff_full_2025-12-09_145519.txt`。
- **告警总数**：1,065 条（相较 13:58 的 934 条回升 131 条，新增告警主要来自恢复 `PLC0415/PLR09x` 规则和合并后的函数内 import 代码）。
- **核心结论**：
  1. **类型/契约告警仍占 38%（406 条）**，集中在 `app/utils/decorators.py`、`app/utils/structlog_config.py`、`app/utils/cache_utils.py` 等工具模块，`TypedDict/Protocol` 与 `ClassVar` 仍未覆盖。
  2. **异常捕获与日志用法 267 条（25%）**，`app/routes/scheduler.py`、`app/scheduler.py`、`app/tasks/capacity_collection_tasks.py` 仍存在裸 `Exception`、`try` 内 `return`、f-string 写日志。
  3. **函数内 import / 过长签名新增 173 条**（`PLC0415/PLR2004/PLR091x`），主要位于 `app/scheduler.py`、`app/routes/scheduler.py`、`app/routes/accounts/*`、`app/utils/data_validator.py`，说明之前的懒加载与 God function 仍未拆分。
  4. **文档、注释与行宽问题维持在 134 条**（`E501/D205/D107/ERA001`），`app/utils/sqlserver_connection_utils.py`、`app/constants/*` 和 `app/models/*` 是长行、缺空行的主要来源。
  5. **结构/性能与安全告警 82 条**（`C901/INP001/PERF401/S608/SLF001`），`app/routes/accounts/ledgers.py`、`app/routes/history/logs.py`、同步适配器仍需拆分与参数化 SQL。

### 1.1 规则分布概览
| 规则 | 命中数 | 典型文件 | 推荐策略 |
| --- | --- | --- | --- |
| ANN401 | 160 | `app/utils/decorators.py`、`app/utils/data_validator.py` | 将通用上下文/返回值抽为 `TypedDict` 或 `Protocol`，限制 `Any`；复杂结构统一在 `app/types/` 维护 |
| BLE001 | 104 | `app/routes/health.py`、`app/routes/dashboard.py` | 细化捕获的异常类型并落盘结构化日志，禁止 `except Exception` 直接吞掉错误 |
| ANN001 | 80 | `app/utils/structlog_config.py`、`app/services/database_sync/adapters/mysql_adapter.py` | 所有形参显式类型注解，模型类型使用 `type[Model]`、`Sequence[Record]` 别名 |
| PLC0415 | 69 | `app/scheduler.py`、`app/routes/scheduler.py` | 禁止在函数内 import，确需惰性加载时封装 `_ensure_*()` 并添加注释，默认移至模块顶层 |
| TRY300 | 61 | `app/services/sync_session_service.py`、`app/utils/cache_utils.py` | 避免在 `try` 中 `return/continue`，改用守卫语句或 `else`/辅助函数收敛异常 |
| ARG002 | 51 | `app/utils/structlog_config.py`、`app/views/classification_forms.py` | 未使用参数统一改 `_unused_*` 或移除；必要时以 `**extra_fields` 承载扩展参数 |
| E501 | 50 | `app/utils/sqlserver_connection_utils.py`、`app/routes/connections.py` | 拆分链式条件，抽出常量/中间变量，保持单行 ≤120 字符 |
| C901 | 43 | `app/routes/history/logs.py`、`app/services/accounts_sync/permission_manager.py` | 依据「解析参数→业务→序列化」分段，必要时引入服务类或 `dataclass` 承载上下文 |
| RUF012 | 40 | `app/constants/status_types.py`、`app/constants/sync_constants.py` | 可变类属性声明为 `ClassVar[...]` 或改用不可变 `tuple`，避免实例间共享状态 |
| G201 | 38 | `app/tasks/capacity_collection_tasks.py`、`app/services/database_sync/persistence.py` | 用 `logger.exception("msg", extra={...})` 代替 `exc_info=True`，同步补充上下文字段 |
| PLR2004 | 36 | `app/utils/version_parser.py`、`app/utils/data_validator.py` | 将魔法数字/字符串抽成 `Enum` 或常量，封装判定函数便于测试 |
| D205 | 35 | `app/constants/sync_constants.py`、`app/errors/__init__.py` | Docstring 摘要行后留一空行，正文使用中文句号结束，遵循 Google 模板 |
| ERA001 | 27 | `app/utils/safe_query_builder.py`、`app/models/credential.py` | 删除注释掉的旧逻辑；确需保留用 feature flag/配置守卫并解释原因 |
| ANN202 | 25 | `app/utils/structlog_config.py`、`app/services/ledgers/database_ledger_service.py` | 私有函数补返回类型（含 `-> None`），必要时引入 `Protocol` 统一回调签名 |
| PGH003 | 25 | `app/routes/scheduler.py`、`app/services/form_service/scheduler_job_service.py` | `type: ignore` 必须注明触发的规则（如 `[attr-defined]`）与缓解计划 |
| D107 | 22 | `app/errors/__init__.py`、`app/scheduler.py` | `__init__`/`__post_init__` 补中文 Docstring，解释初始化副作用并列出 `Args` |
| ANN201 | 21 | `app/models/account_classification.py`、`app/routes/capacity/instances.py` | 公共 property/方法注明返回类型，如 `-> str`、`-> Response` |
| G004 | 21 | `app/scheduler.py`、`app/tasks/capacity_collection_tasks.py` | 禁止 f-string 写日志，改 `%s` + `extra`，或在 formatter 中拼接 |
| PLR0913 | 18 | `app/services/aggregation/database_aggregation_runner.py`、`app/routes/instances/detail.py` | 超过 5~6 个参数的函数拆 `dataclass`/配置对象，或引入上下文结构 |
| TRY301 | 18 | `app/routes/scheduler.py`、`app/routes/connections.py` | 将 `raise` 从 `try` 块中移出，或提炼 `_validate_*` 方法返回布尔再统一抛错 |
| INP001 | 17 | `app/routes/accounts/classifications.py`、`app/routes/accounts/ledgers.py` | 为包补 `__init__.py` 并写明对外蓝图/路由列表，避免隐式命名空间包 |
| PLR0915 | 17 | `app/routes/accounts/ledgers.py`、`app/routes/files.py` | 拆分带大量语句的 Handler，遵循「验证/查询/渲染」分块 |
| PLR0911 | 17 | `app/services/form_service/classification_rule_service.py`、`app/services/form_service/credential_service.py` | 用早返回 + 辅助函数减少 `return` 数量，或整合成映射表驱动 |
| PLR0912 | 16 | `app/routes/accounts/ledgers.py`、`app/utils/data_validator.py` | 合并分支条件，善用策略模式或 `dict` 分派降低嵌套 |
| ANN002 | 15 | `app/utils/decorators.py`、`app/utils/cache_utils.py` | `*args` 注解 `tuple[Any, ...]`，必要时显式列出允许的参数结构 |
| ANN003 | 14 | `app/utils/structlog_config.py`、`app/views/scheduler_forms.py` | `**kwargs` 注解为 `Mapping[str, Any]`，标出允许的 key 并用 `TypedDict` 约束 |
| PERF401 | 10 | `app/routes/accounts/classifications.py`、`app/routes/files.py` | 使用列表/字典推导或 `list.extend`，减少在循环中反复 append |
| S608 | 10 | `app/services/accounts_sync/adapters/sqlserver_adapter.py`、`app/services/accounts_sync/adapters/mysql_adapter.py` | SQL 统一使用 `text("...")` + 绑定参数，禁止字符串拼接用户输入 |
| SLF001 | 2 | `app/routes/dashboard.py`、`app/services/statistics/log_statistics_service.py` | 避免访问私有属性，新增公开 getter 或封装访问层 |
| LOG015 | 2 | `app/utils/logging/queue_worker.py` | 队列日志处理器禁止在 `__del__` 中 log，改成显式 `close()` |
| PYI034 | 1 | `app/services/partition_management_service.py` | 类型注解中使用 `contextlib.AbstractContextManager` 替代弃用类 |

### 1.2 阻断规则簇
- **A. 类型契约（406 条）**：`ANN401/ANN001/ANN202/ANN201/ANN002/ANN003/RUF012/ARG002`。
  - 场景：工具模块、路由表单的上下文缺类型定义，`ClassVar` 缺失导致实例共享可变列表。
  - 处置：为 `app/utils`、`app/views/*forms.py` 制定统一 `types.py`；所有缓存/装饰器返回值统一 `TypedDict`；配套补测试。
- **B. 异常 + 日志（267 条）**：`BLE001/TRY300/TRY301/G201/G004/PGH003`。
  - 场景：路由入口和调度器仍捕获裸异常、`try` 内返回、在 `logger.exception` 中拼接字符串。
  - 处置：引入 `safe_execute()`/`handle_route_error()` 辅助函数，统一结构化日志字段，`type: ignore` 必须补原因。
- **C. 文档/注释/行宽（134 条）**：`D205/D107/E501/ERA001`。
  - 场景：常量模块 Docstring 缺空行、`app/utils/sqlserver_connection_utils.py` 等仍有多处 150+ 字符长行、模型保留注释代码。
  - 处置：批量套用 Google 中文 Docstring 模板，抽常量拆长行，针对旧注释代码要么删除要么改 feature flag。
- **D. 结构/性能/安全（82 条）**：`C901/INP001/PERF401/S608/SLF001`。
  - 场景：账户/历史路由函数过长、包缺 `__init__.py`、同步适配器仍存在字符串拼接 SQL。
  - 处置：路由拆 Handler + 服务层，补包级入口文件，SQL 全量改参数化并新增单元测试。
- **E. 控制流与函数内 import（173 条）**：`PLC0415/PLR2004/PLR0913/PLR0915/PLR0911/PLR0912`。
  - 场景：调度脚本及账户路由为规避循环依赖在函数内 import，并出现 God function/魔法数字。
  - 处置：在模块顶部建立工厂或 lazy loader，顺手拆分 Handler 并抽枚举常量，保证每个函数职责单一。

## 2. 优先修复清单
### P0（立即处理）
1. **类型注解冲刺（406 条）**：`app/utils/decorators.py`、`app/utils/structlog_config.py`、`app/views/*forms.py` 分两批补 `TypedDict/Protocol/ClassVar`，确保新增 handler 均有类型覆盖。
2. **异常与日志基线（267 条）**：`app/routes/scheduler.py`、`app/scheduler.py`、`app/tasks/capacity_collection_tasks.py` 统一异常捕获、移除 f-string 日志，`type: ignore` 增补原因并建 issue 跟踪。
3. **控制流 / 函数内 import（173 条）**：`app/scheduler.py`、`app/routes/accounts/ledgers.py`、`app/routes/files.py` 将 import 上移或封装 lazy loader，同时拆分超过 80 行/6 参数的函数，减少 `PLR09xx`。
4. **SQL 与日志安全（`S608/G201/G004` 共 69 条）**：同步适配器、容量任务中的 SQL/pipeline 全量改参数化，日志统一 `extra={env,request_id}` 并禁止字符串拼接。

### P1（当迭代内完成）
1. **Docstring/注释/行宽（134 条）**：集中修复 `app/constants/*`、`app/errors/__init__.py`、`app/utils/sqlserver_connection_utils.py` 的 `D205/D107/E501/ERA001`，形成 snippet 便于批量填充。
2. **结构/性能告警（82 条）**：针对 `C901/PERF401/SLF001`，按照「验证→查询→序列化」拆分 `app/routes/accounts/ledgers.py` 等 Handler，并统一 `cache_utils` 的私有属性访问。
3. **包初始化（17 条 INP001）**：所有 `app/routes/accounts/*`、`history/*` 子包补 `__init__.py` 并导出蓝图，有助于后续自动发现。

### P2（收尾长尾）
- `LOG015`（2 条）→ 调整日志队列销毁流程；
- `PYI034`（1 条）→ `partition_management_service` 中替换上下文基类；
- `PERF401/S608` 余下个别命中→ 修复时配合单测覆盖；
- 确认 `refactor_naming` 与 `ruff --select PLC0415,PLR091x` 在整仓运行均通过。

## 3. 批量处理策略
1. **类型批修**：执行 `ruff check app/utils app/views app/services --select ANN,ARG,RUF012`，配合 VSCode snippet 统一 `TypedDict/Protocol`；必要时引入 `from __future__ import annotations`。
2. **异常与日志治理**：抽象 `safe_execute`、`log_with_context` 辅助方法，统一 `extra={"account_id": ..., "task_id": ...}`；`try` 语句周围优先使用守卫。
3. **控制流/导入整改**：先运行 `ruff check --select PLC0415,PLR2004,PLR0911,PLR0912,PLR0913,PLR0915`，将函数内 import 迁至模块顶部或惰性加载器，并以 `dataclass`/配置对象承载超长参数列表。
4. **Docstring+行宽修复**：利用 `python scripts/tools/docstring_guard.py --paths app/constants app/errors` 检查 `D205/D107`，长行通过拆常量或组装多行字符串解决；注释代码统一删除。
5. **SQL/安全**：同步适配器统一封装 `run_param_query(sql: str, params: Mapping[str, Any])`，新增最小单测覆盖参数化 SQL；同时校验 `logger` 使用 `%s` 或 `extra`。

## 4. 验证清单
- `./scripts/refactor_naming.sh --dry-run`（确保命名守卫未触发）。
- `ruff check <touched files> --select ANN,ARG,BLE,TRY,G,PLC0415,PLR091x,D`。
- `pytest -m unit`（优先覆盖缓存、同步、调度相关模块）。
- 若调整 SQL/调度逻辑，运行 `make dev start` + 相关集成测试或最小化脚本验证。

## 5. 下一阶段里程碑
1. **12-09 晚班**：完成 P0 第 1、2 批（类型 + 异常），将总告警压至 ≤900 条，并对 `app/utils` 发布类型基线指南。
2. **12-10 上午**：集中清理 `PLC0415/PLR09x`（目标 ≤50 条），完成调度器与账户路由的 import 拆分。
3. **12-10 晚班**：清空 `D205/D107/E501/ERA001`，同步收敛剩余 `S608/SLF001`，以 12-10 23:00 的 `./scripts/ruff_report.sh full` 再次确认总告警逼近 750 条。
