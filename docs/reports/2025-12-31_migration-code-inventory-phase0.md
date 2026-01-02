# 迁移期代码清单（Phase 0 扫描审计）

- **日期**：2025-12-31
- **角色**：迁移清理负责人 + Python/Flask 工程专家 + 风险审计员
- **强约束回顾**：本 Phase 0 **仅扫描与审计**；不修改/删除/重构任何代码与配置（本报告与 artifacts 属于审计产物）

## 1) 扫描范围与过滤规则

### 1.1 必扫目录（已覆盖）

- `app/`
- `scripts/`
- `sql/`
- `tests/unit/`

> 追踪阅读：当上述目录命中引用到 `migrations/`、Alembic/Flask-Migrate 或历史迁移文档时，做了**点对点追踪**（不做全仓无差别扫）。

### 1.2 必扫关键词（已覆盖）

- `migration`, `migrate`, `backfill`, `compat`, `legacy`, `deprecated`
- `feature flag`, `toggle`, `fallback`
- `v1`, `v2`（优先匹配 `/api/v1`、`api_v1`、`_v1`、`v2` 等）

### 1.3 噪声过滤（已执行）

扫描时跳过/忽略：

- 第三方/压缩资源：`app/static/vendor/**`、`**/*.min.js`
- 依赖目录：`**/node_modules/**`

扫描原始输出存档：见 `docs/reports/artifacts/2025-12-31_migration-code-inventory-phase0/`。

## 2) 结论摘要（给后续 Phase 1/2 的“可执行”指引）

### 2.1 本次识别到的“迁移期遗留类型”覆盖情况（满足验收四类）

- **对外 API 方案（当前= `/api/v1`）**：`/api/v1/**` Blueprint + namespaces（见 R001-R024；注意：不是删除候选，仅作为“对外 API 基线”）
- **升级前旧模块式 API（`/<module>/api/**`）已下线**：通过 404 contract tests 固化，避免旧入口被误恢复（见 R065-R080）
- **回填/迁移执行链路**：部署脚本的 `flask db stamp/upgrade`、分区初始化 SQL、一次性 patches（见 R028-R038）
- **迁移开关/feature flag**：`API_V1_DOCS_ENABLED`（见 R041）
- **数据格式兼容点**：权限同步异常兜底、SQLServer 权限查询回退等（见 R051-R052）

### 2.2 风险最高（P0）清单（优先纳入 Phase 1 风险门禁）

- **生产库 Alembic stamp/upgrade 防御链**：`scripts/deploy/update-prod-flask.sh` 的 schema 探测 + stamp 推断（R031-R034）
- **一次性 SQL patches（不可逆 schema/data 变更）**：例如 `DROP COLUMN`（R038）
- **迁移工具链基础设施**：`Flask-Migrate` 初始化与 deploy 脚本强依赖（R026、R034）

### 2.3 可能的“低风险可清理（P2, Yes/Maybe）”候选（建议优先做命中率/引用验证）

- **OpenAPI docs 导出链路**：若团队不再依赖 swagger/openapi，可评估移除（R003，Maybe）
- **旧模块式 API 404 门禁测试**：可长期保留防回归；若要删需补齐替代门禁（R065-R080，Maybe）

## 3) 迁移期代码清单（50+ 逐条可定位）

> 说明：
> - 每条记录均包含：位置、作用、风险级别、依赖方证据、是否可直接删除、删除前置条件与验证。
> - “是否可直接删除”严格按你提供的判定规则：Yes / No / Maybe。

---

## TempRoute（对外 API 路由：当前方案 `/api/v1`）

### R001 — `/api/v1` Blueprint 注册入口（Flask-RESTX 迁移入口）

- 分类：`TempRoute`
- 位置：`app/api/__init__.py:1`；`app/api/__init__.py:15`；`app/api/__init__.py:25`
- 作用：引入版本化 `/api/v1/**`，作为“唯一对外 JSON API”的路由注册入口（迁移期新旧并行的核心开关点）。
- 触发条件：应用启动时 `create_app()` 注册 blueprint；请求路径前缀 `/api/v1/**`。
- 依赖方（证据）：
  - 应用启动调用链：`app/__init__.py:98`（`register_api_blueprints(app, resolved_settings)`）
  - Blueprint 绑定：`app/api/__init__.py:25`（`app.register_blueprint(..., url_prefix="/api/v1")`）
- 风险级别：P0（误删会导致对外 JSON API 核心链路不可用）
- 是否可直接删除：No（仍是当前 API 路由总入口）
- 删除前置条件与验证：
  - 前置条件：明确有替代 API 总入口（例如 `/api/v2/**`）且所有调用方迁移完毕
  - 验证：`./scripts/test/run-unit-tests.sh`（`scripts/test/run-unit-tests.sh:215`）；再结合生产流量/日志确认 `/api/v1/**` 命中为 0
  - 回滚：恢复 blueprint 注册（回滚提交）
- 替代方案/新入口：暂无（仓库内未发现 `/api/v2` 入口，见 artifacts `rg_v1_v2.txt`）
- 删除条件与时间表：以“v2 上线 + v1 命中率为 0 + 对外公告过窗口期”为门槛

### R002 — `/api/v1` Blueprint 构建与 namespaces 装配（Phase 0 目标）

- 分类：`TempRoute`
- 位置：`app/api/v1/__init__.py:38`；`app/api/v1/__init__.py:41`；`app/api/v1/__init__.py:55`
- 作用：创建 `api_v1` blueprint，并将各业务 namespaces 挂载到固定 path（迁移期分阶段上线的装配点）。
- 触发条件：`register_api_blueprints()` 调用 `create_api_v1_blueprint(settings)`；请求 `/api/v1/<namespace path>`。
- 依赖方（证据）：
  - 入口引用：`app/api/__init__.py:22`（导入 `create_api_v1_blueprint`）
  - docs 开关影响 swagger：`app/api/v1/__init__.py:47`（`settings.api_v1_docs_enabled`）
  - namespaces 绑定：`app/api/v1/__init__.py:55` - `app/api/v1/__init__.py:75`
- 风险级别：P0（误删将导致 v1 API 整体不可用）
- 是否可直接删除：No
- 删除前置条件与验证：
  - 前置条件：同 R001（需要明确替代版本/入口）
  - 验证：`./scripts/test/run-unit-tests.sh`；以及（如保留 OpenAPI）`python3 scripts/dev/openapi/export_openapi.py --check`
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R003 — `/api/v1/openapi.json` 导出端点（RestX schema 输出）

- 分类：`TempRoute`
- 位置：`app/api/v1/__init__.py:77`
- 作用：提供 OpenAPI JSON 导出（配合 Swagger UI 或离线导出脚本使用）。
- 触发条件：HTTP GET `/api/v1/openapi.json`。
- 依赖方（证据）：
  - dev 导出脚本默认命中：`scripts/dev/openapi/export_openapi.py:47`（默认 `--endpoint /api/v1/openapi.json`）
  - 文档开关：`app/api/v1/__init__.py:47`（docs_path 由 `API_V1_DOCS_ENABLED` 决定）
- 风险级别：P1（误删会导致 OpenAPI 导出/文档工具链受影响，影响联调与回归）
- 是否可直接删除：Maybe（取决于是否仍需要 OpenAPI/Swagger 能力）
- 删除前置条件与验证：
  - 前置条件：确认团队不再依赖 OpenAPI JSON（或迁移到其他文档生成方式）
  - 验证：`python3 scripts/dev/openapi/export_openapi.py --check`（删除后应同步调整工具链）
  - 回滚：恢复该 route 或恢复导出脚本路径
- 替代方案/新入口：若未来有 `/api/v2/openapi.json`，需同步调整 `export_openapi.py`
- 删除条件与时间表：建议绑定“OpenAPI 导出链路迁移完成”里程碑

### R004 — Auth namespace（Phase 3 全量覆盖 - 认证模块）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/auth.py:1`
- 作用：承载 `/api/v1/auth/**` 的认证相关 JSON API（Phase 3 迁移模块）。
- 触发条件：请求路径 `/api/v1/auth/**`（namespace path="/auth"）。
- 依赖方（证据）：
  - namespace import：`app/api/v1/__init__.py:17`
  - namespace 绑定：`app/api/v1/__init__.py:55`
- 风险级别：P0（误删将导致登录/鉴权核心链路不可用）
- 是否可直接删除：No
- 删除前置条件与验证：需有替代认证 API（例如 v2），并完成客户端迁移；验证跑全量单测与登录相关回归
- 替代方案/新入口：暂无
- 删除条件与时间表：与鉴权迁移窗口期绑定（对外公告 + 流量命中为 0）

### R005 — Health namespace（Phase 0 示例端点）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/health.py:1`
- 作用：提供 `/api/v1/health/*` 健康检查端点（用于运维/探活与错误页验证）。
- 触发条件：请求路径 `/api/v1/health/**`（namespace path="/health"）。
- 依赖方（证据）：
  - namespace import：`app/api/v1/__init__.py:26`
  - namespace 绑定：`app/api/v1/__init__.py:56`
  - 运维脚本依赖：`scripts/ops/nginx/update-error-pages.sh:81`（请求 `/api/v1/health/basic`）
- 风险级别：P0（误删可能导致探活失败，引发发布/运维链路不可用）
- 是否可直接删除：No
- 删除前置条件与验证：除非替换新的健康检查 API 且所有运维脚本/探活配置完成迁移；验证包含部署脚本健康检查
- 替代方案/新入口：无
- 删除条件与时间表：和探活配置迁移、Nginx/部署脚本更新绑定

### R006 — Common/options namespace（Phase 3 全量覆盖 - 通用数据模块）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/common.py:1`
- 作用：通用选项/基础数据的 v1 API（Phase 3 覆盖）。
- 触发条件：请求 `/api/v1/common/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:20`（import）；`app/api/v1/__init__.py:57`（add_namespace）
- 风险级别：P1（误删导致相关前端筛选/下拉数据获取失败）
- 是否可直接删除：No
- 删除前置条件与验证：同 v1->v2 迁移门槛；验证相关页面与单测
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R007 — Connections namespace（Phase 3 全量覆盖 - 连接管理模块）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/connections.py:1`
- 作用：连接管理相关 v1 API。
- 触发条件：请求 `/api/v1/connections/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:21`；`app/api/v1/__init__.py:58`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R008 — Instances namespace（Phase 2 核心域迁移）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/instances.py:1`
- 作用：实例核心域 v1 API（Phase 2）。
- 触发条件：请求 `/api/v1/instances/**`。
- 依赖方（证据）：
  - `app/api/v1/__init__.py:29`；`app/api/v1/__init__.py:59`
  - 前端调用示例：`app/static/js/modules/views/instances/detail.js:559`（`/api/v1/instances/.../permissions`）
- 风险级别：P1（误删导致实例详情/账户权限等功能退化）
- 是否可直接删除：No
- 删除前置条件与验证：同 R001；同时回归实例页面 JS 调用链
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R009 — Capacity namespace（Phase 2 核心域迁移）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/capacity.py:1`
- 作用：容量/统计相关 v1 API。
- 触发条件：请求 `/api/v1/capacity/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:19`；`app/api/v1/__init__.py:60`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R010 — Databases namespace（Phase 2 核心域迁移 - Ledgers）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/databases.py:1`
- 作用：数据库 ledger 相关 v1 API。
- 触发条件：请求 `/api/v1/databases/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:24`；`app/api/v1/__init__.py:61`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R011 — Files namespace（exports/downloads）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/files.py:1`
- 作用：文件导出/下载相关 v1 API。
- 触发条件：请求 `/api/v1/files/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:25`；`app/api/v1/__init__.py:62`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R012 — Tags namespace（Phase 2 核心域迁移）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/tags.py:1`
- 作用：标签管理 v1 API。
- 触发条件：请求 `/api/v1/tags/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:32`；`app/api/v1/__init__.py:63`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R013 — Tags bulk namespace（Phase 4C 标签批量操作）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/tags_bulk.py:1`
- 作用：标签批量操作 v1 API。
- 触发条件：请求 `/api/v1/tags/bulk/**`（namespace path="/tags/bulk"）。
- 依赖方（证据）：`app/api/v1/__init__.py:33`；`app/api/v1/__init__.py:64`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R014 — Cache namespace（Phase 4A 缓存管理）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/cache.py:1`
- 作用：缓存管理 v1 API。
- 触发条件：请求 `/api/v1/cache/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:18`；`app/api/v1/__init__.py:65`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R015 — Credentials namespace（Phase 2 核心域迁移）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/credentials.py:1`
- 作用：凭据管理 v1 API。
- 触发条件：请求 `/api/v1/credentials/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:22`；`app/api/v1/__init__.py:66`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R016 — History logs namespace（Phase 4A 日志中心）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/history_logs.py:1`
- 作用：日志中心 v1 API。
- 触发条件：请求 `/api/v1/history/logs/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:27`；`app/api/v1/__init__.py:67`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001；注意前端 logs_store 可能依赖响应契约（见 R052）
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R017 — History sessions namespace（Phase 4C 同步会话）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/history_sessions.py:1`
- 作用：同步会话 v1 API。
- 触发条件：请求 `/api/v1/history/sessions/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:28`；`app/api/v1/__init__.py:68`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R018 — Partition namespace（Phase 4B 分区管理）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/partition.py:1`
- 作用：分区管理 v1 API（与分区任务/初始化脚本形成闭环）。
- 触发条件：请求 `/api/v1/partition/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:30`；`app/api/v1/__init__.py:69`
- 风险级别：P1（误删影响分区管理能力）
- 是否可直接删除：No
- 删除前置条件与验证：同 R001；并回归分区相关任务/页面
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R019 — Scheduler namespace（Phase 4B 定时任务管理）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/scheduler.py:1`
- 作用：定时任务管理 v1 API。
- 触发条件：请求 `/api/v1/scheduler/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:31`；`app/api/v1/__init__.py:70`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R020 — Users namespace

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/users.py:1`
- 作用：用户管理 v1 API。
- 触发条件：请求 `/api/v1/users/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:34`；`app/api/v1/__init__.py:71`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R021 — Accounts classifications namespace（Phase 3 全量迁移）

- 分类：`TempRoute`、`CompatLayer`
- 位置：`app/api/v1/namespaces/accounts_classifications.py:1`；`app/api/v1/namespaces/accounts_classifications.py:472`
- 作用：账户分类/规则管理 v1 API；并包含“删除阻断”逻辑（提示先迁移关联规则/账户）。
- 触发条件：请求 `/api/v1/accounts/classifications/**`。
- 依赖方（证据）：
  - namespace import：`app/api/v1/__init__.py:15`
  - namespace 绑定：`app/api/v1/__init__.py:72`
  - 删除阻断提示：`app/api/v1/namespaces/accounts_classifications.py:482`
- 风险级别：P1（误删影响分类规则管理；误删阻断可能导致误删除引发业务退化）
- 是否可直接删除：No（属于业务核心域的一部分）
- 删除前置条件与验证：
  - 若未来要删除“迁移提示/阻断”：需确认不再存在旧分类/规则迁移场景；并补充替代的完整性校验与回滚策略
  - 验证：运行单测 + 走一遍“删除分类”的 API 回归；确保不会误删仍在引用的分类
- 替代方案/新入口：无
- 删除条件与时间表：当分类/规则/分配关系的数据迁移完成，并有稳定的删除策略后再评估

### R022 — Accounts namespace（Phase 2 核心域迁移 - Ledgers）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/accounts.py:1`
- 作用：账户台账/权限相关 v1 API（与权限 snapshot/facts 兼容层强相关）。
- 触发条件：请求 `/api/v1/accounts/**`（namespace path="/accounts"）。
- 依赖方（证据）：`app/api/v1/__init__.py:14`；`app/api/v1/__init__.py:73`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001；并结合权限同步/permission_facts 相关验证（见 R051）
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R023 — Dashboard namespace（Phase 3 全量覆盖 - 仪表板模块）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/dashboard.py:1`
- 作用：仪表板 v1 API。
- 触发条件：请求 `/api/v1/dashboard/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:23`；`app/api/v1/__init__.py:74`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R024 — Admin namespace（misc）

- 分类：`TempRoute`
- 位置：`app/api/v1/namespaces/admin.py:1`
- 作用：杂项/管理接口 v1 API。
- 触发条件：请求 `/api/v1/admin/**`。
- 依赖方（证据）：`app/api/v1/__init__.py:16`；`app/api/v1/__init__.py:75`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R001
- 替代方案/新入口：暂无
- 删除条件与时间表：同 R001

### R025 — OpenAPI 导出脚本（迁移期文档/契约工具）

- 分类：`TempRoute`、`BackfillJob`（工具类一次性/批量导出）
- 位置：`scripts/dev/openapi/export_openapi.py:2`；`scripts/dev/openapi/export_openapi.py:47`
- 作用：通过 Flask test_client 拉取 `/api/v1/openapi.json` 并做最小校验（用于迁移期契约固化/回归）。
- 触发条件：人工执行 `python3 scripts/dev/openapi/export_openapi.py --check/--output ...`。
- 依赖方（证据）：
  - 依赖 OpenAPI route：`scripts/dev/openapi/export_openapi.py:47`（默认 endpoint）
  - 依赖应用工厂：`scripts/dev/openapi/export_openapi.py:58`（`create_app(...)`）
- 风险级别：P2（误删主要影响文档导出与契约校验，不直接影响生产主链路）
- 是否可直接删除：Maybe（若 OpenAPI 导出链路不再使用）
- 删除前置条件与验证：
  - 前置条件：确认 CI/发布流程/团队不再依赖该脚本
  - 验证：搜索脚本被引用位置；并在替代工具链上补齐等价校验
- 替代方案/新入口：可迁移到 CI 中自动生成/发布 OpenAPI artifact
- 删除条件与时间表：OpenAPI 工具链稳定替换后

### R026 — 本地同步脚本对 `/api/v1` 的 quick-check 依赖

- 分类：`TempRoute`
- 位置：`scripts/dev/sync-local-code-to-docker.sh:206`；`scripts/dev/sync-local-code-to-docker.sh:216`
- 作用：在容器内 quick check 直接探测 `/api/v1/health/basic`、`/api/v1/openapi.json` 等，作为“同步后自检”。
- 触发条件：运行 `scripts/dev/sync-local-code-to-docker.sh` 且启用 quick_check。
- 依赖方（证据）：脚本内固定检查路径：`scripts/dev/sync-local-code-to-docker.sh:216` - `scripts/dev/sync-local-code-to-docker.sh:220`
- 风险级别：P2（误删会影响开发自检体验；不直接影响生产）
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认团队不再使用该脚本或已迁移到新健康检查路径
  - 验证：更新/替换 quick-check 路径；保持等价自检能力
- 替代方案/新入口：可改为从 `docker compose healthcheck` 或统一的 `/api/v1/health/ping` 探测
- 删除条件与时间表：开发工作流变更完成后

### R027 — Nginx 错误页脚本对 `/api/v1/health/basic` 的依赖

- 分类：`TempRoute`
- 位置：`scripts/ops/nginx/update-error-pages.sh:81`
- 作用：通过访问 `/api/v1/health/basic` 触发 50x 来验证 Nginx 自定义错误页面（迁移后健康检查路径已统一到 v1）。
- 触发条件：运行 `scripts/ops/nginx/update-error-pages.sh`。
- 依赖方（证据）：固定请求路径：`scripts/ops/nginx/update-error-pages.sh:81`
- 风险级别：P1（误删/改动健康检查路径可能导致运维验证脚本失效，影响发布/排障）
- 是否可直接删除：Maybe（若该脚本不再用于生产运维）
- 删除前置条件与验证：
  - 前置条件：确认运维不依赖该脚本，或已替换为新验证方式
  - 验证：运行替代脚本/Runbook 步骤；确保可稳定验证 50x 错误页
- 替代方案/新入口：使用专用的模拟 upstream down 的方式触发 50x
- 删除条件与时间表：运维 Runbook 替换后

---

## BackfillJob（回填/一次性脚本/迁移执行链路）

### R028 — Flask-Migrate 初始化（Alembic/迁移工具链基础设施）

- 分类：`BackfillJob`
- 位置：`app/__init__.py:20`；`app/__init__.py:47`；`app/__init__.py:240`
- 作用：在应用中初始化 `Flask-Migrate`，使 `flask db upgrade/stamp` 可用（部署脚本强依赖）。
- 触发条件：应用启动初始化扩展；或容器内执行 `/app/.venv/bin/flask db ...`。
- 依赖方（证据）：
  - 初始化：`app/__init__.py:240`（`migrate.init_app(app, db)`）
  - 部署脚本调用：`scripts/deploy/update-prod-flask.sh:412`（`flask db upgrade`）
- 风险级别：P0（误删将导致迁移/回填链路不可用，影响生产升级与回滚能力）
- 是否可直接删除：No
- 删除前置条件与验证：除非完全迁移到其他迁移系统；验证需覆盖完整部署升级流程
- 替代方案/新入口：无
- 删除条件与时间表：不建议删除（属于基础设施）

### R029 — 生产初始化：直接执行 `init_postgresql.sql` 建库（并非 alembic upgrade）

- 分类：`BackfillJob`、`CompatLayer`
- 位置：`scripts/deploy/deploy-prod-all.sh:473`；`scripts/deploy/deploy-prod-all.sh:475`
- 作用：在生产部署脚本中直接用 SQL 初始化空库（绕开 Alembic 的 upgrade 路径）。
- 触发条件：运行 `scripts/deploy/deploy-prod-all.sh` 的数据库初始化流程。
- 依赖方（证据）：
  - SQL 文件存在性判断：`scripts/deploy/deploy-prod-all.sh:473`
  - 执行入口：`scripts/deploy/deploy-prod-all.sh:475`（`psql < sql/init/postgresql/init_postgresql.sql`）
- 风险级别：P0（误删/误改可能导致生产初始化失败或 schema 不一致）
- 是否可直接删除：No（除非改为“全量 Alembic 初始化”）
- 删除前置条件与验证：
  - 前置条件：有可替代的全自动初始化方式（例如 `flask db upgrade head` + seed）
  - 验证：在全新环境做端到端部署演练；确保 alembic_version 正确写入
- 替代方案/新入口：用 migrations 作为唯一建库方式
- 删除条件与时间表：当“SQL 初始化路径”正式退役后

### R030 — 生产初始化后的 Alembic `stamp head`（补写 alembic_version）

- 分类：`BackfillJob`
- 位置：`scripts/deploy/deploy-prod-all.sh:532`；`scripts/deploy/deploy-prod-all.sh:535`
- 作用：防御性地写入 `alembic_version`（因为直接 SQL 建库不会自动写入），避免后续 `flask db upgrade` 从 baseline 重放 DDL。
- 触发条件：deploy-prod-all 初始化完成后执行。
- 依赖方（证据）：`scripts/deploy/deploy-prod-all.sh:535`（`flask db stamp head`）
- 风险级别：P0（误删会导致后续迁移执行可能重复建表/重复对象报错，影响生产升级可用性）
- 是否可直接删除：No
- 删除前置条件与验证：需保证初始化路径改为 Alembic 体系且一定写入 `alembic_version`
- 替代方案/新入口：改为 `flask db upgrade head` 作为初始化
- 删除条件与时间表：SQL 初始化路径下线后

### R031 — 热更新脚本：拷贝 migrations 目录进容器（迁移执行前置）

- 分类：`BackfillJob`
- 位置：`scripts/deploy/update-prod-flask.sh:198`
- 作用：热更新时将 `migrations/` 拷入容器，确保容器内可执行 `flask db upgrade/stamp`。
- 触发条件：运行 `scripts/deploy/update-prod-flask.sh`。
- 依赖方（证据）：`scripts/deploy/update-prod-flask.sh:198`（`cp -r migrations ...`）
- 风险级别：P0（误删导致容器缺失迁移脚本，升级失败）
- 是否可直接删除：No
- 删除前置条件与验证：除非容器镜像内已内置 migrations 且不再通过拷贝更新代码
- 替代方案/新入口：构建镜像时固化 migrations；热更新只替换镜像
- 删除条件与时间表：运维模式切换后

### R032 — 热更新脚本：删除 `/app/migrations/versions`（迁移链断裂防御）

- 分类：`BackfillJob`、`CompatLayer`
- 位置：`scripts/deploy/update-prod-flask.sh:231`；`scripts/deploy/update-prod-flask.sh:232`
- 作用：通过删除版本文件避免“历史遗留版本链断裂导致 upgrade 失败”（属于强侵入式 workaround）。
- 触发条件：运行 update-prod-flask，清理缓存阶段。
- 依赖方（证据）：脚本直接执行：`scripts/deploy/update-prod-flask.sh:232`
- 风险级别：P0（误用会破坏迁移历史/回滚能力；潜在导致版本链不可追溯）
- 是否可直接删除：Maybe（取决于 migrations 版本链是否已彻底稳定且容器内无断裂问题）
- 删除前置条件与验证：
  - 前置条件：确认 migrations/versions 在生产链路中完整且不会触发断裂；并有“断裂时的替代处理方案”
  - 验证：在 staging 反复跑 `flask db upgrade`，验证不需要删除 versions；并验证回滚（downgrade）策略
- 替代方案/新入口：修复历史迁移链（或使用单一线性迁移策略）而不是运行时删除
- 删除条件与时间表：当迁移链断裂问题被根治后，优先删除该逻辑

### R033 — 热更新脚本：检测“非空库但无 alembic_version”并执行 `stamp`（总体逻辑）

- 分类：`BackfillJob`、`CompatLayer`
- 位置：`scripts/deploy/update-prod-flask.sh:355`；`scripts/deploy/update-prod-flask.sh:373`
- 作用：当数据库已通过 SQL 初始化但缺失 alembic_version 时，通过 schema 探测推断 revision 并 stamp，防止 upgrade 重放 baseline。
- 触发条件：`table_count>0` 且 `alembic_version` 不存在/为空时（脚本判断）。
- 依赖方（证据）：分支判断：`scripts/deploy/update-prod-flask.sh:373` - `scripts/deploy/update-prod-flask.sh:375`
- 风险级别：P0（误判 revision 会导致迁移状态错乱，影响生产写入一致性与回滚）
- 是否可直接删除：No（在“SQL 初始化路径仍存在”的前提下）
- 删除前置条件与验证：仅当所有环境都保证 alembic_version 正确写入（初始化改造完成）
- 替代方案/新入口：统一初始化为 `flask db upgrade head`
- 删除条件与时间表：SQL 初始化路径下线后

### R034 — 热更新脚本：schema 探测 #1（`credentials.instance_ids` -> revision）

- 分类：`BackfillJob`、`CompatLayer`
- 位置：`scripts/deploy/update-prod-flask.sh:377`；`scripts/deploy/update-prod-flask.sh:381`
- 作用：通过检测 `credentials.instance_ids` 是否存在来推断 `stamp_revision`（强绑定 schema 演进历史）。
- 触发条件：缺失 alembic_version 且 `credentials.instance_ids` 存在。
- 依赖方（证据）：`scripts/deploy/update-prod-flask.sh:378` - `scripts/deploy/update-prod-flask.sh:382`
- 风险级别：P0（误删/误改可能导致 stamp 错误 revision）
- 是否可直接删除：Maybe（若迁移链/初始化链路已统一，不再需要推断）
- 删除前置条件与验证：同 R033；并补充“revision 推断”被替代的证据
- 替代方案/新入口：显式记录初始化 baseline revision；不做 runtime 推断
- 删除条件与时间表：同 R033

### R035 — 热更新脚本：schema 探测 #2（`database_size_aggregations.calculated_at` 类型 -> revision）

- 分类：`BackfillJob`、`CompatLayer`
- 位置：`scripts/deploy/update-prod-flask.sh:383`；`scripts/deploy/update-prod-flask.sh:386`
- 作用：通过字段类型（timestamp tz/no tz）推断 stamp revision（进一步绑定 schema 历史）。
- 触发条件：缺失 alembic_version 且不满足 R034 分支时。
- 依赖方（证据）：`scripts/deploy/update-prod-flask.sh:384` - `scripts/deploy/update-prod-flask.sh:392`
- 风险级别：P0（同 R034）
- 是否可直接删除：Maybe（同 R034）
- 删除前置条件与验证：同 R034
- 替代方案/新入口：同 R034
- 删除条件与时间表：同 R033

### R036 — 热更新脚本：执行 `flask db upgrade`（迁移执行入口）

- 分类：`BackfillJob`
- 位置：`scripts/deploy/update-prod-flask.sh:411`；`scripts/deploy/update-prod-flask.sh:412`
- 作用：升级数据库到最新 migration head。
- 触发条件：运行 `scripts/deploy/update-prod-flask.sh`。
- 依赖方（证据）：`scripts/deploy/update-prod-flask.sh:412`（容器内执行 `/app/.venv/bin/flask db upgrade`）
- 风险级别：P0（误删将导致生产无法升级/回滚窗口受限）
- 是否可直接删除：No
- 删除前置条件与验证：除非彻底替换迁移执行方式
- 替代方案/新入口：镜像发布时自动迁移（CI/CD）等
- 删除条件与时间表：迁移执行策略变更后

### R037 — SQL 目录约定：SQL 初始化后必须 `flask db stamp`（避免重复建表）

- 分类：`BackfillJob`、`DeprecatedCall`（patches 约束属于迁移期流程约束）
- 位置：`sql/README.md:35`；`sql/README.md:42`；`sql/README.md:43`
- 作用：明确“SQL 初始化路径”与 “Alembic baseline stamp” 的耦合流程，避免后续 upgrade 重放 DDL。
- 触发条件：人工/脚本执行 SQL 初始化路径（psql -f init_postgresql.sql）。
- 依赖方（证据）：
  - init 执行建议：`sql/README.md:38`
  - stamp 指令：`sql/README.md:43`
- 风险级别：P0（忽略该约定可能导致迁移状态错乱）
- 是否可直接删除：No（除非 SQL 初始化路径退役；否则文档是关键操作手册）
- 删除前置条件与验证：初始化策略改造完成并更新 Runbook
- 替代方案/新入口：统一 migrations 初始化后，该段可迁移到“历史说明”并弱化
- 删除条件与时间表：SQL 初始化路径完全下线后

### R038 — 月度分区初始化脚本（2025-07）

- 分类：`BackfillJob`
- 位置：`sql/init/postgresql/partitions/init_postgresql_partitions_2025_07.sql:1`
- 作用：从 `init_postgresql.sql` 拆分出的月分区子表初始化脚本（只增不改），用于空库初始化后补分区。
- 触发条件：人工/脚本执行（参考 `sql/README.md:39`）。
- 依赖方（证据）：
  - README 执行顺序：`sql/README.md:39`
  - 脚本内部说明：`sql/init/postgresql/partitions/init_postgresql_partitions_2025_07.sql:4`
- 风险级别：P1（误删会影响新环境初始化完整性；但不直接影响已存在环境）
- 是否可直接删除：No（仍是“空库初始化路径”的一部分）
- 删除前置条件与验证：当分区创建完全由自动化任务完成，且不再依赖“按月脚本补分区”
- 替代方案/新入口：在 Alembic migrations 中创建分区/或启动时自动创建未来分区（见 `app/tasks/partition_management_tasks.py`）
- 删除条件与时间表：分区自动化闭环完成后

### R039 — 月度分区初始化脚本（2025-08）

- 分类：`BackfillJob`
- 位置：`sql/init/postgresql/partitions/init_postgresql_partitions_2025_08.sql:1`
- 作用：同 R038（2025-08 分区）。
- 触发条件：参考 `sql/README.md:40`。
- 依赖方（证据）：`sql/README.md:40`；`sql/init/postgresql/partitions/init_postgresql_partitions_2025_08.sql:4`
- 风险级别：P1
- 是否可直接删除：No
- 删除前置条件与验证：同 R038
- 替代方案/新入口：同 R038
- 删除条件与时间表：同 R038

### R040 — 一次性 patches：删除 tags 字段（不可逆 schema 变更）

- 分类：`BackfillJob`
- 位置：`sql/patches/2025/20251208_remove_tag_sort_description.sql:1`；`sql/patches/2025/20251208_remove_tag_sort_description.sql:7`
- 作用：一次性修复脚本：从 `tags` 表移除 `description`、`sort_order` 字段，并给出回滚参考。
- 触发条件：人工执行该 SQL patch（通常在紧急/一次性变更时）。
- 依赖方（证据）：
  - patches 规则说明：`sql/README.md:77`（执行后需补齐迁移/代码侧对齐并记录执行情况）
- 风险级别：P0（误执行/误删导致数据不可逆丢失；误删脚本会影响审计追溯）
- 是否可直接删除：Maybe（取决于是否需要保留审计凭证/Runbook 记录）
- 删除前置条件与验证：
  - 前置条件：确认该变更已通过 Alembic migration 正式固化，且执行记录已存档（环境/时间/执行人）
  - 验证：在新环境仅通过 migrations 也能得到一致 schema；并确保应用不再引用被删字段
  - 回滚：恢复字段需走 migrations（脚本仅作参考）
- 替代方案/新入口：补齐对应 Alembic migration（首选）
- 删除条件与时间表：当“patches 历史审计”有单独存档策略后

---

## FeatureFlag（迁移开关/灰度/条件启用）

### R041 — `API_V1_DOCS_ENABLED`（Swagger UI 开关，生产默认关闭）

- 分类：`FeatureFlag`、`TempRoute`
- 位置：`app/settings.py:429`；`app/settings.py:439`；`app/settings.py:540`
- 作用：控制 `/api/v1/docs` 是否启用（Phase 4 策略：生产默认关闭 Swagger UI，仅保留 OpenAPI JSON）。
- 触发条件：环境变量 `API_V1_DOCS_ENABLED`；以及 `environment_normalized == "production"` 默认值分支。
- 依赖方（证据）：
  - 开关读取：`app/settings.py:439`
  - swagger doc 路径绑定：`app/api/v1/__init__.py:47`
- 风险级别：P1（误删可能导致生产误暴露 Swagger UI 或导致文档能力缺失）
- 是否可直接删除：No（仍用于控制文档暴露面）
- 删除前置条件与验证：
  - 前置条件：明确文档暴露策略迁移完成（例如统一网关/只在内网暴露）
  - 验证：校验生产环境 Swagger UI 不可访问但 OpenAPI 可导出（如仍需要）
- 替代方案/新入口：在网关层做文档暴露控制
- 删除条件与时间表：文档策略切换完成后再评估

---

## CompatLayer（数据格式兼容 / 双读双写 / fallback）

### R051 — 权限同步：facts 构建失败时写入错误兜底 payload

- 分类：`CompatLayer`
- 位置：`app/services/accounts_sync/permission_manager.py:505`；`app/services/accounts_sync/permission_manager.py:517`
- 作用：当 `build_permission_facts` 抛异常时，将 `permission_facts` 写为可识别的错误 payload（避免整个同步流程崩溃）。
- 触发条件：facts 构建抛异常（解析/数据异常/代码异常）。
- 依赖方（证据）：
  - 主逻辑：`app/services/accounts_sync/permission_manager.py:505` - `app/services/accounts_sync/permission_manager.py:527`
  - 单测覆盖：`tests/unit/services/test_account_permission_manager.py:11`（写入 snapshot/facts）
- 风险级别：P1（误删会导致同步任务在异常数据下更容易失败；影响稳定性）
- 是否可直接删除：No（属于防御性兜底，且异常不可能完全杜绝）
- 删除前置条件与验证：除非有替代的异常隔离机制（例如单条失败不影响批处理）
- 替代方案/新入口：更细粒度的错误隔离 + 告警
- 删除条件与时间表：不建议删除

### R052 — SQL Server 权限查询：SID 路径为空时回退按用户名查询

- 分类：`CompatLayer`
- 位置：`app/services/accounts_sync/adapters/sqlserver_adapter.py:681`；`app/services/accounts_sync/adapters/sqlserver_adapter.py:691`
- 作用：当 SID 查询路径返回空结果时回退为用户名查询，避免权限为空（兼容不同 SQL Server 环境/权限限制）。
- 触发条件：`_is_permissions_empty(result)` 为 True 或无法读取 SID 映射时。
- 依赖方（证据）：
  - adapter 工厂装配：`app/services/accounts_sync/adapters/factory.py:13`；`app/services/accounts_sync/adapters/factory.py:23`
  - fallback 分支：`app/services/accounts_sync/adapters/sqlserver_adapter.py:681` - `app/services/accounts_sync/adapters/sqlserver_adapter.py:694`
- 风险级别：P1（误删会导致部分 SQLServer 环境权限采集退化为“空权限”，影响安全评估）
- 是否可直接删除：No（除非明确所有环境都支持 SID 路径且有证据）
- 删除前置条件与验证：
  - 前置条件：收集生产/真实环境日志确认 `sqlserver_batch_permissions_sid_empty_fallback` 命中为 0
  - 验证：在受限权限/多库场景做联调验证
- 替代方案/新入口：增强 SID 路径的可靠性或补齐必要权限
- 删除条件与时间表：命中率长期为 0 且有替代方案后

---

## DeprecatedCall（升级前“模块/api” 设计下线：404 contract tests）

> 背景：升级前采用 `/<module>/api/**` 的模块式 JSON API；当前方案为 `/api/v1/**`。
> 本组记录的主体是“防回归门禁（tests）”：确保旧入口持续返回 404，避免被误恢复。

### R065 — legacy `/auth/api/csrf-token` 已下线（模块/api -> `/api/v1/auth/csrf-token`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_legacy_api_gone_contract.py:6`；`tests/unit/routes/test_legacy_api_gone_contract.py:7`
- 作用：固化升级前 `/auth/api/csrf-token` 已下线（返回 404），避免旧入口在未来被误恢复。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_auth_contract.py:20`
- 风险级别：P2（删除仅影响防回归能力，不影响生产逻辑）
- 是否可直接删除：Maybe（建议迁移收尾后再评估是否保留门禁）
- 删除前置条件与验证：
  - 前置条件：确认 `/auth/api/*` 族路径永久废弃且团队不再需要门禁
  - 验证：`rg -n \"/auth/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k legacy_api_gone_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/auth/csrf-token`（`app/api/v1/namespaces/auth.py:121`）
- 删除条件与时间表：建议至少跨 1-2 个发布周期观察后再决定

### R066 — legacy `/instances/api/instances` 已下线（模块/api -> `/api/v1/instances`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_instances_list_contract.py:6`；`tests/unit/routes/test_instances_list_contract.py:7`
- 作用：固化升级前实例列表旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_instances_contract.py:52`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/instances/api/instances`
  - 验证：`rg -n \"/instances/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k instances_list_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/instances`（`app/api/v1/namespaces/instances.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R067 — legacy `/users/api/users` 已下线（模块/api -> `/api/v1/users`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_users_list_contract.py:6`；`tests/unit/routes/test_users_list_contract.py:7`
- 作用：固化升级前用户列表旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_users_contract.py:19`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/users/api/users`
  - 验证：`rg -n \"/users/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k users_list_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/users`（`app/api/v1/namespaces/users.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R068 — legacy `/tags/api/list` 已下线（模块/api -> `/api/v1/tags`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_tags_list_contract.py:6`；`tests/unit/routes/test_tags_list_contract.py:7`
- 作用：固化升级前标签列表旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_tags_contract.py:43`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/tags/api/list`
  - 验证：`rg -n \"/tags/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k tags_list_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/tags`（`app/api/v1/namespaces/tags.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R069 — legacy `/credentials/api/credentials` 已下线（模块/api -> `/api/v1/credentials`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_credentials_list_contract.py:6`；`tests/unit/routes/test_credentials_list_contract.py:7`
- 作用：固化升级前凭据列表旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_credentials_contract.py:54`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/credentials/api/credentials`
  - 验证：`rg -n \"/credentials/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k credentials_list_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/credentials`（`app/api/v1/namespaces/credentials.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R070 — legacy `/accounts/api/ledgers` 已下线（模块/api -> `/api/v1/accounts/ledgers`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_accounts_ledgers_contract.py:6`；`tests/unit/routes/test_accounts_ledgers_contract.py:7`
- 作用：固化升级前账户台账旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_accounts_ledgers_contract.py:88`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/accounts/api/ledgers`
  - 验证：`rg -n \"/accounts/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k accounts_ledgers_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/accounts/ledgers`（`app/api/v1/namespaces/accounts.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R071 — legacy `/databases/api/ledgers` 已下线（模块/api -> `/api/v1/databases/ledgers`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_databases_ledger_contract.py:6`；`tests/unit/routes/test_databases_ledger_contract.py:7`
- 作用：固化升级前数据库台账旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_databases_ledgers_contract.py:8`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/databases/api/ledgers`
  - 验证：`rg -n \"/databases/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k databases_ledger_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/databases/ledgers`（`app/api/v1/namespaces/databases.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R072 — legacy `/history/logs/api/list` 已下线（模块/api -> `/api/v1/history/logs/list`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_history_logs_list_contract.py:6`；`tests/unit/routes/test_history_logs_list_contract.py:7`
- 作用：固化升级前历史日志列表旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_history_logs_contract.py:11`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/history/logs/api/list`
  - 验证：`rg -n \"/history/logs/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k history_logs_list_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/history/logs/list`（`app/api/v1/namespaces/history_logs.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R073 — legacy `/dashboard/api/charts?type=logs` 已下线（模块/api -> `/api/v1/dashboard/charts?type=logs`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_dashboard_charts_contract.py:6`；`tests/unit/routes/test_dashboard_charts_contract.py:7`
- 作用：固化升级前 dashboard charts(logs) 旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_dashboard_contract.py:90`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/dashboard/api/charts?type=logs`
  - 验证：`rg -n \"/dashboard/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k dashboard_charts_logs_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/dashboard/charts?type=logs`（`app/api/v1/namespaces/dashboard.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R074 — legacy `/dashboard/api/charts?type=syncs` 已下线（模块/api -> `/api/v1/dashboard/charts?type=syncs`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_dashboard_charts_contract.py:12`；`tests/unit/routes/test_dashboard_charts_contract.py:13`
- 作用：固化升级前 dashboard charts(syncs) 旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_dashboard_contract.py:107`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/dashboard/api/charts?type=syncs`
  - 验证：`rg -n \"/dashboard/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k dashboard_charts_syncs_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/dashboard/charts?type=syncs`（`app/api/v1/namespaces/dashboard.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R075 — legacy `/dashboard/api/charts?type=unknown` 已下线（模块/api -> `/api/v1/dashboard/charts?type=unknown`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_dashboard_charts_contract.py:18`；`tests/unit/routes/test_dashboard_charts_contract.py:19`
- 作用：固化升级前 dashboard charts(unknown) 旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_dashboard_contract.py:129`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/dashboard/api/charts?type=unknown`
  - 验证：`rg -n \"/dashboard/api/\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k dashboard_charts_unknown_type -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/dashboard/charts?type=unknown`（`app/api/v1/namespaces/dashboard.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R076 — legacy `/capacity/api/databases*` 已下线（模块/api -> `/api/v1/capacity/databases*`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_capacity_databases_contract.py:7`；`tests/unit/routes/test_capacity_databases_contract.py:12`
- 作用：固化升级前容量-库趋势与汇总旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_capacity_databases_contract.py:27`；`tests/unit/routes/test_api_v1_capacity_databases_contract.py:35`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/capacity/api/databases*`
  - 验证：`rg -n \"/capacity/api/databases\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k capacity_databases_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/capacity/databases` / `/api/v1/capacity/databases/summary`（`app/api/v1/namespaces/capacity.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R077 — legacy `/capacity/api/instances*` 已下线（模块/api -> `/api/v1/capacity/instances*`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_capacity_instances_contract.py:7`；`tests/unit/routes/test_capacity_instances_contract.py:12`
- 作用：固化升级前容量-实例趋势与汇总旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_capacity_instances_contract.py:79`；`tests/unit/routes/test_api_v1_capacity_instances_contract.py:87`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/capacity/api/instances*`
  - 验证：`rg -n \"/capacity/api/instances\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k capacity_instances_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/capacity/instances` / `/api/v1/capacity/instances/summary`（`app/api/v1/namespaces/capacity.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R078 — legacy `/common/api/instances-options` 已下线（模块/api -> `/api/v1/common/instances/options`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_common_filter_options_contract.py:6`；`tests/unit/routes/test_common_filter_options_contract.py:9`
- 作用：固化升级前“实例下拉 options”旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_common_options_contract.py:28`；`tests/unit/routes/test_api_v1_common_options_contract.py:49`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/common/api/instances-options`
  - 验证：`rg -n \"/common/api/instances-options\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k common_instances_options_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/common/instances/options`（`app/api/v1/namespaces/common.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R079 — legacy `/common/api/databases-options` 已下线（模块/api -> `/api/v1/common/databases/options`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_common_filter_options_contract.py:15`；`tests/unit/routes/test_common_filter_options_contract.py:16`
- 作用：固化升级前“库下拉 options”旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_common_options_contract.py:80`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/common/api/databases-options`
  - 验证：`rg -n \"/common/api/databases-options\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k common_databases_options_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/common/databases/options`（`app/api/v1/namespaces/common.py:1`）
- 删除条件与时间表：迁移收尾后再评估

### R080 — legacy `/common/api/dbtypes-options` 已下线（模块/api -> `/api/v1/common/database-types/options`）

- 分类：`DeprecatedCall`
- 位置：`tests/unit/routes/test_common_filter_options_contract.py:21`；`tests/unit/routes/test_common_filter_options_contract.py:22`
- 作用：固化升级前“数据库类型 options”旧端点已下线（返回 404）。
- 触发条件：运行单测 `pytest -m unit`。
- 依赖方（证据）：
  - 单测入口：`scripts/test/run-unit-tests.sh:215`
  - 新入口契约：`tests/unit/routes/test_api_v1_common_options_contract.py:112`
- 风险级别：P2
- 是否可直接删除：Maybe
- 删除前置条件与验证：
  - 前置条件：确认不存在任何客户端/脚本仍依赖 `/common/api/dbtypes-options`
  - 验证：`rg -n \"/common/api/dbtypes-options\" app scripts sql tests/unit` 为 0 命中；`uv run pytest -m unit -k common_dbtypes_options_contract -v`
  - 回滚：恢复该 contract test
- 替代方案/新入口：`/api/v1/common/database-types/options`（`app/api/v1/namespaces/common.py:1`）
- 删除条件与时间表：迁移收尾后再评估

---

## 4) 存档与扫描 artifacts

### 4.1 报告存档位置

- 本报告：`docs/reports/2025-12-31_migration-code-inventory-phase0.md`

### 4.2 扫描输出（证据文件）

目录：`docs/reports/artifacts/2025-12-31_migration-code-inventory-phase0/`

- `rg_migration_keywords.txt`（migration/migrate/backfill/compat/legacy/deprecated 命中）
- `rg_featureflag_toggle_fallback.txt`（feature flag/toggle/fallback 命中，已人工去噪）
- `rg_v1_v2.txt`（v1/v2 命中，v2 未见有效入口）
- `rg_legacy_module_api_paths_contracts.txt`（升级前 `/<module>/api/**` 旧路径命中，主要来自 404 contract tests）
- `rg_phase.txt`（Phase 标记命中）
- `rg_cn_migration.txt` / `rg_cn_compat.txt`（中文“迁移/兼容”命中）
- `rg_alembic.txt` / `rg_flask_db*.txt` / `rg_stamp_word.txt`（Alembic/Flask-Migrate 相关命中）

## 5) Progress 文档链接（待补）

未提供 `PROGRESS_DOC_PATH`。

请回复一次：**progress 文档路径是什么？**（例如 `docs/changes/refactor/xxx-progress.md` 或你们的统一进度文件）

我拿到路径后，会追加一条链接到本报告：`docs/reports/2025-12-31_migration-code-inventory-phase0.md`。
