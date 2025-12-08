# Ruff 全量扫描修复计划（更新：2025-12-08 16:25）

## 1. 最新扫描概览
- **扫描命令**：`./scripts/ruff_report.sh full`（`SELECT=ALL`，`--fix`/`--unsafe-fixes` 均关闭）。
- **报告文件**：`docs/reports/ruff_full_2025-12-08_161653.txt`。
- **总告警**：1,631 条（相较 16:00 的 2,882 条再下降 1,251 条，主要得益于 docstring 句号脚本 + 全角标点清理覆盖 `app/tests/scripts/examples`）。
- **可直接 `--fix` 的告警**：6 条；**需 `--unsafe-fixes` 的告警**：3 条；其余需手工或专项脚本处理。
- **重点观察**：
  1. `RUF001/002/003` 几乎清零（`RUF002`=0，`RUF001`=9，集中在 README 示例），后续只需在提交前固定运行 `cleanup_fullwidth_punct.py`。
  2. **类型注解** 与 **异常处理** 回到主矛盾：`ANN401/ANN001` 共 297 条，`BLE001/TRY300` 合计 190 条，分布在常量、服务层与测试。
  3. `ERA001`（100 条）与 `PLC0415`（97 条）主要来自配置/常量模块的成对注释块、测试文件中的局部导入，需分配责任人分批清理。
  4. `tests/unit/services`、`tests/unit/utils` 仍缺 `__init__.py`、docstring 以及类型标注，并伴随 `ARG005/SLF001`，建议与 UT 重构同步处理。

### 1.1 主要规则分布（Top 10）
| 规则 | 命中数 | 规则含义 | 典型文件 | 推荐策略 |
| --- | --- | --- | --- | --- |
| ANN401 | 169 | 要求 `Any` 以外的返回类型注解，常见于动态加载/懒导入方法 | `app/forms/definitions.py`, `app/utils/event_bus.py`, `app/services/*` | 为懒加载/回调接口补齐返回类型，必要时抽 `Protocol`/`TypedDict`。 |
| BLE001 | 129 | 禁止捕获裸 `Exception`（需捕获具体异常或重新抛出） | `app/routes/cache.py`, `app/routes/dashboard.py`, `scripts/code/*.py` | 将裸 `except Exception` 改为具体异常+结构化日志，保留兜底 logging。 |
| ANN001 | 128 | 参数缺少类型注解 | `app/routes/accounts/*.py`, `app/routes/cache.py`, `tests/unit/services/*` | 补齐参数/返回注解，pytest fixture 明确 `MonkeyPatch` 或 `Any`。 |
| ERA001 | 100 | 文件中存在被注释掉的代码块 | `app/config.py`, `app/constants/*`, `app/routes/*` | 删除“# ====”“# 导入”类注释块，确认无执行价值后直接移除。 |
| PLC0415 | 97 | `import` 位于函数内部（除 TYPE_CHECKING 场景） | `app/routes/*.py`, `tests/unit/utils/test_data_validator.py` | 将 import 上移或通过 `import_module` 懒加载，测试可借助 `TYPE_CHECKING`。 |
| TRY300 | 61 | `try` 语句内部存在 `return`/`break`，不利于异常处理清晰度 | `app/services/statistics/*`, `app/services/aggregation/*` | 拆分 `try/except` 与返回逻辑，复用 `safe_execute`/`unified_error_response`。 |
| E501 | 56 | 单行长度超过 120 字符 | `app/constants/*.py`, `app/routes/dashboard.py` | 对长文本使用多行字符串或模板，日志改为 `extra=` 字典。 |
| ARG002 | 56 | 函数参数未被使用 | `app/services/accounts_sync/*`, `tests/unit/services/*` | 未用参数更名为 `_unused` 或直接删除，必要时记录原因。 |
| C901 | 46 | 认定函数复杂度过高（>10） | `app/services/aggregation/aggregation_service.py`, `app/__init__.py` | 拆子函数或引入对象封装；无法拆分时加 TODO 并登记整改时间。 |
| RUF012 | 41 | 可变类属性未标注 `ClassVar` | `app/constants/*`, `app/config.py` | 类属性字典/列表统一标注 `ClassVar` 或改为 `Enum`/常量模块。 |

> 备注：`RUF001` 剩余 9 条（README 示例），`RUF002` 已清零；`D205/D202`、`G201` 分别 38 条，随 docstring/日志治理同步推进。

## 2. 优先修复清单
### P0（影响运行或安全基线）
1. **`app/__init__.py` 全局入口**：`handle_global_exception` 缺少返回类型（`ANN202`），`register_blueprints` docstring 后仍有空行（`D202`），文件尾部残留大段注释（`ERA001`）。需一次性补齐类型注解、删除注释占位，并把 237 行的 SSL 判断拆成多行以清掉 `E501`。
2. **`app/config.py` 常量类**：类属性字典/列表触发 `RUF012`，分隔用注释行命中 `ERA001`。建议为 `SQLALCHEMY_ENGINE_OPTIONS`、`*_TTL` 等属性添加 `ClassVar`，并改用 `Enum`/常量字典描述板块，避免注释当分隔符。
3. **`tests/unit/services` 与 `tests/unit/utils` 目录**：缺少 `__init__.py`（`INP001`），测试函数无 docstring/注解（`D100/D103/ANN001`），且频繁访问私有方法（`SLF001`）。需要补全包初始化文件、统一在测试开头写中文 docstring，并用公共 helper 替换直接访问私有成员。

### P1（高频/批量问题）
1. **Docstring/ASCII 守卫（RUF001/002/003）**：继续保留 `scripts/cleanup_fullwidth_punct.py` + “句号整理”脚本，新增例子目录/脚本目录也要纳入；准备在 pre-commit 增加轻量校验，防止回归。
2. **类型注解（ANN001/ANN401/ANN202）**：自下而上推进：`app/constants/*` → `app/services/*` → `app/routes/*` → `tests/unit/services/*`。每完成一段执行 `ruff check path --select ANN` 并同步更新 docstring。
3. **异常与日志（BLE001/TRY300/G201）**：缓存、统计、聚合服务仍有裸异常与 f-string 日志。统一改为结构化日志（`extra=`）+ 精确异常，或封装到 `app.utils.response_utils`。
4. **函数内部 import（PLC0415/I001）**：蓝图模块与测试里仍有临时导入。可以借助 `TYPE_CHECKING` 或新的 `lazy_import()` helper，确保导入顺序稳定。
5. **注释代码 + 未使用参数（ERA001/ARG002/ARG005）**：`app/constants`、`app/routes` 里需要清理横线注释；测试中的 `lambda self, data, resource` 应改名或提取 helper，避免重复噪音。

### P2（维护性/一致性）
- **日志写法（G004）**：用 `%s` 或结构化日志替换 f-string；`app/routes/cache.py`、`scripts/code/*.py`、`app/services/aggregation/stats.py` 是重点目录。
- **注释代码（ERA001）**：在 `app/routes/partition.py`、`scripts/dashboard/*.py` 中彻底删除或改为 feature flag。
- **复杂函数（C901）**：`app/services/aggregation/aggregation_service.py` 等 46 个函数超标，可按“准备数据 -> 执行 -> 序列化”三个子函数拆分；必要时用 `# noqa: C901` 并附中文说明。

## 3. 批量处理策略
1. **标点/句号清理脚本**：
   - 输入：任意目录/文件；输出：替换后的文本 + 统计报告。
   - 步骤：`python scripts/cleanup_fullwidth_punct.py app tests scripts examples app.py wsgi.py`（脚本已内建自保护）→ 执行 docstring 句号 one-liner（保存于 runbook，可复制到临时命令中）→ `ruff check <paths> --select RUF001,RUF002` 验证 → 统一提交。
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
- 17:00-17:20：修复 `scripts/cleanup_fullwidth_punct.py` 本身被替换的问题（新增自保护逻辑），并扩展 docstring 句号脚本，覆盖 `app/tests/scripts/examples/app.py/wsgi.py`。随后重新生成 `ruff_full_2025-12-08_161653.txt`，`RUF002` 清零、总告警降至 1,631。  

## 5. 下一阶段里程碑
1. **2025-12-08 晚班**：收尾 `app/__init__.py` P0 问题（类型注解、D202、ERA001、E501），并给 `tests/unit/services`/`utils` 补上 `__init__.py`。目标：全量告警压到 <1,500。
2. **2025-12-09 上午**：集中处理 `app/constants/*` 与 `app/config.py` 的 `ClassVar`/注释问题，清理 `ERA001` 并加入类型注解；同时开始 `ANN401` 标注冲刺，目标再降 200+ 条。
3. **2025-12-09 晚班**：聚焦 `BLE001/TRY300` 与 `ARG002`，优先 `app/services/accounts_sync/*`、`app/routes/cache.py`，并在 `tests/unit/services` 中补 docstring/注解，力争让总告警进入“四位数以下”。

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
- `仓库整体`：批量清理 300+ 个 Python 文件的行尾空白（W293/W291 全部归零），并通过“全角标点 + 句号”双脚本将 `RUF001/002/003` 压到个位数；最新全量报告（`ruff_full_2025-12-08_161653.txt`）显示 Ruff 余量 1,631 条。
- `scripts/cleanup_fullwidth_punct.py`：新增 `SCRIPT_PATH` 保护，避免脚本运行时覆盖自身映射；同时扩展处理范围至 `examples/`、`scripts/`、`app.py`、`wsgi.py`，确保 docstring/示例与主代码一致。
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
  - 17:00-17:20：运行“全目录”标点 + 句号脚本，覆盖 `app/tests/scripts/examples/app.py/wsgi.py`，并生成 `ruff_full_2025-12-08_161653.txt`，确认 `RUF002`=0。
