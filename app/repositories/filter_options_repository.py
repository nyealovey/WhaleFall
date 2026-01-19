"""筛选器/下拉选项读模型 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func
from sqlalchemy.orm import Query

from app import db
from app.models.account_classification import AccountClassification
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.models.tag import Tag


class FilterOptionsRepository:
    """通用筛选器/下拉选项 Repository."""

    @staticmethod
    def list_active_instances(*, db_type: str | None = None) -> list[Instance]:
        """获取启用的实例列表."""
        active_filter = cast(Any, Instance.is_active).is_(True)
        query = cast("Query", Instance.query).filter(active_filter)

        normalized_type = db_type.strip() if db_type is not None else ""
        if normalized_type:
            query = cast("Query", query).filter(func.lower(Instance.db_type) == normalized_type.lower())

        return cast("Query", query).order_by(Instance.name.asc()).all()

    @staticmethod
    def list_databases_by_instance(
        instance_id: int,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[InstanceDatabase], int]:
        """按实例ID分页获取数据库列表."""
        query = InstanceDatabase.query.filter(InstanceDatabase.instance_id == instance_id).order_by(
            InstanceDatabase.database_name.asc(),
        )
        total_count = query.count()

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all(), total_count

    @staticmethod
    def list_active_databases_by_instance(instance_id: int) -> list[InstanceDatabase]:
        """获取启用的实例数据库列表."""
        active_filter = cast(Any, InstanceDatabase.is_active).is_(True)
        query = InstanceDatabase.query.filter(
            InstanceDatabase.instance_id == instance_id,
            active_filter,
        ).order_by(InstanceDatabase.database_name.asc())
        return query.all()

    @staticmethod
    def list_active_tags() -> list[Tag]:
        """获取启用的标签列表."""
        return cast("list[Tag]", Tag.get_active_tags())

    @staticmethod
    def list_active_tag_categories() -> list[str]:
        """获取启用的标签分类列表."""
        category_column = cast(Any, Tag.category)
        active_filter = cast(Any, Tag.is_active).is_(True)
        rows = db.session.query(category_column).filter(active_filter).distinct().order_by(category_column.asc()).all()
        return [category for (category,) in rows if category]

    @staticmethod
    def list_active_account_classifications() -> list[AccountClassification]:
        """获取启用的账户分类列表."""
        return (
            AccountClassification.query.filter(AccountClassification.is_active.is_(True))
            .order_by(AccountClassification.priority.desc(), AccountClassification.name.asc())
            .all()
        )
