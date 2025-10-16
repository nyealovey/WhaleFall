# 清理技术债总览与修复优先级

## 背景
本项目在认证鉴权、调度器持久化、日志与错误处理、缓存与限流、输入验证、配置与环境变量、数据库迁移与测试CI等方面持续演进。为降低维护成本与提升稳定性，需要形成统一的技术债清单与修复优先级，指导近期重构工作。

## 范围与定位
- 配置与环境变量管理（`env.development`、`env.production`、`app/config.py`）
- 认证与鉴权（Flask-Login、Flask-JWT-Extended、`app/utils/decorators.py`）
- 日志与可观测性（`app/models/unified_log.py`、`app/utils/logging_config.py`）
- 错误处理与异常分类（`app/utils/error_handler.py`、`app/utils/api_response.py`）
- 调度器与后台任务（`app/scheduler.py`、`app/routes/scheduler.py`）
- 数据库模型与迁移一致性（`app/models/*`、`migrations/versions/*`）
- 缓存与限流重复性（`app/utils/cache_manager.py`、`app/services/cache_manager.py`、`app/utils/rate_limiter.py`）
- API设计与输入验证（`app/utils/validation.py`、`app/utils/data_validator.py`、`app/routes/*`）
- 前端与CSRF统一性（`app/static/js/pages/auth/login.js`、`/auth/api/csrf-token`）
- 测试覆盖率与CI管线（`tests/*`、`.github/workflows/*`）

## 修复优先级
- P0（立即修复）
  - 统一 API 的认证/授权失败响应为 JSON，包含 `code/message/trace_id`。
  - 登录、改密等敏感端点接入限流与审计日志（统一使用 `utils/rate_limiter.py`）。
  - APScheduler 持久层改为外部数据库并通过环境变量配置，避免生产环境 SQLite 锁争用。
  - 集中化配置与环境变量校验，强制检查 `SECRET_KEY`、`JWT_SECRET_KEY` 强度与存在性。
  - 为日志注入 `request_id/user_id/job_id` 等上下文标识，统一结构化 JSON 输出。
- P1（短期内修复）
  - 权限命名规范（对象域 + 操作）并与 `permission_config.py` 对齐，例如：`instance.view`、`instance.update`、`admin.manage`。
  - 统一 CSRF 使用方式与前端集成规范：表单隐藏字段 + AJAX `X-CSRFToken`。
  - 引入错误层级与错误码表，完善 `error_handler.py` 映射规则与日志等级。
  - 统一缓存管理器与 TTL 策略，移除重复实现，建立命名空间前缀便于批量失效。
  - 任务重试/退避/幂等支持，统一调度器错误路径与指标采集。
- P2（中期优化）
  - 迁移脚本规范化与数据库契约测试（空库升级、旧库升级校验）。
  - 指标与告警体系完善（如 Prometheus 指标与阈值告警）。
  - 文档化环境变量清单与默认值建议，补充示例配置与使用说明。

## 具体行动项
- 配置与环境变量
  - 在 `app/config.py` 集中读取与校验变量；缺失或弱强度时启动失败。
  - 将 APScheduler JobStore 连接串改为环境变量（支持 `sqlite/postgres/mysql`）。
- 认证与鉴权
  - 规范 `permission_required` 与其包装装饰器的 JSON 错误响应结构与日志。
  - 对 `/auth/api/login`、`/auth/api/change-password` 接入 `rate_limit` 并记录审计事件。
- 日志与错误处理
  - 注入 `trace_id/request_id/user_id/job_id` 到日志 `context` 字段；统一结构化 JSON 格式器。
  - 在 `error_handler.py` 实现异常层级到标准响应与日志等级的映射。
- 调度器与后台任务
  - 改造 JobStore 持久层为外部数据库；统一内部时间为 `UTC`，界面按用户时区。
  - 引入任务重试（次数、指数退避）与幂等标识；统一失败上报。
- 数据库模型与迁移
  - 将 `alembic upgrade head` 与 schema 契约测试加入 CI；核对模型/迁移一致性。
- 缓存与限流
  - 保留 `utils/cache_manager.py` 作为统一层；合并服务层特定缓存并规范 TTL。
  - 移除 `decorators.py` 的限流占位，统一使用 `utils/rate_limiter.py`。
- API与输入验证
  - 编写通用验证装饰器（如 `@validate_json(schema)`）；关键路由定义请求/响应 schema。
- 前端与CSRF
  - 文档化统一获取与注入流程；测试覆盖需要 CSRF 的路由。
- 测试与CI
  - 在 CI 执行 `pytest --cov` 并设置最小覆盖率阈值；加入 `scripts/validate_env.sh` 与迁移校验。

## 参考与关联文档
- `docs/refactoring/error_handling_unification.md`
- `docs/refactoring/timezone_and_loglevel_unification.md`

## 推进策略（建议）
- Sprint-1：完成 P0 项目并在 CI 中建立质量门槛。
- Sprint-2：推进 P1 的权限、CSRF、错误码与缓存统一。
- Sprint-3：完善 P2 的迁移契约测试与指标/告警体系，收尾文档化。