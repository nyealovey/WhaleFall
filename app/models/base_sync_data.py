"""
鲸落 - 基础同步数据模型
"""

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped

from app import db


class BaseSyncData(db.Model):
    """基础同步数据模型（抽象基类）"""

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def instance_id(cls) -> Mapped[int]:
        return db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)

    db_type = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )  # 数据库类型：mysql、postgresql、sqlserver、oracle

    # 关联实例 - 在子类中定义

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "db_type": self.db_type,
        }
