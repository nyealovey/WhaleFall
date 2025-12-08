# Ruff 全量扫描修复文档（2025-12-08）

## 1. 扫描概览
- **扫描命令**：`./scripts/ruff_report.sh full`（默认配置，未开启 `--fix`），生成时间 2025-12-08 13:15:17。
- **命中总数**：12,558 条（其中 4,276 条可直接通过 `ruff --fix` 解决，另有 3,748 条需启用 `--unsafe-fixes` 才能自动处理）。
- **报告位置**：`docs/reports/ruff_full_2025-12-08_131517.txt`。
- **主因分类**（按命中次数排序）：

| 规则 | 命中次数 | 典型含义 | 推荐处理策略 |
| --- | --- | --- | --- |
| D400 | 1,451 | Docstring 首行缺少句号 | 批量补充“。”；可用 `ruff --fix`。
| D415 | 1,451 | Docstring 首行缺少标点结尾 | 与 D400 同步处理。
| Q000 | 1,187 | 需要统一为双引号 | 可通过 `ruff --fix --select Q000` 全局修复。
| D413 | 1,087 | Docstring 结尾缺少空行 | 运行 `ruff --fix --select D4`，留意 hand-written blocks。
| W293 | 721 | 空行包含空白字符 | 执行 `ruff --fix --select W293`，必要时人工核查。
| UP006 | 371 | `typing` 别名应改为内置泛型（Python ≥3.9） | `ruff --fix --select UP006`，逐个确认兼容性。
| EM101 | 198 | `raise Exception(...)` 过于宽泛 | 手动替换为语义明确的异常类型。
| D212 | 162 | Docstring 摘要需与引号同一行 | 建议在编辑器中批改；避免多语言 docstring 移位。
| T201 | 159 | 禁止生产代码中使用 `print` | 替换为结构化日志或测试断言。
| F401 | 157 | 未使用的导入 | 以模块为单位清理，避免误删 side-effect 导入。

> 小技巧：先使用 `ruff --fix --select Q000,W293,D4,UP006` 处理机械化问题，可显著降低剩余任务量。

## 2. 优先级划分

### P0（阻塞运行 / 语法错误）
1. **`scripts/password/show_admin_password.py`**：第 36 行 `if env_password:` 缺少缩进体，直接导致 `invalid-syntax`。必须先补全逻辑（例如打印提示或回退到数据库密码），否则脚本无法运行。
2. **`wsgi.py`**：`monkey.patch_all()` 包裹的 bare `except Exception` 会吞掉启动错误，同时 `E402` 指出导入顺序问题；需整理模块顶部结构，保证 gevent 可选导入且保留日志。
3. **`app.py` / `app/__init__.py`**：大量 `PLC0415`（函数内部 import）与 `PLW1508`（env 默认值类型）若不修复会导致 Ruff 持续失败，也暗含配置隐患。

### P1（安全 / 合规）
1. **S104**：`app.py`、`wsgi.py` 对外暴露 `0.0.0.0`，可在非 Docker 场景触发安全基线。建议在开发模式下由环境变量控制 host，或在配置中添加“仅开发环境允许”的注释并关闭该规则。
2. **S608 / S110 / S105**（SQL 注入、`open` 权限等）零星出现，需逐条确认。如果确实安全，可在局部添加 `# noqa` 并解释原因。
3. **T201**：全局的 `print`（尤其在脚本和服务层）需要替换为结构化日志，以满足“禁止 `print`”的规范要求。

### P2（代码风格 / 维护性）
- **Docstring 套餐（D200/D202/D205/D400/D413 等）**：集中在 `app/`、`tests/` 与 `scripts/`，修复时遵循“单行摘要 + 详细描述 + Args/Returns/Raises”结构。
- **字符串风格（Q000/RUF001/RUF002/RUF003）**：确保中文全角标点在 docstring 中使用场景明确；若需保留全角字符，应在 docstring 后补充一句解释，并加 `# noqa: RUF00x`。
- **导入顺序（PLC0415/E402/I001）**：将“函数内部 import”提升到模块顶部，与现有 `isort` 规则保持一致；若 import 仅在调试路径使用，可改为 `typing.TYPE_CHECKING` 或懒加载函数。
- **环境变量类型（PLW1508）**：任何 `os.getenv(..., 3600)` 都应传入字符串：`os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600")`，再调用 `int()`。
- **日志格式（G004/G201）**：使用 `logger.info("🌐 访问地址: http://%s:%s", host, port)` 或结构化日志 API。

## 3. 模块级修复指南

### 3.1 入口与部署
- **`app.py`**：
  - 统一 docstring 格式；`main()` 的 docstring 按“主函数。”结尾。
  - 将所有 `from app.xxx import` 提升到文件顶部，函数内部使用 of? (no). Need restructure.
  - 用 `logger.info("🌐 访问地址: http://%s:%s", host, port)` 替换 f-string 日志；`debug` 变量也要通过 `%s` 或结构化日志打印。
  - 对 `FLASK_PORT` 默认值使用字符串：`port = int(os.environ.get("FLASK_PORT", "5001"))`。
- **`app/__init__.py`**：
  - 大部分 docstring 命中 D400/D413；逐段补“。”，并确保摘要后空行。
  - 将 `configure_structlog` 等 import 移至文件顶部，若存在递归引用，可使用延迟导入 + 注释说明。
  - 将多处 `os.getenv(..., 3600)` 默认值包裹字符串。
  - 替换 `logger.warning` 的中文句号为英文 `,` 或在 docstring 中使用解释性 `# noqa: RUF001`。
  - 把 `detect_protocol()` 中的多重条件合并 (`SIM114`)，并用双引号。
- **`wsgi.py`**：
  - 将 `monkey.patch_all()` 放入 `try/except ImportError`，不要捕获 `Exception`。
  - 屏蔽 `S104` 的方式：通过环境变量控制 host，或在 `wsgi.py` 中引用 `FLASK_HOST`。

### 3.2 ORM / 表单 / 服务层
- **表单定义**（如 `app/forms/definitions/*.py`）：大量 F401（未使用导入）。逐文件确认是否为未来使用；若确实不需要，直接删除。若 import 用作类型提示，转移到 `if TYPE_CHECKING` 块。
- **模型与服务**：
  - `app/models/unified_log.py`、`app/services/aggregation/aggregation_service.py` 命中 F811（变量重定义）。将内部 `from datetime import timedelta` 替换为现有导入或重命名。
  - `app/services/cache_service.py` 等多个文件出现未使用的 `datetime`/`DatabaseType` 导入，需要清理。
  - `app/services/aggregation` 模块 `C901`（函数复杂度）计 46 次，后续可结合重构或添加 `# noqa` 并解释原因。

### 3.3 路由与蓝图
- 典型命中项：F401、T201、G004、Q000。
- 逐个蓝图（`app/routes/accounts/*.py`, `app/routes/capacity/*.py`）移除 `current_user`、`db` 等未使用导入，或在调试时 log 这些变量。
- 在 `app/routes/accounts/sync.py` 中还有多处 `flash`/`redirect` 未使用，可删除或补充逻辑。

### 3.4 脚本与工具
- **`scripts/password/reset_admin_password.py`**：
  - 清理空行空白（W293）。
  - 将单引号替换为双引号（Q000）。
  - `argparse` 描述中的全角括号命中 `RUF001`，用英文括号代替。
- **`scripts/password/show_admin_password.py`**：
  - 修复 if/else 空块；建议在 `if env_password:` 中打印提示“当前使用环境变量密码”，`else` 则回退至数据库哈希比较。
  - 加入结构化日志替换 `print`。

### 3.5 测试与示例
- **`tests/conftest.py`**：触发 `INP001`，在 `tests/` 根目录创建空的 `__init__.py`。
- **测试文件**：
  - 多个 `monkeypatch` 参数未使用（ARG001/ARG005）。若 fixture 未使用，可移除形参或添加 `del monkeypatch`。
  - Docstring 同样需补“。”。
- **`examples/`**：大量 F401/F841 与 Q000，可通过 `ruff --fix` 扫描后人工确认。

## 4. 建议的修复流程
1. **集中处理可自动修复的规则**（建议顺序）：
   1. `ruff --fix --select Q000,W293,D4`（引号、空白、docstring 结构）。
   2. `ruff --fix --select UP006,UP035,UP045,UP037`（类型提示升级）。
   3. `ruff --fix --select I001,PLC0415`（导入顺序）——若担心影响运行，可局部执行。
2. **手动处理高优问题**：
   - 修复语法/逻辑错误（`scripts/password/show_admin_password.py`、`wsgi.py` 等）。
   - 清理未使用导入（F401）、未使用变量（F841）。
   - 替换 `print` 为日志（T201）。
   - 安全性规则（S104/S608/S110）逐条评估后，选择修复或加 `noqa` + 注释。
3. **更新 Ruff 配置**：
   - 将 `[tool.ruff]` 中的 `select`/`ignore` 移动到 `[tool.ruff.lint]`，消除“top-level 设置已弃用”的警告。
   - 根据团队需要决定是否启用 `extend-ignore`（例如 `COM812`、`ISC001`）。
4. **回归验证**：
   - 运行 `./scripts/ruff_report.sh quick` 确认无语法/导入类错误。
   - 执行 `./scripts/ruff_report.sh full`，确保报告清零。
   - 补充 `pytest -m unit` / `make test` 以验证行为。

## 5. 责任分配建议
| 模块 | 建议负责人 | 备注 |
| --- | --- | --- |
| 入口与配置（`app.py`, `app/__init__.py`, `wsgi.py`） | 平台基础组 | 涉及安全与日志策略，需整体把控。
| 表单 & 服务 | 数据建模组 | D 类 docstring + F401 + 复杂度，需要了解业务语义。
| 路由层 | 前后端协同 | 需确保移除导入后不影响模板上下文。
| 脚本与工具 | 运维工具组 | 修复 password 脚本 & 环境检查脚本。
| 测试与示例 | QA 团队 | 统一 docstring，处理未使用 fixture。

## 6. 风险与注意事项
- **Docstring 语言**：根据仓库规范，新增/修改 docstring 必须使用中文。英文原文若需保留，请追加中文解释。
- **颜色/样式限制**：在修复前端代码（若涉及）时严禁手写颜色值；若 Ruff 报告引导你到 CSS/JS，请同步检查颜色规范。
- **命名脚本检查**：完成大规模重命名/导入调整后，务必运行 `./scripts/refactor_naming.sh --dry-run`，确保没有触发命名守卫。

## 7. 验证清单
1. `uv sync --group dev --active`（确保 Ruff/Black 已安装）。
2. `./scripts/ruff_report.sh quick` → 0 错误。
3. `./scripts/ruff_report.sh full` → 0 错误并更新报告。
4. `pytest -m unit`、`pytest -m integration`（视改动范围选择）。
5. 更新 `docs/reports/` 中的修复记录（可在本文件后追加“处理结果”章节）。

## 8. 近期修复进展（2025-12-08）
- `app.py`：完成入口重构，移除对外绑定 `0.0.0.0`，引入 `_ensure_admin_account`、`_load_runtime_config`、`_log_startup_instructions`，并统一使用结构化日志，已清除 `S104`、`G004`、`PLC0415` 等告警。
- `wsgi.py`：改为 `ImportError` 兜底的 gevent 初始化，新增 `_resolve_host_and_port()`，默认绑定 `127.0.0.1` 并允许环境变量覆盖，消除 `BLE001`、`S104`、`E402`。
- `scripts/password/show_admin_password.py`：修复语法错误，补充环境变量与数据库两类输出路径，使用 stdout/结构化日志替代 `print`，解决 `invalid-syntax`、`T201`、`W293` 等问题。
- `pyproject.toml`：将 Ruff 的 `select`/`ignore` 迁移至 `[tool.ruff.lint]`，不再出现 “top-level settings deprecated” 提示。
- `scripts/ruff_report.sh`：支持自动探测 `.venv` 中的 Ruff 可执行文件，运行 `./scripts/ruff_report.sh MODE` 无需手动修改 PATH。
- `scripts/code/safe_update_code_analysis.py`：引入 `logging`，所有 CLI 输出改为结构化日志，避免 `T201` 告警。
- `scripts/crud_smoke.py`：统一封装 `LOGGER` 处理执行日志，覆盖登录、步骤与汇总阶段的 20+ 个 `print`，T201 剩余 138 条（主要分布在测试和其他脚本）。
- `scripts/audit_colors.py`、`scripts/check_missing_docs_smart.py`、`scripts/code/analyze_code.py`：分别使用 `logging` 或 `_echo` 替换 `print`，保证 JSON/文本输出一致同时去除 `T201`。
- `scripts/password/reset_admin_password.py`：将 `argparse`、`db` 等导入提升到模块顶部，并添加 `# noqa: E402`，清理 `PLC0415/E402` 告警。
- `仓库整体`：批量清理 300+ 个 Python 文件的行尾空白（W293/W291 全部归零），最新报告 `docs/reports/ruff_full_2025-12-08_133747.txt`/`134056.txt` 显示 Ruff 余量降至 810 条，主要集中在 `PLC0415`、`T201`（CLI/测试）、`TRY30x`、`ARG00x`、`PLW1508` 等类别。

---
本修复文档整理自 `docs/reports/ruff_full_2025-12-08_131517.txt`，后续若重新运行 Ruff，请同步更新命中统计和优先级列表。
