"""数据模型模块。.

定义所有数据库模型，包括用户、实例、凭据、账户权限、同步记录、统计数据等。

主要模型：
- User: 用户模型
- Instance: 数据库实例模型
- Credential: 凭据模型
- AccountPermission: 账户权限模型
- AccountClassification: 账户分类模型
- SyncSession: 同步会话模型
- SyncInstanceRecord: 同步实例记录模型
- DatabaseSizeStat: 数据库容量统计模型
- InstanceSizeStat: 实例容量统计模型
- DatabaseSizeAggregation: 数据库容量聚合模型
- InstanceSizeAggregation: 实例容量聚合模型
"""

from app import db  # noqa: F401

from .account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)

# 账户相关模型
from .account_permission import AccountPermission
from .credential import Credential

# 新增模型
from .database_size_aggregation import DatabaseSizeAggregation
from .database_size_stat import DatabaseSizeStat
from .instance import Instance
from .instance_account import InstanceAccount
from .instance_database import InstanceDatabase
from .instance_size_aggregation import InstanceSizeAggregation
from .instance_size_stat import InstanceSizeStat
from .permission_config import PermissionConfig

# 移除SyncData导入，使用新的优化同步模型
from .sync_instance_record import SyncInstanceRecord
from .sync_session import SyncSession

# 导入所有模型
from .user import User

# 导出所有模型
__all__ = [
    "AccountClassification",
    "AccountClassificationAssignment",
    "AccountPermission",
    "ClassificationRule",
    "Credential",
    "DatabaseSizeAggregation",
    "DatabaseSizeStat",
    "Instance",
    "InstanceAccount",
    "InstanceDatabase",
    "InstanceSizeAggregation",
    "InstanceSizeStat",
    "PermissionConfig",
    "SyncInstanceRecord",
    "SyncSession",
    "User",
]
