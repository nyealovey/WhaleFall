"""账户分类每日统计模型.

落库两类统计:
- 规则命中数(B 口径): 每条规则当日评估命中账号数
- 分类去重账号数: 某分类下任意规则命中账号的去重数(按 instance/db_type 维度)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.orm_kwargs import AccountClassificationDailyClassificationMatchStatOrmFields
    from app.core.types.orm_kwargs import AccountClassificationDailyRuleMatchStatOrmFields


class AccountClassificationDailyRuleMatchStat(db.Model):
    """分类规则每日命中统计(B 口径)."""

    __tablename__ = "account_classification_daily_rule_match_stats"

    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    stat_date = db.Column(db.Date, nullable=False, index=True)

    rule_id = db.Column(db.Integer, db.ForeignKey("classification_rules.id"), nullable=False, index=True)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False, index=True)
    db_type = db.Column(db.String(20), nullable=False, index=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)

    matched_accounts_count = db.Column(db.Integer, nullable=False, default=0)
    computed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    __table_args__ = (
        db.UniqueConstraint(
            "stat_date",
            "rule_id",
            "db_type",
            "instance_id",
            name="uq_ac_daily_rule_match_key",
        ),
        db.Index(
            "ix_ac_daily_rule_match_classification_date",
            "classification_id",
            "stat_date",
        ),
        db.Index(
            "ix_ac_daily_rule_match_rule_date",
            "rule_id",
            "stat_date",
        ),
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[AccountClassificationDailyRuleMatchStatOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...


class AccountClassificationDailyClassificationMatchStat(db.Model):
    """分类每日去重命中统计(去重账号数)."""

    __tablename__ = "account_classification_daily_classification_match_stats"

    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    stat_date = db.Column(db.Date, nullable=False, index=True)

    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False, index=True)
    db_type = db.Column(db.String(20), nullable=False, index=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)

    matched_accounts_distinct_count = db.Column(db.Integer, nullable=False, default=0)
    computed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    __table_args__ = (
        db.UniqueConstraint(
            "stat_date",
            "classification_id",
            "db_type",
            "instance_id",
            name="uq_ac_daily_classification_match_key",
        ),
        db.Index(
            "ix_ac_daily_classification_match_classification_date",
            "classification_id",
            "stat_date",
        ),
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[AccountClassificationDailyClassificationMatchStatOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...
