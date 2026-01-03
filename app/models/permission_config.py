"""鲸落 - 权限配置数据模型.

默认权限数据通过 SQL 初始化脚本下发,模型层仅负责读取/序列化.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.types.orm_kwargs import PermissionConfigOrmFields


class PermissionConfig(db.Model):
    """权限配置数据模型.

    存储不同数据库类型的权限配置信息,用于权限展示和验证.
    默认权限数据通过 SQL 初始化脚本下发,模型层仅负责读取和序列化.

    Attributes:
        id: 主键 ID.
        db_type: 数据库类型(mysql/postgresql/sqlserver/oracle).
        category: 权限分类(如 global_privileges、server_roles 等).
        permission_name: 权限名称.
        description: 权限描述.
        is_active: 是否启用.
        sort_order: 排序顺序.
        introduced_in_major: 引入版本(数据库大版本号,仅用于展示/提示).
        created_at: 创建时间.
        updated_at: 更新时间.

    """

    __tablename__ = "permission_configs"

    id = db.Column(db.Integer, primary_key=True)
    db_type = db.Column(
        db.String(50),
        nullable=False,
    )  # 数据库类型:mysql/postgresql/sqlserver/oracle
    category = db.Column(
        db.String(50),
        nullable=False,
    )  # 权限分类,如 global_privileges、server_roles 等
    permission_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    introduced_in_major = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    __table_args__ = (
        db.UniqueConstraint("db_type", "category", "permission_name", name="uq_permission_config"),
        db.Index("idx_permission_config_db_type", "db_type"),
        db.Index("idx_permission_config_category", "category"),
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[PermissionConfigOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

    def __repr__(self) -> str:  # pragma: no cover - 便于调试
        """返回权限配置的调试字符串.

        Returns:
            str: 组合数据库类型、分类与权限名的可读文本.

        """
        return f"<PermissionConfig {self.db_type}.{self.category}.{self.permission_name}>"

    def to_dict(self) -> dict:
        """序列化权限配置.

        Returns:
            dict: 包含分类、描述及时间戳信息的字典.

        """
        return {
            "id": self.id,
            "db_type": self.db_type,
            "category": self.category,
            "permission_name": self.permission_name,
            "description": self.description,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "introduced_in_major": self.introduced_in_major,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_permissions_by_db_type(cls, db_type: str) -> dict[str, list[dict[str, str | None]]]:
        """按数据库类型返回权限配置,供 UI 展示.

        Args:
            db_type: 数据库类型.

        Returns:
            按分类分组的权限配置字典,格式:
            {
                'category1': [{'name': 'perm1', 'description': 'desc1'}, ...],
                'category2': [...]
            }

        """
        columns = [
            cls.category,
            cls.permission_name,
            cls.description,
            cls.sort_order,
            cls.introduced_in_major,
        ]

        permissions = (
            db.session.query(*columns)
            .filter(cls.db_type == db_type, cls.is_active.is_(True))
            .order_by(cls.category, cls.sort_order, cls.permission_name)
            .all()
        )
        grouped: dict[str, list[dict[str, str | None]]] = {}
        for row in permissions:
            category, name, description, _, introduced_in_major = row

            grouped.setdefault(category, []).append(
                {
                    "name": name,
                    "description": description,
                    "introduced_in_major": introduced_in_major,
                },
            )
        return grouped
