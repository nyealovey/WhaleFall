"""鲸落 - 账户分类管理模型."""

import json
from typing import TYPE_CHECKING, Unpack

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.orm_kwargs import (
        AccountClassificationAssignmentOrmFields,
        AccountClassificationOrmFields,
        ClassificationRuleOrmFields,
    )
    from app.models.account_permission import AccountPermission


class AccountClassification(db.Model):
    """账户分类模型.

    管理账户的分类信息,支持自定义分类、风险等级、图标等.
    可以通过规则自动分类或手动分配.

    Attributes:
        id: 主键 ID.
        code: 分类标识(code),唯一且不可变.
        display_name: 分类展示名(可改,仅用于 UI 展示).
        description: 分类描述.
        risk_level: 风险等级(1-6,1 最高,6 最低).
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
    # 稳定口径: code 创建后不可改,用于统计/规则引用的语义锚点
    code = db.Column(db.String(100), nullable=False, unique=True)
    # 展示口径: 允许 UI 改名但不影响统计语义
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)  # 分类描述
    risk_level = db.Column(db.SmallInteger, nullable=False, default=4)  # 风险等级: 1(最高) ... 6(最低)
    icon_name = db.Column(db.String(50), nullable=True, default="fa-tag")  # 图标名称
    priority = db.Column(db.Integer, default=0)  # 优先级,数字越大优先级越高
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # 是否为系统分类
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    # 关联关系
    rules = db.relationship(
        "ClassificationRule",
        back_populates="classification",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    account_assignments = db.relationship(
        "AccountClassificationAssignment",
        backref="classification",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[AccountClassificationOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

    def __repr__(self) -> str:
        """Return concise label for debugging.

        Returns:
            str: 格式 `<AccountClassification code>`.

        """
        return f"<AccountClassification {self.code}>"

    def to_dict(self) -> dict:
        """转换为字典.

        Returns:
            dict: 包含分类元数据和统计字段.

        """
        display_name = getattr(self, "display_name", None) or self.code
        return {
            "id": self.id,
            # 兼容旧前端：name 继续返回展示名
            "name": display_name,
            "code": self.code,
            "display_name": display_name,
            "description": self.description,
            "risk_level": self.risk_level,
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
    __allow_unmapped__ = True  # 允许运行时附加的非映射字段

    id = db.Column(db.Integer, primary_key=True)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    db_type = db.Column(
        db.String(20),
        nullable=False,
    )  # 数据库类型:mysql、postgresql、sqlserver、oracle
    rule_name = db.Column(db.String(100), nullable=False)  # 规则名称
    rule_expression = db.Column(db.Text, nullable=False)  # 规则表达式(JSON格式)
    # 匹配相关字段(rule_expression)不可变版本化：同一 rule_group_id 下按 rule_version 递增生成新 rule_id
    rule_group_id = db.Column(db.String(36), nullable=False, index=True)
    rule_version = db.Column(db.Integer, nullable=False, default=1)
    superseded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    classification = db.relationship("AccountClassification", back_populates="rules")
    operator: str | None = None
    """规则逻辑运算符,当前由服务层写入内存用于表达式解析."""
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[ClassificationRuleOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

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
            "rule_group_id": self.rule_group_id,
            "rule_version": self.rule_version,
            "superseded_at": (self.superseded_at.isoformat() if self.superseded_at else None),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def get_rule_expression(self) -> dict:
        """获取规则表达式(解析 JSON).

        Returns:
            dict: 解析后的规则表达式.

        """
        try:
            return json.loads(self.rule_expression)
        except (json.JSONDecodeError, TypeError) as exc:
            rule_id = getattr(self, "id", None)
            rule_name = getattr(self, "rule_name", None)
            raise ValueError(f"rule_expression JSON decode failed (rule_id={rule_id}, rule_name={rule_name})") from exc

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
    assigned_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
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

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[AccountClassificationAssignmentOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

    def __repr__(self) -> str:
        """Return assignment label.

        Returns:
            str: `<AccountClassificationAssignment account -> classification>`.

        """
        classification = getattr(self, "classification", None)
        label = None
        if classification is not None:
            label = getattr(classification, "display_name", None) or classification.code
        return f"<AccountClassificationAssignment {self.account_id} -> {label}>"

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
            "classification_name": (
                (getattr(self.classification, "display_name", None) or self.classification.code)
                if self.classification
                else None
            ),
        }

    if TYPE_CHECKING:
        classification: AccountClassification
        account: "AccountPermission"
