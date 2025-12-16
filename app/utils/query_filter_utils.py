"""统一筛选器数据访问工具.

负责提供所有需要从数据库动态获取的筛选数据,避免在视图或模板中重复查询.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from app import db
from app.models.account_classification import AccountClassification
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.models.tag import Tag
from app.models.unified_log import UnifiedLog
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable


def get_active_tags() -> list[Tag]:
    """获取所有激活状态的标签,按分类与显示名称排序.

    Returns:
        标签对象列表,按 category、display_name、name 排序.

    Example:
        >>> tags = get_active_tags()
        >>> for tag in tags:
        ...     print(f"{tag.category}: {tag.name}")

    """
    return (
        cast(Any, Tag.query)
        .filter(cast(Any, Tag.is_active).is_(True))
        .order_by(cast(Any, Tag.category).asc(), cast(Any, Tag.display_name).asc(), cast(Any, Tag.name).asc())
        .all()
    )


def get_active_tag_options() -> list[dict[str, str]]:
    """返回适用于下拉多选的标签选项字典.

    Returns:
        标签选项列表,每个选项包含:
        - value: 标签名称
        - label: 显示名称
        - color: 标签颜色
        - category: 标签分类

    Example:
        >>> options = get_active_tag_options()
        >>> print(options[0])
        {'value': 'prod', 'label': '生产环境', 'color': '#ff0000', 'category': 'env'}

    """
    tags = get_active_tags()
    return [
        {
            "value": tag.name,
            "label": tag.display_name,
            "color": tag.color,
            "category": tag.category,
        }
        for tag in tags
    ]


def get_tag_categories() -> list[dict[str, str]]:
    """获取当前存在的标签分类.

    分类展示名称优先使用 Tag 内置的映射,若找不到则退回原始分类值.

    Returns:
        分类选项列表,每个选项包含:
        - value: 分类值
        - label: 分类显示名称

    Example:
        >>> categories = get_tag_categories()
        >>> print(categories)
        [{'value': 'env', 'label': '环境'}, {'value': 'region', 'label': '区域'}]

    """
    label_mapping = dict(Tag.get_category_choices())
    categories_raw = [
        category
        for (category,) in (
            db.session.query(cast(Any, Tag.category))
            .filter(cast(Any, Tag.is_active).is_(True))
            .distinct()
            .order_by(cast(Any, Tag.category).asc())
            .all()
        )
    ]

    categories: list[dict[str, str]] = []
    for category in categories_raw:
        categories.append(
            {
                "value": category,
                "label": label_mapping.get(category, category),
            },
        )
    return categories


def get_classifications() -> list[AccountClassification]:
    """获取可用的账户分类,按优先级与名称排序.

    Returns:
        账户分类对象列表,按 priority 降序、name 升序排列.

    Example:
        >>> classifications = get_classifications()
        >>> for c in classifications:
        ...     print(f"{c.name} (优先级: {c.priority})")

    """
    return (
        AccountClassification.query.filter(AccountClassification.is_active.is_(True))
        .order_by(AccountClassification.priority.desc(), AccountClassification.name.asc())
        .all()
    )


def get_classification_options() -> list[dict[str, str]]:
    """返回账户分类下拉选项.

    Returns:
        分类选项列表,每个选项包含:
        - value: 分类 ID(字符串)
        - label: 分类名称
        - color: 分类颜色

    Example:
        >>> options = get_classification_options()
        >>> print(options[0])
        {'value': '1', 'label': '业务账户', 'color': '#00ff00'}

    """
    classifications = get_classifications()
    return [
        {"value": str(classification.id), "label": classification.name, "color": classification.color or ""}
        for classification in classifications
    ]


def get_instances_by_db_type(db_type: str | None = None, *, include_inactive: bool = False) -> list[Instance]:
    """获取实例列表,可选按数据库类型过滤.

    Args:
        db_type: 数据库类型标识,例如 mysql、postgresql.
        include_inactive: 是否包含已禁用的实例.

    Returns:
        指定过滤条件下的实例对象列表,按名称升序排列.

    """
    query = Instance.query
    if not include_inactive:
        query = query.filter(Instance.is_active.is_(True))
    if db_type:
        query = query.filter(Instance.db_type == db_type)
    return query.order_by(Instance.name.asc()).all()


def get_instance_options(db_type: str | None = None) -> list[dict[str, str]]:
    """返回实例下拉选项.

    Args:
        db_type: 可选的数据库类型过滤.

    Returns:
        实例选项列表,每个选项包含:
        - value: 实例 ID(字符串)
        - label: 实例显示名称(包含数据库类型)
        - db_type: 数据库类型

    Example:
        >>> options = get_instance_options('mysql')
        >>> print(options[0])
        {'value': '1', 'label': 'prod-mysql-01 (mysql)', 'db_type': 'mysql'}

    """
    instances = get_instances_by_db_type(db_type=db_type)
    return [
        {
            "value": str(instance.id),
            "label": f"{instance.name} ({instance.db_type})",
            "db_type": instance.db_type,
        }
        for instance in instances
    ]


def get_databases_by_instance(instance_id: int) -> list[InstanceDatabase]:
    """获取指定实例下仍然活跃的数据库列表,按名称排序.

    Args:
        instance_id: 实例 ID.

    Returns:
        数据库对象列表,按 database_name 排序.

    Example:
        >>> databases = get_databases_by_instance(1)
        >>> for db in databases:
        ...     print(db.database_name)

    """
    return (
        InstanceDatabase.query.filter(
            InstanceDatabase.instance_id == instance_id,
            InstanceDatabase.is_active.is_(True),
        )
        .order_by(InstanceDatabase.database_name.asc())
        .all()
    )


def get_database_options(instance_id: int) -> list[dict[str, str]]:
    """返回数据库选择下拉选项.

    Args:
        instance_id: 实例 ID.

    Returns:
        数据库选项列表,每个选项包含:
        - value: 数据库 ID(字符串)
        - label: 数据库名称
        - name: 数据库名称

    Example:
        >>> options = get_database_options(1)
        >>> print(options[0])
        {'value': '10', 'label': 'mydb', 'name': 'mydb'}

    """
    databases = get_databases_by_instance(instance_id)
    return [
        {
            "value": str(database.id),
            "label": database.database_name,
            "name": database.database_name,
        }
        for database in databases
    ]


def get_log_modules(limit_hours: int | None = None) -> list[str]:
    """获取日志模块列表.

    Args:
        limit_hours: 限制只统计最近多少小时内的日志;为 None 时无限制.

    Returns:
        模块名称列表,按字母顺序排序.

    Example:
        >>> modules = get_log_modules(limit_hours=24)
        >>> print(modules)
        ['api', 'auth', 'database', 'sync']

    """
    query = db.session.query(cast(Any, UnifiedLog.module)).distinct()
    if limit_hours is not None:
        start_time = time_utils.now() - timedelta(hours=limit_hours)
        query = query.filter(UnifiedLog.timestamp >= start_time)

    rows = query.order_by(UnifiedLog.module.asc()).all()
    return [module for (module,) in rows if module]
