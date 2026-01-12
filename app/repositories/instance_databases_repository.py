"""实例数据库 Repository.

职责:
- 负责 Query 组装与数据库读取（read）
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import cast

from app.models.instance_database import InstanceDatabase


class InstanceDatabasesRepository:
    """实例数据库查询 Repository."""

    def get_by_id(self, database_id: int) -> InstanceDatabase | None:
        """按 ID 获取实例数据库记录."""
        return cast("InstanceDatabase | None", InstanceDatabase.query.get(database_id))

    @staticmethod
    def list_by_instance_id(instance_id: int) -> list[InstanceDatabase]:
        """按实例 ID 获取数据库记录列表."""
        return InstanceDatabase.query.filter_by(instance_id=instance_id).all()
