---
title: Bootstrap/Entrypoint 启动规范
aliases:
  - bootstrap-entrypoint-standards
tags:
  - standards
  - standards/backend
status: active
enforcement: gate
created: 2026-01-12
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/__init__.py`, `app.py`, `wsgi.py`, `app/api/__init__.py`"
related:
  - "[[standards/backend/configuration-and-secrets]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/task-and-scheduler]]"
  - "[[standards/backend/layer/README|后端分层标准]]"
  - "[[standards/backend/layer/api-layer-standards]]"
---

# Bootstrap/Entrypoint 启动规范

> [!note] 说明
> Bootstrap/Entrypoint 的目标是“可控组装”：把应用创建、扩展初始化、蓝图注册、日志与调度器启动收敛到少量入口，避免把副作用散落到各层导致启动口径漂移与循环依赖。

## 目的

- 固化应用创建与初始化顺序，避免开发/生产/测试入口各自拼装导致行为差异。
- 收敛启动期副作用（启动调度器、patch gevent、初始化扩展），让失败策略可审计且可回滚。
- 明确 API 注册入口的语义归属：`app/api/__init__.py` 属于 API 层，不单独作为一层。

## 适用范围

- Flask App Factory：`app/__init__.py::create_app`
- 本地开发入口：`app.py`
- WSGI 入口：`wsgi.py`
- API blueprint 注册入口：`app/api/__init__.py::register_api_blueprints`（语义属于 API 层）

## 规则(MUST/SHOULD/MAY)

### 1) 单一应用工厂（强约束）

- MUST: 统一使用 `app/__init__.py::create_app` 创建 Flask app。
- MUST: 测试/脚本需要创建 app 时，必须通过 `create_app(init_scheduler_on_start=False)` 关闭调度器副作用。
- MUST NOT: 在 `app.py`/`wsgi.py` 内重复初始化扩展或注册蓝图（入口只负责调用工厂并启动 server）。

### 2) 启动期副作用与导入约束

- MUST: import 阶段禁止做 DB 查询、网络访问、写文件等重副作用。
- SHOULD: 为避免循环导入，允许使用惰性加载（例如 `importlib.import_module` 或在函数体内 import），但必须保持导入路径稳定。
- MUST: 若存在“容错继续启动”的行为（例如调度器初始化失败不阻塞启动），必须记录结构化日志并确保错误可观测。

### 3) 配置入口（Settings）

- MUST: 配置解析/默认值/校验收敛到 `app/settings.py::Settings`，遵循 [[standards/backend/configuration-and-secrets|配置与密钥]]。
- MAY: `app.py`/`wsgi.py` 使用 `os.environ.setdefault(...)` 写入少量运行默认值（仅限入口脚本，且仅允许下列 allowlist）。
- MUST: `os.environ.setdefault(...)` 仅用于“运行期识别/启动工具”类变量，不得用于业务语义、功能开关或安全边界变量。
- MUST NOT: 对任何敏感/密钥/连接信息使用 `setdefault`（例如 `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, `PASSWORD_ENCRYPTION_KEY` 等）。
- MUST NOT: 对任何会影响业务行为的 feature flag 使用 `setdefault`（例如 `ENABLE_SCHEDULER` 等），必须由部署注入或 Settings 默认值策略决定。
- SHOULD: 如需新增 allowlist 项，必须在评审中说明“为何必须在入口写默认值”与“为何不应放到 Settings 默认值”，并更新本文档的 allowlist。
- MUST NOT: 在业务模块中散落 `os.environ.get(...)` 决策业务逻辑。

> [!important] `os.environ.setdefault(...)` allowlist（可执行判据）
> 仅允许在 `app.py`/`wsgi.py` 中出现以下变量的 `setdefault`，其余一律视为越界：
>
> - `FLASK_APP`
>   - 默认值: `"app"`（`app.py` / `wsgi.py`）
>   - 理由: 仅用于 Flask 启动工具定位应用入口，不承载业务语义。
> - `FLASK_ENV`
>   - 默认值: `"development"`（`app.py`），`"production"`（`wsgi.py`）
>   - 理由: 仅用于“入口环境默认值”，让 `Settings(environment=...)` 有稳定来源；`setdefault` 不会覆盖部署显式注入的环境变量。

### 4) API 注册入口的层归属

- MUST: `app/api/__init__.py` 作为 API blueprint 注册入口，语义属于 API 层（不建议为它单开一层）。
- MUST: API 注册入口只负责 “组装并 register blueprint”，不得承载业务逻辑或数据库访问。
- SHOULD: API 标准 scope 覆盖 `app/api/**`（含注册入口），详见 [[standards/backend/layer/api-layer-standards]]。

### 5) 日志与错误处理

- MUST: 全局异常必须通过统一错误处理器映射为统一封套，遵循 [[standards/backend/error-message-schema-unification|错误消息字段统一]]。
- SHOULD: 启动期关键路径（配置、蓝图注册、调度器启动）写结构化日志，便于定位启动失败原因。

### 6) 调度器启动策略

- MUST: 调度器启动由 `create_app(init_scheduler_on_start=...)` 控制，并遵循 [[standards/backend/task-and-scheduler|任务与调度(APScheduler)]] 的启停约束。
- MUST: 当调度器初始化失败时不得阻塞应用启动（必须记录错误日志并继续返回 app）。

## 门禁/检查方式

- 评审检查:
  - 入口脚本是否只做“组装与启动”，没有把业务逻辑/查库塞进启动流程？
  - 是否存在 import-time 的重副作用？
  - API blueprint 注册入口是否保持薄且无业务/DB？
- 自查命令(示例):

```bash
rg -n "create_app\\(|register_api_blueprints\\(" app/__init__.py app.py wsgi.py app/api/__init__.py
rg -n "os\\.environ\\.setdefault\\(" app.py wsgi.py
# 如出现新增 setdefault，请对照 allowlist（仅允许 FLASK_APP/FLASK_ENV）
rg -n "os\\.environ\\.setdefault\\(" app | rg -v "^(app\\.py|wsgi\\.py):"
```

## 变更历史

- 2026-01-12: 新增启动规范, 明确 `create_app` 为单一工厂入口, 并澄清 API 注册入口的层归属.
- 2026-01-13: 为 `os.environ.setdefault(...)` 增加 allowlist 与禁止项, 让入口默认值策略可审计/可执行检查.
