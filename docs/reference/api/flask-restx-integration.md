# Flask-RESTX 引入指南（内部同源 + `/api/docs` 登录保护）

本文描述如何在鲸落现有 Flask 项目中引入 `flask-restx`，用于：

- 为新 API 提供更清晰的路由组织（Namespace/Resource）。
- 自动生成 Swagger UI 与 OpenAPI 规范（文档路径：`/api/docs`）。
- 与现有的统一响应、结构化日志与异常处理保持一致。

## 1. 适用范围与约束

适用范围：

- 内部前端同源访问（浏览器携带 Cookie / Session）。
- 文档路径固定为 `/api/docs`，并且需要登录保护。

关键约束：

- 路由层仍需遵守仓库规范：业务闭包必须通过 `app/utils/route_safety.py` 的 `safe_route_call` 执行，不在路由里散落 `try/except`。
- 统一响应结构优先使用 `app/utils/response_utils.py`（避免 `error/message` 漂移，参见 `docs/standards/backend/error-message-schema-unification.md`）。

## 2. 目标与非目标

目标：

- 在不影响现有蓝图体系的前提下新增一个 RestX API 蓝图。
- 最小可用：`/api/docs` 可访问并需要登录；`/api/swagger.json` 可被 Swagger UI 正常加载。
- 新增的 RestX 接口优先复用 `safe_route_call` 与 `jsonify_unified_success/jsonify_unified_error`，保持统一日志与错误封套。

非目标（本次引入不强制做）：

- 立刻把所有现有 `/xxx/api/*` 接口迁移到 RestX。
- 彻底统一所有历史接口的 OpenAPI schema。

## 3. 依赖管理与安装（uv）

项目已使用 `uv` 锁定依赖（`uv.lock`），推荐按以下方式引入：

```bash
uv add "flask-restx>=1.3.2,<2"
uv sync
```

如果你们需要同步导出 `requirements.txt`（给某些部署/审计流程使用），可执行：

```bash
uv export --format requirements.txt -o requirements.txt
```

`requirements-prod.txt` 是否更新取决于你的生产部署流程（仓库里目前既保留 `uv.lock`，也保留 `requirements-prod.txt`）。

## 4. 路由与文档路径设计

### 4.1 期望的访问路径

通过把 RestX 蓝图挂载在 `url_prefix="/api"`，并在 `Api(..., doc="/docs")` 中使用相对路径，可得到：

- Swagger UI：`/api/docs`
- OpenAPI JSON：`/api/swagger.json`（默认路径）

### 4.2 为什么用独立蓝图

- 避免和现有 `app/routes/*` 的蓝图、URL 前缀耦合。
- 引入初期便于回滚：移除蓝图注册即可彻底下线 RestX。
- 便于给整个 RestX 子系统做统一“登录保护 / 权限 / 速率限制 / 埋点”。

## 5. 登录保护策略（推荐：蓝图级 before_request）

为确保 `/api/docs` 与 `/api/swagger.json` 都需要登录，推荐对 RestX 蓝图整体做登录保护：

- 在 RestX 蓝图上添加 `before_request`，并用 `flask_login.login_required` 装饰。
- 这样未登录用户访问 `/api/docs` 会被重定向到登录页；登录后正常显示文档。

注意：

- 如果你希望“部分 RestX 接口公开但 docs 仍需登录”，不要用蓝图级别保护；改为对 docs 端点单独加保护，或拆成两个蓝图（一个公开、一个内部）。

## 6. 与现有统一响应 / 异常处理的集成建议

### 6.1 成功响应

在 `Resource` 方法中直接返回 `jsonify_unified_success(...)` 的结果（`(Response, status_code)`）：

- 保持统一字段：`success/error/message/timestamp/data/meta`。
- 让现有前端/调用方无需引入新的 schema 兼容分支。

### 6.2 错误响应与异常处理

项目已有全局异常处理（`app/__init__.py` 中的 `@app.errorhandler(Exception)`），会将异常转换为统一错误结构。

引入 RestX 后需要关注两点：

- `flask-restx` 可能对部分异常（例如请求校验、404 等）有自身的处理路径，导致错误结构与项目统一封套不一致。
- 为避免引入新的 `error/message` 漂移消费代码，建议在落地阶段补充 RestX 层的 error handler（例如将 `HTTPException`、`AppError` 等统一交给 `unified_error_response`），确保 RestX 端点也遵循项目规范。

## 7. CSRF 与 Swagger UI “Try it out” 说明

仓库启用了 `CSRFProtect`（见 `app/__init__.py` 的 `csrf.init_app(app)`）：

- `GET/HEAD/OPTIONS` 通常不受 CSRF 影响。
- `POST/PUT/DELETE` 等写操作可能需要携带 `X-CSRF-Token`（或项目约定的 CSRF 头部/表单字段），否则 Swagger UI 的直接调用会失败。

推荐做法（本项目采用）：

- 只把 Swagger UI 用于浏览与只读接口的调试；写接口用现有前端页面或脚本调用，避免在 Swagger UI 内处理 CSRF/会话细节导致误判与额外维护成本。

## 8. 推荐的代码组织（后续落地时参考）

仓库规范建议“服务端点”和“蓝图 wiring”分离，但当前代码主要在 `app/routes/` 内直接实现接口。引入 RestX 时可以采用两种渐进路径：

1) 最小改动（先跑通）：RestX 蓝图与 Namespace/Resource 都放在 `app/routes/`。
2) 规范化拆分（推荐长期）：新增 `app/api/`（服务端点/业务组织），`app/routes/` 只负责注册蓝图与挂载。

无论采用哪种路径，Resource 方法里都建议：

- 使用 `safe_route_call(...)` 执行业务闭包，复用统一事务/日志/异常模板。
- 成功统一用 `jsonify_unified_success(...)`，错误统一用现有错误体系（避免漂移）。

## 9. 最小落地步骤（清单）

下面是“最小可用”的落地清单（供后续实现用）：

1. 添加依赖：`flask-restx`（见第 3 节）。
2. 新增蓝图文件：例如 `app/routes/rest_api.py`。
3. 在 `create_app()` 的 `configure_blueprints()` 中注册蓝图：`url_prefix="/api"`。
4. 验证：登录后访问 `/api/docs`，Swagger UI 正常加载 `/api/swagger.json`。

## 10. 验收与回滚

验收清单：

- 未登录访问 `/api/docs`：跳转到登录页（或返回未授权，取决于 `flask-login` 配置）。
- 登录后访问 `/api/docs`：可看到 Swagger UI 页面。
- 登录后访问 `/api/swagger.json`：返回 JSON。

回滚方案：

- 移除 RestX 蓝图的注册（`configure_blueprints()` 中对应条目）并删除相关文件，即可恢复到引入前状态。
