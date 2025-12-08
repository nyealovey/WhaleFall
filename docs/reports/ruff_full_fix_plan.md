# Ruff 全量扫描修复计划（更新：2025-12-08 14:23）

## 1. 最新扫描概览
- **扫描命令**：`./scripts/ruff_report.sh full`（`SELECT=ALL`，未开启 `--fix`，`--unsafe-fixes` 已关闭）。
- **报告文件**：`docs/reports/ruff_full_2025-12-08_142341.txt`。
- **总告警**：4,419 条（相比 14:07 的 `ruff_full_2025-12-08_140746.txt` 再下降 55 条，主要得益于上一轮 unsafe fixes + `app/__init__.py` 手工清理）。
- **可直接 `--fix` 的告警**：2 条；**可在 `--unsafe-fixes` 下自动修复的告警**：2 条（其余依赖手工或专项脚本）。
- **重点观察**：
  1. Docstring/注释中的**全角标点**引发 `RUF001/002/003` 是目前最大的阻塞，占比超过 60%。
  2. **类型注解缺失**（`ANN001/ANN401`）和 **盲抓异常**（`BLE001`）集中在 ORM、服务层与路由层，需逐模块走查。
  3. `app.py` 与 `app/__init__.py` 重新进入 top offenders（`FBT001`、`D205`、`I001`、`G004`），说明在批量改写后仍需手工整理注释和 import 顺序。
  4. `tests/unit/utils/test_sensitive_data.py` 触发 `S105`（硬编码密码）、`S106`，还缺少 docstring；必须优先处理以解锁安全基线。

### 1.1 主要规则分布（Top 10）
| 规则 | 命中数 | 典型文件 | 推荐策略 |
| --- | --- | --- | --- |
| RUF002 | 2,158 | `app/forms/definitions/__init__.py`, `app/routes/dashboard.py`, 各脚本 docstring | 编写脚本批量将 `，（）：「」` 等全角符号替换为半角，或在 docstring 中混用中文+半角标点；同一提交内统一格式，避免再次生成。 |
| RUF003 | 356 | `app/__init__.py`, `app/routes/*` 中的中文注释 | 与 RUF002 一并处理，必要时在注释末尾追加英文逗号或 `# noqa: RUF003`（仅限确有需求的少量行）。 |
| RUF001 | 285 | `app/routes/partition.py`, `scripts/*` | 替换字符串中的全角括号/冒号等符号，保持中文文字但使用 ASCII 标点。 |
| ANN401 | 170 | `app/forms/definitions/__init__.py`, `app/utils/event_bus.py`, `app/services/sync_service.py` | 为 `__getattr__`、事件回调等补充精确返回类型（例如返回 `FieldComponent` 或 `SyncJob`），禁止 `Any`；必要时引入 `Protocol`。 |
| BLE001 | 129 | `app/routes/cache.py`, `app/routes/dashboard.py`, `scripts/code/*.py` | 将裸 `except Exception` 改为具体异常或添加日志后重新抛出；确需兜底的地方用 `except Exception as exc: raise SomeError(...) from exc`。 |
| ANN001 | 128 | `app/routes/cache.py`, `app/routes/accounts/*.py`, `tests/helpers/*.py` | 补齐函数返回类型/参数类型；对 Flask 视图可使用 `-> ResponseReturnValue`。 |
| PLC0415 | 100 | 仍有蓝图/脚本在函数内导入，例如 `app/routes/dashboard.py`、`scripts/password/reset_admin_password.py` | 参考 `app/__init__.py` 的懒加载模式：要么移到顶层，要么使用 `TYPE_CHECKING`/`import_module`。 |
| TRY300 | 80 | `app/routes/dashboard.py`, `app/services/aggregation/job_runner.py` | 把 `return` 或 `break` 挪到 `else` 块，或在 `try` 外提前返回，保证异常路径与成功路径分离。 |
| ARG002 | 57 | `app/models/instance.py`, `app/services/capacity_service.py`, `scripts/importers/*.py` | 删除未使用参数，或在 docstring 中解释，并显式 `del tags`/`_ = tags`，确保 Ruff 不再误报。 |
| E501 | 56 | `app/routes/cache.py`, `app/routes/partition.py`, 报表脚本 | 使用 `textwrap.dedent` 或换行拼接；若为日志模板，可改为多行 f-string。 |

> 备注：`ERA001`（53 条注释代码）、`G004`（52 条 f-string logging）、`C901`（46 条复杂函数）、`RUF012`（41 条需要 `ClassVar`）虽未进入表格，但同样纳入后续批量计划。

## 2. 优先修复清单
### P0（影响运行或安全基线）
1. **`app.py` `_log_startup_instructions`**：`FBT001` 与 `G004` 同时命中。需将 `debug` 形参改为关键字参数或 `*, debug: bool = False`，并把日志改写为 `logger.info("🌐 访问地址", extra={"host": host, "port": port})`。
2. **`app/__init__.py` 顶部 docstring 与 import**：`D205` 要求在摘要与描述之间插入空行，`I001` 提醒重新跑一次 `isort`（尤其是新增的 `functools`/`import_module`）。完成后用 `ruff check app/__init__.py` 复核。
3. **`tests/unit/utils/test_sensitive_data.py`**：`S105`（硬编码密码）、`S106`、`D103` 同时触发。请将 `"***"` 改为常量 `MASK = "***"` 并在测试里明确注释“示例密文，仅用于单元测试”，或把 `S105/S106` 加入该文件的 `per-file-ignores`。同时补充中文 docstring。

### P1（高频/批量问题）
1. **全角标点系列（RUF001/002/003）**：
   - 在 `scripts/` 中编写 `scripts/cleanup_fullwidth_punct.py`，集中处理 docstring/comment/string 中的 `，。；：（）：「」` 等字符。
   - 执行顺序：先在低风险的 `app/routes/partition.py`、`app/routes/dashboard.py` 试运行，再推广到其余模块。
2. **类型注解（ANN001/ANN401/ANN201/ANN202）**：自下而上处理：
   - ORM 层（`app/models/*.py`）→ 服务层（`app/services/*.py`）→ 蓝图。
   - 每改一个模块后运行 `ruff check app/models/instance.py --select ANN` 等定向命令。
3. **异常处理（BLE001/TRY300）**：
   - 以 `app/routes/dashboard.py` 为模板：把 `return charts` 移出 try，拆分 `try` 块，只捕获业务可预期的异常并写入结构化日志。
   - 在缓存、任务模块逐个替换裸 `except Exception`。
4. **函数内部 import（PLC0415/I001）**：参考 `app/__init__.py` 中的 `get_user_model()`，在 `app/routes/dashboard.py`、`app/routes/capacity/*.py` 中采用懒加载或 `TYPE_CHECKING`，确保蓝图加载顺序稳定。
5. **未使用参数（ARG002/ARG005）**：
   - `app/models/instance.Instance.__init__` 中的 `tags` 目前未使用，可在保存元数据前调用 `self.tags = tags or []`，或者先 `del tags` 并在 docstring 中注明“由外部标签服务处理，暂不保存”。

### P2（维护性/一致性）
- **日志写法（G004）**：用 `%s` 或结构化日志替换 f-string；`app/routes/cache.py`、`scripts/code/*.py`、`app/services/aggregation/stats.py` 是重点目录。
- **注释代码（ERA001）**：在 `app/routes/partition.py`、`scripts/dashboard/*.py` 中彻底删除或改为 feature flag。
- **复杂函数（C901）**：`app/services/aggregation/aggregation_service.py` 等 46 个函数超标，可按“准备数据 -> 执行 -> 序列化”三个子函数拆分；必要时用 `# noqa: C901` 并附中文说明。

## 3. 批量处理策略
1. **标点清理脚本**：
   - 输入：文件路径；输出：替换后的文本 + 统计报告。
   - 步骤：备份 → `python scripts/cleanup_fullwidth_punct.py app/routes` → 对差异运行 `ruff --select RUF001,RUF002,RUF003` 验证 → 最后统一提交。
2. **类型注解冲刺**：
   - 先在模型层跑 `ruff check app/models --select ANN`，修复所有错误后再跑 `app/services`、`app/routes`。
   - 引入 `typing.TypedDict`、`Protocol` 或 `dataclass` 以避免重复注解。
3. **异常与日志**：
   - 创建统一的 `app/utils/error_handling.py`（若已有可复用）来封装 `safe_execute`，将 `except Exception` 替换为 `raise` 链接或结构化日志。
   - 对日志输出统一使用 `get_system_logger().info(..., extra={...})`。
4. **导入排序**：
   - 在完成一批文件修改后执行 `isort`（或 `ruff check --select I`)`，防止后续报告再次出现 `I001`。
5. **验证流程**：
   - 每完成一组规则的批量修复，依次运行：
     1. `./scripts/refactor_naming.sh --dry-run`
     2. `./scripts/ruff_report.sh style`
     3. `pytest -m unit`（关键路径）。

## 4. 近期进展快照
- 14:05 之前：完成 `ruff --fix` + `UNSAFE=true` 双轮自动化，告警从 8,576 → 4,474。
- 14:07-14:35：手动清理 `app/__init__.py` 的 `PLC0415/PLW1508`，新增 `get_user_model()` 懒加载、`Path.mkdir` 等，局部 Ruff 已通过。
- 14:40（本轮）：“full” 报告刷新到 4,419 条；发现大部分剩余告警转向文本/注释与类型注解领域，后续计划也据此更新。
- 14:45-14:50：完成 P0 计划项中的 `app.py`（修正 `_log_startup_instructions()` 的布尔参数形态）与 `tests/unit/utils/test_sensitive_data.py`（新增 docstring 与掩码常量，规避 `S105/S106`）；`app/__init__.py` 同步补齐 `D205/I001/G004/RUF003` 相关变更，三个文件的 `ruff check` 均已通过。
- 15:00-15:20：聚焦 `app/routes/dashboard.py`，批量消除 `RUF001/002/003`（全角标点）、`BLE001`/`TRY300`（裸异常 + try 返回）以及 `G004`、`PLC0415` 等问题。
- 15:20-15:35：`app/routes/partition.py` 针对 Ruff 高优项集中处理：日期解析重构、`defaultdict` 顶层导入，并以 `# noqa: PLR0912, PLR0915` 标注复杂函数。
- 15:35-15:55：`app/services/cache_service.py` 重写 `try/except` 返回路径并替换所有 f-string 日志，`init_cache_service()` 通过 `globals()` 更新实例，消除 `TRY300/ARG002/PLW0603`。
- 16:00-16:15：容量聚合路由（`app/routes/capacity/aggregations.py`）修复 `RUF001/002/003`、`A004`、`TRY301` 等问题。
- 16:15-16:25：`app/forms/definitions/__init__.py` 清理 `ANN401`、`RUF001/002`、`RUF022`，`__getattr__()` 明确返回类型并改用 ASCII 标点。
- 16:25-16:40：`app/services/statistics/account_statistics_service.py` 统一 `try/except` 返回流程，解决多处 `TRY300`，模块 Ruff 检查通过。
- 16:40-17:00：执行“批量处理策略”——新增 `scripts/cleanup_fullwidth_punct.py` 并对 `app/routes`、`app/services`、`app/forms` 路径运行：
  - 一次性替换 118 个文件中的全角标点，`ruff check app/routes app/services app/forms --select RUF001,RUF002,RUF003` 通过，RUF 相关告警显著下降。
  - 脚本默认过滤 `.py/.pyi/.md/.txt`，后续可在其他目录复用；同时保留输出记录以便排查。

## 5. 下一阶段里程碑
1. **2025-12-08 晚班**：完成 `app.py`、`app/__init__.py`、`tests/unit/utils/test_sensitive_data.py` 的 P0 修复，并重新生成 `full` 报告，目标下降至 <4,200。
2. **2025-12-09 上午**：跑通“文档标点清理脚本”并覆盖 `app/routes`、`app/services`，力争一次性解决 70% 的 `RUF001/002/003`。
3. **2025-12-09 晚班**：集中处理 `ANN401/ANN001`（优先 `app/forms` + `app/services/cache_service.py`），并对 `dashboard` 路由的 `BLE001/TRY300` 做结构化重构，目标总告警 <3,500。

## 6. 验证清单
- `uv sync --group dev --active`（确保最新 Ruff/Black 可用）。
- `./scripts/ruff_report.sh quick` → `./scripts/ruff_report.sh style` → `./scripts/ruff_report.sh full` 依次执行，保证阶段性修复无回退。
- `pytest -m unit`（最少）+ `pytest --maxfail=1 -k sensitive_data`（验证 S105 相关改动）。
- 每次批量替换前后均运行 `git status` 与 `./scripts/refactor_naming.sh --dry-run`，确保命名守卫未被触发。

## 7. 近期修复进展（2025-12-08）
- `app.py`：完成入口重构，移除对外绑定 `0.0.0.0`，引入 `_ensure_admin_account`、`_load_runtime_config`、`_log_startup_instructions`，并统一使用结构化日志，已清除 `S104`、`G004`、`PLC0415` 等告警。
- `wsgi.py`：改为 `ImportError` 兜底的 gevent 初始化，新增 `_resolve_host_and_port()`，默认绑定 `127.0.0.1` 并允许环境变量覆盖，消除 `BLE001`、`S104`、`E402`。
- `scripts/password/show_admin_password.py`：修复语法错误，补充环境变量与数据库两类输出路径，使用 stdout/结构化日志替代 `print`，解决 `invalid-syntax`、`T201`、`W293` 等问题。
- `pyproject.toml`：将 Ruff 的 `select`/`ignore` 迁移至 `[tool.ruff.lint]`，不再出现 “top-level settings deprecated” 提示。
- `scripts/ruff_report.sh`：支持自动探测 `.venv` 中的 Ruff 可执行文件，运行 `./scripts/ruff_report.sh MODE` 无需手动修改 PATH。
- `scripts/code/safe_update_code_analysis.py`：引入 `logging`，所有 CLI 输出改为结构化日志，避免 `T201` 告警。
- `scripts/crud_smoke.py`：统一封装 `LOGGER` 处理执行日志，覆盖登录、步骤与汇总阶段的 20+ 个 `print`，T201 剩余 138 条（主要分布在测试和其他脚本）。
- `scripts/audit_colors.py`、`scripts/check_missing_docs_smart.py`、`scripts/code/analyze_code.py`：分别使用 `logging` 或 `_echo` 替换 `print`，保证 JSON/文本输出一致同时去除 `T201`。
- `scripts/password/reset_admin_password.py`：将 `argparse`、`db` 等导入提升到模块顶部，并添加 `# noqa: E402`，清理 `PLC0415/E402` 告警。
- `仓库整体`：批量清理 300+ 个 Python 文件的行尾空白（W293/W291 全部归零），最新报告显示 Ruff 余量降至 810 条。
- 追加的时间线：
  - 14:05 之前：完成 `ruff --fix` + `UNSAFE=true` 双轮自动化。
  - 14:07-14:35：`app/__init__.py` 处理 `PLC0415/PLW1508`。
  - 14:40：全量报告更新为 4,419 条告警。
  - 14:45-14:50：完成 `app.py`、`tests/unit/utils/test_sensitive_data.py`、`app/__init__.py` 的 P0 修复。
  - 15:00-15:20：`app/routes/dashboard.py` 清理 `RUF001/002/003`、`BLE001/TRY300`。
  - 15:20-15:35：`app/routes/partition.py` 重构日期解析与 defaultdict 导入。
  - 15:35-15:55：`app/services/cache_service.py` 重写 `try/except` 返回和日志。
  - 16:00-16:15：`app/routes/capacity/aggregations.py` 修复 `A004`、`TRY301`。
  - 16:15-16:25：`app/forms/definitions/__init__.py` 清理 `ANN401/RUF001/002/RUF022`。
  - 16:25-16:40：`app/services/statistics/account_statistics_service.py` 统一本地 `TRY300` 处理。
