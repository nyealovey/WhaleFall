"""风险中心规则配置模型."""

from __future__ import annotations

from app import db
from app.utils.time_utils import time_utils


class RiskCenterRuleSetting(db.Model):
    """风险中心内置规则的展示配置."""

    __tablename__ = "risk_center_rule_settings"

    id = db.Column(db.Integer, primary_key=True)
    rule_key = db.Column(db.String(64), nullable=False, unique=True, index=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    severity = db.Column(db.String(16), nullable=False, default="medium")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    def to_dict(self) -> dict[str, object]:
        """序列化规则配置."""
        return {
            "rule_key": str(self.rule_key),
            "enabled": bool(self.enabled),
            "severity": str(self.severity),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
