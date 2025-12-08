"""数据模型模块.

定义所有数据库模型,包括用户、实例、凭据、账户权限、同步记录、统计数据等.

主要模型:
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


def __getattr__(name: str):
    """延迟加载模型, 避免初始化周期引发的循环导入."""

    if name not in __all__:
        msg = f"module 'app.models' has no attribute {name}"
        raise AttributeError(msg)

    from importlib import import_module

    module_map = {
        "AccountClassification": "app.models.account_classification",
        "AccountClassificationAssignment": "app.models.account_classification",
        "ClassificationRule": "app.models.account_classification",
        "AccountPermission": "app.models.account_permission",
        "Credential": "app.models.credential",
        "DatabaseSizeAggregation": "app.models.database_size_aggregation",
        "DatabaseSizeStat": "app.models.database_size_stat",
        "Instance": "app.models.instance",
        "InstanceAccount": "app.models.instance_account",
        "InstanceDatabase": "app.models.instance_database",
        "InstanceSizeAggregation": "app.models.instance_size_aggregation",
        "InstanceSizeStat": "app.models.instance_size_stat",
        "PermissionConfig": "app.models.permission_config",
        "SyncInstanceRecord": "app.models.sync_instance_record",
        "SyncSession": "app.models.sync_session",
        "User": "app.models.user",
    }

    module = import_module(module_map[name])
    value = getattr(module, name)
    globals()[name] = value
    return value

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
