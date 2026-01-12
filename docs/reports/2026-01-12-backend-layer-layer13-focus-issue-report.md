# 后端分层标准问题报告（layer/13 篇 + shared kernel 聚焦审计，2026-01-12）
> 状态: Draft  
> 创建: 2026-01-12  
> 更新: 2026-01-12  
> 范围: `docs/Obsidian/standards/backend/layer/*.md`(13 篇) + `docs/Obsidian/standards/backend/shared-kernel-standards.md` + 代码对照(`app/**`)  
> 本次重点: Shared Kernel 合规扫描 + Infra/Schemas/Settings 落地回归 + API/Constants/Utils 漂移检查

## 0. 结论摘要（TL;DR）

- 标准覆盖现状：layer 标准 13 篇 + shared kernel 标准 1 篇（覆盖 `app/core/**` 的职责与依赖边界）。
- 门禁/基线（本次复跑）：
  - `./scripts/ci/pyright-guard.sh`：diagnostics 0
  - `./scripts/ci/api-layer-guard.sh`：通过（API 未发现 models/routes 依赖或 DB/query）
  - `./scripts/ci/forms-layer-guard.sh`：通过
  - `./scripts/ci/tasks-layer-guard.sh`：通过
  - `./scripts/ci/services-repository-enforcement-guard.sh`：命中 0（允许减少，禁止新增）
  - `./scripts/ci/db-session-write-boundary-guard.sh`：通过（commit allowlist 命中 28，均在允许位置）
  - `./.venv/bin/ruff check --select PLR2004 --output-format concise app`：All checks passed
- 本次已处理的“标准/实现漂移”（按影响排序）：
  1) Shared Kernel 漂移：将框架相关 typing 从 `app/core/**` 迁出到 `app/infra/flask_typing.py`，`app/core/**` 不再运行时依赖 Flask/扩展。
  2) Utils 层 DB 漂移：将 `DatabaseBatchManager` 从 `app/utils/database_batch_manager.py` 迁移到 `app/infra/database_batch_manager.py`，utils 恢复为“无 DB 依赖”。
  3) Settings env alias：移除 `*_SECONDS` 历史别名入口（旧变量存在时直接 fail-fast），避免长期兼容链。
- 本轮口径已落地/保持一致：
  - API 层 query 参数解析：统一迁移到 `reqparse.RequestParser` + `@ns.expect(parser)`（`app/api/v1/resources/query_parsers.py`）。
  - Schemas 层不再 import models；阈值集中到 `app/core/constants/validation_limits.py`。
  - Constants 层不再承载 helper methods（`app/core/constants/**` 内 `def` 0 处）。

## 1. 范围与口径变化（本次复跑）

- 将 `docs/Obsidian/standards/backend/shared-kernel-standards.md` 纳入审计范围：`app/core/**`（exceptions + constants + types）需要满足 “不依赖 HTTP/DB/框架、外层做适配” 的 shared kernel 口径。
- layer 标准依赖方向以 `docs/Obsidian/standards/backend/layer/README.md` 的依赖图为准：`app/core/**` 为内核，不应被外层能力反向牵引出循环依赖或框架耦合。

## 2. 代码扫描发现（按 13 层 + shared kernel 标准）

### 2.1 API 层（`app/api/**`）

- 门禁通过：未发现 `models/routes` 依赖、未发现 `db.session` 或 `.query`（`./scripts/ci/api-layer-guard.sh` 覆盖 `app/api/**`）。
- Query 参数统一入口：`app/api/v1/resources/query_parsers.py`（`new_parser` / `bool_with_default` / `split_comma_separated`），降低 endpoint 内重复解析与兜底链。

### 2.2 Schemas 层（`app/schemas/**`）

- 未发现反向依赖 models：`app/schemas/**` 不 import `app.models.*`（符合 schemas-layer-standards）。
- 兼容/规范化逻辑集中在 schema（示例：`cleaned or None`、颜色字段回退等），避免 service 中散落 `data.get(...) or ...` 的字段兼容链。

### 2.3 Infra 层（`app/infra/**` + `app/scheduler.py`）

- 与写操作边界口径一致：允许 `commit/rollback` 作为事务边界入口；异常集中转换/记录并保持可观测性字段（符合 infra-layer-standards + 写操作边界标准）。
- 备注：`app/scheduler.py` 仍是“大文件多职责”，虽口径覆盖但可读性与可测性收益仍建议后续拆分到 `app/infra/**`。

### 2.4 Settings/Config 层（`app/settings.py`）

- env 变量口径：仅保留 `JWT_REFRESH_TOKEN_EXPIRES`、`REMEMBER_COOKIE_DURATION`（秒）；历史别名 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` / `REMEMBER_COOKIE_DURATION_SECONDS` 已移除（检测到会 fail-fast）。
- dev fallback / production fail-fast：密钥缺失时 debug 生成随机值，production 抛出 `ValueError`（符合 settings-layer-standards）。

### 2.5 Shared Kernel（`app/core/**`）

- Shared kernel 合规：`app/core/**` 未发现运行时依赖 Flask/扩展/边界工具；框架相关 typing 已迁移到 `app/infra/flask_typing.py`。

### 2.6 Utils 层（`app/utils/**`）

- 已修复：`DatabaseBatchManager` 已迁移到 `app/infra/database_batch_manager.py`，utils 恢复为“无 DB 依赖”。

### 2.7 Constants 层（`app/core/constants/**`）

- constants 仅保留值/枚举/静态映射（`app/core/constants/**` 内 `def` 0 处），业务阈值集中到 `app/core/constants/validation_limits.py`（schemas/settings/API 可复用）。

### 2.8 其他层（Models/Repositories/Services/Tasks/Forms/Types）

- services 层直查库/query：基线已清零（`./scripts/ci/services-repository-enforcement-guard.sh` 命中 0）。
- tasks 层 query/execute/add/delete/merge/flush：门禁通过（`./scripts/ci/tasks-layer-guard.sh`）。
- forms/views 跨层依赖/DB/query：门禁通过（`./scripts/ci/forms-layer-guard.sh`）。

## 3. 防御/兼容/回退/适配逻辑清单（聚焦 `or` 兜底）

- 位置：`app/infra/route_safety.py:111`  
  类型：防御  
  描述：`options.get("log_event") or ...` 提供缺省日志事件兜底，避免调用方漏传导致日志不可读  
  建议：保持在 infra 入口集中兜底，不要在各 endpoint 自己拼兜底链

- 位置：`app/infra/route_safety.py:117`  
  类型：防御  
  描述：`func_kwargs or {}` / `func_args or ()`，确保调用形状稳定  
  建议：若调用方已统一传入非空容器，可逐步收敛减少兜底分支

- 位置：`app/scheduler.py:584`  
  类型：防御  
  描述：`yaml.safe_load(...) or {}`，配置文件为空/解析为 None 时回退空 dict，避免 `config.get(...)` 抛错  
  建议：如要强约束配置格式，引入显式 schema 校验并明确“何时 fail-fast、何时可降级”

- 位置：`app/api/v1/resources/query_parsers.py:40`  
  类型：防御  
  描述：`(item or "").split(",")`，兼容 tags 传参为重复参数/逗号分隔/空值等形态，集中兜底避免各 endpoint 重复实现  
  建议：保持“兜底逻辑集中在 API parsing 层”，不要在各 endpoint 内写重复兜底链

- 位置：`app/schemas/tags.py:59`  
  类型：兼容  
  描述：`cleaned or (fallback or "primary")`，把空白颜色值规范化为默认色，避免上层散落“空值回退”处理  
  建议：确认空字符串是否应视为缺省；如是，建议补单测覆盖并在迁移期结束后删除不必要的回退形态

- 位置：`app/core/exceptions.py:63`  
  类型：防御  
  描述：`message_key = message_key or ...`（以及 `extra or {}`），确保异常语义字段完整且调用形状稳定  
  建议：保持兜底集中在 shared kernel 的异常基类，避免上层重复实现默认值链

- 位置：`app/services/accounts_sync/inventory_manager.py:95`  
  类型：兼容  
  描述：`item.get("db_type") or instance.db_type`，缺失字段回退实例默认 db_type  
  建议：确认空串是否应视为“缺失”；如需区分空串/未提供，改为 `is None` 判断

- 位置：`app/services/capacity/current_aggregation_service.py:41`  
  类型：回退  
  描述：`status = (result.get("status") or "completed").lower()`，缺失状态回退为 completed  
  建议：确认“缺失 status”是否真实表示 completed；否则应改为显式失败并给出可观测错误

## 4. 魔法数字扫描（`PLR2004`）

扫描命令：

```bash
./.venv/bin/ruff check --select PLR2004 --output-format concise app
```

现状：All checks passed（0 errors）。

落地口径：

- 业务阈值：集中到 `app/core/constants/validation_limits.py`（schemas/settings/API 可复用）。
- 版本号/索引等实现细节：保留为对应模块内具名常量（例如 adapter 行字段 index）。

## 5. Types：pyright 基线（复跑）

验证命令：

```bash
./scripts/ci/pyright-guard.sh
```

现状：

- `pyright` diagnostics: 0

## 6. 后续建议（按收益排序）

1) 收敛框架 typing 的导入路径：routes/app bootstrap 建议统一从 `app/infra/flask_typing.py` 引用，避免散落 `flask.typing` 与跨层 re-export。
2) 同步文档口径：`docs/Obsidian/reference/config/environment-variables.md` 中移除历史别名说明，确保“单一变量名”不再产生配置漂移。
