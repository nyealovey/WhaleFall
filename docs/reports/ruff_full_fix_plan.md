# Ruff 全量扫描修复计划（更新：2025-12-10 13:51）

> 最新全量报告：`docs/reports/ruff_full_2025-12-10_135107.txt`（840 条告警，`./scripts/ruff_report.sh full`）。类型专项（ANN/ARG/RUF012）仍参考 `docs/reports/ruff_types_2025-12-10_134006.txt`，其余章节均根据 13:51 报告刷新。

## 0. 类型脚本专项（ANN/ARG/RUF012）

### 0.1 本轮扫描摘要
- **命令**：`ruff check app/forms app/views app/models --select ANN,ARG,RUF012`
- **报告**：`docs/reports/ruff_types_2025-12-10_134006.txt`
- **结果**：**0** 条告警（已清空 ANN/ARG/RUF012），上一版本 `docs/reports/ruff_types_2025-12-10_133612.txt` 中的 7 条问题均已修复。

### 0.2 本轮成果
- `app/types/structures.py` 新增 `NumericLike/ColorHex/ColorName/CssClassName/ColorToken` 别名并集中导出，`app/types/__init__.py`、`app/models/tag.py`、`app/models/instance_size_aggregation.py`、`app/models/__init__.py`、`app/models/sync_session.py` 按照别名联动修复。
- `_to_float`、颜色属性与 `SyncSession.created_by` 均已具备显式类型，`__getattr__` 也改为 `-> object` 避免 Any。

### 0.3 后续动作
1. 将颜色/数值别名在更多服务层持续推广（如表单选项、校验器），避免重复 `str` 标注。
2. 维持类型脚本零告警：后续改动涉及 `app/forms/app/views/app/models` 时，需重新执行 `ruff check ... --select ANN,ARG,RUF012` 并更新 `docs/reports/ruff_types_*.txt`。

---

## 1. 最新扫描概览

### 1.0 今日扫描结果（报告：2025-12-10 13:51:07）
- **命令**：`./scripts/ruff_report.sh full`（Python 3.12，禁用 `--fix/--unsafe-fixes`）。
- **报告**：`docs/reports/ruff_full_2025-12-10_135107.txt`，共 **840** 条告警。类型专项清零后，新增告警主要集中在基础设施模块（`app/__init__.py`、`app/utils/structlog_config.py`）、路由（`app/routes/accounts/ledgers.py`、`accounts/sync.py` 等）与运维脚本（`migrations/env.py`、`nginx/gunicorn/*`）。
- **热点概览**：
  1. **核心框架 (`app/__init__.py` + `app/config.py`)**：`ANN202`, `C901`, `E501`, `RUF012` 同时命中，需拆分 `configure_app`、补错误处理返回类型、为配置类属性声明 `ClassVar` 并格式化长行。
  2. **日志系统 (`app/utils/structlog_config.py`)**：`ANN001/ANN201/ANN401/BLE001` 密集，必须为装饰器、hook、日志 helper 补注解并将 `**kwargs` 重写为 `Mapping[str, JsonValue]` 等安全类型，顺带消除裸 `Exception`。
  3. **账户账本路由 (`app/routes/accounts/ledgers.py`)**：函数拆分不彻底，`ANN001/ANN202/BLE001/PLR0913` 叠加，需要 typed query helper、特定异常处理和策略映射。
  4. **系统脚本 (`migrations/env.py`, `nginx/gunicorn/*.py`)**：缺少 `__init__.py`、函数返回类型、合法模块名，属于发布拦路虎；需先补包装模块再继续版本控制。
  5. **Docstring/行宽 (`app/models/*`, `app/routes/cache.py`, `app/utils/time_utils.py`)**：`D205/D202/E501/PLR2004` 集中在模型/工具，建议脚本化处理（模板化 Docstring + 常量提升）。

### 1.1 规则分布概览
| 规则 | 命中数 | 典型文件 | 推荐策略 |
| --- | --- | --- | --- |
| ANN401 | 171 | `app/utils/structlog_config.py` | 使用 `Mapping[str, JsonValue]`/`TypedDict` 替代 `Any`，收紧 `**kwargs/**args`。 |
| BLE001 | 102 | `app/routes/accounts/ledgers.py` | 捕获具体异常或交由统一 helper 处理，禁止裸 `Exception`。 |
| ANN001 | 74 | `app/routes/accounts/ledgers.py` | 为 query/filters 补类型，复用 `app/types` 中的别名。 |
| TRY300 | 49 | `app/routes/accounts/sync.py` | 将 `raise/return` 移出 `try`，必要时用 `_fail()` helper。 |
| E501 | 45 | `app/__init__.py`, `app/routes/cache.py` | 拆分长条件或使用辅助变量，保持 ≤120 字符。 |
| PLC0415 | 42 | `app/utils/time_utils.py`, `app/routes/accounts/sync.py` | 移除函数内 import，或封装 `_lazy_import` 并注明原因。 |
| C901 | 33 | `app/__init__.py::configure_app` | 拆阶段函数或策略表，控制复杂度 ≤10。 |
| PLR2004 | 32 | `app/models/credential.py`, `app/utils/version_parser.py` | 用具名常量/Enum 替代魔法数字（密码长度、版本片段等）。 |
| D205 | 29 | `app/models/database_size_aggregation.py` 等 | Docstring 摘要 + 空行 + 详情，批量脚本化。 |
| TC001 | 25 | `app/views/mixins/resource_forms.py` | TYPE_CHECKING 内导入，其他位置使用字符串注解。 |
| ANN202 | 23 | `app/__init__.py`, `migrations/env.py` | 错误处理/私有 helper 补 `-> Response | None` 等返回类型。 |
| PLR0913 | 19 | `app/models/credential.py` | 引入 dataclass/config 对象或 kwargs 打包长参数。 |
| TC006 | 16 | `app/views/mixins/resource_forms.py` | `cast()` 调用使用引号包裹类型表达式。 |
| UP037 | 14 | `app/views/*forms.py` | 去掉多余引号，直接引用类型。 |
| ARG002 | 13 | `app/models/sync_session.py` | 删除未用参数或更名 `_unused_*` 并在 docstring 说明。 |
| ANN201 | 12 | `app/models/tag.py` | property 明确返回类型。 |
| PLR0911 | 12 | `app/utils/time_utils.py` | 拆成策略 map / guard clause 减少 return。 |
| G201 | 12 | `app/routes/accounts/sync.py` | 改用 `logger.exception` + `extra`，禁用 `.error(..., exc_info=True)`。 |
| I001 | 11 | `app/views/scheduler_forms.py` | 整理 import 顺序，遵循 isort 规则。 |
| PLR0915 | 11 | `app/routes/history/logs.py` | 拆 `fetch/serialize` 阶段降低语句数。 |
| RUF012 | 10 | `app/config.py`, `app/utils/version_parser.py` | 类级容器标记 `ClassVar` 或 `MappingProxyType`。 |

### 1.2 阻断规则簇
1. **类型与契约（ANN 系列 + ARG002 + RUF012）**：涉及 40% 以上告警。先处理 `app/forms/definitions`, `app/views`, `app/models` 的基础类型，在 `app/types/` 中定义通用别名，结合 Pyright 确认。
2. **异常/控制流（BLE001/TRY300/TRY301/G201）**：集中在 routes、scheduler、同步服务。通过统一 `safe_execute` helper 和结构化日志接口，将捕获范围收敛并补上下文。
3. **结构与魔法数字（PLC0415/C901/PLR09x/PLR2004/PERF401）**：models、routes、utils 需要拆分函数、抽常量并上移 import。
4. **文档/样式（D205/D107/E501/D202 等）**：批量 Docstring 模板化和行宽整改，配合脚本辅助。
5. **安全与配置（S608/S105/N999/INP001）**：SQL 参数化、敏感文案 `noqa` 说明、包结构合法化需专项处理。

## 2. 优先修复清单

### P0（本轮迭代务必完成）
1. **核心框架与配置**：`app/__init__.py`、`app/config.py`、`app/errors/__init__.py` 中的 `ANN202/C901/E501/RUF012` 直接影响启动流程，优先拆分 `configure_app`、补全错误处理返回类型，并为配置类字典声明 `ClassVar`。
2. **结构化日志栈**：`app/utils/structlog_config.py`、`app/utils/time_utils.py` 需统一 `JsonValue` 别名、限制 `*args/**kwargs`、补齐 hook/装饰器类型，同时清理裸 `Exception` 捕获。
3. **账户账本路由**：`app/routes/accounts/ledgers.py`、`app/routes/accounts/sync.py` 中的 `ANN001/ANN202/BLE001/TRY301/PLC0415` 要求立即治理——拆 query helper、改成具体异常、移动内部 import。
4. **运维脚本与部署资产**：`migrations/env.py`、`nginx/gunicorn/*.py`、`app/routes/cache.py` 的 `INP001/N999/D205/E501` 直接阻断部署；补 `__init__.py`、合法模块名、模板化 Docstring 并压短行。

### P1（当前迭代次优先）
1. **Docstring/行宽批量修复**：集中处理 `app/models/*`、`app/routes/cache.py`、`app/routes/capacity/*` 的 `D205/D202/PLR2004/E501`，可编写脚本统一插入模板与常量。
2. **版本/时间工具精简**：`app/utils/version_parser.py`、`app/utils/time_utils.py` 存在 `C901/PLR0911/PLR2004/PLC0415`，需拆分阶段函数并转换魔法数字、移除内部 import。
3. **安全与 SQL 规范**：同步服务、数据库适配器保持 `S608/S105` 零新增，同时继续推进 `G201`（结构化日志）和 `RUF012`（可变类属性）的遗留模块。

### P2（滚动跟进）
- 处理剩余的 `N999/INP001` 边角（如 gunicorn 变种配置、脚本工具）。
- 将新增的类型别名推广到 `app/forms/definitions`、`app/services/*`，确保后续 Pyright/ Ruff 不回弹。
- 补全 tests/migrations 的类型标注与 `__init__.py`，保持 Ruff / Pyright 双清零。

## 3. 批量治理策略
1. **类型脚本**：执行 `ruff check app/forms app/views app/models --select ANN,ARG,RUF012`，结合 Pyright 输出，在 `app/types/` 中沉淀常用别名（如 `ResourceContext`, `FormPayload`）。
2. **异常处理模板**：抽象 `safe_execute(func, *, context: str)` 和 `log_with_context`，路由中仅负责组装上下文，其余交给 helper，顺便在 Pig builder 里统一 `TRY300/TRY301` 处理方式。
3. **Docstring Guard**：使用脚本批量插入 Docstring 空行，统一中文 Google 模板；对 models/errors 运行自动化校验。
4. **结构拆分清单**：建立 `refactor/scheduler_breakdown.md` 跟踪 `configure_app`、`history/logs`、`accounts/ledgers` 的拆分计划，逐步降低 `C901/PLR09x`。
5. **SQL 安全审计**：扩展 `scripts/tools/sql_param_guard.py` 扫描 `cursor.execute(f"` 模式，联动单测验证，确保所有 `text()` 语句都带参数绑定。

## 4. 验证清单
- `./scripts/refactor_naming.sh --dry-run`
- `ruff check <touched files> --select ANN,ARG,RUF012,BLE,TRY,G,PLC0415,PLR091x,D,S`
- `pytest -m unit`
- 涉及调度/同步的改动需在 `make dev start` 环境跑一次 smoke（accounts sync / scheduler reload）。

## 5. 下一阶段里程碑
1. **12-10 下午**：完成类型/异常 P0 改动，让 ANN+BLE+TRY 总数降至 500 条以下，并输出《类型规范补充说明》。
2. **12-10 晚班**：推进 scheduler/connections 拆分、SQL 参数化，争取将总告警压到 720 条左右；同步更新此 fix plan。
3. **12-11 上午**：集中清理 Docstring/行宽/魔法数字，运行 `./scripts/ruff_report.sh full` 复核成果并评估下一波 P1 任务。
