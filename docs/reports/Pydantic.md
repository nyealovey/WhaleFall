# Pydantic 迁移记录

> 日期: 2026-01-13  
> 目的: 统一 schema/配置读取的类型系统,减少手写解析与漂移

## 1) 背景

- 项目已引入 `pydantic`(v2) 用于 schema/校验等场景。
- `app/settings.py` 原实现为手写环境变量读取/默认值/校验,包含 `os.environ.get(...)` 共 51 处,维护成本高且容易产生口径漂移。

## 2) Settings：`pydantic-settings` `BaseSettings`（可替换 51 处）

### 目标

- 保持 “Settings 单一真源” 不变: 仍由 `app/settings.py::Settings` 负责解析 + 默认值 + 校验。
- 保持对外接口稳定: `Settings.load()` / `Settings.to_flask_config()` 不改调用方式。
- 保持环境变量命名稳定: 不引入新的 env alias / silent fallback（除非明确标注迁移窗口与删除计划）。

### 迁移策略（本仓库约束）

1. **先引入依赖,再替换读取点**
   - 在 `pyproject.toml` 引入 `pydantic-settings` 依赖并更新 `uv.lock`。
2. **先“替换读取”,不改变业务语义**
   - 将 `app/settings.py` 中所有 `os.environ.get(...)` 改为 `BaseSettings` 字段读取,通过 `validation_alias` 显式绑定 env 名称。
   - 动态默认值/跨字段规则仍集中在 `Settings` 内部,通过 `model_validator` 统一处理。
3. **`.env` 加载策略保持旧行为**
   - 仍由 `python-dotenv` 的 `load_dotenv(override=False)` 负责加载本地 `.env`。
   - 原因: 保持历史语义 —— “环境变量即使为空字符串也应阻止 `.env` 注入同名变量”。

### 已完成

- 依赖引入:
  - `pydantic-settings>=2.2,<3`（由 `uv` resolve 到 `2.12.0`）
- 代码迁移:
  - `app/settings.py`：移除 `os.environ.get(...)` 共 51 处,改为 `BaseSettings` 字段读取 + `validation_alias`。
- 验证:
  - `uv run pytest -m unit tests/unit/test_settings_database_url_policy.py`
  - `uv run pytest -m unit tests/unit/test_settings_password_encryption_key_validation.py`

### 约束与注意事项

- 禁止在下游新增 `payload.get("new") or payload.get("old")` 互兜底链；如必须兼容旧字段,只能在边界层做一次 canonicalization。
- `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` / `REMEMBER_COOKIE_DURATION_SECONDS` 属于已移除的 legacy env:
  - 若检测到存在(非空),必须 fail-fast 提示迁移到新 env。
