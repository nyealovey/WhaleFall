# 后端分层 / Shared Kernel 边界审计报告（2026-01-12）

> 依据：`docs/Obsidian/standards/backend/shared-kernel-standards.md` 与 `docs/Obsidian/standards/backend/layer/*.md`  
> 范围：`app/**`（静态审计：import 依赖方向 + 关键门禁模式扫描）  
> 目标：识别**边界跨越**、**职责漂移**、**标准违规**（以 MUST/MUST NOT 为主，补充 SHOULD 风险提示）

## TL;DR（结论摘要）

- **高风险（MUST 违规）**：Routes 层存在多处**未使用 `safe_route_call`** 的路由处理函数，绕过统一兜底/日志/事务边界。
- **高风险（MUST 违规）**：Settings/Config 存在多处**在非 `app/settings.py` 中读取环境变量**（`os.getenv/os.environ.get`），造成配置口径漂移与隐式降级风险。
- **中风险（漂移/耦合）**：Repository/Service 内出现对 `app/infra/route_safety.py` 的复用（`log_with_context`），导致“边界工具”在多层扩散、耦合 request/actor 语义。
- **低风险（OK）**：Shared Kernel（`app/core/**`）整体符合“只依赖标准库与 shared primitives”的依赖约束，未发现反向依赖外层。

## 审计方法（简述）

1. **依赖方向扫描（import）**
   - Shared Kernel：检查 `app/core/**` 是否依赖 `app.(api|routes|tasks|services|repositories|models|forms|views|settings|infra|schemas).*`。
   - 各层：按标准文件的“允许/禁止依赖”扫描典型反向 import（例如 routes→repositories、services→routes/api、repositories→services 等）。
2. **门禁模式扫描（关键词）**
   - Routes/API：`safe_route_call(` 覆盖情况、`db.session`/`Model.query` 是否出现。
   - Settings：`os.getenv/os.environ.get` 是否只出现在 `app/settings.py`（以及标准允许的入口脚本）。
   - Repository：`first_or_404/get_or_404`、`HTTPException` 语义渗透风险（作为“漂移”提示项）。

> 说明：该报告为静态审计，不包含运行期行为验证；若要落地整改，建议按“建议优先级”逐项补测试与灰度验证。

## 发现清单（按优先级）

### 1) Routes 层：未统一使用 `safe_route_call`（MUST）

依据：`docs/Obsidian/standards/backend/layer/routes-layer-standards.md`（“统一兜底(safe_route_call)”章节）

| 严重度 | 位置 | 问题类型 | 描述 | 建议 |
|---|---|---|---|---|
| 高 | `app/routes/main.py:16` | 违规（兜底缺失） | 路由函数未通过 `safe_route_call(...)` 包裹（`index/about/favicon/apple_touch_icon/chrome_devtools` 均同类问题）。 | 为每个 route handler 添加 `safe_route_call`，补齐 `module/action/public_error/context`；若确认是“纯静态/无 DB/无失败语义”的端点，也应在标准中明确例外范围并统一执行。 |
| 高 | `app/routes/auth.py:39` | 违规（兜底缺失 + 逻辑漂移） | `login()` 未使用 `safe_route_call`；同时函数体较长，部分编排逻辑仍在 Routes 层（标准建议 routes “薄”）。 | 1) 用 `safe_route_call` 统一兜底；2) 将登录编排进一步下沉到 `app/services/auth/login_service.py`（已存在 `build_login_result`/`login`）。 |
| 高 | `app/routes/auth.py:122` | 违规（兜底缺失） | `logout()` 未使用 `safe_route_call`。 | 同上：统一兜底。 |
| 高 | `app/routes/partition.py:17` | 违规（兜底缺失） | `partitions_page()` 未使用 `safe_route_call`。 | 同上：统一兜底。 |
| 高 | `app/routes/scheduler.py:17` | 违规（兜底缺失） | `index()` 未使用 `safe_route_call`。 | 同上：统一兜底。 |
| 高 | `app/routes/capacity/instances.py:20` | 违规（兜底缺失） | `list_instances()` 未使用 `safe_route_call`。 | 同上：统一兜底。 |
| 高 | `app/routes/databases/ledgers.py:48` | 违规（兜底缺失） | `list_databases()` 未使用 `safe_route_call`。 | 同上：统一兜底。 |
| 高 | `app/routes/accounts/classifications.py:27` | 违规（兜底缺失） | `index()` 未使用 `safe_route_call`。 | 同上：统一兜底。 |
| 高 | `app/routes/tags/bulk.py:19` | 违规（兜底缺失） | `batch_assign()` 未使用 `safe_route_call`。 | 同上：统一兜底。 |

补充观察（非 MUST、但属于“漂移风险”）：
- `safe_route_call` 当前实现会在成功分支执行 `db.session.commit()`（见 `app/infra/route_safety.py`），即使 GET 页面也会 commit。若团队希望 GET 不触发 commit，需要在 Infra 标准/实现层统一改造（例如按方法/显式标记控制），避免在 Routes 层引入例外分支。

### 2) Settings/Config：环境变量读取散落在非 `app/settings.py`（MUST NOT）

依据：`docs/Obsidian/standards/backend/layer/settings-layer-standards.md`（“单一入口”章节、自查命令）

| 严重度 | 位置 | 问题类型 | 描述 | 建议 |
|---|---|---|---|---|
| 高 | `app/utils/password_crypto_utils.py:50` | 违规（配置漂移 + 隐式降级） | 直接读取 `PASSWORD_ENCRYPTION_KEY`，并在缺失时生成临时 key（会导致“重启后无法解密”）。这类“降级策略”应集中在 Settings 层并受环境(生产/开发)约束。 | 将 `PASSWORD_ENCRYPTION_KEY` 纳入 `app/settings.py`（解析 + 默认值策略 + 生产 fail-fast/开发可降级 + 结构化 warning），并通过显式参数注入 `PasswordManager`。 |
| 高 | `app/services/connection_adapters/adapters/oracle_adapter.py:65` | 违规（配置漂移） | 直接读取 `ORACLE_CLIENT_LIB_DIR`（Oracle 客户端路径）。 | 将 Oracle 客户端配置收敛到 `app/settings.py`（可支持 alias/默认值/校验），在连接适配器初始化时注入配置。 |
| 高 | `app/services/connection_adapters/adapters/oracle_adapter.py:69` | 违规（配置漂移） | 直接读取 `ORACLE_HOME`（Oracle 客户端路径）。 | 同上。 |
| 高 | `app/scheduler.py:407` | 违规（配置漂移） | 直接读取 `ENABLE_SCHEDULER`。虽语义属于 Infra，但按 Settings 标准仍应由 `Settings` 统一承载并由 `create_app` 传入。 | 将开关纳入 `Settings`（例如 `enable_scheduler: bool`），避免“模块内部读 env”。 |
| 高 | `app/scheduler.py:415` | 违规（配置漂移） | 直接读取 `SERVER_SOFTWARE` 用于 gunicorn 判定。 | 同上：由 Settings 统一读取/封装（或将“进程角色判定”封装到 infra 并只消费 Settings）。 |
| 高 | `app/scheduler.py:423` | 违规（配置漂移） | 直接读取 `FLASK_RUN_FROM_CLI`/`WERKZEUG_RUN_MAIN` 用于 reloader 判定。 | 同上。 |

### 3) Repository/Infra：`log_with_context` 扩散到 Repository（漂移/耦合）

依据：
- `docs/Obsidian/standards/backend/layer/infra-layer-standards.md`（Infra 作为“包装器/适配器/门面”，避免反向耦合业务层）
- `docs/Obsidian/standards/backend/layer/repository-layer-standards.md`（Repository 的“职责边界”与“依赖规则”）

| 严重度 | 位置 | 问题类型 | 描述 | 建议 |
|---|---|---|---|---|
| 中 | `app/repositories/ledgers/accounts_ledger_repository.py:26` | 漂移（层间耦合） | Repository 引入 `app.infra.route_safety.log_with_context`（该模块含 `flask_login.current_user` 等 request/actor 语义）。这会让 Repository 层间接受到“HTTP 边界工具”的影响，增加循环依赖与复用成本。 | 将“结构化日志拼装”抽到 `app/utils/**`（或新增 `app/infra/logging/**` 但不绑定 route_safety），Repository 仅依赖纯日志工具；或在 repository 内使用 `app.utils.structlog_config` 的 logger 并显式携带 context。 |

### 4) Service 层：`db.session.rollback()` 分散出现（漂移/审计点）

依据：
- `docs/Obsidian/standards/backend/layer/services-layer-standards.md`（“事务边界”章节：事务边界需一致、可审计）
- `docs/Obsidian/standards/backend/layer/infra-layer-standards.md`（失败隔离/兜底应集中在 Infra，可审计）

| 严重度 | 位置 | 问题类型 | 描述 | 建议 |
|---|---|---|---|---|
| 中 | `app/services/dashboard/dashboard_overview_service.py:31` | 漂移（事务边界分散） | Read service 在入口主动 `db.session.rollback()`；同时在异常分支再次 rollback。该行为会影响外层事务语义，且与 `safe_route_call` 的统一事务边界存在重叠。 | 明确“为什么需要 rollback”：若是为清理上一轮异常导致的 session 状态，优先让事务边界入口处理；如确需在 service 内处理，建议用 `begin_nested()` 做局部隔离并补单测覆盖。 |
| 中 | `app/services/statistics/log_statistics_service.py:44` | 漂移（事务边界分散） | 同类：service 内主动 rollback。 | 同上。 |
| 中 | `app/services/tags/tag_write_service.py:78` | 漂移（重复 rollback） | 捕获 `SQLAlchemyError` 后 rollback 并转为 `ValidationError`；而上层若使用 `safe_route_call` 仍会 rollback（重复/分散）。 | 统一策略：要么由边界入口 rollback（推荐），要么在 service 内用 savepoint/局部回滚并清晰文档化；避免“每个 service 自己决定 rollback”。 |

### 5) App bootstrap：登录 user_loader 直接使用 `Model.query`（需评估）

依据：分层依赖方向与“Repository 统一数据访问”的总体原则（见 `docs/Obsidian/standards/backend/layer/README.md`）

| 严重度 | 位置 | 问题类型 | 描述 | 建议 |
|---|---|---|---|---|
| 低 | `app/__init__.py:275` | 漂移（数据访问入口分散） | `login_manager.user_loader` 直接 `user_model.query.get(...)`。这是框架集成点，通常可接受，但会使数据访问入口不一致。 | 评估是否改为 `UsersRepository().get_by_id(...)` 或抽 `UserLoader` adapter；如保留现状，建议在代码中写清“集成点例外”的理由与边界。 |

## Shared Kernel 审计结果（OK）

依据：`docs/Obsidian/standards/backend/shared-kernel-standards.md`

- `app/core/**` 未发现对外层模块的依赖（未检出 `app.(api|routes|tasks|services|repositories|models|forms|views|settings|infra|schemas).*`）。
- `app/core/constants/**` 未发现对 `app.core.types/**` 或 `app.core.exceptions` 的依赖，符合“constants 最底层纯净”约束。
- `app/core/types/**` 未发现对 `app.core.exceptions` 或 `app.models.*`（含 `TYPE_CHECKING`）的依赖，符合 Types 层约束。

## 建议优先级（行动项）

1. **P0：补齐 Routes `safe_route_call` 覆盖**（先解决 MUST 违规，统一兜底与事务边界）
2. **P0：把 env var 读取收敛到 `app/settings.py`**（先解决 MUST NOT，消除配置漂移与隐式降级）
3. **P1：收敛 `log_with_context` 的归属**（从 `route_safety` 拆出通用日志 helper，降低 infra 在多层扩散）
4. **P1：统一 Service 层 rollback 策略**（避免事务边界分散，减少“局部兜底”引发的副作用）

