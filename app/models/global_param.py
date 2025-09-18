"""
全局参数模型
"""

from datetime import datetime

from app import db


class GlobalParam(db.Model):
    """全局参数模型"""

    __tablename__ = "global_params"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False, comment="参数键")
    value = db.Column(db.Text, nullable=False, comment="参数值")
    description = db.Column(db.Text, comment="参数描述")
    param_type = db.Column(db.String(50), nullable=False, default="string", comment="参数类型")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self) -> str:
        return f"<GlobalParam {self.key}>"

    def to_dict(self) -> dict[str, any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "param_type": self.param_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
