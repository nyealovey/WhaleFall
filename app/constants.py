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


class LogType(Enum):
    """日志类型枚举"""

    OPERATION = "operation"
    SYSTEM = "system"
    ERROR = "error"
    SECURITY = "security"
    API = "api"
    DATABASE = "database"


class UserRole(Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class TaskStatus(Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstanceStatus(Enum):
    """实例状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DatabaseType(Enum):
    """数据库类型枚举"""

    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"
    SQLITE = "sqlite"


class TaskType(Enum):
    """任务类型枚举"""

    SYNC_ACCOUNTS = "sync_accounts"
    SYNC_VERSION = "sync_version"
    SYNC_SIZE = "sync_size"
    CUSTOM = "custom"
    BACKUP = "backup"
    RESTORE = "restore"


class SyncType(Enum):
    """同步类型枚举"""

    MANUAL_SINGLE = "manual_single"  # 手动单台
    MANUAL_BATCH = "manual_batch"  # 手动批量
    MANUAL_TASK = "manual_task"  # 手动任务
    SCHEDULED_TASK = "scheduled_task"  # 定时任务


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
    LOGIN_RATE_LIMIT = 999999  # 取消登录速率限制
    LOGIN_RATE_WINDOW = 300

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
    """默认配置值"""

    # 数据库配置
    DATABASE_URL = "postgresql://taifish_user:Taifish2024!@localhost:5432/taifish_dev"
    REDIS_URL = "redis://:Taifish2024!@localhost:6379/0"

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
    RESOURCE_NOT_FOUND = "资源不存在"
    INVALID_REQUEST = "无效的请求"

    # 认证错误
    INVALID_CREDENTIALS = "用户名或密码错误"
    TOKEN_EXPIRED = "令牌已过期"  # noqa: S105 - 这是错误消息，不是密码
    TOKEN_INVALID = "无效的令牌"  # noqa: S105 - 这是错误消息，不是密码
    ACCOUNT_DISABLED = "账户已被禁用"
    ACCOUNT_LOCKED = "账户已被锁定"

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


# 正则表达式常量
class RegexPatterns:
    """正则表达式常量"""

    # 用户名模式
    USERNAME_PATTERN = r"^[a-zA-Z0-9_]{3,20}$"

    # 邮箱模式
    EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    # 密码模式（至少8位，包含大小写字母和数字）
    PASSWORD_PATTERN = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$"  # noqa: S105 - 这是正则表达式模式，不是密码

    # IP地址模式
    IP_PATTERN = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    # 数据库连接字符串模式
    DATABASE_URL_PATTERN = r"^(mysql|postgresql|sqlite|oracle|mssql)://.*$"

    # 端口号模式
    PORT_PATTERN = r"^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"


# 危险字符模式
class DangerousPatterns:
    """危险字符模式"""

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"<style[^>]*>",
    ]

    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\b\s+\'\w+\'\s*=\s*\'\w+\')",
        r"(\b(OR|AND)\b\s+\w+\s*=\s*\w+)",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
    ]


# 数据库字段长度常量
class FieldLengths:
    """数据库字段长度常量"""

    # 用户相关
    USERNAME_MAX_LENGTH = 255
    PASSWORD_HASH_LENGTH = 255
    ROLE_MAX_LENGTH = 50

    # 实例相关
    INSTANCE_NAME_MAX_LENGTH = 255
    INSTANCE_TYPE_MAX_LENGTH = 50
    HOST_MAX_LENGTH = 255
    PORT_MAX_LENGTH = 10
    DATABASE_NAME_MAX_LENGTH = 255

    # 凭据相关
    CREDENTIAL_NAME_MAX_LENGTH = 255
    PASSWORD_MAX_LENGTH = 255

    # 日志相关
    LOG_LEVEL_MAX_LENGTH = 20
    LOG_TYPE_MAX_LENGTH = 50
    MODULE_MAX_LENGTH = 100
    IP_ADDRESS_MAX_LENGTH = 45

    # 任务相关
    TASK_NAME_MAX_LENGTH = 255
    TASK_TYPE_MAX_LENGTH = 50
    STATUS_MAX_LENGTH = 20

    # 参数相关
    PARAM_NAME_MAX_LENGTH = 255
    PARAM_TYPE_MAX_LENGTH = 50
    CATEGORY_MAX_LENGTH = 100


# 缓存键前缀
class CacheKeys:
    """缓存键前缀"""

    USER_PREFIX = "user:"
    INSTANCE_PREFIX = "instance:"
    CREDENTIAL_PREFIX = "credential:"
    TASK_PREFIX = "task:"
    LOG_PREFIX = "log:"
    DASHBOARD_PREFIX = "dashboard:"
    API_PREFIX = "api:"
    HEALTH_PREFIX = "health:"

    @staticmethod
    def user_key(user_id: int) -> str:
        return f"{CacheKeys.USER_PREFIX}{user_id}"

    @staticmethod
    def instance_key(instance_id: int) -> str:
        return f"{CacheKeys.INSTANCE_PREFIX}{instance_id}"

    @staticmethod
    def dashboard_key(key: str) -> str:
        return f"{CacheKeys.DASHBOARD_PREFIX}{key}"

    @staticmethod
    def api_key(endpoint: str, params: str = "") -> str:
        return f"{CacheKeys.API_PREFIX}{endpoint}:{params}"


# 时间格式常量
class TimeFormats:
    """时间格式常量"""

    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    CHINESE_DATETIME_FORMAT = "%Y年%m月%d日 %H:%M:%S"
    CHINESE_DATE_FORMAT = "%Y年%m月%d日"


# 分页常量
class Pagination:
    """分页常量"""

    DEFAULT_PAGE = 1
    DEFAULT_PER_PAGE = SystemConstants.DEFAULT_PAGE_SIZE
    MAX_PER_PAGE = SystemConstants.MAX_PAGE_SIZE
    MIN_PER_PAGE = SystemConstants.MIN_PAGE_SIZE

    @staticmethod
    def validate_page(page: int) -> int:
        """验证页码"""
        return max(1, page)

    @staticmethod
    def validate_per_page(per_page: int) -> int:
        """验证每页数量"""
        return max(Pagination.MIN_PER_PAGE, min(per_page, Pagination.MAX_PER_PAGE))


# 导出所有常量
__all__ = [
    "LogLevel",
    "LogType",
    "UserRole",
    "TaskStatus",
    "InstanceStatus",
    "DatabaseType",
    "TaskType",
    "SyncType",
    "SystemConstants",
    "DefaultConfig",
    "ErrorMessages",
    "SuccessMessages",
    "RegexPatterns",
    "DangerousPatterns",
    "FieldLengths",
    "CacheKeys",
    "TimeFormats",
    "Pagination",
]
