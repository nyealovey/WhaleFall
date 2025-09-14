"""
泰摸鱼吧 - 数据模型
"""

from app import db  # noqa: F401

# Account模型已废弃，使用CurrentAccountSyncData
from .account_change import AccountChange
from .account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from .classification_batch import ClassificationBatch
from .credential import Credential
from .instance import Instance
from .log import Log
from .permission_config import PermissionConfig

# 移除SyncData导入，使用新的优化同步模型
from .sync_instance_record import SyncInstanceRecord
from .sync_session import SyncSession
from .task import Task

# 导入所有模型
from .user import User

# 新增模型
from .global_param import GlobalParam

# 导出所有模型
__all__ = [
    "User",
    "Instance",
    "Credential",
    # "Account",  # 已废弃，使用CurrentAccountSyncData
    "Task",
    "Log",
    # 移除SyncData导出
    "SyncSession",
    "SyncInstanceRecord",
    "AccountChange",
    "AccountClassification",
    "ClassificationRule",
    "AccountClassificationAssignment",
    "ClassificationBatch",
    "PermissionConfig",
    "GlobalParam",
]
