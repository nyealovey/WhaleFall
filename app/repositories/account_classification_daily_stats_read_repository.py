"""账户分类每日统计 Read Repository.

职责:
- 封装日表的查询/聚合细节（按天 sum，供上层做周/月/季 rollup）
- 不做业务编排、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func

from app import db
from app.models.account_classification_daily_stats import (
    AccountClassificationDailyClassificationMatchStat,
    AccountClassificationDailyRuleMatchStat,
)


class AccountClassificationDailyStatsReadRepository:
    """账户分类每日统计 Read Repository."""

    @staticmethod
    def fetch_classification_daily_totals(
        *,
        classification_id: int,
        start_date: date,
        end_date: date,
        db_type: str | None,
        instance_id: int | None,
    ) -> dict[date, int]:
        """按天汇总分类去重账号数."""
        query = (
            db.session.query(
                AccountClassificationDailyClassificationMatchStat.stat_date,
                func.sum(AccountClassificationDailyClassificationMatchStat.matched_accounts_distinct_count).label(
                    "total"
                ),
            )
            .filter(
                AccountClassificationDailyClassificationMatchStat.classification_id == classification_id,
                AccountClassificationDailyClassificationMatchStat.stat_date >= start_date,
                AccountClassificationDailyClassificationMatchStat.stat_date <= end_date,
            )
            .group_by(AccountClassificationDailyClassificationMatchStat.stat_date)
            .order_by(AccountClassificationDailyClassificationMatchStat.stat_date.asc())
        )

        if db_type:
            query = query.filter(AccountClassificationDailyClassificationMatchStat.db_type == db_type)
        if instance_id is not None:
            query = query.filter(AccountClassificationDailyClassificationMatchStat.instance_id == instance_id)

        rows = query.all()
        return {row.stat_date: int(row.total or 0) for row in rows}

    @staticmethod
    def fetch_rule_daily_totals(
        *,
        rule_id: int,
        start_date: date,
        end_date: date,
        db_type: str | None,
        instance_id: int | None,
    ) -> dict[date, int]:
        """按天汇总规则命中账号数."""
        query = (
            db.session.query(
                AccountClassificationDailyRuleMatchStat.stat_date,
                func.sum(AccountClassificationDailyRuleMatchStat.matched_accounts_count).label("total"),
            )
            .filter(
                AccountClassificationDailyRuleMatchStat.rule_id == rule_id,
                AccountClassificationDailyRuleMatchStat.stat_date >= start_date,
                AccountClassificationDailyRuleMatchStat.stat_date <= end_date,
            )
            .group_by(AccountClassificationDailyRuleMatchStat.stat_date)
            .order_by(AccountClassificationDailyRuleMatchStat.stat_date.asc())
        )

        if db_type:
            query = query.filter(AccountClassificationDailyRuleMatchStat.db_type == db_type)
        if instance_id is not None:
            query = query.filter(AccountClassificationDailyRuleMatchStat.instance_id == instance_id)

        rows = query.all()
        return {row.stat_date: int(row.total or 0) for row in rows}

    @staticmethod
    def fetch_rule_totals_by_rule_id(
        *,
        classification_id: int,
        start_date: date,
        end_date: date,
        db_type: str | None,
        instance_id: int | None,
    ) -> dict[int, int]:
        """按规则汇总窗口内命中账号数(用于列表排序/贡献统计)."""
        query = (
            db.session.query(
                AccountClassificationDailyRuleMatchStat.rule_id,
                func.sum(AccountClassificationDailyRuleMatchStat.matched_accounts_count).label("total"),
            )
            .filter(
                AccountClassificationDailyRuleMatchStat.classification_id == classification_id,
                AccountClassificationDailyRuleMatchStat.stat_date >= start_date,
                AccountClassificationDailyRuleMatchStat.stat_date <= end_date,
            )
            .group_by(AccountClassificationDailyRuleMatchStat.rule_id)
        )

        if db_type:
            query = query.filter(AccountClassificationDailyRuleMatchStat.db_type == db_type)
        if instance_id is not None:
            query = query.filter(AccountClassificationDailyRuleMatchStat.instance_id == instance_id)

        rows = query.all()
        return {int(row.rule_id): int(row.total or 0) for row in rows if row.rule_id is not None}

    @staticmethod
    def fetch_rule_stat_dates(
        *,
        classification_id: int,
        start_date: date,
        end_date: date,
        db_type: str | None,
        instance_id: int | None,
    ) -> set[date]:
        """返回窗口内存在统计记录的日期集合(用于 coverage 计算)."""
        query = (
            db.session.query(AccountClassificationDailyRuleMatchStat.stat_date)
            .filter(
                AccountClassificationDailyRuleMatchStat.classification_id == classification_id,
                AccountClassificationDailyRuleMatchStat.stat_date >= start_date,
                AccountClassificationDailyRuleMatchStat.stat_date <= end_date,
            )
            .distinct()
        )
        if db_type:
            query = query.filter(AccountClassificationDailyRuleMatchStat.db_type == db_type)
        if instance_id is not None:
            query = query.filter(AccountClassificationDailyRuleMatchStat.instance_id == instance_id)
        return {row.stat_date for row in query.all() if row.stat_date is not None}
