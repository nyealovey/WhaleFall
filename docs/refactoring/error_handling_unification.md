

# 日志与错误处理统一方案（无过渡兼容，强制版）

本方案在上一版“错误处理统一与重复模式消除方案”的基础上，采纳“无过渡兼容”的策略：所有组件立即切换到统一日志与错误响应堆栈，旧实现不再提供桥接或兼容层。前端与第三方调用方必须同步适配新的响应结构。

## 1. 目标与策略
- 强制统一日志入口、异常定义与错误响应格式，彻底移除标准库 `logging`、`APIResponse` 等遗留工具。
- 通过模块拆分与职责收敛，降低 `structlog_config.py` 的复杂度，避免后续扩展继续恶化结构。
- 提供可执行的迁移步骤、搜索脚本与测试清单，确保一次性完成迁移并具备回滚方案。

## 2. 模块职责拆分
- `app/utils/structlog_config.py`
- 只负责 structlog 初始化、logger 工厂、上下文绑定与装饰器（`log_*` / `get_*_logger` 等）。
  - 不定义业务异常、枚举或错误响应结构；相关常量通过参数注入或从常量模块引用。
- `app/utils/response_utils.py`（新增）
  - 提供 `unified_success_response`、`unified_error_response` 等响应构造函数，专注于 JSON 结构和默认字段。
  - 内部调用 `enhanced_error_handler` 生成错误载荷；避免路由直接拼装字典。
- `app/errors/__init__.py`（或同名单一文件）
  - 集中定义业务异常层次结构和 `EXCEPTION_STATUS_MAP`。
  - 异常类接受 `message_code` / `payload` 等参数，禁止写死文案；文案从 `app/constants/system_constants.py` 的 `ErrorMessages`、`SuccessMessages` 获取。
- `app/constants/system_constants.py` / `app/constants/sync_constants.py`
  - 维护日志/错误相关枚举与系统默认值（`LogLevel`、`ErrorCategory`、`ErrorSeverity`、默认日志级别、日志文件路径、保留天数等）。
  - 任何新增枚举或常量必须在此补齐，结构化引用，禁止在日志/错误处理模块硬编码。

> 说明：通过职责拆分，既满足“统一入口”的目标，又避免单文件体积过大、相互依赖混乱的问题。

## 3. 强制统一原则
- 日志只允许通过 `log_info/log_warning/log_error/log_debug/log_critical` 或指定 logger（例如 `get_system_logger()`、`get_api_logger()`）。
- 错误响应必须产出统一结构：`{"error": true, "error_id": "...", "category": "...", "severity": "...", "message": "...", "timestamp": "...", "recoverable": bool, "suggestions": []}`。
- 路由/服务层禁止捕获 `Exception` 后自建响应；除显式业务异常外，一律上抛由全局 handler 接管。
- DEBUG 过滤、时间/时区统一由 `structlog` processors 与 `app/utils/time_utils.py` 承担；禁止重复实现。
- 命令行脚本默认仍可使用 `print`，但必须在文档中列出白名单脚本；非白名单脚本改用日志接口。

## 4. 清理与新增文件
- 必须删除：
  - `app/utils/logging_config.py`
  - `app/utils/debug_log_filter.py`
  - `app/utils/error_handler.py`
  - `app/utils/api_response.py`
- 必须新增或扩写：
  - `app/utils/structlog_config.py`：完成职责收敛后补充统一日志接口、装饰器与 `enhanced_error_handler`。
  - `app/utils/response_utils.py`：新增成功/错误响应工具函数。
  - `app/errors/__init__.py`：新增业务异常基类、子类与状态码映射。
- 若已有文件内容被迁移，请在 PR 中标注删除原因与新位置，以便审阅。

## 5. 状态码与异常映射
- 在 `app/errors/__init__.py` 定义异常层次结构，并提供 `EXCEPTION_STATUS_MAP`：
  - `ValidationError` → 400
  - `AuthenticationError` → 401
  - `AuthorizationError` → 403
  - `NotFoundError` → 404
  - `ConflictError` → 409
  - `RateLimitError` → 429
  - `ExternalServiceError` → 502
  - `DatabaseError` / `SystemError` → 500
- 全局错误处理器实现：
  - 如异常继承自 `HTTPException`，优先读取 `error.code`。
  - 如异常定义了 `status_code` 属性，优先使用。
  - 否则从 `EXCEPTION_STATUS_MAP` 读取，缺省回退 500。
  - 支持记录 `extra_context` 供 `unified_error_response` 使用。
- 所有异常类禁止在构造函数中硬编码消息文本；使用 `ErrorMessages` / `SuccessMessages` 的键值并在响应阶段组装文案。

## 6. 统一响应结构规范
- `unified_success_response(data=None, message=None, status=200, meta=None)`：
  - 默认字段：`error=false`、`data`、`message`、`timestamp`、`meta`。
  - `message` 缺省取 `SuccessMessages.OPERATION_SUCCESS`；`timestamp` 采用 ISO8601（UTC）字符串。
- `enhanced_error_handler(error: Exception)`：
  - 返回包含 `error_id`（UUID4）、`category`、`severity`、`message_code`、`message`、`timestamp`、`recoverable`、`suggestions`、`context`。
  - `category` / `severity` 来源于异常定义，默认回退 `ErrorCategory.system`、`ErrorSeverity.error`。
- `unified_error_response(error: Exception, *, status_code=None, extra=None)`：
  - 封装 `enhanced_error_handler` 并允许调用方补充 `extra` 字段（如 `trace_id`）。
  - 当 `status_code` 为空，按照第 5 节的映射获得最终 HTTP 状态码。
- 文档中必须说明：前端解析 `error_id` 用于错误追踪；如需国际化，`message_code` 供客户端进行二次翻译。

## 7. 迁移步骤
1. **基础设施更新**
   - 重写 `structlog_config.py`，抽离与日志无关的逻辑。
   - 新增 `response_utils.py`、`app/errors/__init__.py` 并编写初版单元测试。
2. **全局错误处理器改造**
   - 在 `app/__init__.py` 中调用 `configure_structlog(app)`。
   - 注册 `@app.errorhandler(Exception)`，内部调用 `unified_error_response(error)` 并返回状态码。
   - 对 `HTTPException` 保留原始状态码与 headers。
3. **批次化迁移业务代码**
   - 批次 A（基础设施）：确认旧文件删除、配置无残留。
   - 批次 B（路由层）：处理 `app/routes/` 下所有蓝图，包括 streaming/SSE/第三方回调路由，确保移除 `logging`、`APIResponse`、`try: ... except Exception`。
   - 批次 C（服务与任务）：覆盖 `app/services/`、`app/tasks/` 以及 scheduler，统一 logger 与装饰器。
   - 批次 D（工具模块）：`app/utils/**`、`app/models/**` 内的打印与日志调用全部替换；明确 CLI 白名单。
   - 批次 E（其余入口）：例如 `app/api/`、`app/websocket/`、`middleware/` 等非主流路径，逐一审查。
4. **前端与外部依赖同步**
   - 发送错误结构示例给前端与第三方团队，约定字段与生效时间。
   - 如需灰度，为 API 增加版本头或网关路由，确保在发布窗口内同步上线。
5. **测试与回归**
   - 运行新增单测、覆盖率、集成测试，确保统一响应与日志落库正常。
6. **残留扫描与审阅**
   - 使用第 9 节命令扫描，审阅 PR，确保禁用模式为零。

## 8. 覆盖范围与遗漏检查
- 必查路径：
  - `app/routes/**`、`app/api/**`、`app/websocket/**`
  - `app/services/**`、`app/tasks/**`、`app/scheduler.py`
  - 启动与配置模块：`app/__init__.py`、`wsgi.py`、初始化脚本
  - 工具与模型层：`app/utils/**`、`app/models/**`、`app/repositories/**`
- CLI 与脚本：
  - `scripts/`、`migrations/` 下如需保留 `print` 必须注明“CLI Only”并记录在发布说明中。
- 数据落库相关：
  - 若 `UnifiedLog` 需要新增字段（如 `error_id`、`category`），必须同步 Alembic migration 并更新 ORM 模型。
- 审查 checklist：
  - 确认没有遗留 `logging.getLogger`、`app.logger`、`APIResponse`、`{"success": False}`。
  - 确认所有异常抛出都能映射到枚举与状态码，未使用魔法字符串。

## 9. 自动化辅助脚本
- 搜索旧入口（推荐使用 `rg`）：
  - `rg -n "logging\\.getLogger" app/`
  - `rg -n "from\\s+logging\\s+import\\s+getLogger" app/`
  - `rg -n "app\\.logger\\.(info|error|warning|debug|critical)" app/`
  - `rg -n "APIResponse\\.(success|error)" app/`
  - `rg -n "error_response\\(" app/`
  - `rg -n "jsonify\\(\\{\\s*\"success\"\\s*:\\s*False" app/`
  - `rg -n "try:\\n[\\s\\S]{0,200}?except\\s+Exception" app/`
  - `rg -n "\\bprint\\s*\\(" app/`
- 替换示例脚本（需人工确认后执行）：
  ```bash
  #!/usr/bin/env bash
  files=$(rg -l "logging\\.getLogger")
  for f in $files; do
    perl -0777 -pe 's/^\\s*import\\s+logging\\s*\\n//mg' -i "$f"
    perl -0777 -pe 's/logging\\.getLogger\\((__name__|"[^"]+")\\)/from app.utils.structlog_config import get_system_logger\\nlogger = get_system_logger()/g' -i "$f"
  done
  ```
- 执行脚本前务必手动备份或在单独分支操作，避免误替换。

## 10. 测试与验证计划
- **单元测试**
  - `tests/unit/utils/test_response_utils.py`：校验成功/错误响应字段、时间格式、错误码生成。
  - `tests/unit/errors/test_exception_mapping.py`：验证异常到状态码映射与默认行为。
  - `tests/unit/utils/test_structlog_config.py`：mock structlog，确认上下文处理与装饰器行为。
- **集成测试**
  - 新增 `tests/integration/errors/test_error_shapes.py`：覆盖权限、校验、数据库、外部服务异常，断言响应结构与状态码。
  - `tests/integration/logs/test_log_persistence.py`：触发 INFO/WARN/ERROR，确认 `UnifiedLog` 记录字段完整且无 DEBUG 落库。
- **覆盖率与工具**
  - 运行 `make test`、`pytest --cov=app --cov-report=term-missing`，确保关键路径被覆盖。
  - `make quality` 确认 `ruff`、`mypy` 通过，防止新模块引入类型问题。

## 11. 验收指标
- 代码库不再包含被禁模式（见第 9 节命令）。
- 任意 10 个端点在异常场景下返回统一结构，自动化测试全绿。
- 前端或第三方服务已经验证新结构并关闭旧格式逻辑。
- `UnifiedLog` 或相关落库表记录包含 `error_id`、`category`、`severity` 等字段，DEBUG 未落库。
- 发布说明中包含“统一错误结构”变更、需要同步的客户端版本与 CLI 白名单。

## 12. 风险与回滚
- **主要风险**
  - 前端或第三方未及时适配新结构导致调用失败。
  - 删除旧模块时忽略部分脚本或异步任务，导致运行时错误。
  - 日志表或监控系统未更新字段映射，引发告警缺失。
- **缓解措施**
  - 发布前至少一周通知前端/外部团队，提供示例 payload 与字段解释。
  - 在灰度环境执行全量测试，用 API gateway 或 feature flag 控制生效窗口。
  - 更新运维监控（Sentry、Prometheus、ELK）字段映射，确认新字段被正确索引。
- **回滚策略**
  - 按批次提交拆分（基础设施 → 路由 → 服务 → 工具）；出现严重阻塞时可逐批回滚提交。
  - 保留旧模块的 tag，必要时快速恢复，并在发布说明中记录回滚条件。
  - 如需紧急恢复，可在部署脚本中临时切换到旧镜像；同时通知前端恢复旧解析逻辑。

## 附录：常见替换映射
- `logging.getLogger(__name__)` → `from app.utils.structlog_config import get_system_logger` + `logger = get_system_logger()`
- `app.logger.info/error/...` → `log_info/log_error` 并补充 `module`、`request_id` 等上下文字段。
- `APIResponse.success(...)` → `jsonify(unified_success_response(...))`
- `APIResponse.error(...)` / `error_response(...)` / `jsonify({"success": False, ...})` → 抛出自定义异常或 `jsonify(unified_error_response(error))`
- `print(...)`（非白名单 CLI）→ `log_info/log_warning`
- 自定义异常散落各处 → 迁移到 `app/errors/__init__.py` 并统一继承结构
