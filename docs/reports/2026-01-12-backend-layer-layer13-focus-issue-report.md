# 后端分层标准问题报告（layer/13篇聚焦审计，2026-01-12）
> 状态: Draft  
> 创建: 2026-01-12  
> 更新: 2026-01-12  
> 范围: `docs/Obsidian/standards/backend/layer/*.md`(13 篇) + 代码对照(`app/**`)  
> 本次重点: 新增层(Infra/Schemas/Settings)落地扫描 + 回归检查 API/Constants/Utils 漂移

## 0. 结论摘要（TL;DR）

- layer 标准现为 13 篇（新增 `infra-layer-standards.md`, `schemas-layer-standards.md`, `settings-layer-standards.md`；并扩展 API 标准 scope 至 `app/api/**`）。
- 门禁/基线（本次复跑）：
  - `./scripts/ci/pyright-guard.sh`：diagnostics 0
  - `./scripts/ci/api-layer-guard.sh`：通过（API 未发现 models/routes 依赖或 DB/query）
  - `./scripts/ci/forms-layer-guard.sh`：通过
  - `./scripts/ci/tasks-layer-guard.sh`：通过
  - `./scripts/ci/services-repository-enforcement-guard.sh`：命中 0（允许减少，禁止新增）
  - `./scripts/ci/db-session-write-boundary-guard.sh`：通过（commit allowlist 命中 28，均在允许位置）
  - `./.venv/bin/ruff check --select PLR2004 --output-format concise app`：0 errors
- 仍需处理的“标准/实现漂移”（按影响排序）：
  - Utils 层 DB 访问：`app/utils/database_batch_manager.py` 直用 `db.session`，与 utils-layer-standards “无 DB 依赖”冲突。
- 本轮已按决策落地：
  - API 层 query 参数解析：已统一迁移到 `reqparse.RequestParser` + `@ns.expect(parser)`（新增 `app/api/v1/resources/query_parsers.py`）。
  - Schemas 层与 Models 解耦：schemas 不再 import models，阈值下沉到 `app/core/constants/validation_limits.py`。
  - Constants 层 helper methods：按方案 B 下沉到 `app/utils/**`，constants 仅保留值/枚举/静态映射。
  - 魔法数字（`PLR2004`）：已清零（0 errors），阈值集中到 `app/core/constants/validation_limits.py`，形状/索引常量保留为模块内常量。

## 1. 与 2026-01-11 报告相比的已完成项（口径对齐）

- 1.1 `layer/README.md` 依赖图方向已按“方案 A”修正。
- 1.2 `constants-layer-standards.md` 依赖规则已收窄：允许 `app.core.constants.*` 同层互相 import，并禁止业务层依赖。
- 1.3 `types-layer-standards.md` 的“无逻辑”口径已通过迁移落地：`parse_payload` 与 converters 已迁移到 `app/utils/**`，并删除 `app/core/types/request_payload.py` 与 `app/core/types/converters.py`。
- API 标准 scope 已扩展到 `app/api/**`，纳入 `app/api/__init__.py` 注册入口语义。

## 2. 代码扫描发现（按 13 层标准）

### 2.1 API 层（`app/api/**`）

- 门禁通过：未发现 `models/routes` 依赖、未发现 `db.session` 或 `.query`（`./scripts/ci/api-layer-guard.sh`，已扩展覆盖 `app/api/**`）。
- 方案 A 已落地：query 参数统一使用 `flask_restx.reqparse.RequestParser` 并配套 `@ns.expect(parser)`。
  - 复用入口：`app/api/v1/resources/query_parsers.py`（`new_parser` / `bool_with_default` / `split_comma_separated`）。
  - 口径：允许保留 `request.args.to_dict(flat=False)` 作为审计快照，但 endpoint 不再用 `request.args.get/getlist` 读取具体参数。

### 2.2 Schemas 层（`app/schemas/**`）

- 已移除反向依赖 models：`app/schemas/**` 不再 import `app.models.*`。
- 风险：
  - schemas 对 models 的依赖容易带来循环引用/隐式耦合；
  - “校验口径”被 model 层牵引，导致 schema 难以独立复用与单测。
- 落地方式：
  - 将校验阈值下沉到 `app/core/constants/validation_limits.py`；
  - schema 仅 import constants/types/utils，保持可独立复用与单测。

### 2.3 Infra 层（`app/infra/**` + `app/scheduler.py`）

- 与写操作边界口径一致（允许 commit/rollback 作为入口）：
  - `app/infra/route_safety.py`：成功后 commit，异常 rollback，并集中处理异常转换与日志字段。
  - `app/infra/logging/queue_worker.py`：worker 入口提交/回滚（位于 commit allowlist 允许范围内）。
  - `app/scheduler.py`：env flag + 文件锁控制单实例，配置 I/O 失败隔离。
- 备注：
  - `app/scheduler.py` 仍是“大文件多职责”，即使标准已覆盖，仍建议后续按 infra package 拆分（收益：可读性/可测性/减少防御分支散落）。

### 2.4 Settings/Config 层（`app/settings.py`）

- 现状与标准对齐：
  - env alias：`app/settings.py:160`（`JWT_REFRESH_TOKEN_EXPIRES` / `JWT_REFRESH_TOKEN_EXPIRES_SECONDS`）
  - dev fallback：secret key 缺失时 debug 生成随机值，production fail-fast
  - 生产关键密钥校验：`PASSWORD_ENCRYPTION_KEY` presence + Fernet key 格式校验
- 建议：为 env alias 补充“迁移窗口/删除计划”的注释或日志提示，避免永久兼容链。

### 2.5 Utils 层（`app/utils/**`）

- 违反标准：`app/utils/database_batch_manager.py` 直依赖 `from app import db` 并使用 `db.session.*`（例如 `app/utils/database_batch_manager.py:13` / `app/utils/database_batch_manager.py:151`）。
- 建议（方向建议）：
  - 迁移到允许 DB 的层：`app/infra/**`（偏事务入口/失败隔离）或 `app/repositories/common/**`（偏数据访问复用）；
  - 或重构为“纯批次队列 + 显式注入 session/flush/commit”，但需避免引入隐式事务边界。

### 2.6 Constants 层（`app/core/constants/**`）

- 方案 B 已落地：helper methods 已下沉到 `app/utils/**`，constants 仅保留值/枚举/静态映射（`app/core/constants/**` 内 `def` 0 处）。
  - 示例：`ThemeColors/DatabaseType/UserRole/SyncStatus` 等保留静态映射；对应 “校验/归一化/展示/权限判定” 迁移到 `app/utils/*_utils.py`。
  - 示例：`TimeConstants` 仅保留静态秒数常量，不再提供运行时计算方法。

### 2.7 其他层（Models/Repositories/Services/Tasks/Forms/Types）

- services 层直查库/query：基线已清零（`services-repository-enforcement-guard` 命中 0）。
- tasks 层直查库/直写库：门禁通过（允许 commit/rollback 作为边界入口）。
- forms 层跨层依赖/DB/query：门禁通过。
- types 层：`parse_payload`/converters 已移出；当前 `app/core/types/**` 未发现明显业务函数定义（`rg "^def "` 仅命中 stub `.pyi`）。

## 3. 防御/兼容/回退/适配逻辑清单（聚焦 `or` 兜底）

- 位置：`app/settings.py:160`  
  类型：兼容  
  描述：env var alias，`JWT_REFRESH_TOKEN_EXPIRES` 缺失时 `or` 回退到旧变量 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS`  
  建议：标注迁移窗口并在删除旧变量后移除兼容分支

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

现状：0 errors（已清零）。

落地口径：

- 业务阈值：集中到 `app/core/constants/validation_limits.py`（schemas/settings/API 可复用）。
- 版本号/索引等实现细节：保留为对应模块内具名常量（例如 permissions snapshot v4、adapter 行字段 index）。

## 5. Types：pyright 基线（复跑）

验证命令：

```bash
./scripts/ci/pyright-guard.sh
```

现状：

- `pyright` diagnostics: 0

## 6. 后续建议（按收益排序）

1) 处理 utils 层 DB 漂移：`app/utils/database_batch_manager.py` 迁移到 infra/repository 允许 DB 的层，并在标准中明确其归属。
2) 将错误定义从“Errors 层”调整为 shared kernel：异常类型放在 `app/core/exceptions.py`，异常→HTTP status 映射在 API 边界(`app/api/error_mapping.py`)完成；移除 `app/errors.py` 兼容门面，全仓统一改用 `app.core.exceptions`。
