"""
鲸落 - 基础同步数据模型
"""

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped

from app import db


class BaseSyncData(db.Model):
    """基础同步数据模型（抽象基类）。

    为同步数据模型提供通用字段和方法的抽象基类。
    所有同步相关的模型（如 AccountPermission）都应继承此类。

    Attributes:
        id: 主键 ID。
        instance_id: 关联的实例 ID（外键）。
        db_type: 数据库类型（mysql/postgresql/sqlserver/oracle）。
    """

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def instance_id(cls) -> Mapped[int]:
        """返回与实例表关联的外键字段定义。

        Returns:
            sqlalchemy.orm.Mapped: 指向 `instances.id` 的整型外键列。
        """

        return db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)

    db_type = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )  # 数据库类型：mysql、postgresql、sqlserver、oracle

    # 关联实例 - 在子类中定义

    def to_dict(self) -> dict:
        """转换为字典。

        Returns:
            包含基础字段的字典。
        """
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "db_type": self.db_type,
        }
