---
title: Settings/Config 配置层编写规范
aliases:
  - settings-layer-standards
  - config-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
enforcement: gate
created: 2026-01-12
updated: 2026-01-12
owner: WhaleFall Team
scope: "`app/settings.py` 统一配置读取与校验"
related:
  - "[[standards/backend/configuration-and-secrets]]"
  - "[[standards/backend/bootstrap-and-entrypoint]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/layer/README|后端分层标准]]"
---

# Settings/Config 配置层编写规范

> [!note] 说明
> Settings/Config 层的职责是“集中读取环境变量、提供默认值并校验”，输出稳定的 `Settings` 对象供 `create_app` 消费。它不是业务层，不负责业务规则与数据访问。

## 目的

- 把 `os.environ.get/os.getenv` 的读取、默认值与校验收敛到单一入口，避免各层重复解析导致口径漂移。
- 明确生产环境的关键配置缺失时必须 fail-fast（抛出 `ValueError`），避免“半启动/隐式降级”。
- 将兼容/回退策略显式化并可审计，尤其是 env var alias 与 `or` 兜底链。

## 适用范围

- `app/settings.py`（包含 `Settings.load()`、解析函数、默认值常量、跨字段校验与 `to_flask_config()`）。

## 规则(MUST/SHOULD/MAY)

### 1) 单一入口（强约束）

- MUST: 新增/修改配置项必须落在 `app/settings.py` 的 `Settings`（解析 + 默认值 + 校验 + 导出）。
- MUST: `create_app(settings=...)` 只消费 `Settings`（或其 `to_flask_config()`），禁止在 `create_app` 内直接读环境变量。
- MUST NOT: 在业务模块中新增 `os.environ.get(...)`（入口脚本 `app.py/wsgi.py` 设置运行默认值除外，详见 [[standards/backend/bootstrap-and-entrypoint]]）。

### 2) 类型、默认值与校验

- MUST: 每个配置项必须有明确类型与默认值策略（默认值常量/显式 `None`/运行期生成）。
- MUST: 生产环境缺失关键配置必须 fail-fast（抛出 `ValueError`），避免 silent fallback。
- SHOULD: 解析函数分组并保持纯净（只依赖标准库/必要第三方库），例如：
  - `_load_database_settings(...)`
  - `_load_cache_settings(...)`
  - `_load_proxy_fix_settings(...)`
- SHOULD: `Settings._validate()` 只做跨字段校验与统一错误聚合，错误信息面向运维可读。

### 3) 兼容/回退/兜底（重点：`or` 约束）

- MUST: 仅在“语义明确的缺省”场景使用 `or` 兜底：
  - env var alias：`os.environ.get("NEW") or os.environ.get("OLD")`
  - 可选字典/元组入参：`options.get("x") or {}`
- MUST NOT: 对可能合法为 `0/""/[]` 的业务值使用 `or` 兜底（会覆盖合法值），应使用 `is None` 或显式判断空白字符串。
- SHOULD: env var alias 必须在文档或代码注释标注“旧变量名/迁移窗口/删除计划”，迁移完成后删除兼容入口，避免长期保留。
- SHOULD: 当存在“开发环境降级”（如未提供 `DATABASE_URL` 回退 SQLite、未提供 `SECRET_KEY/JWT_SECRET_KEY` 生成随机值），必须记录结构化 warning 且禁止在生产环境触发。

### 4) 敏感信息处理

- MUST NOT: 把密钥/口令/令牌/连接串原文写入日志。
- SHOULD: 需要排障时只记录“变量名/是否存在/来源/长度”等非敏感信息，遵循 [[standards/backend/sensitive-data-handling]]。

### 5) 导出到 Flask 配置

- MUST: 通过 `Settings.to_flask_config()` 输出 `app.config` 所需键值，避免在多处重复 mapping。
- SHOULD: `to_flask_config()` 仅做 key 映射与轻量派生值（例如 `preferred_url_scheme`），禁止做 I/O 或复杂逻辑。

### 6) 依赖规则

允许依赖:

- MUST: 标准库（`os`, `dataclasses`, `pathlib` 等）
- MAY: `python-dotenv`（本地 `.env` 支持）
- MAY: 必要的第三方加解密/校验库（例如 `cryptography` 用于 key 格式校验）

禁止依赖:

- MUST NOT: `app.models.*`, `app.services.*`, `app.repositories.*`, `app.routes.*`, `app.api.*`
- MUST NOT: 读写数据库、网络请求等重副作用

## 门禁/检查方式

- 评审检查:
  - 是否把 env 读取散落到业务模块？
  - 是否出现 `or` 兜底覆盖合法空值？
  - 是否在日志中输出了敏感信息？
- 自查命令(示例):

```bash
rg -n "os\\.(environ\\.get|getenv)\\(" app | rg -v "app/settings\\.py|app\\.py|wsgi\\.py"
```

## 变更历史

- 2026-01-12: 新增 Settings/Config 层标准, 覆盖 `app/settings.py`.

