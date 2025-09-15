# 泰摸鱼吧 - 上下文日志系统使用指南

## 概述

泰摸鱼吧的上下文日志系统为每个功能模块提供了专门的日志记录功能，确保日志包含丰富的业务上下文信息，便于问题排查和系统监控。

## 核心组件

### 1. 上下文管理器 (ContextManager)

位置：`app/utils/context_manager.py`

负责构建和管理各模块的上下文信息，包括：
- 基础上下文（请求信息、用户信息等）
- 业务上下文（基于各模块的字段定义）
- 数据提取（从模型对象中提取上下文信息）

### 2. 模块日志记录器 (ModuleLoggers)

位置：`app/utils/module_loggers.py`

为每个功能模块提供专用的日志记录函数，包括：
- 信息日志 (log_xxx_info)
- 错误日志 (log_xxx_error)
- 警告日志 (log_xxx_warning)
- 严重错误日志 (log_xxx_critical)

### 3. 增强的Structlog配置

位置：`app/utils/structlog_config.py`

更新了上下文构建逻辑，支持：
- 模型对象自动转换
- 特殊数据类型处理
- 系统字段过滤

## 支持的功能模块

### 1. 用户认证管理 (auth)
```python
from app.utils.module_loggers import module_loggers

# 用户登录成功
module_loggers.log_auth_info(
    "用户登录成功",
    user_id=1,
    username="admin",
    role="admin",
    auth_method="password",
    ip_address="192.168.1.100"
)

# 用户登录失败
module_loggers.log_auth_error(
    "用户登录失败",
    username="admin",
    login_attempts=3,
    exception=Exception("密码错误")
)
```

### 2. 数据库实例管理 (instances)
```python
# 实例创建成功
module_loggers.log_instance_info(
    "数据库实例创建成功",
    instance_data=instance,  # Instance模型对象
    operation_type="create"
)

# 实例连接失败
module_loggers.log_instance_error(
    "数据库连接失败",
    instance_data=instance,
    connection_status="failed",
    connection_error="Connection refused",
    exception=Exception("无法连接")
)
```

### 3. 凭据管理 (credentials)
```python
# 凭据创建成功
module_loggers.log_credential_info(
    "数据库凭据创建成功",
    credential_data=credential,  # Credential模型对象
    operation_type="create"
)

# 凭据验证失败
module_loggers.log_credential_error(
    "凭据验证失败",
    credential_data=credential,
    operation_type="verify",
    exception=Exception("密码不正确")
)
```

### 4. 账户信息管理 (accounts)
```python
# 账户同步成功
module_loggers.log_account_info(
    "账户信息同步成功",
    account_data=account,  # CurrentAccountSyncData模型对象
    operation_type="sync",
    permissions_count=5
)

# 账户权限获取失败
module_loggers.log_account_error(
    "获取账户权限失败",
    account_data=account,
    operation_type="get_permissions",
    exception=Exception("权限查询超时")
)
```

### 5. 账户同步管理 (account_sync) - 重点模块
```python
# 同步开始
module_loggers.log_sync_info(
    "开始账户同步",
    instance_data=instance,
    credential_data=credential,
    sync_type="scheduled",
    sync_mode="full",
    total_accounts=100
)

# 同步成功
module_loggers.log_sync_info(
    "账户同步完成",
    instance_data=instance,
    credential_data=credential,
    sync_status="completed",
    total_accounts=100,
    synced_accounts=95,
    failed_accounts=5,
    duration=120
)

# 同步失败
module_loggers.log_sync_error(
    "账户同步失败",
    instance_data=instance,
    credential_data=credential,
    sync_status="failed",
    error_count=5,
    last_error="连接超时",
    retry_count=3,
    exception=Exception("数据库连接超时")
)
```

### 6. 账户分类管理 (account_classification)
```python
# 分类成功
module_loggers.log_classification_info(
    "账户分类成功",
    classification_data=classification,  # AccountClassification模型对象
    rule_data=rule,  # ClassificationRule模型对象
    account_data=account,  # CurrentAccountSyncData模型对象
    classification_result="特权账户",
    confidence_score=0.95,
    matched_permissions=["GRANT", "SUPER"],
    classification_reason="匹配特权权限规则"
)

# 分类失败
module_loggers.log_classification_error(
    "账户分类失败",
    classification_data=classification,
    rule_data=rule,
    account_data=account,
    exception=Exception("规则评估异常")
)
```

### 7. 定时任务管理 (tasks)
```python
# 任务执行成功
module_loggers.log_task_info(
    "任务执行成功",
    task_data=task,  # Task模型对象或字典
    execution_status="completed",
    duration=300,
    records_processed=1000
)

# 任务执行失败
module_loggers.log_task_error(
    "任务执行失败",
    task_data=task,
    execution_status="failed",
    error_count=5,
    last_error="数据库连接失败",
    exception=Exception("连接超时")
)
```

### 8. 同步会话管理 (sync_sessions)
```python
# 会话开始
module_loggers.log_sync_session_info(
    "同步会话开始",
    session_data=session,  # SyncSession模型对象或字典
    target_instances=[1, 2, 3, 4, 5],
    target_database_types=["MySQL", "PostgreSQL"]
)

# 会话完成
module_loggers.log_sync_session_info(
    "同步会话完成",
    session_data=session,
    status="completed",
    progress_percentage=100.0,
    duration=1800
)
```

### 9. 系统管理 (admin)
```python
# 配置更新
module_loggers.log_admin_info(
    "系统配置更新",
    operation_type="config",
    operation_name="update_config",
    config_key="sync_interval",
    old_value="3600",
    new_value="1800",
    admin_user_id=1,
    admin_username="admin"
)

# 用户管理
module_loggers.log_admin_info(
    "用户角色更新",
    operation_type="user",
    operation_name="update_user_role",
    target_user_id=2,
    target_username="user1",
    old_value="user",
    new_value="admin"
)
```

### 10. 日志管理 (unified_logs)
```python
# 日志查询
module_loggers.log_logs_info(
    "日志查询完成",
    query_type="search",
    search_term="error",
    result_count=50,
    query_duration=0.5
)

# 日志导出
module_loggers.log_logs_info(
    "日志导出完成",
    query_type="export",
    export_format="csv",
    export_size=1024000,
    export_status="completed"
)
```

### 11. 健康监控 (health)
```python
# 系统健康检查
module_loggers.log_health_info(
    "系统健康检查完成",
    check_type="system",
    check_name="system_health",
    check_status="healthy",
    memory_usage=75.5,
    cpu_usage=45.2,
    disk_usage=60.8
)

# 服务异常
module_loggers.log_health_error(
    "服务响应异常",
    check_type="service",
    check_name="api_response",
    check_status="critical",
    response_time=5000.0,
    error_rate=15.5,
    exception=Exception("服务响应超时")
)
```

## 上下文字段说明

每个模块都有预定义的上下文字段，确保日志信息的一致性和完整性。主要字段类型包括：

### 基础字段
- `user_id`: 用户ID
- `username`: 用户名
- `role`: 用户角色
- `ip_address`: IP地址
- `user_agent`: 用户代理
- `timestamp`: 时间戳

### 实例相关字段
- `instance_id`: 实例ID
- `instance_name`: 实例名称
- `db_type`: 数据库类型
- `host`: 主机地址
- `port`: 端口号
- `environment`: 环境类型

### 同步相关字段
- `sync_type`: 同步类型
- `sync_status`: 同步状态
- `total_accounts`: 总账户数
- `synced_accounts`: 已同步账户数
- `failed_accounts`: 失败账户数
- `duration`: 持续时间

### 分类相关字段
- `classification_id`: 分类ID
- `classification_name`: 分类名称
- `risk_level`: 风险级别
- `rule_id`: 规则ID
- `rule_name`: 规则名称
- `classification_result`: 分类结果

## 最佳实践

### 1. 使用模型对象
```python
# 推荐：传递模型对象
module_loggers.log_instance_info(
    "实例创建成功",
    instance_data=instance  # Instance模型对象
)

# 不推荐：手动传递字段
module_loggers.log_instance_info(
    "实例创建成功",
    instance_id=instance.id,
    instance_name=instance.name,
    db_type=instance.db_type
)
```

### 2. 包含异常信息
```python
# 推荐：包含异常对象
module_loggers.log_sync_error(
    "同步失败",
    instance_data=instance,
    exception=e  # Exception对象
)

# 不推荐：只包含异常消息
module_loggers.log_sync_error(
    "同步失败",
    instance_data=instance,
    error_message=str(e)
)
```

### 3. 提供足够的上下文
```python
# 推荐：提供完整的业务上下文
module_loggers.log_sync_info(
    "账户同步完成",
    instance_data=instance,
    credential_data=credential,
    sync_type="scheduled",
    sync_status="completed",
    total_accounts=100,
    synced_accounts=95,
    failed_accounts=5,
    duration=120
)

# 不推荐：上下文信息不足
module_loggers.log_sync_info(
    "同步完成"
)
```

### 4. 使用适当的日志级别
- `log_xxx_info`: 正常操作信息
- `log_xxx_warning`: 警告信息
- `log_xxx_error`: 错误信息
- `log_xxx_critical`: 严重错误信息

## 测试和调试

### 运行测试示例
```python
from app.utils.logging_examples import LoggingExamples

examples = LoggingExamples()
examples.example_sync_logging()  # 测试同步日志
examples.example_classification_logging()  # 测试分类日志
```

### 查看日志输出
日志会输出到控制台和数据库，可以通过日志中心查看详细的上下文信息。

## 注意事项

1. **性能考虑**: 避免在循环中记录大量日志
2. **敏感信息**: 不要在日志中记录密码等敏感信息
3. **日志级别**: 合理使用日志级别，避免日志噪音
4. **异常处理**: 确保日志记录本身不会抛出异常
5. **上下文完整性**: 确保提供足够的上下文信息便于问题排查

## 扩展和自定义

### 添加新的上下文字段
在 `ContextManager.MODULE_CONTEXT_FIELDS` 中添加新字段定义。

### 添加新的模块日志记录器
在 `ModuleLoggers` 类中添加新的日志记录方法。

### 自定义上下文提取器
在 `ContextManager` 中添加新的数据提取方法。

---

通过使用这个上下文日志系统，您可以获得更加详细和结构化的日志信息，大大提高问题排查和系统监控的效率。
