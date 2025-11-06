# 仓库使用规范

## 项目结构与模块组织
Flask 服务位于 `app/`，拆分为若干聚焦模块：`api/` 负责服务端点，`routes/` 对应蓝图，`models/` 存放 ORM 实体，`utils/` 提供通用工具，`tasks/` 保存异步任务，定时任务位于 `scheduler.py`。客户端模板与静态资源分别位于 `templates/` 与 `static/`。测试目录在 `tests/unit/` 和 `tests/integration/`，并共享 `tests/conftest.py` 中的基线数据。脚本与其他支撑资产放在 `scripts/`、`migrations/`、`sql/`、`docs/`。环境预设文件（如 `env.development`）位于仓库根目录；敏感信息只写入未跟踪的 `.env`。

## 构建、测试与开发命令
运行 `make install` 同步 Python 依赖（优先使用 `uv sync`，退而求其次执行 `pip install -r requirements.txt`）。`make dev start` 启动 PostgreSQL 与 Redis 组合，`make dev start-flask` 启动 API，`make dev stop` 停止并清理。验证阶段使用 `make test`（或 `make dev test`）运行 pytest；通过 `pytest -k pattern` 或 `-m unit` 过滤测试集。质量门控执行 `make quality`，`make format` 调用 `black` 与 `isort`。

## 编码风格与命名约定
统一使用四个空格缩进，单行不超过 120 个字符。将 `app` 视为一方导入根目录，依赖 `black`、`isort`、`ruff` 完成格式化与静态检查。模块、函数、变量采用 `snake_case`，类名使用 `CapWords`，蓝图名称需与对应的路由模块保持一致。尽量使用结构化日志工具而非 `print`。

## 测试规范
为测试用例添加 `@pytest.mark.unit`、`integration` 或 `slow` 标记，便于执行 `pytest -m "unit"` 等选择性测试。集成测试需在执行 `make dev start` 后对 Docker 组合运行，并确保夹具对外部系统无残留影响。关键代码路径建议执行 `pytest --cov=app --cov-report=term-missing`，关注覆盖率缺口。

## 提交与 Pull Request 规范
提交主题使用 `fix:`、`feat:`、`refactor:` 或简洁中文动词前缀，长度不超过 72 个字符。引用相关 issue，记录验证步骤（例如 `make test`、手工流程），模板变更附上界面截图。PR 描述需突出配置改动、提示新增端口或 API，并确保 `.env`、`instance/` 等敏感文件不纳入版本控制。

## 安全与配置建议
通过本地 `.env` 文件加载环境变量，不要提交密钥。若调整入口流量或服务拓扑，请同步更新 `nginx/` 配置。发布前确认 `migrations/` 中的迁移及 `sql/` 数据与 `env.production` 指向的环境保持一致。
