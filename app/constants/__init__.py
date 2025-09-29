"""
鲸落 - 常量模块
统一管理应用中的各种常量定义
"""

# 导入同步相关常量
from .sync_constants import SyncOperationType, SyncCategory, SyncConstants

# 导入系统常量
from .system_constants import SystemConstants, DefaultConfig, ErrorMessages, SuccessMessages, RegexPatterns, DangerousPatterns, FieldLengths, CacheKeys, TimeFormats, Pagination, LogLevel, LogType, UserRole, TaskStatus, InstanceStatus, DatabaseType, TaskType, SyncType

__all__ = [
    # 同步相关常量
    'SyncOperationType',
    'SyncCategory', 
    'SyncConstants',
    # 系统常量
    'SystemConstants',
    'DefaultConfig',
    'ErrorMessages',
    'SuccessMessages',
    'RegexPatterns',
    'DangerousPatterns',
    'FieldLengths',
    'CacheKeys',
    'TimeFormats',
    'Pagination',
    'LogLevel',
    'LogType',
    'UserRole',
    'TaskStatus',
    'InstanceStatus',
    'DatabaseType',
    'TaskType',
    'SyncType'
]
