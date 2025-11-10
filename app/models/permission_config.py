"""
鲸落 - 权限配置数据模型

默认权限数据通过 SQL 初始化脚本下发，模型层仅负责读取/序列化。
"""

from app import db
from app.utils.time_utils import time_utils


class PermissionConfig(db.Model):
    """权限配置数据模型"""

    __tablename__ = "permission_configs"

    id = db.Column(db.Integer, primary_key=True)
    db_type = db.Column(db.String(50), nullable=False)  # mysql/postgresql/sqlserver/oracle
    category = db.Column(db.String(50), nullable=False)  # 如 global_privileges / server_roles
    permission_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    __table_args__ = (
        db.UniqueConstraint("db_type", "category", "permission_name", name="uq_permission_config"),
        db.Index("idx_permission_config_db_type", "db_type"),
        db.Index("idx_permission_config_category", "category"),
    )

    def __repr__(self) -> str:  # pragma: no cover - 便于调试
        return f"<PermissionConfig {self.db_type}.{self.category}.{self.permission_name}>"

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "db_type": self.db_type,
            "category": self.category,
            "permission_name": self.permission_name,
            "description": self.description,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_permissions_by_db_type(cls, db_type: str) -> dict[str, list[dict[str, str | None]]]:
        """按数据库类型返回权限配置，供 UI 展示"""
        permissions = (
            cls.query.filter_by(db_type=db_type, is_active=True)
            .order_by(cls.category, cls.sort_order, cls.permission_name)
            .all()
        )
        grouped: dict[str, list[dict[str, str | None]]] = {}
        for perm in permissions:
            grouped.setdefault(perm.category, []).append(
                {
                    "name": perm.permission_name,
                    "description": perm.description,
                }
            )
        return grouped
