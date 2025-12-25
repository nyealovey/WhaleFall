# 仓库使用规范

## 1. 项目结构
- Flask 服务代码位于 `app/`，拆分为 `api/`（服务端点）、`routes/`（蓝图）、`models/`（ORM 实体）、`utils/`（通用工具）、`tasks/`（异步任务），定时任务集中在 `app/scheduler.py`。
- 客户端模板与静态资源分别放在 `templates/`、`static/`；测试在 `tests/unit/`、`tests/integration/`，共享 `tests/conftest.py` 基线数据。
- 辅助资产位于 `scripts/`、`migrations/`、`sql/`、`docs/`。环境预设文件（如 `env.development`）存放在仓库根目录，敏感值仅写入未跟踪的 `.env`。

## 2. 构建、测试与开发命令
- 运行 `make install` 同步依赖（优先 `uv sync`，必要时回退 `pip install -r requirements.txt`）。
- `make dev start` 启动 PostgreSQL+Redis；`make dev start-flask` 启动 API；`make dev stop` 负责回收资源。
- 质量命令：`make format`（black+isort）、`make quality`（静态分析门禁）、`make test`/`make dev test`（pytest）。可用 `pytest -k pattern`、`pytest -m unit` 做精确集。

## 3. 编码与命名规范
### 3.1 通用准则
- 统一四空格缩进，单行 ≤120 字符，将 `app` 视作一方导入根。
- 默认依赖 structured logging，禁止在新代码中使用 `print` 输出。
- Docstring/注释使用 Google 风格结构，且必须使用中文：首行摘要 + 空行 + 详细描述 + `Args/Returns/Raises`。外部协议/RFC 需英文时，首句说明原因再写英文，并补充中文解释。
- Python 模块/函数/变量使用 `snake_case`，类使用 `CapWords`，常量使用 `CAPS_WITH_UNDER`。JavaScript 文件/变量使用 `camelCase`/`kebab-case`，类使用 `UpperCamelCase`，常量 `CONSTANT_CASE`，函数名称需动词开头。

### 3.2 命名守卫
- 模块/文件须用完整单词 `snake_case`，禁止缩写；`app/services/form_service/` 下的文件名不得包含 `_form_service` 后缀，应使用 `resource_service.py`、`password_service.py` 等具体名称。
- 蓝图函数必须是动词短语（例如 `list_instances`、`get_user`），严禁 `_api`、`api_` 及类似后缀/前缀。
- 函数命名禁止包含实现细节（如 `_optimized`）。聚合函数需保持单数（`get_instance_aggregations`），禁止双复数。
- 前端 JS/CSS/目录使用 kebab-case，禁止新增下划线命名。

### 3.3 前端与样式限制
- 当前仅支持桌面端，禁止新增移动端 @media 适配样式。
- 所有 `filter_card` 渲染的搜索/下拉控件必须采用 `col-md-2 col-12` 栅格，禁止写死像素宽度；若要突破，需局部 utility class 并在评审说明。
- 色彩统一由 `app/static/css/variables.css` 或 ColorTokens 输出，禁止手写 HEX/RGB/RGBA。

### 3.4 类型治理
- 共享的 TypedDict/TypeAlias/Protocol 必须集中于 `app/types/`（已拆分 `structures.py`、`resources.py`、`accounts.py`、`query_protocols.py` 等），禁止在业务模块中临时声明 `dict[str, Any]` 结构。
- 新增资源/查询/远端账户结构需先在 `app/types/` 建立别名（示例：`RemoteAccount`、`PermissionSnapshot`、`QueryProtocol`、`StructlogEventDict`），再在模块中导入复用，避免重复定义。
- 引入新类型后需运行 `ruff check <files> --select ANN,ARG,RUF012` 与 Pyright，确保 `Any` 不回退，并在 PR 描述中说明新增别名。

### 3.5 路由异常模板
- Flask 路由必须通过 `app/utils/route_safety.py` 中的 `safe_route_call` 执行业务闭包，禁止再写 `try/except Exception` + `log_error` 的模式；`module/action/context` 参数必须覆盖关键维度，方便结构化追踪。
- 声明 `expected_exceptions` 以透传可控的业务错误（如 `ValidationError`、`NotFoundError`），其余异常交由 helper 统一包装为 `SystemError`。
- 批量、导入/导出、删除等需要事务保障的接口要同时配合 `with db.session.begin()` 等上下文，确保失败自动回滚并只记录一条失败日志。参见 `app/routes/files.py`、`app/routes/instances/manage.py` 的最新实现。

## 4. Ruff 基线（新代码强制）
- 每次提交前运行 `./scripts/ruff_report.sh style`，并对本次改动的文件执行 `ruff check <files>`。若进行了命名调整，仍需优先运行 `./scripts/refactor_naming.sh --dry-run`。
- 新增或修改的代码不得引入新的 Ruff 告警；若文件存在遗留问题，必须确保新行符合规范，并在 PR 中说明遗留告警由专项修复。
- 重点规则：
  - **类型注解**（`ANN001/002/003/201/202/204/206/401`）：新增/修改的函数、`@classmethod`、上下文管理方法必须补齐参数与返回类型，避免 `Any`。
  - **异常与日志**（`BLE001/TRY300/TRY301/S110/S112/SIM105/TRY401/G004`）：禁止捕获裸 `Exception`、`try/except/pass`、在 `try` 中直接 `return`、使用 f-string 记录日志或在 `logger.exception` 中拼接 `{exc}`。
  - **导入与状态**（`PLC0415/I001/PLW0603`）：不可在函数体内 import、导入需保持 isort 顺序、禁止 `global` 写入；如需惰性加载，请封装 helper 并注释原因。
  - **布尔参数与路径**（`FBT001/002/003`、`PTH107/109/110/118/120/123/208`）：新增接口要用关键字或枚举取代布尔位置参数，文件与路径操作统一使用 `pathlib.Path` API。
  - **文档与文本**（`D100/103/104/107/202/205/400/413/415`、`RUF001/002/003`）：所有新 docstring 采用中文 Google 模板，摘要以句号结尾，禁止使用全角标点。
- 验证顺序：完成开发 → `./scripts/refactor_naming.sh --dry-run` → `./scripts/ruff_report.sh style`（或 `ruff check <files>`）→ 需要时执行 `pytest -m unit`。若 Ruff 仍对改动文件报错，视为阻断，禁止合并。

## 4.1 Pyright 基线（新代码强制）
- 新增或修改的 Python 代码必须运行 `npx pyright --warnings <文件或目录>`，确保 **0 error / 0 warning**。
- 禁止新增 `# pyright: ignore[...]` 等抑制标记；如确需豁免，需在 PR 描述中说明原因和后续清理计划。
- 若引入/调整本地 stub，须同步更新 `pyrightconfig.json` 的 `extraPaths` / `typeshedPath`，并保留 `app/py.typed`。
- 推荐快捷命令：
  - 仅检查改动文件：`git diff --name-only --diff-filter=AM | grep '\.py$' | xargs npx pyright --warnings`
  - 子目录快速检查：`npx pyright --warnings app/routes/<子目录>`
- 与 Ruff 一致：若 Pyright 对改动文件仍报错视为阻断，禁止合并。

## 4.2 ESLint 基线（前端/静态资源）
- 前端与静态资源改动必须确保 `npm run lint`（或 `make quality` 中的 ESLint 阶段）无 error/warning；如需加速迭代，可先对改动文件执行 `npx eslint <files>`，但合并前需跑全量。
- 禁止新增 `eslint-disable` 类抑制；如确因第三方调用无法改写，可使用单行 `// eslint-disable-next-line <rule>`，并用中文注释说明原因和后续计划。
- 对安全规则 `security/detect-object-injection` 优先采用键白名单、`Object.hasOwn`/固定映射、受控枚举等方式消除警告，避免以关闭规则或宽泛的 `/* global */` 方式绕过。
- 缺失的全局依赖应优先改为显式 `import/require`；仅当运行环境确无打包链路时，才在文件顶部使用 `/* global XXX */` 并补充初始化兜底。
- 处理 no-undef/no-unused-vars 时，确认是否为必要签名参数；无用变量直接删除，回调占位使用前导下划线命名（如 `_event`）。
- 变更公共 util 或全局挂载后需回归关键页面（scheduler、instances、tags 等）基础交互，防止静态检查通过但运行期全局缺失。

## 4.3 结果结构基线（`error/message` 漂移门禁）
- 禁止新增 `result.get("error") or result.get("message")` / `result.get("message") or result.get("error")` 这类互兜底链；统一规范见 `docs/standards/backend/error-message-schema-unification.md`。
- 门禁脚本：`./scripts/code_review/error_message_drift_guard.sh`（允许减少命中，禁止新增命中）；baseline 文件：`scripts/code_review/baselines/error_message_drift.txt`。
- 仅在“确已清理完漂移命中”或“新增命中已评审同意”的前提下，才允许执行 `./scripts/code_review/error_message_drift_guard.sh --update-baseline` 更新 baseline，并在 PR 描述中说明原因。

## 5. 语言约定与 Agent 协作
- 新增或修改的 docstring、注释、JSDoc 必须使用中文（RFC/协议除外，需先说明再给英文，并补中文解释）。
- 与同事或自动化 Agent 协作（回复、命令说明、评审意见等）默认使用中文，术语保持一致。
- 自研脚本输出应优先中文提示，可采用“中文 + 英文关键词”帮助定位。
- 读写仓库文件时优先通过 `filesystem-mcp` 工具；若临时无法使用需在回复中说明原因。

## 6. 测试规范
- 测试用例应打上 `@pytest.mark.unit`、`integration` 或 `slow`，方便 `pytest -m "unit"` 等选择性执行。
- 集成测试需在 `make dev start` 后运行 Docker 组合，确保夹具不会污染外部系统。
- 关键路径建议执行 `pytest --cov=app --cov-report=term-missing`，关注覆盖率缺口。

## 7. 提交与 Pull Request
- 提交主题使用 `fix:`、`feat:`、`refactor:` 或简洁中文动词前缀，长度 ≤72 字符；关联 issue 并记录验证步骤（如 `make test`）。
- 模板或界面变更需附截图。PR 描述需强调配置改动、端口/API 变更，并确认 `.env`、`instance/` 等敏感文件未纳入版本控制。
- 在 PR 中显式说明 Ruff 告警状态，如遗留问题未触及需明确理由。

## 8. 安全与配置
- 通过本地 `.env` 注入环境变量，禁止提交密钥或密码；`S105/S106` 报警需给出合理豁免或改用配置。
- 调整入口流量或拓扑时同步更新 `nginx/` 配置。
- 发布前确认 `migrations/` 与 `sql/` 数据与 `env.example` 指向环境保持一致。

## 9. Ruff 修复作业特别约束
- 修复现有 Ruff 告警时，禁止引入新的 Ruff 告警或降级已有抑制；改动后必须对所修改文件再次运行 `ruff check <files>` 并确认 0 报错。
- 处理循环导入或背景线程问题时，不得将导入移入函数体（违背 `PLC0415`）；如需惰性导入，请封装单独 helper 并解释原因。
- 调度器/后台线程执行任务时必须在可用的 Flask `app.app_context()` 内运行，避免后续出现 `Working outside of application context`；若复用现有 `current_app`，需先检查 `has_app_context()`，否则创建新应用后再包裹上下文。
- 应急提交后，如同一文件再次修改，仍需重复上述 Ruff 校验流程，避免“修复引发新告警”的回归。
