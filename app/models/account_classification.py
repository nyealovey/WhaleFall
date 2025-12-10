"""鲸落 - 账户分类管理模型."""

import json
from typing import TYPE_CHECKING

from app import db
from app.constants.colors import ThemeColors
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.models.account_permission import AccountPermission


class AccountClassification(db.Model):
    """账户分类模型.

    管理账户的分类信息,支持自定义分类、风险等级、颜色、图标等.
    可以通过规则自动分类或手动分配.

    Attributes:
        id: 主键 ID.
        name: 分类名称,唯一.
        description: 分类描述.
        risk_level: 风险等级(low/medium/high/critical).
        color: 显示颜色.
        icon_name: 图标名称(Font Awesome).
        priority: 优先级,数字越大优先级越高.
        is_system: 是否为系统分类.
        is_active: 是否启用.
        created_at: 创建时间.
        updated_at: 更新时间.
        rules: 关联的分类规则.
        account_assignments: 关联的账户分配记录.

    """

    __tablename__ = "account_classifications"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # 特权账户、高风险账户等
    description = db.Column(db.Text, nullable=True)  # 分类描述
    risk_level = db.Column(
        db.String(20),
        nullable=False,
        default="medium",
    )  # 风险等级:low(低)、medium(中)、high(高)、critical(严重)
    color = db.Column(db.String(20), nullable=True)  # 显示颜色
    icon_name = db.Column(db.String(50), nullable=True, default="fa-tag")  # 图标名称
    priority = db.Column(db.Integer, default=0)  # 优先级,数字越大优先级越高
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # 是否为系统分类
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

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
        """Return concise label for debugging.

        Returns:
            str: 格式 `<AccountClassification name>`.

        """
        return f"<AccountClassification {self.name}>"

    @property
    def color_value(self) -> str:
        """获取实际颜色值.

        Returns:
            str: 颜色 HEX 值.

        """
        return ThemeColors.get_color_value(self.color)

    @property
    def color_name(self) -> str:
        """获取颜色名称.

        Returns:
            str: 颜色中文名称.

        """
        return ThemeColors.get_color_name(self.color)

    @property
    def css_class(self) -> str:
        """获取 CSS 类名.

        Returns:
            str: 用于前端展示的 class 名称.

        """
        return ThemeColors.get_css_class(self.color)

    def to_dict(self) -> dict:
        """转换为字典.

        Returns:
            dict: 包含分类元数据和统计字段.

        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "color": self.color,
            "color_value": self.color_value,
            "color_name": self.color_name,
            "css_class": self.css_class,
            "icon_name": self.icon_name,
            "priority": self.priority,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "rules_count": self.rules.count(),
            "assignments_count": self.account_assignments.filter_by(is_active=True).count(),
        }


class ClassificationRule(db.Model):
    """分类规则模型."""

    __tablename__ = "classification_rules"

    id = db.Column(db.Integer, primary_key=True)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    db_type = db.Column(
        db.String(20),
        nullable=False,
    )  # 数据库类型:mysql、postgresql、sqlserver、oracle
    rule_name = db.Column(db.String(100), nullable=False)  # 规则名称
    rule_expression = db.Column(db.Text, nullable=False)  # 规则表达式(JSON格式)
    operator: str
    """规则逻辑运算符,当前由服务层写入内存用于表达式解析."""
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    def __repr__(self) -> str:
        """Return rule label for debugging.

        Returns:
            str: `<ClassificationRule rule_name for db_type>`.

        """
        return f"<ClassificationRule {self.rule_name} for {self.db_type}>"

    def to_dict(self) -> dict:
        """转换为字典.

        Returns:
            dict: 规则基础字段.

        """
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
        """获取规则表达式(解析 JSON).

        Returns:
            dict: 解析后的规则表达式,失败返回空字典.

        """
        try:
            return json.loads(self.rule_expression)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_rule_expression(self, expression: dict) -> None:
        """设置规则表达式(保存为 JSON).

        Args:
            expression: 已验证的表达式字典.

        Returns:
            None.

        """
        self.rule_expression = json.dumps(expression, ensure_ascii=False)


class AccountClassificationAssignment(db.Model):
    """账户分类分配模型."""

    __tablename__ = "account_classification_assignments"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("account_permission.id"), nullable=False)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey("classification_rules.id"), nullable=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # 分配人
    assignment_type = db.Column(
        db.String(20),
        nullable=False,
        default="auto",
    )  # 分配方式:auto(自动)、manual(手动)
    confidence_score = db.Column(db.Float, nullable=True)  # 自动分配的置信度分数
    notes = db.Column(db.Text, nullable=True)  # 备注
    batch_id = db.Column(db.String(36), nullable=True)  # 批次ID
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    __table_args__ = (
        db.UniqueConstraint(
            "account_id",
            "classification_id",
            "batch_id",
            name="unique_account_classification_batch",
        ),
    )

    def __repr__(self) -> str:
        """Return assignment label.

        Returns:
            str: `<AccountClassificationAssignment account -> classification>`.

        """
        return f"<AccountClassificationAssignment {self.account_id} -> {self.classification.name}>"

    def to_dict(self) -> dict:
        """转换为字典.

        Returns:
            dict: 包含分配基础字段.

        """
        return {
            "id": self.id,
            "account_id": self.account_id,
            "classification_id": self.classification_id,
            "rule_id": self.rule_id,
            "assigned_by": self.assigned_by,
            "assignment_type": self.assignment_type,
            "confidence_score": self.confidence_score,
            "notes": self.notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "account_username": self.account_id,  # 直接使用ID,避免关联查询
            "classification_name": (self.classification.name if self.classification else None),
        }

    if TYPE_CHECKING:
        classification: AccountClassification
        account: "AccountPermission"
