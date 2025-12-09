# Ruff 全量扫描修复计划（更新：2025-12-09 13:58）

## 1. 最新扫描概览
- **扫描命令**：`./scripts/ruff_report.sh full`（禁用 `--fix/--unsafe-fixes`；Python 3.12/uv 环境）。
- **报告文件**：`docs/reports/ruff_full_2025-12-09_135750.txt`。
- **告警总数**：934 条（相较 13:12 的 1,146 条再下降 212 条，主要得益于前一轮 docstring 批修与路由模块清理）。
- **核心结论**：
  1. **类型/契约告警仍占 43%**（`ANN401/ANN001/ANN202/ANN201/ANN002/ANN003/RUF012/ARG002` 共 404 条），集中在 `app/forms/definitions`、`app/models/*`、`app/services/accounts_sync/*`。
  2. **异常处理 + 日志仍未合规**（`BLE001/TRY300/TRY301/G201/G004/PGH003/TRY401/F841` 共 278 条），主要分布在账户/容量路由与同步任务入口。
  3. **文档、注释与行宽问题 152 条**（`D205/D107/D400/D413/D415/D100/D104/E501/ERA001`），`app/constants/*` 与 `migrations/env.py` 仍需统一 Google 风格中文 docstring。
  4. **结构性风险**（`C901/INP001/I001/PERF401/S608/FBT001/UP017/UP037/SIM118/RUF022/TC003/SLF001`）共有 100 条，涉及蓝图拆分、SQL 拼接、布尔位置参与时间解析。

### 1.1 规则分布概览（全部仍有命中的规则）
| 规则 | 命中数 | 典型文件 | 推荐策略 |
| --- | --- | --- | --- |
| ANN401 | 159 | `app/forms/definitions/base.py`、`app/routes/instances/batch.py` | 定义 TypedDict/Protocol，限制 `Any`；统一模板上下文的返回结构 |
| BLE001 | 104 | `app/routes/accounts/ledgers.py`、`app/routes/cache.py` | 精确捕获异常并记录结构化日志，必要时拆出 `_apply_*` 辅助函数 |
| ANN001 | 80 | `app/models/instance_size_aggregation.py`、`app/services/account_classification/classifiers/mysql_classifier.py` | 为全部形参加注解，复用 `type[Model]`、`Sequence[RuleConfig]` 等别名 |
| TRY300 | 61 | `app/routes/health.py`、`app/scheduler.py` | 避免在 `try` 内直接 `return`/`break`，改用守卫语句或 `else` 子句 |
| ARG002 | 51 | `app/models/instance.py`、`app/models/sync_session.py` | 未使用参数改 `_unused_*` 或移除，必要时使用 `**kwargs` 承载扩展参数 |
| E501 | 50 | `app/__init__.py`、`app/errors/__init__.py` | 拆分长行、抽常量或先赋临时变量，保持 ≤120 字符 |
| C901 | 43 | `app/routes/accounts/ledgers.py`、`app/routes/capacity/aggregations.py` | 依据「查询→处理→序列化」拆分函数或引入服务层对象 |
| RUF012 | 40 | `app/config.py`、`app/constants/database_types.py` | 可变类属性改 `ClassVar[...]` 或不可变 `tuple`，避免实例共享状态 |
| G201 | 38 | `app/services/accounts_sync/adapters/mysql_adapter.py`、`.../oracle_adapter.py` | 用 `logger.exception`（含 extra 字段）替代 `exc_info=True`，保持结构化日志 |
| D205 | 36 | `app/constants/sync_constants.py`、`app/errors/__init__.py` | Docstring 摘要行后补空行，描述段落使用中文句号收尾 |
| ERA001 | 27 | `app/__init__.py`、`app/models/account_permission.py` | 删除注释掉的代码；需保留时改成 feature flag 并解释 |
| ANN202 | 25 | `app/__init__.py`、`app/models/__init__.py` | 私有函数补返回类型（`-> None` 或具体类），配合 `from __future__ import annotations` |
| PGH003 | 24 | `app/routes/scheduler.py`、`app/services/form_service/scheduler_job_service.py` | `type: ignore` 附带具体错误类型及原因（例如 `[attr-defined]`） |
| G004 | 23 | `app/models/credential.py`、`app/scheduler.py` | 禁止 f-string 日志，改用 `%s` 或 `logger.info("msg", extra={...})` |
| D107 | 22 | `app/errors/__init__.py`、`app/scheduler.py` | `__init__`/`__post_init__` 添加中文 Google 风格 docstring，含 Args/Returns |
| ANN201 | 21 | `app/models/account_classification.py`、`app/routes/capacity/databases.py` | 公共 property/函数补齐返回类型（如 `-> str`、`-> Response`） |
| TRY301 | 18 | `app/routes/accounts/sync.py`、`app/routes/connections.py` | 将 `raise` 移出 `try`，或抽成 `_raise_invalid_params()` 私有函数再调用 |
| INP001 | 17 | `app/routes/accounts/*.py`、`app/routes/history/*.py` | 在包内新增最小 `__init__.py`，写明蓝图暴露接口 |
| ANN002 | 14 | `app/services/aggregation/database_aggregation_runner.py` | `*args` 注解为 `tuple[Any, ...]`，确保动态参数可追踪 |
| ANN003 | 14 | `app/utils/response_utils.py`、`app/utils/structlog_config.py` | `**kwargs` 统一注解为 `Mapping[str, Any]` 并限制允许键名 |
| PERF401 | 10 | `app/routes/accounts/classifications.py`、`app/routes/files.py` | 用列表/字典推导或 `list.extend` 替代 `append` 循环，压缩转换逻辑 |
| S608 | 10 | `app/services/accounts_sync/adapters/mysql_adapter.py`、`.../oracle_adapter.py` | SQL 改为参数化查询（`text()` + 绑定参数），避免字符串拼接 |
| F841 | 9 | `app/scheduler.py`、`app/services/accounts_sync/accounts_sync_filters.py` | 删除未使用变量或改写为日志/metrics，必要时注释原因 |
| FBT001 | 8 | `app/routes/instances/detail.py`、`app/services/accounts_sync/adapters/mysql_adapter.py` | 布尔位置参数改关键字或 Enum，并同步更新调用方 |
| D400 | 5 | `migrations/env.py` | Docstring 首行使用完整句子并以句号结尾 |
| D413 | 5 | `migrations/env.py` | `Args/Returns/Raises` 等段落之间保留一行空白 |
| D415 | 5 | `migrations/env.py` | Docstring 首行与描述段分隔，并以标点结尾 |
| I001 | 3 | `app/routes/main.py`、`app/utils/database_batch_manager.py` | 运行 `ruff --select I`/isort，保持导入顺序一致 |
| UP017 | 3 | `app/routes/capacity/instances.py`、`app/services/partition_management_service.py` | 使用 `datetime.UTC` 或 `time_utils.now()`，避免朴素时间对象 |
| SIM118 | 2 | `app/routes/dashboard.py`、`app/services/statistics/log_statistics_service.py` | 合并嵌套 `if`，或使用单条件表达式简化判断 |
| D100 | 1 | `nginx/gunicorn/gunicorn-prod.conf.py` | 模块开头添加中文概述 docstring，说明入口作用 |
| D104 | 1 | `app/routes/tags/__init__.py` | 包级 docstring 描述暴露的蓝图或路由注册方式 |
| RUF022 | 1 | `app/utils/rate_limiter.py` | 生成器/async 上下文明确 `yield` 位置，满足 Ruff 的上下文检测 |
| SLF001 | 1 | `app/utils/cache_utils.py` | 避免访问私有属性，改用公开 getter 或封装接口 |
| TC003 | 1 | `app/services/partition_management_service.py` | `TYPE_CHECKING` 块放在导入区域，符合 Ruff 对顺序的要求 |
| TRY401 | 1 | `app/utils/data_validator.py` | `logger.exception` 直接带异常即可，移除 `{exc}` 等占位符 |
| UP037 | 1 | `app/services/partition_management_service.py` | 将弃用的 `typing.ContextManager` 替换为 `contextlib.AbstractContextManager` |

### 1.2 阻断规则簇（仅保留仍未清零的规则）
- **A. 类型契约（404 条）**：`ANN401/ANN001/ANN202/ANN201/ANN002/ANN003/RUF012/ARG002`
  - 场景：模型属性、表单定义、服务入口缺乏类型定义，`ClassVar`/`Any` 滥用。
  - 处置：优先处理模型与服务层，形成 `typing.Protocol`/`TypedDict`，对 `__init__` 未用参数改 `_unused_*`。
- **B. 异常 + 日志（278 条）**：`BLE001/TRY300/TRY301/G201/G004/PGH003/TRY401/F841`
  - 场景：蓝图捕获裸 `Exception`、在 `try` 中 `return`、f-string 日志、`type: ignore` 无理由。
  - 处置：抽象 `safe_execute()`、细化异常类型、`logger.exception` 统一结构化字段。
- **C. 文档/注释/行宽（152 条）**：`D205/D107/D400/D413/D415/D100/D104/E501/ERA001`
  - 场景：常量模块 docstring 缺空行、`migrations/env.py` 文档缺段、`app/__init__.py` 行超宽且仍留注释代码。
  - 处置：复用 Google 中文模板 + VSCode snippet，长行拆多段或抽常量。
- **D. 结构/性能/接口（100 条）**：`C901/INP001/I001/PERF401/S608/FBT001/UP017/UP037/SIM118/RUF022/TC003/SLF001`
  - 场景：蓝图缺 `__init__.py` 导致 namespace 包；连接/实例路由存在 SQL 字符串拼接与布尔位置参；`datetime.strptime` 返回朴素时间。
  - 处置：按照路由粒度补包初始化，SQL 改参数化 + 枚举布尔选项，引入 `datetime.UTC` + `time_utils.now()`。

## 2. 优先修复清单（仅列仍未完成项）
### P0（立即阻断项）
1. **类型注解冲刺**（`ANN401/ANN001/ANN202/ANN201/ANN002/ANN003/RUF012/ARG002`）：
   - 批次一：`app/forms/definitions/*` + `app/routes/instances/*`，补上下文返回/参数类型。
   - 批次二：`app/models/*`（尤其 `instance_*`, `account_*`）加入 `ClassVar`、property 返回类型。
2. **异常与日志基线**（`BLE001/TRY300/TRY301/G201/G004/PGH003/TRY401/F841`）：
   - 路由入口（`app/routes/accounts/*.py`, `app/routes/cache.py`, `app/routes/capacity/*.py`）统一 `try` 结构，拆分查询逻辑。
   - 同步与调度（`app/scheduler.py`, `app/services/accounts_sync/*`）替换 f-string 日志、`type: ignore` 增补原因。
3. **文档 & 注释整治**（`D205/D107/D400/D413/D415/D100/D104/E501/ERA001`）：
   - 常量/错误定义模块按 Google 中文模板补 docstring 与空行。
   - `migrations/env.py`、`nginx/gunicorn/*.py` 与 `app/routes/tags/__init__.py` 填写包说明，清理注释代码并控制行宽。
4. **SQL/连接安全**（`S608/FBT001/UP017/UP037`)：
   - 同步适配器内的 SQL 改为参数化，`datetime.strptime` 结果 `.replace(tzinfo=datetime.UTC)`。

### P1（可在本迭代完成）
1. **复杂度/结构**（`C901/INP001/I001/PERF401/SIM118`)：
   - `app/routes/accounts/ledgers.py`、`app/routes/history/logs.py` 拆 Handler；补 `__init__.py` 并整理导入顺序。
2. **日志工具与缓存**（`SLF001/RUF022/TC003`)：
   - `app/utils/cache_utils.py` 避免访问私有属性；`app/utils/rate_limiter.py` 调整装饰器签名，`app/services/partition_management_service.py` 修正上下文协议注解。
3. **代码注释清理**（`ERA001` 剩余 27 条）：
   - 模型与 `app/__init__.py` 中的临时代码改 feature flag 或删除。

### P2（收尾长尾）
- `F841` 未使用变量（集中在 `app/scheduler.py`）；
- `D400/D413/D415`（全部在 `migrations/env.py`）；
- `I001`（3 条，分别在 `app/routes/main.py`、`app/utils/database_batch_manager.py`、`app/utils/logging/queue_worker.py`）。

## 3. 批量处理策略
1. **类型批修**：
   - `ruff check app/forms app/routes app/models --select ANN,ARG,RUF012`。
   - 默认引入 `from __future__ import annotations`，将常见结构提炼为 `TypedDict`/`Protocol`。
2. **异常与日志收敛**：
   - 结合 `scripts/logging_helpers.py`（若无则新增）封装 `log_error/log_info`，统一 extra 字段。
   - 对捕获裸异常的函数建立私有 `_apply_filters()` 并在调用点处理异常，避免在 `try` 中 `return`。
3. **Docstring 与注释**：
   - 使用 `python scripts/tools/docstring_guard.py --paths app/constants app/errors migrations/env.py` 校验 `D205/D107/D400/D413/D415`。
   - 注释代码统一移除；若需保留，请添加 Feature Flag 解释并解除 `ERA001`。
4. **SQL/布尔参数修复**：
   - 将 `S608` 涉及的 SQL 改为 `text("SELECT ... WHERE col = :value")` + `params`。
   - 将布尔参数整理为枚举或关键字实参，更新调用点并补测试。

## 4. 验证清单
- `./scripts/refactor_naming.sh --dry-run`（确保命名守卫未触发）。
- `ruff check <touched files> --select ANN,ARG,BLE,TRY,G,D`。
- `pytest -m unit`（尤其覆盖缓存/同步服务）。
- 若调整 SQL/连接逻辑，运行 `make dev start` + 相关集成测试或最小化脚本。

## 5. 下一阶段里程碑
1. **12-09 下午班**：完成 P0 类型 + 异常治理（目标 <=700 条），`app/models/*`、`app/routes/accounts/*` 通过 `ruff --select ANN,BLE,TRY`。
2. **12-10 上午**：清空常量/错误模块的 docstring/注释告警（`D205/D107/E501/ERA001`），并补 `app/routes/accounts` 子包的 `__init__.py`。
3. **12-10 晚班**：聚焦 `S608/FBT001/UP017/UP037` 与复杂度 (`C901/PERF401`)，每修完一批立即刷新 `./scripts/ruff_report.sh full`，力争将总告警压至 500 以内。
