"""
鲸落 - 数据模型
"""

from app import db  # noqa: F401

# Account模型已废弃，使用CurrentAccountSyncData
from .account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from .credential import Credential

# 新增模型
from .database_size_aggregation import DatabaseSizeAggregation
from .database_size_stat import DatabaseSizeStat
from .instance_size_aggregation import InstanceSizeAggregation
from .instance_size_stat import InstanceSizeStat
from .instance_database import InstanceDatabase
from .instance import Instance
from .permission_config import PermissionConfig

# 移除SyncData导入，使用新的优化同步模型
from .sync_instance_record import SyncInstanceRecord
from .sync_session import SyncSession

# 导入所有模型
from .user import User

# 导出所有模型
__all__ = [
    "User",
    "Instance",
    "Credential",
    # "Account",  # 已废弃，使用CurrentAccountSyncData
    # 移除Task导出，只使用APScheduler管理任务
    # 移除SyncData导出
    "SyncSession",
    "SyncInstanceRecord",
    "AccountClassification",
    "ClassificationRule",
    "AccountClassificationAssignment",
    "PermissionConfig",
    "DatabaseSizeStat",
    "DatabaseSizeAggregation",
    "InstanceSizeAggregation",
    "InstanceSizeStat",
    "InstanceDatabase",
]
