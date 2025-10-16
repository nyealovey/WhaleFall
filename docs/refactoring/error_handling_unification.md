> 注意：本文件已被《统一改造执行计划》整合与编排。执行请以 `docs/refactoring/unified_refactoring_plan.md` 为准；本文件保留作专题说明与背景参考。

# 日志与错误处理统一方案（无过渡兼容，强制版）
 
 本文档在上一版“错误处理统一与重复模式消除方案”的基础上，采纳“无过渡兼容”的强制统一策略：立即淘汰所有旧有日志与错误响应入口，全面切换到 `app/utils/structlog_config.py` 提供的统一实现。
 
 全局声明：所有日志与错误响应必须使用 `structlog_config.py` 中的函数与装饰器，无例外。
 
 ## 方案摘要
 - 单一中心文件：日志配置、过滤、上下文增强、错误处理全部合并在 `structlog_config.py`。
 - 强制统一响应：错误返回统一采用增强错误结构（例如 `{"error": true, "error_id", "category", "severity", "message", "timestamp"}`），不再输出旧的 `{"success": false, ...}` 或 `APIResponse.error(...)`。
 - 全量迁移：删除冗余文件与入口，移除标准库 `logging` 使用痕迹，统一切换到 `structlog`。
 - 无过渡兼容：前端/调用方必须立即适配新的错误结构；后端不再提供桥接层。
 
 ## 强制统一原则
 - 文件中心：仅 `structlog_config.py` 提供日志记录器、便捷函数与错误处理器。
 - 日志系统：只使用 `log_info/log_warning/log_error/log_critical/log_debug` 与专用记录器 `get_system_logger/get_api_logger/...`。
 - 错误响应：只使用增强错误处理器 `enhanced_error_handler` 的输出结构；端点不要本地构造旧格式。
 - 异常策略：路由/服务层禁止通用 `try/except Exception` 本地返回；让异常上抛，由全局处理器统一响应。仅对明确的业务/校验异常进行显式抛出或转换。
 - 配置与过滤：DEBUG 过滤整合到 `structlog` 的 processors，开关由环境变量控制；时间与时区统一由 `time_utils` 管理。
 
 ## 清理与合并（必须执行）
 - 删除文件：
   - `app/utils/logging_config.py`
   - `app/utils/debug_log_filter.py`
   - `app/utils/error_handler.py`
   - `app/utils/api_response.py`（用新的响应工具函数替代）
 - 保留并强化：
   - `app/utils/structlog_config.py`：唯一中心，提供日志入口、上下文绑定、装饰器与增强错误处理器；简化 `SQLAlchemyLogHandler`，统一时间处理。
 
 ## 响应工具（建议加入 structlog_config.py）
 - `unified_success_response(data=None, message=None, status=200) -> dict`（规划新增）
   - 返回统一成功结构：`{"error": false, "data": data, "message": message, "timestamp": ...}`。
 - `enhanced_error_handler(error: Exception) -> dict`（已存在）
   - 生成统一错误结构：`{"error": true, "error_id", "category", "severity", "message", "timestamp", "recoverable", "suggestions"}`。
 - `unified_error_response(error: Exception, status_code: int | None = None, extra: dict | None = None) -> dict`（规划新增）
   - 用于极少数需要在本地提前返回的场景，内部调用 `enhanced_error_handler` 形成统一结构；常规场景应直接上抛异常，由全局处理器接管。
 
 ## 全局替换规则（机械化执行）
 - 替换日志入口：
   - 将 `import logging` 与 `logger = logging.getLogger(__name__)` 全局替换为：
     - `from app.utils.structlog_config import get_system_logger, log_info, log_warning, log_error, log_debug`
     - 如需绑定记录器：`logger = get_system_logger()` 或使用便捷函数直接记录。
 - 替换成功/错误返回：
   - `APIResponse.success(...)` → `jsonify(unified_success_response(...))`（如未实现，可直接构造统一成功结构：`jsonify({"error": False, "data": ..., "message": ...})`）
   - `APIResponse.error(...)` / `error_response(...)` / `jsonify({"success": False, ...})` → 移除本地返回，改为上抛异常或（极少数场景）`jsonify(unified_error_response(error))`
 - 移除通用本地异常捕获：
   - 删除端点与服务中的 `try/except Exception`，让异常上抛。
   - 对可预期的业务/校验错误，抛出自定义异常（例如 `ValidationError/BusinessLogicError/SecurityError`），由全局错误处理器分类。
 - 添加装饰器（按需）：
   - `@error_handler`：在需要统一错误响应的函数/端点上使用。
   - `@error_monitor`：仅记录增强日志但继续上抛异常的监控场景使用。
 
 ## 应用入口更新（app/__init__.py）
 - 初始化与注册：
   - `from app.utils.structlog_config import configure_structlog, enhanced_error_handler`
   - 在应用创建时调用 `configure_structlog(app)`。
   - 注册全局错误处理器：
     ```python
     from flask import jsonify
     from app.utils.structlog_config import enhanced_error_handler

     @app.errorhandler(Exception)
     def handle_exception(error):
         payload = enhanced_error_handler(error)
         # 当前 enhanced_error_handler 返回 dict，由装饰器/调用方决定状态码
         # 如需映射不同异常到不同状态码，可在此处扩展
         return jsonify(payload), 500
     ```
 
 ## 自定义异常与分类
 - 所有业务异常统一迁移到 `structlog_config.py`（或其引用的统一异常模块）进行分类：
   - 分类字段：`category`（如 `validation|business|security|system`）、`severity`（如 `warning|error|critical`）。
   - 路由/服务应抛出对应异常类型或使用辅助函数将外部异常映射为统一分类。
 
 ## 测试与验证（必须通过）
 - 响应结构校验：
   - 端点错误返回包含 `error=true`、`error_id`、`category`、`severity`、`message`、`timestamp` 等字段。
 - 日志落库校验：
   - 触发错误与警告场景后，`UnifiedLog` 中出现规范化条目，且无 `DEBUG` 级别落库。
 - 残留扫描：
   - 全局搜索不应出现 `logging.getLogger`、`APIResponse.*`、`error_response(...)`、`{"success": False,...}`。
 - 装饰器行为：
   - 带 `@error_handler` 的端点在严重错误时能直接返回统一结构；`@error_monitor` 场景仅记录日志且异常继续上抛。
 
 ## 禁止事项（立即生效）
 - 禁止使用标准库 `logging` 作为业务日志入口。
 - 禁止在路由/服务中返回旧的 `{"success": False, ...}` 或 `APIResponse.error(...)`。
 - 禁止在通用异常场景下本地构造错误响应；统一由全局处理器完成。
 - 除脚本型 CLI 输出（`scripts/` 目录）外，禁止使用 `print(...)`，应改用 `log_info/log_warning`。
 
 ## 迁移步骤（强制执行）
 - 第 0 步：用新实现覆盖 `structlog_config.py`（包含统一日志入口、装饰器、增强错误处理器与响应工具函数）。
 - 第 1 步：删除冗余文件：`logging_config.py`、`debug_log_filter.py`、`error_handler.py`、`api_response.py`。
 - 第 2 步：更新 `app/__init__.py`，注册全局 `@app.errorhandler(Exception)` 并返回 `jsonify(enhanced_error_handler(error))` 的输出。
 - 第 3 步：全局替换日志与错误返回入口（见“全局替换规则”），移除通用 `try/except Exception`。
 - 第 4 步：补充/更新测试用例，覆盖数据库异常、权限异常、校验异常、未知异常等路线。
 - 第 5 步：残留检查与质量门禁（CI）：禁止提交含旧入口与结构的代码。
 
 ## 参考代码片段
 - 路由示例（上抛统一处理）：
  ```python
   from flask import Blueprint, jsonify
   from app.utils.structlog_config import log_info, error_handler

   bp = Blueprint("users", __name__)

   @bp.route("/api/users/<int:user_id>")
   @error_handler
   def api_get_user(user_id):
       # 仅抛出业务异常/校验异常，其他异常由装饰器/全局处理器统一响应
       user = User.query.get_or_404(user_id)  # 未找到将上抛
       log_info("获取用户信息成功", module="users", user_id=user_id)
       # 统一成功结构（如已实现 unified_success_response，可切换）：
       return jsonify({
           "error": False,
           "data": {"user": user.to_dict()},
           "message": "操作成功"
       })
  ```
 - 服务示例（监控记录并上抛）：
   ```python
   from app.utils.structlog_config import error_monitor
 
   class ConnectionTestService:
       @error_monitor
       def test_connection(self, instance):
           # 测试逻辑；异常将被记录并继续上抛
           ...
   ```
 - 全局错误处理器：
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
 
 ## 验收标准
 - 代码库中不再存在：`logging.getLogger(__name__)`、`APIResponse.*`、`error_response(...)`、`jsonify({"success": False, ...})`、无意义的 `print(...)`。
 - 错误响应结构统一且包含必需字段；前端已完成适配并通过集成测试。
 - 日志统一通过 `structlog` 入口记录，`UnifiedLog` 落库结构完整、上下文丰富。
 
 —— 本方案为强制统一版本；审阅通过后请按“迁移步骤”执行并提交重构 PR。

 ## 技术债盘点与优先级矩阵（执行导向）
 - 日志入口混用（高优先级）：`logging.getLogger(__name__)`、`app.logger` 残留 → 全部替换为 `get_system_logger/log_*`。
 - 错误返回不统一（高优先级）：`APIResponse.error/error_response/jsonify({"success": False,...})` → 统一为上抛异常或 `unified_error_response(...)`。
 - 通用 `try/except Exception` 本地返回（高优先级）：移除通用捕获，保留明确业务/校验异常并上抛。
 - 冗余文件与入口（中优先级）：`logging_config.py`、`debug_log_filter.py`、`error_handler.py`、`api_response.py` 删除。
 - 直接 `print(...)`（中优先级）：迁移为 `log_info/log_warning`；CLI 脚本例外并注明界限。
 - 文档/测试缺口（中优先级）：补齐端点错误场景测试与统一响应说明。

 ## 分批行动计划（精确到文件）
 - 批次 A（基础设施清理）
   - 删除：`app/utils/logging_config.py`、`app/utils/debug_log_filter.py`、`app/utils/error_handler.py`、`app/utils/api_response.py`。
   - 更新：`app/__init__.py` 注册 `@app.errorhandler(Exception)`，调用 `enhanced_error_handler` 并 `jsonify` 返回。
   - 强化：`app/utils/structlog_config.py` 增加/确认 `unified_success_response`、`unified_error_response`、`error_handler`、`error_monitor`、`configure_structlog`。
 
 - 批次 B（路由层统一）
   - 强制替换与移除通用捕获的文件：
     - `app/routes/tags.py`、`app/routes/users.py`、`app/routes/scheduler.py`、`app/routes/instances.py`、`app/routes/partition.py`、`app/routes/logs.py`、`app/routes/health.py`。
   - 具体动作：
     - 删除 `try/except Exception` 本地返回；对 `404/权限/校验` 等明确异常，抛出自定义异常。
     - 替换旧返回：
       `APIResponse.success` → `jsonify(unified_success_response(...))`
       `APIResponse.error/error_response/jsonify({"success": False,...})` → 异常上抛或 `jsonify(unified_error_response(error))`（少数场景）。
     - 日志统一：移除 `logging.getLogger(...)`，改用 `log_info/log_error` 或 `get_system_logger()`。

 - 批次 C（服务与任务层统一）
   - 目标文件：`app/tasks/partition_management_tasks.py`、`app/tasks/database_size_collection_tasks.py`、`app/services/partition_management_service.py` 等。
   - 具体动作：统一记录器入口；为关键对外函数加 `@error_monitor`；移除标准 `logging` 与本地错误结构。

 - 批次 D（工具与打印输出）
   - 目标文件：`app/utils/constants_manager.py`、`app/utils/constants_monitor.py`、`app/utils/constants_doc_generator.py`、`app/utils/constants_validator.py`、`app/models/user.py`。
   - 具体动作：将 `print(...)` 替换为 `log_info/log_warning` 并绑定上下文；CLI-only 脚本在文档中标注边界。

 ## 自动化迁移命令片段（可直接使用/改造）
 - 搜索残留（建议用 `ripgrep`）：
   - `rg -n "logging.getLogger\(__name__\)|app\.logger" app/`
   - `rg -n "APIResponse\.(success|error)|error_response\(|jsonify\(\{\s*\"success\":\s*False" app/`
   - `rg -n "try:\n[\s\S]{0,200}?except\s+Exception" app/`
   - `rg -n "\bprint\s*\(" app/`
 - 批量替换（谨慎审阅后执行）：
   - 标准日志入口替换（示例脚本）：
     ```bash
     #!/usr/bin/env bash
     files=$(rg -l "logging.getLogger\(__name__\)")
     for f in $files; do
       perl -0777 -pe 's/import\s+logging\s*\n//g; s/logger\s*=\s*logging\.getLogger\(__name__\)/from app.utils.structlog_config import get_system_logger\nlogger = get_system_logger()/g' -i "$f"
     done
     ```
   - 错误返回统一（示例策略）：人工审阅替换点 → 删除本地错误返回 → 改为上抛异常或使用 `unified_error_response`。

 ## CI 质量门禁与禁用模式
 - 在 `pre-commit` 增加自定义检查脚本（示例 `scripts/quality/banned_patterns.py`）：
   - 禁止：`logging.getLogger(__name__)`、`app.logger`、`APIResponse.*`、`error_response(`、`jsonify({"success": False`、`print(`（非 `scripts/`）。
   - 发现则退出非零状态并提示文件与行号。
 - 在 CI（GitHub Actions）中加入同样的检查步骤；PR 必须通过门禁才可合并。

 ## 测试清单与验收指标
 - 测试维度：
   - 路由错误场景：DB 异常、权限异常、校验异常、未知异常 → 响应含 `error=true`、`error_id/category/severity/message/timestamp`。
   - 装饰器行为：`@error_handler` 返回统一结构；`@error_monitor` 只记录并上抛。
   - 日志落库：`UnifiedLog` 中 INFO+ 级别落库；无 DEBUG 落库；上下文包含 `request_id/user_id/module`。
 - 验收量化指标：
   - 被禁模式出现次数为零（见上文 `rg` 命令）。
   - 随机抽样 10 个端点错误场景通过集成测试。
   - 前端适配完成（解析统一错误结构），UI 无旧结构依赖。

 ## 风险与回滚（无兼容前提下）
 - 风险：前端或外部依赖旧结构；需同步适配时间与资源。
 - 回滚策略：如出现严重阻塞，按提交粒度回滚对应批次；不引入后端兼容层。

 ## 附录 A：常见替换映射表
 - `logging.getLogger(__name__)` → `from app.utils.structlog_config import get_system_logger; logger = get_system_logger()`
 - `app.logger.*` → `log_info/log_warning/log_error`（绑定 `module`）。
 - `APIResponse.success(...)` → `jsonify(unified_success_response(...))`（如未实现则直接构造统一成功结构）
 - `APIResponse.error(...)` / `error_response(...)` / `jsonify({"success": False, ...})` → 上抛异常或 `jsonify(unified_error_response(error))`
 - `print(...)`（非 CLI）→ `log_info/log_warning`。

 ## 附录 B：搜索模板（复制即用）
 - `rg -n "logging.getLogger\(__name__\)" app/`
 - `rg -n "app\.logger\.(info|error|warning|debug)\(" app/`
 - `rg -n "APIResponse\.(success|error)\(" app/`
 - `rg -n "error_response\(" app/`
 - `rg -n "jsonify\(\{\s*\"success\":\s*False" app/`
  - `rg -n "\bprint\s*\(" app/`

## 涉及代码位置
- `app/utils/structlog_config.py`（统一日志、错误处理、响应工具）
- `app/__init__.py`（注册全局错误处理器）
- `app/routes/*.py`（移除通用 try/except，统一日志与错误返回）
- `app/services/*.py`、`app/tasks/*.py`（统一日志入口与错误监控）
- （清理）`app/utils/logging_config.py`、`app/utils/error_handler.py`