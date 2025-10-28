"""
鲸落 - 常量定义模块
统一管理所有魔法数字、硬编码值和配置常量
"""

# 移除循环导入
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """错误分类枚举"""

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
    """错误严重程度枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# 系统常量
class SystemConstants:
    """系统常量"""

    # 分页常量
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1

    # 密码常量
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_HASH_ROUNDS = 12

    # 缓存常量
    DEFAULT_CACHE_TIMEOUT = 300  # 5分钟
    LONG_CACHE_TIMEOUT = 3600  # 1小时
    SHORT_CACHE_TIMEOUT = 60  # 1分钟

    # 文件上传常量
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {".txt", ".csv", ".json", ".sql", ".py"}

    # 数据库连接常量
    CONNECTION_TIMEOUT = 30
    QUERY_TIMEOUT = 60
    MAX_CONNECTIONS = 20
    CONNECTION_RETRY_ATTEMPTS = 3

    # 速率限制常量
    RATE_LIMIT_REQUESTS = 1000
    RATE_LIMIT_WINDOW = 300  # 5分钟
    LOGIN_RATE_LIMIT = 10  # 每窗口最多尝试次数
    LOGIN_RATE_WINDOW = 60  # 1分钟

    # 日志常量
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_RETENTION_DAYS = 30

    # JWT常量
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1小时
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30天

    # 会话常量
    SESSION_LIFETIME = 3600  # 1小时
    REMEMBER_ME_LIFETIME = 2592000  # 30天

    # 重试常量
    MAX_RETRY_ATTEMPTS = 3
    RETRY_BASE_DELAY = 1.0
    RETRY_MAX_DELAY = 60.0

    # 性能常量
    SLOW_QUERY_THRESHOLD = 1.0  # 1秒
    SLOW_API_THRESHOLD = 2.0  # 2秒
    MEMORY_WARNING_THRESHOLD = 80  # 80%
    CPU_WARNING_THRESHOLD = 80  # 80%

    # 安全常量
    CSRF_TOKEN_LIFETIME = 3600
    PASSWORD_RESET_TOKEN_LIFETIME = 1800  # 30分钟
    EMAIL_VERIFICATION_TOKEN_LIFETIME = 3600  # 1小时

    # 监控常量
    HEALTH_CHECK_INTERVAL = 30  # 30秒
    METRICS_COLLECTION_INTERVAL = 60  # 1分钟
    ALERT_CHECK_INTERVAL = 300  # 5分钟


# 配置默认值
class DefaultConfig:
    """
    默认配置值
    
    安全警告：
    - DATABASE_URL 和 REDIS_URL 必须从环境变量获取，不允许硬编码密码
    - 所有敏感信息（密码、密钥）必须通过环境变量配置
    - 生产环境必须设置所有必需的环境变量
    """

    # 数据库配置 - 使用环境变量，避免硬编码密码
    DATABASE_URL = None  # 必须从环境变量获取
    REDIS_URL = None  # 必须从环境变量获取

    # 应用配置
    SECRET_KEY = None  # 从环境变量获取
    JWT_SECRET_KEY = None  # 从环境变量获取
    DEBUG = True
    TESTING = False

    # 日志配置
    LOG_LEVEL = LogLevel.INFO.value
    LOG_FILE = "userdata/logs/app.log"

    # 缓存配置
    CACHE_TYPE = "redis"
    CACHE_DEFAULT_TIMEOUT = SystemConstants.DEFAULT_CACHE_TIMEOUT

    # 安全配置
    BCRYPT_LOG_ROUNDS = SystemConstants.PASSWORD_HASH_ROUNDS
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # 文件上传配置
    UPLOAD_FOLDER = "userdata/uploads"
    MAX_CONTENT_LENGTH = SystemConstants.MAX_FILE_SIZE

    # 外部数据库配置
    SQL_SERVER_HOST = "localhost"
    SQL_SERVER_PORT = 1433
    MYSQL_HOST = "localhost"
    MYSQL_PORT = 3306
    POSTGRES_HOST = "localhost"
    POSTGRES_PORT = 5432
    ORACLE_HOST = "localhost"
    ORACLE_PORT = 1521


# 错误消息常量
class ErrorMessages:
    """错误消息常量"""

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
    TOKEN_EXPIRED = "令牌已过期"  # noqa: S105 - 这是错误消息，不是密码
    TOKEN_INVALID = "无效的令牌"  # noqa: S105 - 这是错误消息，不是密码
    ACCOUNT_DISABLED = "账户已被禁用"
    ACCOUNT_LOCKED = "账户已被锁定"
    RATE_LIMIT_EXCEEDED = "请求过于频繁，请稍后再试"

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
    """成功消息常量"""

    # 通用成功
    OPERATION_SUCCESS = "操作成功"
    DATA_SAVED = "数据保存成功"
    DATA_DELETED = "数据删除成功"
    DATA_UPDATED = "数据更新成功"

    # 认证成功
    LOGIN_SUCCESS = "登录成功"
    LOGOUT_SUCCESS = "登出成功"
    PASSWORD_CHANGED = "密码修改成功"  # noqa: S105 - 这是成功消息，不是密码
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
    "LogLevel",
    "SystemConstants",
    "DefaultConfig",
    "ErrorMessages",
    "SuccessMessages",
    "ErrorCategory",
    "ErrorSeverity",
]
