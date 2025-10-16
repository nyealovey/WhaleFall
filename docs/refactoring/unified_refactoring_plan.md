# 统一改造执行计划（五大主题整合版）

范围与目标
- 将以下五个专题整合为一套按顺序执行的改造计划：
  - `docs/refactoring/request_validation_unification.md`
  - `docs/refactoring/cache_rate_limit_unification.md`
  - `docs/refactoring/csrf_frontend_unification.md`
  - `docs/refactoring/error_handling_unification.md`
  - `docs/refactoring/timezone_and_loglevel_unification.md`
- 保证各专题的改动在代码库中相互协同，最终达到统一：校验入口一致、错误响应一致、时间与枚举一致、缓存与限流一致、前端 CSRF 统一。

执行顺序（推荐）
1) 基础设施铺设（日志与错误 + 时间/枚举）
2) 请求校验统一（装饰器与校验器）
3) CSRF 与前端统一（写操作保护）
4) 缓存与限流统一（性能与安全）
5) 强制切换与清理（删除旧入口，统一响应）
6) 测试与验收（端到端校验）

单人项目模式（无 CI/门禁）
- 不启用 CI 或门禁时，按本地检查与脚本化自检替代：
  - 使用本文档“全局搜索模板”的 `rg` 命令进行自查，确保无旧入口/旧结构残留。
  - 可编写简单脚本（例如 `scripts/quality/local_check.sh`）聚合 `rg` 命令，作为日常质量检查；也可在 `Makefile` 增加 `make quality` 目标调用这些检查。
  - 测试以手动/本地运行为主：重点走通错误场景、CSRF 成功/失败、限流命中、缓存失效与降级路径。
  - PR 切分与排期建议可作为你个人的里程碑划分，不强制。

冲突避免与依赖矩阵（必须遵守）
- 统一失败路径的“中心”必须存在（依赖第 1 步）：所有步骤的失败都应当最终由全局错误处理器输出结构；第 2/3/4 步在迁移期可暂时内联返回，但第 5 步后必须上抛。
- 迁移期双写兼容：第 2/3/4 步的改造不得提前删除旧错误入口与返回结构；旧入口的删除只在第 5 步进行。
- 装饰器与中间件顺序统一（避免重复读取与语义冲突）：
  - `@api_rate_limit`（尽早拒绝，成本最低）
  - `@require_json_csrf`（仅写操作；从 Header 校验令牌，不读取 Body）
  - `@validate_json(required_fields=...)`（写接口；保证 JSON 体与必填字段存在）
  - 路由函数内部：`DataValidator`（领域）→ `InputValidator`（通用）→ 业务逻辑
  - 写操作成功后：统一触发缓存失效；读操作可使用缓存，但不要缓存错误响应。
- 查询参数统一不破坏现有默认：命名统一为 `page/per_page/q/sort_by/order`，迁移期保留原默认（10/20/50 差异允许），仅强制 `per_page<=100` 上限。
- 异常到状态码映射（在第 1 步与第 5 步落地）：
  - `ValidationError/InputError` → 400
  - `PermissionDenied`/`CSRFError` → 403
  - `RateLimitExceeded` → 429（含 `Retry-After`）
  - `NotFound` → 404
  - `IntegrityError`/资源冲突 → 409
  - `DatabaseError`/未知异常 → 500
- 依赖关系：
  - 第 2/3/4 步都依赖第 1 步的全局错误处理器存在（至少兜底）。
  - 第 5 步（强制切换）必须在第 2/3/4 步达到既定覆盖率后执行（见“执行门槛与回滚点”）。
  - 第 6 步（测试）覆盖第 1–5 步改造后的统一行为。

—— 以下为逐步执行清单（每步含：动作、涉及文件、成功标准、风险与回退） ——

第 1 步：基础设施铺设（结构日志 + 全局错误 + 时间与枚举）
- 动作：
  - 在应用初始化中注册统一日志与错误处理：
    - `from app.utils.structlog_config import configure_structlog, enhanced_error_handler`
    - `configure_structlog(app)`；注册 `@app.errorhandler(Exception)` 返回 `jsonify(enhanced_error_handler(error))`。
  - 时间与枚举统一：模型时间列统一为 `timezone=True`，日志级别枚举统一从 `app.constants` 导入。
- 涉及文件：
  - `app/__init__.py`（初始化与错误处理器注册）
  - `app/utils/structlog_config.py`（确认/增强入口与处理器）
  - `app/models/global_param.py`、`app/models/unified_log.py`（时间列与枚举来源）
- 成功标准：
  - 能启动应用并在错误场景下返回统一增强错误结构（不要求全量替换旧入口，先具备全局兜底）。
  - 模型中的新增/整改时间列采用 `db.DateTime(timezone=True)`；日志级别引用来自 `app.constants.LogLevel`。
- 风险与回退：
  - 风险：强制替换过早导致前端未适配；策略：先保留旧入口，等待第 5 步统一切换。
  - 回退：保留 `error_handler.py` 与 `api_response.py` 的现状入口，统一切换在第 5 步执行。

第 2 步：请求校验统一（装饰器与校验器）
- 动作：
  - JSON 写接口统一入口：为存在 JSON 请求体的路由补齐 `@validate_json(required_fields=[...])`（来自 `app/utils/decorators.py`）。
  - 领域校验优先走 `DataValidator`，通用输入类型/范围走 `InputValidator`；查询参数统一使用 `page/per_page/q/sort_by/order`，`per_page` 上限建议 `100`。
  - 时间解析统一回用 `app/utils/time_utils.py`（如 `to_utc`）。
- 涉及文件：
  - `app/utils/decorators.py`、`app/utils/data_validator.py`、`app/utils/validation.py`、`app/utils/time_utils.py`
  - 路由：`app/routes/*.py`（重点：`instances.py`、`logs.py`、`credentials.py`、`users.py`）
- 成功标准：
  - 抽样 5 个写接口：缺少必填字段时被 `@validate_json` 拦截；领域校验失败统一返回 400（临时可保留内联 JSON，最终在第 5 步上抛统一处理）。
  - 抽样 5 个列表接口：查询参数命名一致；`per_page` 上限生效。
- 风险与回退：
  - 风险：差异默认值影响前端分页；策略：迁移期保留现状默认值，逐步收敛上限与命名。
  - 回退：保留原有校验与返回结构，确保路径可用；在第 5 步切换错误路径。

第 3 步：CSRF 与前端统一
- 动作：
  - 后端：为所有 `/api/*` 的写操作加统一 CSRF 装饰器（示例：`require_json_csrf`），从 `X-CSRFToken` 读取令牌并校验。
  - 前端：统一接入 `csrf-utils.js`/`csrf-fetch.js`，在写操作自动注入 `X-CSRFToken`。
- 涉及文件：
  - 后端：`app/__init__.py`（`CSRFProtect`）、`app/utils/security_csrf.py`（若不存在则新增）、`app/routes/*.py`
  - 前端：`app/static/js/common/csrf-utils.js`、`app/static/js/common/csrf-fetch.js`、`app/templates/base.html`
- 成功标准：
  - 写操作缺少或错误令牌时，由全局错误处理器输出统一错误结构；正常写操作通过。
  - 前端统一封装写请求，无散落的手工令牌注入代码。
- 风险与回退：
  - 风险：跨域与 `SameSite` 导致令牌传递异常；策略：文档化 Cookie 策略与跨域建议。
  - 回退：对个别接口临时豁免（明确清单），尽快补齐封装后再收回豁免。

第 4 步：缓存与限流统一
- 动作：
  - 缓存：统一走 `app/utils/cache_manager.py` 生成 Key 与 TTL；业务层禁止手写 Key 与直接 `cache.get/set`。
  - 限流：统一使用 `app/utils/rate_limiter.py` 的 `rate_limit/api_rate_limit`，响应头包含 `X-RateLimit-*` 与可选 `Retry-After`；迁移到上抛统一错误路径。
- 涉及文件：
  - `app/utils/cache_manager.py`、`app/utils/rate_limiter.py`、`app/utils/decorators.py`
  - 路由与服务：`app/routes/*.py`、`app/services/*.py`
- 成功标准：
  - 抽样 5 个路由：缓存 Key 前缀与 TTL 整齐划一；写操作后相关前缀失效。
  - 抽样 3 个敏感接口：限流响应头完整；触发 429 时错误路径统一（或标注迁移清单）。
- 风险与回退：
  - 风险：过度缓存导致一致性问题；策略：TTL 审慎设定、写后失效、日志审计。
  - 回退：降低或移除问题路由的缓存策略；限流维持最小安全线并记录。

第 5 步：强制切换与清理（错误与日志统一的强制版）
- 动作：
  - 删除冗余文件与旧入口：`app/utils/logging_config.py`、`app/utils/error_handler.py`、`app/utils/api_response.py`（及其他旧日志入口）。
  - 替换日志入口与错误返回：
    - `import logging` / `logging.getLogger(__name__)` → `get_system_logger/log_*`。
    - `APIResponse.success/error` / `jsonify({"success": False, ...})` → 上抛异常或统一成功/错误结构。
  - 移除通用 `try/except Exception` 的本地返回；异常上抛，由全局处理器统一响应。
- 涉及文件：
  - `app/routes/*.py`、`app/services/*.py`、`app/tasks/*.py`
  - （清理）`app/utils/logging_config.py`、`app/utils/error_handler.py`、`app/utils/api_response.py`
- 成功标准：
  - 全库搜索无旧模式残留（见下方 `rg` 模板）。
  - 前端适配统一错误结构完成并通过集成测试。
- 风险与回退：
  - 风险：前端依赖旧结构被强制切断；策略：与前端同步排期，分批 PR；如阻塞，按批次回滚。
  - 回退：逐步恢复旧入口文件（按提交粒度），并保留统一方案为目标。

完成第 5 步后回看第 1 步（再统一与加固）
- 动作：
  - 强化 `structlog_config`：完善异常→状态码映射；确保 `CSRFError=403`、`RateLimitExceeded=429`、`ValidationError=400` 等分类准确。
  - 删除迁移期遗留的本地内联错误返回与双写逻辑；统一改为上抛异常。
  - 时间与枚举再审计：模型时间列统一 `timezone=True`；统一使用 `app.constants.LogLevel`；自测序列化为 UTC。
  - 建立本地检查清单：禁止旧模式（`APIResponse.*`、`jsonify({"success": False,...})`、`logging.getLogger`、新增非时区列、散落 `print`），通过“全局搜索模板”的 `rg` 命令或自用脚本定期检查。
- 成功标准：
  - 统一错误响应在全局与局部路径一致；任何失败均由全局处理器输出增强结构。
  - 本地搜索检查通过；无旧模式残留。
- 风险与回退：
  - 风险：个别接口仍需局部返回成功结构；策略：提供 `unified_success_response` 并归一。
  - 回退：针对极少数不兼容点，临时豁免并在下一批修复。

第 6 步：测试与验收（端到端）
- 动作：
  - 单测与本地集成测试覆盖：校验异常、权限异常、DB 异常、未知异常；CSRF 成功/失败；限流命中；缓存失效与降级。
  - 本地质量检查：执行本文档“全局搜索模板”的 `rg` 检查（或自用脚本），确保无旧日志入口、无旧错误结构、无新增非时区时间列、无散落 `print`。
- 成功标准：
  - 抽样 10 个端点错误场景通过集成测试并返回统一结构。
  - 本地 `rg` 搜索禁用模式为零；缓存与限流抽样指标达标。
  - 日志落库结构完整、时间戳为 UTC，前端显示正确（中国时区）。

跨模块依赖与协同
- 错误与日志统一是基础：限流与 CSRF 的失败路径应上抛，由全局错误处理器统一结构；请求校验失败最终也上抛。
- 时间与枚举统一支撑日志与错误链路：所有时间戳统一 `UTC`；日志级别统一来源避免枚举不一致。
- 校验与 CSRF前后配合：先校验请求体与参数，再进行 CSRF 校验；两者失败路径一致。
- 缓存策略与写路径：写操作成功后统一失效相关缓存前缀；限流头部与错误结构统一，便于前端一致处理。

装饰器与中间件执行顺序（建议）
```python
# 写接口典型顺序
@api_rate_limit(limit=60, window=60)         # 早拒绝、便宜
@require_json_csrf                           # 仅校验 Header，不读取 Body
@validate_json(required_fields=[...])        # 校验 JSON 体与必填
def endpoint():
    # 领域 + 通用校验
    is_valid, msg = DataValidator.validate_xxx(data)
    if not is_valid:
        # 迁移期可内联返回；第 5 步后必须上抛
        # return jsonify({"error": msg}), 400
        raise ValidationError(msg)
    # 业务逻辑...
    # 写成功后失效相关缓存前缀
    invalidate_cache_prefix("instances:*")
    return jsonify({"error": False, "data": {...}})
```

全局搜索模板（执行与门禁）
- 日志与错误旧入口：
  - `rg -n "logging.getLogger\(__name__\)|app\.logger" app/`
  - `rg -n "APIResponse\.(success|error)|error_response\(|jsonify\(\{\s*\"success\":\s*False" app/`
  - `rg -n "try:\n[\s\S]{0,200}?except\s+Exception" app/`
- 时间与枚举：
  - `rg -n "db\.DateTime\(" app/models | rg -v "timezone=True"`
  - `rg -n "class\s+LogLevel\(Enum\)" app/utils app/models`
  - `rg -n "from\s+app\.models\.unified_log\s+import\s+LogLevel" app/`

PR 切分与排期建议
- 批次 A：基础设施铺设（`app/__init__.py` + structlog 配置 +全局错误处理器）
- 批次 B：请求校验统一（装饰器与校验器落地、查询参数一致化）
- 批次 C：CSRF 与前端（后端装饰器 + 前端封装接入）
- 批次 D：缓存与限流（统一入口与响应头）
- 批次 E：强制清理（删除旧文件、全库替换、门禁上线）
- 批次 F：测试与验收（覆盖用例与 CI 门禁）

验收总表（跨主题）
- 错误结构：统一包含 `error=true`、`error_id/category/severity/message/timestamp`。
- 日志落库：INFO+ 入库，DEBUG 仅控制台；时间字段为 UTC。
- 校验：`@validate_json` 拦截必填；`DataValidator/InputValidator` 覆盖领域与通用校验；查询参数一致。
- CSRF：缺失/错误令牌返回统一错误；前端封装无散落注入。
- 缓存/限流：Key 与 TTL 统一；限流头完整；失败路径统一或列入过渡清单。

风险与回滚策略（统一）
- 风险：前端或外部依赖旧结构；缓存一致性；限流参数不当；跨域 CSRF。
- 回滚：按批次回滚对应提交；对缓存与限流适度降级；临时豁免 CSRF；保留全局错误处理器为兜底。

附录：关键代码片段（统一参考）
- 全局错误处理器注册：
```python
from flask import jsonify
from app.utils.structlog_config import configure_structlog, enhanced_error_handler

def create_app():
    app = Flask(__name__)
    configure_structlog(app)

    @app.errorhandler(Exception)
    def handle_exception(error):
        payload = enhanced_error_handler(error)
        return jsonify(payload), 500

    return app
```
- JSON 写接口（校验 + 领域校验 + 统一错误路径演进）：
```python
from flask import request, jsonify
from app.utils.decorators import validate_json
from app.utils.data_validator import DataValidator

@validate_json(required_fields=["name", "db_type", "host", "port"])
def create_instance_api():
    data = request.get_json() or {}
    is_valid, error_msg = DataValidator.validate_instance_data(data)
    if not is_valid:
        # 迁移期可保留内联 JSON；第 5 步切换为上抛由全局处理器统一
        return jsonify({"error": error_msg}), 400
    return jsonify({"message": "实例创建成功"}), 201
```
- CSRF 装饰器（示例）：
```python
from functools import wraps
from flask import request
from flask_wtf.csrf import validate_csrf, CSRFError

def require_json_csrf(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-CSRFToken")
        if not token:
            raise CSRFError("CSRF_MISSING")
        validate_csrf(token)
        return f(*args, **kwargs)
    return wrapper
```

—— 本统一计划文件为执行主线，专题文档保留作背景与细则参考。执行以本文件为准。