# Ruff 全量扫描修复计划（更新：2025-12-10 12:20）

## 1. 最新扫描概览

### 1.0 今日扫描结果（报告：2025-12-10 09:24:30）
- **命令**：`./scripts/ruff_report.sh full`（Python 3.12，禁用 `--fix/--unsafe-fixes`）。
- **报告**：`docs/reports/ruff_full_2025-12-10_092430.txt`，共 1,008 条告警，较 2025-12-09 14:55 的 1,065 条下降 57 条，主要得益于昨晚的路由分层与表单重构；但调度、账户同步与常量模块仍是高频来源。
- **热点概览**：
  - **类型/契约类（421 条）**：`ANN401/ANN001/ANN202/ANN201/ANN002/ANN003/RUF012/ARG002`，集中在 `app/views/*forms.py`、`app/forms/definitions/base.py`、`app/routes/connections.py` 以及 `app/constants/*`。
  - **异常与日志（247 条）**：`BLE001/TRY300/TRY301/G201/G004/PGH003`，以 `app/views/scheduler_forms.py`、`app/routes/health.py`、`app/scheduler.py`、`app/services/accounts_sync/*` 为主。
  - **文档与行宽（131 条）**：`D205/D107/E501/ERA001/D202`，集中在常量模块、错误定义和账户/文件路由。
  - **结构与控制流（187 条）**：`PLC0415/PLR091x/PLR2004/C901/PERF401`，`app/routes/accounts/ledgers.py`、`app/routes/files.py`、`app/models/credential.py`、`app/scheduler.py` 告警最密集。
  - **SQL/安全（10 条 S608）**：全部来自 `app/services/accounts_sync/adapters/*`，需要统一参数化查询与测试覆盖。
- **建议验证**：针对上述热点文件先执行 `ruff check <file> --select ANN,ARG,BLE,TRY,G,PLC0415,PLR091x,D,S`，再跑 `pytest -m unit` 覆盖改动范围。

### 1.1 规则分布概览
| 规则 | 命中数 | 典型文件 | 推荐策略 |
| --- | --- | --- | --- |
| ANN401 | 191 | `app/forms/definitions/base.py`、`app/views/mixins/resource_forms.py`、`app/routes/connections.py` | 为表单上下文定义 `TypedDict/Protocol`，`resource/instance` 参数改为具体类型或泛型。 |
| BLE001 | 102 | `app/views/scheduler_forms.py`、`app/routes/health.py` | 细化异常类型，落盘结构化日志并向上抛业务异常。 |
| ANN001 | 89 | `app/routes/accounts/ledgers.py`、`app/views/password_forms.py` | 为查询、实例、资源参数加显式类型；复用 `types` 模块别名。 |
| TRY300 | 54 | `app/routes/health.py`、`app/scheduler.py` | 将 `return/raise` 从 `try` 中移出，使用守卫或 `_validate_*` 辅助函数。 |
| PLC0415 | 48 | `app/models/__init__.py`、`app/models/credential.py`、`app/models/unified_log.py` | 禁止函数内 import；需惰性加载时封装 `_ensure_*` 并说明原因。 |
| E501 | 46 | `app/__init__.py`、`app/errors/__init__.py`、`app/routes/connections.py` | 拆分长条件或拆出常量，确保行宽 ≤120。 |
| RUF012 | 38 | `app/constants/database_types.py`、`app/constants/flash_categories.py`、`app/constants/sync_constants.py` | 可变类属性声明为 `ClassVar` 或换成不可变 `tuple`. |
| ARG002 | 38 | `app/views/classification_forms.py`、`app/views/tag_forms.py` | 移除未使用参数，或更名 `_unused_*` 并在 docstring 说明。 |
| G201 | 38 | `app/services/accounts_sync/accounts_sync_service.py`、`app/services/accounts_sync/adapters/mysql_adapter.py` | 使用 `logger.exception("msg", extra=...)` 替代 `.error(..., exc_info=True)`。 |
| D205 | 35 | `app/constants/sync_constants.py`、`app/constants/system_constants.py`、`app/errors/__init__.py` | 摘要行后插入空行，按中文 Google 模板重写 docstring。 |
| ANN202 | 34 | `app/__init__.py`、`app/views/*forms.py` | 私有函数补返回类型（含 `-> None`），必要时引入协议类统一签名。 |
| C901 | 34 | `app/__init__.py`、`app/routes/health.py`、`app/routes/history/logs.py` | 拆分「解析参数→业务→序列化」，必要时创建服务类。 |
| PLR2004 | 32 | `app/models/credential.py`、`app/utils/version_parser.py` | 将魔法数字提到常量或枚举，便于测试。 |
| ERA001 | 23 | `app/models/credential.py`、`app/models/account_permission.py`、`app/models/account_classification.py` | 删除注释掉的旧逻辑；需保留时写 feature flag 注释。 |
| PGH003 | 23 | `app/routes/scheduler.py` | `type: ignore` 必须指定触发规则（如 `[attr-defined]`）并补 TODO。 |
| D107 | 22 | `app/errors/__init__.py`、`app/models/credential.py` | `__init__` 需中文 docstring 描述副作用与参数。 |
| ANN201 | 21 | `app/models/account_classification.py`、`app/routes/capacity/instances.py` | `@property` 返回类型显式化，例如 `-> str`。 |
| G004 | 21 | `app/models/credential.py`、`app/scheduler.py` | 日志改 `%s` + `extra`，禁止 f-string。 |
| PLR0913 | 19 | `app/models/credential.py`、`app/routes/accounts/classifications.py` | 超过 5 参数的函数拆 `dataclass`/配置对象。 |
| INP001 | 13 | `app/routes/instances/*`、`app/services/ledgers/database_ledger_service.py`、`nginx/gunicorn/*.py` | 为子包补 `__init__.py` 并导出蓝图/工厂。 |
| PLR0915 | 12 | `app/routes/accounts/ledgers.py`、`app/routes/files.py` | 大函数按「解析→查询→渲染」拆段并引入 helper。 |
| PLR0911 | 12 | `app/services/form_service/*` | 汇总 `return` 路径到映射表或辅助函数。 |
| S608 | 10 | `app/services/accounts_sync/adapters/mysql_adapter.py`、`oracle_adapter.py` 等 | 所有 SQL 使用 `text()` + 绑定参数，并补测试覆盖。 |
| TRY301 | 9 | `app/routes/scheduler.py` | 在 `try` 外部抛异常，内部只保留易失败语句。 |
| PLR0912 | 9 | `app/routes/accounts/ledgers.py` | 改用策略映射或拆子函数降低嵌套。 |
| PERF401 | 8 | `app/routes/accounts/classifications.py`、`app/routes/files.py` | 改推导式/批量构建列表，避免循环累积 append。 |
| D202 | 5 | `app/routes/accounts/classifications.py`、`app/routes/ledgers.py`、`app/routes/scheduler.py` | Docstring 后禁止空行；使用 snippet 统一格式。 |
| ANN002 | 5 | `app/views/scheduler_forms.py`、`app/views/mixins/resource_forms.py` | `*args` 注解为 `tuple[Any, ...]` 或更明确的协议。 |
| ANN003 | 5 | `app/views/scheduler_forms.py`、`app/views/mixins/resource_forms.py` | `**kwargs` 注解 `Mapping[str, Any]`，必要时 `TypedDict`。 |
| EM101 | 3 | `app/routes/files.py` | 将异常信息先保存在变量，再传入异常。 |

> 其余低频规则（如 `LOG015`、`PYI034`、`SLF001`）仍存在，但命中数未进入前 30；处理上述主干后再统一收尾。

### 1.2 阻断规则簇（按照命中量排序）
1. **A. 类型与契约（421 条）**：`ANN401/ANN001/ANN202/ANN201/ANN002/ANN003/RUF012/ARG002`，先给 `app/views/*forms.py`、`app/forms/definitions/base.py` 和常量模块补类型与 `ClassVar`，完成后推行 `app/types/` 统一别名。
2. **B. 异常处理与日志（247 条）**：`BLE001/TRY300/TRY301/G201/G004/PGH003`，聚焦 `app/views/scheduler_forms.py`、`app/routes/health.py`、`app/scheduler.py`、`app/services/accounts_sync/*`，引入 `safe_execute`、`log_with_context` 等 helper。
3. **C. 文档/注释/行宽（131 条）**：`D205/D107/E501/ERA001/D202`，由 `app/constants/*`、`app/errors/__init__.py`、`app/routes/files.py` 组成，需批量套用 docstring 模板并删除注释代码。
4. **D. 结构与控制流（132 条）**：`PLC0415/PLR2004/PLR0913/PLR0915/PLR0911/PLR0912`，`app/routes/accounts/ledgers.py`、`app/routes/files.py`、`app/models/credential.py` 为重点，需引入 helper/配置对象降低复杂度。
5. **E. 复杂度/性能/包结构（55 条）**：`C901/INP001/PERF401`，需要补包 `__init__.py`、拆分 God function，并在路由层引入服务类。
6. **F. SQL 安全（10 条 S608）**：集中在数据库适配器，统一参数化查询并补单测。

## 2. 优先修复清单
### P0（立即执行）
1. **类型与 ClassVar 冲刺（421 条）**：
   - 先覆盖 `app/views/mixins/resource_forms.py`、`app/views/*_forms.py`、`app/forms/definitions/base.py`，将 `resource/instance` 重写为 `TypedDict | Protocol`。
   - `app/constants/*` 批量加 `ClassVar[...]` 并调成不可变 `tuple`，顺带补中文 docstring。
2. **异常+日志基线（247 条）**：
   - `app/views/scheduler_forms.py` 建立 `SchedulerFormErrorHandler` 帮助类，统一捕获 `ValidationError`/`NotFoundError`，仅在集中位置捕获 `Exception`。
   - `app/routes/health.py`、`app/scheduler.py`、`app/services/accounts_sync/*` 改 `%s` + `extra`，`logger.error(..., exc_info=True)` 替换成 `logger.exception`。
3. **控制流/函数内 import（132 条）**：
   - `app/models/credential.py`、`app/models/unified_log.py`、`app/models/__init__.py` 将懒加载 import 放到 `_lazy_importer` 函数，顶层仅持有 mapping。
   - `app/routes/accounts/ledgers.py`、`app/routes/files.py` 拆出 `_build_query`、`_serialize_payload`，解决 `PLR091x` 与 `PLC0415`。
4. **SQL 参数化（10 条 S608）**：
   - 同步适配器全部换成 `text("...")` + `bindparams`，新增最小单测验证参数绑定，并记录安全审计日志。

### P1（当前迭代引入）
1. **Docstring/注释/行宽（131 条）**：`app/constants/*`、`app/errors/__init__.py`、`app/routes/files.py` 使用 snippet 批量纠正 `D205/D107/E501/ERA001/D202`。
2. **结构/性能告警（55 条）**：将 `app/routes/accounts/ledgers.py`、`app/routes/accounts/classifications.py`、`app/routes/files.py` 依据「解析→查询→序列化」拆分，同时优化列表构建解决 `PERF401`。
3. **包初始化（13 条 INP001）**：依次为 `app/routes/instances/*`, `app/services/ledgers/`, `nginx/gunicorn/` 创建 `__init__.py` 并导出蓝图/配置对象。

### P2（长尾收敛）
- 清理 `G004` 余量及 `PLR2004` 残留魔法数字，必要时新增常量模块。
- 处理 `EM101/LOG015/PYI034/SLF001` 等低频规则，确保收敛前 `ruff check` 全绿。

## 3. 批量治理策略
1. **类型批修**：执行 `ruff check app/views app/forms app/constants --select ANN,ARG,RUF012`；重用 snippet 自动补中文 docstring + 类型注解。
2. **异常与日志模板**：实现 `app/utils/logging/handlers.py`（暂名）暴露 `log_with_context(logger, level, msg, *, extra)`，路由中引用，配合 `safe_execute()` 控制捕获范围。
3. **控制流拆分**：针对路由/模型大函数，优先使用 `dataclass` 承载查询条件；`app/models/credential.py` 的多分支逻辑改策略映射，减少条件深度。
4. **SQL 参数化脚本**：在 `scripts/tools/sql_param_guard.py` 中检测 `cursor.execute(f"...{variable}")`，对同步适配器跑一遍，确保无字符串拼接。
5. **Docstring+注释清理**：利用 `python scripts/tools/docstring_guard.py --paths app/constants app/errors app/routes/files.py` 自动检查 `D205/D202`，并用 `rg "# .*TODO"` 核对需保留的注释。

## 4. 验证清单
- `./scripts/refactor_naming.sh --dry-run`
- `ruff check <touched files> --select ANN,ARG,RUF012,BLE,TRY,G,PLC0415,PLR091x,D,S`
- `pytest -m unit`
- 涉及 SQL/调度逻辑时，`make dev start` 后跑对应集成测试或 smoke script。

## 5. 下一阶段里程碑
1. **12-10 下午班**：完成 P0 第 1、2 项（类型 + 异常），把总告警压到 ≤900 条，并产出 `app/types/forms.py` 模板。
2. **12-10 晚班**：处理 `PLC0415/PLR09x` 与 SQL 参数化，目标总告警 ≤820 条；同步记录 `safe_execute` 落地说明。
3. **12-11 上午**：集中攻克 `D205/D107/E501/ERA001/D202`，清理包初始化问题；运行 `./scripts/ruff_report.sh full` 再确认指标，并在 PR 中注明 Ruff 告警余量与后续计划。
