"""
统一筛选器数据访问工具

负责提供所有需要从数据库动态获取的筛选数据，避免在视图或模板中重复查询。
"""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import distinct

from app import db
from app.models.account_classification import AccountClassification
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.models.tag import Tag
from app.models.unified_log import UnifiedLog


def get_active_tags() -> list[Tag]:
    """获取所有激活状态的标签，按分类与排序顺序排列。"""
    return (
        Tag.query.filter(Tag.is_active.is_(True))
        .order_by(Tag.category.asc(), Tag.sort_order.asc(), Tag.name.asc())
        .all()
    )


def get_active_tag_options() -> list[dict[str, str]]:
    """返回适用于下拉多选的标签选项字典。"""
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
    """
    获取当前存在的标签分类。

    分类展示名称优先使用 Tag 内置的映射，若找不到则退回原始分类值。
    """
    label_mapping = {value: label for value, label in Tag.get_category_choices()}
    rows: Iterable[tuple[str]] = (
        db.session.query(distinct(Tag.category))
        .filter(Tag.is_active.is_(True))
        .order_by(Tag.category.asc())
        .all()
    )

    categories: list[dict[str, str]] = []
    for (category,) in rows:
        categories.append(
            {
                "value": category,
                "label": label_mapping.get(category, category),
            }
        )
    return categories


def get_classifications() -> list[AccountClassification]:
    """获取可用的账户分类，按优先级与名称排序。"""
    return (
        AccountClassification.query.filter(AccountClassification.is_active.is_(True))
        .order_by(AccountClassification.priority.desc(), AccountClassification.name.asc())
        .all()
    )


def get_classification_options() -> list[dict[str, str]]:
    """返回账户分类下拉选项。"""
    classifications = get_classifications()
    return [
        {"value": str(classification.id), "label": classification.name, "color": classification.color or ""}
        for classification in classifications
    ]


def get_instances_by_db_type(db_type: str | None = None, *, include_inactive: bool = False) -> list[Instance]:
    """
    获取实例列表，可选按数据库类型过滤。

    Args:
        db_type: 数据库类型标识，例如 mysql、postgresql。
        include_inactive: 是否包含已禁用的实例。
    """
    query = Instance.query
    if not include_inactive:
        query = query.filter(Instance.is_active.is_(True))
    if db_type:
        query = query.filter(Instance.db_type == db_type)
    return query.order_by(Instance.name.asc()).all()


def get_instance_options(db_type: str | None = None) -> list[dict[str, str]]:
    """返回实例下拉选项。"""
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
    """获取指定实例下仍然活跃的数据库列表，按名称排序。"""
    return (
        InstanceDatabase.query.filter(
            InstanceDatabase.instance_id == instance_id, InstanceDatabase.is_active.is_(True)
        )
        .order_by(InstanceDatabase.database_name.asc())
        .all()
    )


def get_database_options(instance_id: int) -> list[dict[str, str]]:
    """返回数据库选择下拉选项。"""
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
    """
    获取日志模块列表。

    Args:
        limit_hours: 限制只统计最近多少小时内的日志；为 None 时无限制。
    """
    query = db.session.query(distinct(UnifiedLog.module))
    if limit_hours is not None:
        from datetime import timedelta

        from app.utils.time_utils import time_utils

        start_time = time_utils.now() - timedelta(hours=limit_hours)
        query = query.filter(UnifiedLog.timestamp >= start_time)

    rows = query.order_by(UnifiedLog.module.asc()).all()
    return [module for (module,) in rows if module]
