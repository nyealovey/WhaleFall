"""常量模块。

集中管理所有系统常量，包括颜色、状态、错误消息、HTTP 相关常量等。

主要常量：
- ThemeColors: 主题颜色常量
- DatabaseType: 数据库类型常量
- SyncStatus: 同步状态常量
- UserRole: 用户角色常量
- ErrorMessages: 错误消息常量
- HttpStatus: HTTP 状态码常量
- TimeConstants: 时间常量
"""

# 导入颜色常量
from .colors import ThemeColors

# 导入所有系统常量
from .system_constants import (
    ErrorCategory,
    ErrorMessages,
    ErrorSeverity,
    LogLevel,
    SuccessMessages,
)

# 导入HTTP状态码常量（使用Python标准库）
from http import HTTPStatus as HttpStatus

# 导入时间常量
from .time_constants import TimeConstants

# 导入数据库类型常量
from .database_types import DatabaseType

# 导入状态类型常量
from .status_types import InstanceStatus, JobStatus, SyncStatus, TaskStatus

# 导入用户角色常量
from .user_roles import UserRole

# 导入Flash类别常量
from .flash_categories import FlashCategory

# 导入HTTP头常量
from .http_headers import HttpHeaders

# 导入HTTP方法常量
from .http_methods import HttpMethod

# 导入筛选选项常量
from .filter_options import (
    CREDENTIAL_TYPES,
    DATABASE_TYPES,
    LOG_LEVELS,
    PAGINATION_SIZES,
    PERIOD_TYPES,
    STATUS_ACTIVE_OPTIONS,
    STATUS_SYNC_OPTIONS,
    SYNC_CATEGORIES,
    SYNC_TYPES,
    TIME_RANGES,
)

# 导出所有常量
__all__ = [
    # 筛选选项
    "CREDENTIAL_TYPES",
    "DATABASE_TYPES",
    "LOG_LEVELS",
    "PAGINATION_SIZES",
    "PERIOD_TYPES",
    "STATUS_ACTIVE_OPTIONS",
    "STATUS_SYNC_OPTIONS",
    "SYNC_CATEGORIES",
    "SYNC_TYPES",
    "TIME_RANGES",
    # 数据库类型
    "DatabaseType",
    "ErrorCategory",
    "ErrorMessages",
    "ErrorSeverity",
    # Flash类别
    "FlashCategory",
    # HTTP头
    "HttpHeaders",
    # HTTP方法
    "HttpMethod",
    # HTTP状态码
    "HttpStatus",
    "InstanceStatus",
    "JobStatus",
    # 系统常量
    "LogLevel",
    "SuccessMessages",
    # 状态类型
    "SyncStatus",
    "TaskStatus",
    # 颜色常量
    "ThemeColors",
    # 时间常量
    "TimeConstants",
    # 用户角色
    "UserRole",
]
