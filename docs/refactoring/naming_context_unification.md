# 命名约定与上下文字段统一规范

目标
- 统一变量与字段命名，避免同义不同名与中英文混用。
- 统一日志上下文字段，保证结构化落库一致。

命名约定
- 统一使用 `snake_case`。
- ID 命名统一：`instance_id`, `credential_id`, `account_id`, `user_id`。
- 状态与布尔：`is_active`, `is_valid`, `is_admin`。
- 时间字段：`created_at`, `updated_at`，统一用 `time_utils.now()`（东八区）。
- 错误码：全大写 + 下划线，如 `VALIDATION_ERROR`。

日志上下文字段
- 基础：`request_id`, `user_id`, `module`, `ip_address`, `user_agent`, `url`, `method`。
- 业务：按模块补充（如 `instance_id`, `credential_id` 等）。
- 避免重复语义：不要混用 `uid` / `user_id`。

落地建议
- 在 `structlog_config` 的 `LogContext` 或 `bind_context` 统一添加字段。
- 代码 review 阶段按此规范检查 PR。