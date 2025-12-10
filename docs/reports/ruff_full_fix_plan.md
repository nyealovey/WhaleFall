# Ruff 全量扫描修复计划（更新：2025-12-10 16:31）

> 最新全量报告：`docs/reports/ruff_full_2025-12-10_163106.txt`（800 条告警，202 条可自动修复）。以下内容基于该报告刷新，不再重复前置摘要。

## 1. 最新扫描概览

### 1.1 规则分布概览
| 规则 | 命中数 | 典型文件 | 推荐策略 |
| --- | --- | --- | --- |
| BLE001 | 102 | `app/routes/accounts/ledgers.py`、`app/routes/cache.py` | 统一 `safe_route_call`/`log_with_context` helper，只捕获特定异常并复用结构化日志。 |
| TC006 | 87 | `app/routes/accounts/ledgers.py`、`app/routes/accounts/sync.py` | `cast()` 使用字符串化类型或转向 Protocol，集中在查询构建/关系操作段落批量替换。 |
| TC001 | 57 | `app/views/mixins/resource_forms.py`、`app/services/form_service/*` | 将重型导入包裹在 TYPE_CHECKING 中，运行期改用字符串注解。 |
| UP037 | 49 | `app/forms/definitions/*`、`app/views/*forms.py` | 去掉类型注解中的引号，确保 Ruff/pyright 共识；可脚本化处理。 |
| TRY300 | 49 | `app/routes/accounts/sync.py`、`app/routes/cache.py` | 将 `raise/return` 从 `try` 中移出或拆 `_fail()` helper，保障 finally 执行。 |
| E501 | 46 | `app/__init__.py`、`app/models/*` | 拆长日志/SQL/条件，必要时提取常量或多行字符串。 |
| C901 | 33 | `app/__init__.py::configure_app`、`app/routes/history/logs.py` | 划分配置阶段或序列化步骤，控制分支/语句数 < 10。 |
| D205 | 27 | `app/models/database_*`、`app/models/instance_*` | Docstring 首行与说明留空行，统一中文 Google 模板，可批处理。 |
| D102 | 24 | `app/routes/accounts/ledgers.py` Protocol、`app/views/*` | 为公共 Protocol 与视图方法补中文 docstring，以解释用途/参数。 |
| F401 | 21 | `app/routes/*`、`app/services/*` | 清理未使用导入，或在 TYPE_CHECKING 中保留；与 TC001 联动。 |
| TC003 | 15 | `app/views/mixins/resource_forms.py` | stdlib/typing 导入放入 TYPE_CHECKING 或引用 `typing` 前缀。 |
| ARG002 | 13 | `app/models/instance.py`、`migrations/env.py` | 删除未使用参数或前缀 `_unused_` 并在 docstring 中说明。 |
| G201 | 12 | `app/routes/accounts/sync.py`、`app/utils/structlog_config.py` | 用 `logger.exception` + `extra` 取代 `.error(..., exc_info=True)`。 |
| S608 | 10 | `app/routes/files.py` 等 SQL 片段 | 确认文本 SQL 均使用参数绑定或 `sa.text().bindparams()`。 |

### 1.2 阻断规则簇
1. **日志与异常（BLE001/G201/TRY300/TRY301）**：集中在账户路由、缓存路由、scheduler；需要模版化异常处理、引入专用 helper，防止裸 `Exception` 与 try/finally 早退。
2. **类型导入与注解（TC006/TC001/UP037/TC003）**：表单/视图层的 cast 与 TYPE_CHECKING 不规范导致 150+ 告警，需统一 `app/types` 别名并脚本替换注解格式。
3. **文档与风格（D205/D102/E501）**：模型和 Protocol 缺少中文 docstring，配合黑名单文件批量填充；同时拆长行，避免引入新的 Style 告警。
4. **结构复杂度（C901/PLR0913/PLR0915）**：`configure_app`、历史日志路由、Credential 模型构造函数需拆分参数对象或阶段函数，减少 10+ 重度告警。
5. **配置/脚本合法性（N999/S608/RUF012）**：`nginx/gunicorn/*.py`、`app/config.py` 中的命名与可变 ClassVar 要在部署前修正，防止再次阻断。

## 2. 优先修复清单

### P0（立即推进）
1. **`app/__init__.py` & `app/config.py`**：聚焦 `C901/E501/RUF012`，拆出 `configure_logging`、`configure_security`、`register_blueprints`，并将配置字典标注 `ClassVar`，顺带解决 import 顺序。
2. **账户/缓存路由的异常治理**：`app/routes/accounts/ledgers.py`、`app/routes/accounts/sync.py`、`app/routes/cache.py` 的 `BLE001/TRY300/TC006`；引入 `QueryLogger` Protocol + helper，批量补 docstring 与类型注解。
3. **`app/views/mixins/resource_forms.py` 类型导入**：重构 TYPE_CHECKING 块与 cast，用 `app/types` 内别名 + `typing.TYPE_CHECKING`，同时处理 57 个 `TC001` 与 15 个 `TC003`。
4. **部署脚本合法化**：`migrations/env.py`、`nginx/gunicorn/*.py` 的 `ANN001/N999`；添加 `__init__.py`、更名配置或改为 `.conf_template`，确保 Ruff/Pyright 均可 import。

### P1（本迭代后半程）
1. **Docstring/长行批处理**：针对 `app/models/database_*`、`app/models/instance_*`、`app/models/unified_log.py` 的 `D205/E501/D102` 编写脚本自动插入中文 Google 模板、拆长参数列表。
2. **凭据/用户模型重构**：`app/models/credential.py` 与 `app/models/user.py` 的 `PLR0913/PLR2004`，引入配置 dataclass（如 `CredentialOptions`）、常量化密码长度，避免魔法值。
3. **结构化日志栈**：`app/utils/structlog_config.py`、`app/utils/time_utils.py` 的 `G201/PLC0415/S608`，梳理 import、logger helper（`LoggerProtocol`）、SQL 调用的参数绑定。

### P2（滚动跟进）
- 清理 `F401/I001`（未使用导入）与 `UP035/UP037`（typing import）以降低后续增量冲突。
- 继续拓展 `app/types/`，将路由层使用的 Query/Context 别名沉淀，减少 cast/Any。
- 审核脚本与测试目录（`scripts/*`, `tests/unit/*`）的 docstring 与 pytest 导入缺失，避免 Pyright 与 Ruff 互相打架。

## 3. 批量治理策略
1. **异常/日志模板化**：落地 `safe_route_call`（捕获已知异常、记录 context）与 `log_with_context(logger, event, **extra)`，路由调用全部走模板，顺带消除 `BLE001/G201/TRY300`。
2. **类型注解脚本**：编写 `scripts/tools/fix_casts.py`，将 `cast(Type, ...)` 自动转换为 `cast("Type", ...)` 并将 `typing` 导入移入 `TYPE_CHECKING`，一次性清空 `TC006/TC001`。
3. **Docstring 生成器**：使用 `scripts/tools/add_cn_docstrings.py` 扫描 models/routes，插入中文 Google 模板，配合 `black`/`isort` 自动格式，批量解决 `D102/D205`。
4. **配置拆分计划**：在 `docs/tech/refactor_config.md` 中列出 `configure_app` 拆分步骤与 owner，确保 `C901/PLR0915` 任务可跟踪。
5. **SQL/安全审计**：扩展 `scripts/tools/sql_param_guard.py`，扫描 `execute(f"` 模板并回写 `sa.text().bindparams()`，降低 `S608` 复发。

## 4. 验证清单
- `./scripts/refactor_naming.sh --dry-run`
- `ruff check <touched files> --select ANN,ARG,RUF012,BLE,G,TRY,TC,PLR09x,D,E,S`
- `npx pyright app`（关注 TYPE_CHECKING、Protocol 与 ResourceForm 泛型）
- `pytest -m unit`
- 涉及调度/同步的改动需在 `make dev start` 后跑一次 smoke（scheduler reload + accounts sync）

## 5. 下一阶段里程碑
1. **12-10 晚上**：完成 P0 中 `configure_app` 拆分与账户路由异常治理，目标将 BLE/TRY 组合压至 <70；提交“日志异常治理”说明。
2. **12-11 上午**：批量处理模型 Docstring 与表单 TYPE_CHECKING，清空 `TC006/TC001/UP037`，触发一次 `./scripts/ruff_report.sh full` 验证。
3. **12-11 下午**：聚焦凭据/用户模型、structlog 栈，推动 `PLR0913/PLR2004/G201` 剩余告警下降 50%，并在 PR 中同步配置更改与验证记录。
