"""鲸落 - 常量定义模块

统一管理所有魔法数字、硬编码值和配置常量.
"""

# 移除循环导入
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """错误分类枚举."""

    VALIDATION = "validation"
    BUSINESS = "business"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SECURITY = "security"
    DATABASE = "database"
    EXTERNAL = "external"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """错误严重程度枚举."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# 错误消息常量
class ErrorMessages:
    """错误消息常量."""

    # 通用错误
    INTERNAL_ERROR = "服务器内部错误"
    VALIDATION_ERROR = "数据验证失败"
    PERMISSION_DENIED = "权限不足"
    PERMISSION_REQUIRED = "需要 {permission} 权限"
    RESOURCE_NOT_FOUND = "资源不存在"
    INVALID_REQUEST = "无效的请求"
    AUTHENTICATION_REQUIRED = "请先登录"
    ADMIN_PERMISSION_REQUIRED = "需要管理员权限"
    JSON_REQUIRED = "请求必须是JSON格式"
    REQUEST_DATA_EMPTY = "请求数据不能为空"
    MISSING_REQUIRED_FIELDS = "缺少必需字段: {fields}"

    # 认证错误
    INVALID_CREDENTIALS = "用户名或密码错误"
    TOKEN_EXPIRED = "令牌已过期"
    TOKEN_INVALID = "无效的令牌"
    ACCOUNT_DISABLED = "账户已被禁用"
    ACCOUNT_LOCKED = "账户已被锁定"
    RATE_LIMIT_EXCEEDED = "请求过于频繁,请稍后再试"

    # 数据库错误
    DATABASE_CONNECTION_ERROR = "数据库连接失败"
    DATABASE_QUERY_ERROR = "数据库查询错误"
    DATABASE_TIMEOUT = "数据库操作超时"
    CONSTRAINT_VIOLATION = "数据约束错误"

    # 文件错误
    FILE_TOO_LARGE = "文件过大"
    INVALID_FILE_TYPE = "无效的文件类型"
    FILE_UPLOAD_ERROR = "文件上传失败"
    FILE_NOT_FOUND = "文件不存在"

    # 业务错误
    INSTANCE_NOT_FOUND = "数据库实例不存在"
    CREDENTIAL_INVALID = "凭据无效"
    TASK_EXECUTION_FAILED = "任务执行失败"
    SYNC_DATA_ERROR = "数据同步错误"


# 成功消息常量
class SuccessMessages:
    """成功消息常量."""

    # 通用成功
    OPERATION_SUCCESS = "操作成功"
    DATA_SAVED = "数据保存成功"
    DATA_DELETED = "数据删除成功"
    DATA_UPDATED = "数据更新成功"

    # 认证成功
    LOGIN_SUCCESS = "登录成功"
    LOGOUT_SUCCESS = "登出成功"
    PASSWORD_CHANGED = "密码修改成功"
    PROFILE_UPDATED = "资料更新成功"

    # 业务成功
    INSTANCE_CREATED = "实例创建成功"
    INSTANCE_UPDATED = "实例更新成功"
    INSTANCE_DELETED = "实例删除成功"
    TASK_CREATED = "任务创建成功"
    TASK_EXECUTED = "任务执行成功"
    SYNC_COMPLETED = "同步完成"


# 导出所有常量
__all__ = [
    "ErrorCategory",
    "ErrorMessages",
    "ErrorSeverity",
    "LogLevel",
    "SuccessMessages",
]
