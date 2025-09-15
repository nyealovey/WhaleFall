"""
泰摸鱼吧 - 全局参数模型
管理系统的全局配置参数
"""

from datetime import datetime
from typing import Any

from app import db
from app.utils.timezone import now


class GlobalParam(db.Model):
    """全局参数模型"""

    __tablename__ = "global_params"

    id = db.Column(db.Integer, primary_key=True)
    param_type = db.Column(db.String(50), nullable=False, comment="参数类型")
    name = db.Column(db.String(255), nullable=False, comment="参数名称")
    config = db.Column(db.JSON, nullable=True, comment="参数配置")
    created_at = db.Column(db.DateTime, nullable=True, comment="创建时间")
    updated_at = db.Column(db.DateTime, nullable=True, comment="更新时间")
    deleted_at = db.Column(db.DateTime, nullable=True, comment="删除时间")

    def __repr__(self) -> str:
        return f"<GlobalParam {self.param_type}:{self.name}>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "param_type": self.param_type,
            "name": self.name,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }

    @classmethod
    def get_by_type(cls, param_type: str) -> list["GlobalParam"]:
        """根据类型获取参数"""
        return cls.query.filter_by(param_type=param_type, deleted_at=None).all()

    @classmethod
    def get_by_name(cls, name: str) -> "GlobalParam":
        """根据名称获取参数"""
        return cls.query.filter_by(name=name, deleted_at=None).first()

    @classmethod
    def get_config_value(cls, name: str, default: Any = None) -> Any:
        """获取配置值"""
        param = cls.get_by_name(name)
        if param and param.config:
            return param.config
        return default

    @classmethod
    def set_config_value(cls, name: str, value: Any, param_type: str = "config") -> "GlobalParam":
        """设置配置值"""
        param = cls.get_by_name(name)
        if param:
            param.config = value
            param.updated_at = now()
        else:
            param = cls(
                name=name,
                param_type=param_type,
                config=value,
                created_at=now(),
                updated_at=now(),
            )
            db.session.add(param)

        db.session.commit()
        return param

    def soft_delete(self) -> None:
        """软删除"""
        self.deleted_at = now()
        db.session.commit()
