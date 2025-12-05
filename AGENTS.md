# 仓库使用规范

## 项目结构与模块组织
Flask 服务位于 `app/`，拆分为若干聚焦模块：`api/` 负责服务端点，`routes/` 对应蓝图，`models/` 存放 ORM 实体，`utils/` 提供通用工具，`tasks/` 保存异步任务，定时任务位于 `scheduler.py`。客户端模板与静态资源分别位于 `templates/` 与 `static/`。测试目录在 `tests/unit/` 和 `tests/integration/`，并共享 `tests/conftest.py` 中的基线数据。脚本与其他支撑资产放在 `scripts/`、`migrations/`、`sql/`、`docs/`。环境预设文件（如 `env.development`）位于仓库根目录；敏感信息只写入未跟踪的 `.env`。

## 构建、测试与开发命令
运行 `make install` 同步 Python 依赖（优先使用 `uv sync`，退而求其次执行 `pip install -r requirements.txt`）。`make dev start` 启动 PostgreSQL 与 Redis 组合，`make dev start-flask` 启动 API，`make dev stop` 停止并清理。验证阶段使用 `make test`（或 `make dev test`）运行 pytest；通过 `pytest -k pattern` 或 `-m unit` 过滤测试集。质量门控执行 `make quality`，`make format` 调用 `black` 与 `isort`。

## 编码风格与命名约定
统一使用四个空格缩进，单行不超过 120 个字符。将 `app` 视为一方导入根目录，依赖 `black`、`isort`、`ruff` 完成格式化与静态检查。模块、函数、变量采用 `snake_case`，类名使用 `CapWords`，蓝图名称需与对应的路由模块保持一致。尽量使用结构化日志工具而非 `print`。

- **Google 风格对齐**  
  - Python 代码遵循 Google 风格：docstring 必须包含单行摘要、详细描述以及 `Args/Returns/Raises` 区块；模块/函数/类/常量分别使用 `snake_case`、`CapWords`、`CAPS_WITH_UNDER`；所有对外函数需保持类型注解；注释使用中英文皆可但需清晰具体。  
  - JavaScript 代码遵循相同理念：文件/变量使用 `camelCase`/`kebab-case`，类名 `UpperCamelCase`，常量 `CONSTANT_CASE`；函数命名前缀用动词；注释描述行为而非实现细节；避免魔法字符串和匈牙利命名。  
  - 以上要求直接落在命名脚本与质量门禁中，一旦偏离需立即修复。

- **命名规范守卫（强制要求）**
  - **模块/文件**: 使用完整单词加 `snake_case`，禁止缩写，如 `database_aggregations.py`、`instance_aggregations.py`。服务目录 `app/services/form_service/` 内文件名称不得再使用 `_form_service` 后缀，必须改为 `resource_service.py`、`password_service.py` 等。
  - **路由/视图**: 蓝图函数必须以动词短语命名，例如 `list_instances`、`get_user`；禁止 `api_list`、`statistics_api` 之类前后缀。任何 `_api`、`api_` 前后缀均视为违规。
  - **函数**: 不允许带实现细节的后缀，如 `_optimized`；聚合函数需使用单数：`get_database_aggregations`、`get_instance_aggregations`，不得出现 `databases_aggregations` 等复数嵌套。
  - **前端资源**: JS/CSS/目录一律使用 kebab-case（`capacity-stats/database-aggregations.js`），禁止新增下划线命名。
- **响应式限制**: 当前交互仅面向桌面端，禁止为筛选搜索栏或其他页面元素新增移动端 @media 适配样式。
- **筛选卡片列宽**: 所有通过 `filter_card` 渲染的搜索框与下拉框必须使用统一的 `col-md-2 col-12` 栅格组合，不得再在 CSS 中写死像素宽度；若确有特殊布局需求，应在局部添加 utility class，并在评审中说明原因。
- **最近违规示例**: 历史上 `app/routes/users.py` 曾使用 `api_get_users()` 之类命名；此类 `_api`/`api_` 前缀一经发现立即驳回。
- **色彩管控**: 禁止在 CSS/JS/HTML 中手写颜色值（HEX/RGB/RGBA 等），必须使用 `app/static/css/variables.css` 中的 token 或 `ColorTokens` 工具提供的接口；PR 审查需检查“无硬编码颜色”项，发现违反直接驳回。
- **提交前检查**: 在提交任何涉及命名/结构的改动前，必须运行 `./scripts/refactor_naming.sh --dry-run`，确认输出为“无需要替换的内容”；若脚本提示命名违规，需先修复再提交。
- **代码评审清单**: PR 审查必须包含“命名规范”检查项；若发现新命名与指南不符，直接要求作者对齐或运行脚本修正。
- **CI/质量门禁**: 若在 CI 中新增命名检测（建议扩展 `make quality`），脚本输出告警视为阻断条件，直至命名与文档一致。

## 语言约定与 Agent 协作

- **注释与文档**: 新增或修改的 docstring、函数注释、JSDoc 等文字说明必须使用中文，除外部协议或 RFC 要求英文时可在首句注明原因后使用英文。若已有英文说明且需保留，请同时补充中文解释。
- **交付物/回复**: 在与同事或自动化 Agent 协作时（包括命令输出说明、代码评审意见等），默认使用中文回答，并确保术语一致、语义明确。
- **脚本/工具输出**: 自研脚本在打印提示时应优先输出中文说明，必要时可以“中文 + 原始英文关键词”形式帮助定位。
- **工具使用**: 读写仓库文件时优先通过 `filesystem-mcp` 提供的接口完成操作，除非该通道暂不可用；若需要临时改用其他方式，需在回复中说明原因。

## 测试规范
为测试用例添加 `@pytest.mark.unit`、`integration` 或 `slow` 标记，便于执行 `pytest -m "unit"` 等选择性测试。集成测试需在执行 `make dev start` 后对 Docker 组合运行，并确保夹具对外部系统无残留影响。关键代码路径建议执行 `pytest --cov=app --cov-report=term-missing`，关注覆盖率缺口。

## 提交与 Pull Request 规范
提交主题使用 `fix:`、`feat:`、`refactor:` 或简洁中文动词前缀，长度不超过 72 个字符。引用相关 issue，记录验证步骤（例如 `make test`、手工流程），模板变更附上界面截图。PR 描述需突出配置改动、提示新增端口或 API，并确保 `.env`、`instance/` 等敏感文件不纳入版本控制。

## 安全与配置建议
通过本地 `.env` 文件加载环境变量，不要提交密钥。若调整入口流量或服务拓扑，请同步更新 `nginx/` 配置。发布前确认 `migrations/` 中的迁移及 `sql/` 数据与 `env.production` 指向的环境保持一致。
