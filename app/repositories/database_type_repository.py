"""数据库类型 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from app.models.database_type_config import DatabaseTypeConfig


class DatabaseTypeRepository:
    """数据库类型读模型 Repository."""

    @staticmethod
    def list_all_types() -> list[DatabaseTypeConfig]:
        """列出全部数据库类型配置."""
        return DatabaseTypeConfig.query.order_by(DatabaseTypeConfig.sort_order, DatabaseTypeConfig.name).all()

    @staticmethod
    def list_active_types() -> list[DatabaseTypeConfig]:
        """列出启用的数据库类型配置."""
        return DatabaseTypeConfig.get_active_types()

    @staticmethod
    def get_by_name(name: str) -> DatabaseTypeConfig | None:
        """按名称获取数据库类型配置."""
        return DatabaseTypeConfig.get_by_name(name)
