"""
泰摸鱼吧 - 账户分类管理模型
"""

import json
from datetime import datetime

from app import db


class AccountClassification(db.Model):
    """账户分类模型"""

    __tablename__ = "account_classifications"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # 特权账户、高风险账户等
    description = db.Column(db.Text, nullable=True)  # 分类描述
    risk_level = db.Column(db.String(20), nullable=False, default="medium")  # low, medium, high, critical
    color = db.Column(db.String(20), nullable=True)  # 显示颜色
    priority = db.Column(db.Integer, default=0)  # 优先级，数字越大优先级越高
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # 是否为系统分类
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    rules = db.relationship(
        "ClassificationRule",
        backref="classification",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    account_assignments = db.relationship(
        "AccountClassificationAssignment",
        backref="classification",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AccountClassification {self.name}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "color": self.color,
            "priority": self.priority,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "rules_count": self.rules.count(),
            "assignments_count": self.account_assignments.filter_by(is_active=True).count(),
        }


class ClassificationRule(db.Model):
    """分类规则模型"""

    __tablename__ = "classification_rules"

    id = db.Column(db.Integer, primary_key=True)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    db_type = db.Column(db.String(20), nullable=False)  # mysql, postgresql, sqlserver, oracle
    rule_name = db.Column(db.String(100), nullable=False)  # 规则名称
    rule_expression = db.Column(db.Text, nullable=False)  # 规则表达式（JSON格式）
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ClassificationRule {self.rule_name} for {self.db_type}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "classification_id": self.classification_id,
            "db_type": self.db_type,
            "rule_name": self.rule_name,
            "rule_expression": self.rule_expression,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def get_rule_expression(self) -> dict:
        """获取规则表达式（解析JSON）"""
        try:
            return json.loads(self.rule_expression)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_rule_expression(self, expression: dict) -> None:
        """设置规则表达式（保存为JSON）"""
        self.rule_expression = json.dumps(expression, ensure_ascii=False)


class AccountClassificationAssignment(db.Model):
    """账户分类分配模型"""

    __tablename__ = "account_classification_assignments"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("current_account_sync_data.id"), nullable=False)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # 分配人
    assignment_type = db.Column(db.String(20), nullable=False, default="auto")  # auto, manual
    confidence_score = db.Column(db.Float, nullable=True)  # 自动分配的置信度分数
    notes = db.Column(db.Text, nullable=True)  # 备注
    batch_id = db.Column(db.String(36), nullable=True)  # 批次ID
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 唯一约束：一个账户在同一个批次中只能有一个分类分配
    __table_args__ = (
        db.UniqueConstraint(
            "account_id",
            "classification_id",
            "batch_id",
            name="unique_account_classification_batch",
        ),
    )

    def __repr__(self) -> str:
        return f"<AccountClassificationAssignment {self.account_id} -> {self.classification.name}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "classification_id": self.classification_id,
            "assigned_by": self.assigned_by,
            "assignment_type": self.assignment_type,
            "confidence_score": self.confidence_score,
            "notes": self.notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "account_username": self.account_id,  # 直接使用ID，避免关联查询
            "classification_name": (self.classification.name if self.classification else None),
        }
