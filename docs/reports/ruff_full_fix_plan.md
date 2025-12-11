# Ruff 全量扫描修复计划（更新：2025-12-11 11:35）

> 最新全量报告：`docs/reports/ruff_full_2025-12-11_112236.txt`（共 640 条告警，168 条可自动修复）。以下统计与优先级均基于该报告刷新，旧版内容作废。

## 1. 最新扫描概览

### 1.1 主要规则分布
| 规则 | 命中数 | 代表文件 | 治理建议 |
| --- | --- | --- | --- |
| **C901** 复杂函数 | 33 | `app/__init__.py::configure_app`、`app/routes/history/logs.py::_search_logs_impl` | 拆分配置/序列化阶段，提炼子函数，控制语句数 <10。 |
| **E501** 长行 | 46 | `app/__init__.py`、`app/models/*` | 拆条件、提常量、改用多行字符串，确保 ≤120 字符。 |
| **RUF012** ClassVar | 12 | `app/config.py` | 配置字典改为 `ClassVar[dict[str, Any]]` 或常量模块。 |
| **UP035/UP037** typing 导入 | 40+ | `app/constants/user_roles.py`、`app/forms/definitions/base.py` | 统一 `collections.abc` 导入与类型注解去引号，可脚本化。 |
| **PLR0913/PLR0915** 过多参数/语句 | 25 | `app/errors/__init__.py`, `app/models/credential.py`, `app/models/instance.py` | 通过 dataclass/options 对象收束入参；拆装饰器/逻辑块。 |
| **PLR2004** Magic value | 18 | `app/models/credential.py`, `app/models/user.py` | 定义常量（`MIN_PASSWORD_LENGTH` 等）并引用。 |
| **D205/D102** Docstring | 70+ | `app/models/database_*`, `app/routes/accounts/ledgers.py` | 插入中文 Google Docstring、空行，Protocol 也需解释。 |
| **TC006/TC001** cast/TYPE_CHECKING | 60+ | `app/routes/accounts/ledgers.py`, `app/routes/accounts/sync.py` | 将 `cast()` 类型字符串化，重整 TYPE_CHECKING 块。 |
| **I001/F401** 导入顺序/未使用 | 20+ | `app/routes/accounts/ledgers.py` 等 | 统一 isort，清理未使用导入或置于 `TYPE_CHECKING`. |

### 1.2 阻断主题
1. **日志与异常（BLE001/G201/TRY300/TRY301）**：账户路由、缓存路由与 scheduler 已迁移到 `safe_route_call`，报告中已无此类命中；保持后续新增路由遵循模板。
2. **类型导入与 cast**：表单/视图层 `TC006/TC001/UP037` 仍是增量冲突高发区，需要脚本化替换并沉淀 `app/types` 别名。
3. **Docstring & 长行**：模型、Protocol 仍缺中文注释，阻塞 `D205/D102/E501`；建议批量脚本+人工 spot check。
4. **结构复杂度**：`configure_app`、Credential/Instance 模型 `__init__` 需拆分对象与 builder，结合 C901/PLR091x 统一治理。

## 2. 优先修复清单

### P0（本迭代-前半）
1. **`app/__init__.py` 与 `app/config.py`**  
   - 目标：消解 `C901/E501/RUF012`。  
   - 动作：拆 `configure_app` 为 `configure_blueprints`、`configure_security`、`configure_logging` 三段；把 `SQLALCHEMY_ENGINE_OPTIONS` 等设为 `ClassVar` 或单独 `settings.py`。  
   - 验证：`ruff check app/__init__.py app/config.py --select C901,E501,RUF012`。

2. **`app/forms/definitions/base.py` & 相关视图**  
   - 目标：清空 `UP037/TC006/TC001/PLC0105`。  
   - 动作：重命名 `ContextResourceT`→`ContextResourceT_contra`，去掉类型注解引号，统一 `TYPE_CHECKING` 导入，并为 `cast()` 使用字符串。  
   - 验证：`ruff check ... --select UP037,TC006,TC001,PLC0105`。

3. **凭据/实例模型**  
   - 目标：处理 `PLR0913/PLR2004`。  
   - 动作：新增 `CredentialOptions`/`InstanceOptions` dataclass，把魔法数字转常量（如 `PASSWORD_VISIBLE_TAIL = 4`，`MIN_PASSWORD_LENGTH = 8`），并分层初始化。  
   - 验证：`ruff check app/models/credential.py app/models/instance.py --select PLR0913,PLR2004`。

### P1（本迭代-后半）
1. **Docstring & 长行批处理**  
   - 范围：`app/models/database_*`, `instance_*`, `unified_log.py`。  
   - 工具：`scripts/tools/add_cn_docstrings.py` 自动插入中文 Google 模板，结合 `black`、`isort`，确保 `D205/D102/E501` 清零。  
2. **账户台账路由 (`app/routes/accounts/ledgers.py`)**  
   - 规则：`I001/D102/TC006`。  
   - 动作：整理 import、为 Protocol 增加 docstring、统一 `cast()`。  
3. **错误基类 (`app/errors/__init__.py`)**  
   - 规则：`PLR0913/E501`。  
   - 动作：拆 `__init__` 参数对象或使用 `**kwargs`, 将长三元条件拆多行。

### P2（滚动）
- 重构 `configure_app` 后完善 `docs/tech/refactor_config.md`，记录新函数职责。
- 扩展 `scripts/sql_param_guard.py` 检测潜在 `S608`。
- 每次提交前运行 `./scripts/ruff_report.sh style` + `pyright`，确保无回归。

## 3. 批量治理策略
1. **类型脚本化**：在 `scripts/tools` 新增 `fix_typing_imports.py`，遍历 `.py` 自动将 `typing.Mapping`→`collections.abc.Mapping`，并将 `cast(Type, ...)` 转 `cast("Type", ...)`。可配合 `pre-commit`。
2. **Docstring 生成器**：复用 `scripts/tools/add_cn_docstrings.py`，输入模型路径批量插入中文 Google 模板，并根据 `schema` 自动填充字段描述。
3. **配置拆分蓝图**：在 `docs/tech/refactor_config.md` 中列出 `configure_app` 的新阶段、owner、截止时间，避免 C901 反复复现。
4. **日志与异常模板**：继续推广 `safe_route_call`/`log_with_context`，任何新增路由默认引用 helper；在 README 的贡献者章节补示例。

## 4. 验证清单（提交前）
- `./scripts/refactor_naming.sh --dry-run`
- `ruff check <touched files> --select BLE,G,TRY,TC,UP,PLR09x,D,E,RUF012`
- `npx pyright app`
- `pytest -m unit`
- 涉及 scheduler/同步的改动需在 `make dev start` 后跑一次 smoke（scheduler reload + account sync）。

## 5. 里程碑
1. **12-11 中午**：完成 P0（配置、forms、模型）并复跑 `ruff_full`，目标将告警降至 <500。  
2. **12-11 晚上**：完成 Docstring/E501 批处理与台账路由治理，输出“Ruff 全量整改阶段性总结”。  
3. **12-12 上午**：收尾剩余 `PLR0913/PLR2004`、`TC006` 零星告警，并将自动脚本纳入 CI（pre-commit + 贡献指南更新）。
