"""账户分类每日统计读取服务.

提供:
- 分类趋势(去重账号数): 支持日/周/月/季聚合(非日=均值展示,缺失天不计入分母)
- 规则趋势(命中账号数): 同上
- 规则贡献(当前周期 TopN)
- 规则列表(最新周期命中均值/当日值, 支持保留窗口累计用于排查)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TypedDict

from app.core.exceptions import ValidationError
from app.models.account_classification import ClassificationRule
from app.repositories.account_classification_daily_stats_read_repository import (
    AccountClassificationDailyStatsReadRepository,
)
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.services.aggregation.calculator import PeriodCalculator
from app.utils.time_utils import time_utils

_SUPPORTED_PERIOD_TYPES = {"daily", "weekly", "monthly", "quarterly"}
_SUPPORTED_RULE_STATUS = {"active", "archived", "all"}


@dataclass(frozen=True, slots=True)
class PeriodBucket:
    """周期桶(用于周/月/季聚合计算)."""

    period_start: date
    period_end: date

    @property
    def expected_days(self) -> int:
        """周期应有天数(含首尾)."""
        return (self.period_end - self.period_start).days + 1


class RuleContributionItem(TypedDict):
    """规则贡献列表项."""

    rule_id: int
    rule_name: str
    db_type: str | None
    rule_version: int | None
    is_active: bool | None
    value_avg: float | int
    value_sum: int
    coverage_days: int
    expected_days: int


class RuleOverviewItem(TypedDict):
    """规则概览列表项(左侧列表)."""

    rule_id: int
    rule_name: str
    db_type: str
    rule_version: int
    is_active: bool
    latest_value_avg: float | int
    latest_value_sum: int
    latest_coverage_days: int
    latest_expected_days: int
    window_value_sum: int


class AccountClassificationDailyStatsReadService:
    """账户分类每日统计读取服务."""

    def __init__(
        self,
        repository: AccountClassificationDailyStatsReadRepository | None = None,
        classifications_repository: AccountsClassificationsRepository | None = None,
    ) -> None:
        """初始化读取服务."""
        self._repository = repository or AccountClassificationDailyStatsReadRepository()
        self._classifications_repository = classifications_repository or AccountsClassificationsRepository()
        self._period_calculator = PeriodCalculator(now_func=lambda: time_utils.now_china().date())

    def get_classification_trend(
        self,
        *,
        classification_id: int,
        period_type: str,
        periods: int,
        db_type: str | None,
        instance_id: int | None,
    ) -> list[dict[str, object]]:
        """获取分类趋势(分类去重账号数)."""
        normalized_period_type = self._normalize_period_type(period_type)
        normalized_periods = self._normalize_periods(periods)

        buckets = self._build_period_buckets(normalized_period_type, normalized_periods)
        start_date = buckets[0].period_start
        end_date = buckets[-1].period_end

        daily_totals = self._repository.fetch_classification_daily_totals(
            classification_id=classification_id,
            start_date=start_date,
            end_date=end_date,
            db_type=db_type,
            instance_id=instance_id,
        )
        return self._rollup_to_buckets(buckets=buckets, daily_totals=daily_totals)

    def get_all_classifications_trends(
        self,
        *,
        period_type: str,
        periods: int,
        db_type: str | None,
        instance_id: int | None,
    ) -> dict[str, object]:
        """获取全分类趋势(未选分类时用于多折线展示)."""
        normalized_period_type = self._normalize_period_type(period_type)
        normalized_periods = self._normalize_periods(periods)

        buckets = self._build_period_buckets(normalized_period_type, normalized_periods)
        start_date = buckets[0].period_start
        end_date = buckets[-1].period_end

        daily_totals_map = self._repository.fetch_all_classifications_daily_totals(
            start_date=start_date,
            end_date=end_date,
            db_type=db_type,
            instance_id=instance_id,
        )

        bucket_payload = [
            {
                "period_start": bucket.period_start.isoformat(),
                "period_end": bucket.period_end.isoformat(),
                "expected_days": bucket.expected_days,
            }
            for bucket in buckets
        ]

        classifications = self._classifications_repository.fetch_active_classifications()

        series: list[dict[str, object]] = []
        for classification in classifications:
            classification_id = int(classification.id)
            points = self._rollup_to_buckets(
                buckets=buckets,
                daily_totals=daily_totals_map.get(classification_id, {}),
            )
            display_name = getattr(classification, "display_name", None) or getattr(classification, "code", None) or ""
            series.append(
                {
                    "classification_id": classification_id,
                    "classification_name": display_name,
                    "points": points,
                }
            )

        return {
            "period_type": normalized_period_type,
            "periods": normalized_periods,
            "buckets": bucket_payload,
            "series": series,
        }

    def get_rule_trend(
        self,
        *,
        rule_id: int,
        period_type: str,
        periods: int,
        db_type: str | None,
        instance_id: int | None,
    ) -> list[dict[str, object]]:
        """获取规则趋势(规则命中账号数)."""
        normalized_period_type = self._normalize_period_type(period_type)
        normalized_periods = self._normalize_periods(periods)

        buckets = self._build_period_buckets(normalized_period_type, normalized_periods)
        start_date = buckets[0].period_start
        end_date = buckets[-1].period_end

        daily_totals = self._repository.fetch_rule_daily_totals(
            rule_id=rule_id,
            start_date=start_date,
            end_date=end_date,
            db_type=db_type,
            instance_id=instance_id,
        )
        return self._rollup_to_buckets(buckets=buckets, daily_totals=daily_totals)

    def get_rule_contributions(
        self,
        *,
        classification_id: int,
        period_type: str,
        db_type: str | None,
        instance_id: int | None,
        limit: int = 10,
    ) -> dict[str, object]:
        """获取规则贡献(用于“未选规则”的柱状图)."""
        normalized_period_type = self._normalize_period_type(period_type)
        limit = max(1, min(int(limit or 10), 50))

        current_start, current_end = self._period_calculator.get_current_period(normalized_period_type)
        totals = self._repository.fetch_rule_totals_by_rule_id(
            classification_id=classification_id,
            start_date=current_start,
            end_date=current_end,
            db_type=db_type,
            instance_id=instance_id,
        )
        stat_dates = self._repository.fetch_rule_stat_dates(
            classification_id=classification_id,
            start_date=current_start,
            end_date=current_end,
            db_type=db_type,
            instance_id=instance_id,
        )

        coverage_days = len(stat_dates)
        expected_days = (current_end - current_start).days + 1

        rule_ids = list(totals.keys())
        rules = self._fetch_rules_by_ids(rule_ids)

        items: list[RuleContributionItem] = []
        for rule_id, value_sum in totals.items():
            rule = rules.get(rule_id)
            rule_name = rule.rule_name if rule else f"规则#{rule_id}"
            db_type_value = rule.db_type if rule else None
            rule_version = rule.rule_version if rule else None
            is_active = bool(rule.is_active) if rule else None

            value_avg = (
                float(value_sum)
                if normalized_period_type == "daily"
                else (float(value_sum) / coverage_days if coverage_days else 0.0)
            )
            items.append(
                {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "db_type": db_type_value,
                    "rule_version": rule_version,
                    "is_active": is_active,
                    "value_avg": round(value_avg, 1) if normalized_period_type != "daily" else int(value_sum),
                    "value_sum": int(value_sum),
                    "coverage_days": coverage_days,
                    "expected_days": expected_days,
                },
            )

        items.sort(key=lambda item: item["value_sum"], reverse=True)

        return {
            "period_start": current_start.isoformat(),
            "period_end": current_end.isoformat(),
            "coverage_days": coverage_days,
            "expected_days": expected_days,
            "contributions": items[:limit],
        }

    def list_rules_overview(
        self,
        *,
        classification_id: int,
        period_type: str,
        periods: int,
        db_type: str | None,
        instance_id: int | None,
        status: str,
    ) -> dict[str, object]:
        """列出规则概览(用于左侧列表).

        口径:
        - 主展示值: 最新周期的命中均值(weekly/monthly/quarterly)或最新当日值(daily)
        - 兼容字段: 保留窗口累计(window_value_sum), 便于排查
        """
        normalized_period_type = self._normalize_period_type(period_type)
        normalized_periods = self._normalize_periods(periods)
        status = self._normalize_rule_status(status)

        buckets = self._build_period_buckets(normalized_period_type, normalized_periods)
        start_date = buckets[0].period_start
        end_date = buckets[-1].period_end

        latest_start, latest_end = self._period_calculator.get_current_period(normalized_period_type)
        latest_expected_days = (latest_end - latest_start).days + 1

        totals = self._repository.fetch_rule_totals_by_rule_id(
            classification_id=classification_id,
            start_date=start_date,
            end_date=end_date,
            db_type=db_type,
            instance_id=instance_id,
        )
        latest_totals = self._repository.fetch_rule_totals_by_rule_id(
            classification_id=classification_id,
            start_date=latest_start,
            end_date=latest_end,
            db_type=db_type,
            instance_id=instance_id,
        )
        latest_coverages = self._repository.fetch_rule_coverage_days_by_rule_id(
            classification_id=classification_id,
            start_date=latest_start,
            end_date=latest_end,
            db_type=db_type,
            instance_id=instance_id,
        )
        latest_stat_dates = self._repository.fetch_rule_stat_dates(
            classification_id=classification_id,
            start_date=latest_start,
            end_date=latest_end,
            db_type=db_type,
            instance_id=instance_id,
        )
        latest_coverage_days = len(latest_stat_dates)

        is_active: bool | None = None
        if status == "active":
            is_active = True
        elif status == "archived":
            is_active = False
        rules = self._classifications_repository.fetch_rules_for_overview(
            classification_id=classification_id,
            db_type=db_type,
            is_active=is_active,
        )

        items: list[RuleOverviewItem] = []
        for rule in rules:
            window_sum = int(totals.get(rule.id, 0))
            latest_sum = int(latest_totals.get(rule.id, 0))
            rule_coverage_days = int(latest_coverages.get(rule.id, 0))

            if normalized_period_type == "daily":
                latest_value_avg: float | int = latest_sum
            else:
                latest_value_avg = round((latest_sum / rule_coverage_days) if rule_coverage_days else 0.0, 1)
            items.append(
                {
                    "rule_id": int(rule.id),
                    "rule_name": rule.rule_name,
                    "db_type": rule.db_type,
                    "rule_version": rule.rule_version,
                    "is_active": bool(rule.is_active),
                    "latest_value_avg": latest_value_avg,
                    "latest_value_sum": latest_sum,
                    "latest_coverage_days": rule_coverage_days,
                    "latest_expected_days": latest_expected_days,
                    "window_value_sum": window_sum,
                },
            )

        items.sort(
            key=lambda item: (
                float(item["latest_value_avg"]),
                int(item["window_value_sum"]),
            ),
            reverse=True,
        )

        return {
            "window_start": start_date.isoformat(),
            "window_end": end_date.isoformat(),
            "latest_period_start": latest_start.isoformat(),
            "latest_period_end": latest_end.isoformat(),
            "latest_coverage_days": int(latest_coverage_days),
            "latest_expected_days": int(latest_expected_days),
            "rules": items,
        }

    # ------------------------------ Internals ------------------------------
    @staticmethod
    def _normalize_period_type(raw_value: str) -> str:
        normalized = (raw_value or "daily").strip().lower()
        if normalized == "yearly":
            raise ValidationError("年统计周期尚未支持")
        if normalized not in _SUPPORTED_PERIOD_TYPES:
            raise ValidationError("不支持的统计周期")
        return normalized

    @staticmethod
    def _normalize_periods(raw_value: int | str | None) -> int:
        try:
            resolved = 7 if raw_value in (None, "") else int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValidationError("periods 必须为整数") from exc
        return max(1, min(resolved, 365))

    @staticmethod
    def _normalize_rule_status(raw_value: str) -> str:
        normalized = (raw_value or "active").strip().lower()
        if normalized not in _SUPPORTED_RULE_STATUS:
            raise ValidationError("不支持的规则状态")
        return normalized

    def _build_period_buckets(self, period_type: str, periods: int) -> list[PeriodBucket]:
        if periods <= 0:
            raise ValidationError("periods 必须大于 0")

        current_start, current_end = self._period_calculator.get_current_period(period_type)

        buckets: list[PeriodBucket] = []
        start_date = current_start
        end_date = current_end
        for _ in range(periods):
            buckets.append(PeriodBucket(period_start=start_date, period_end=end_date))
            start_date, end_date = self._period_calculator.get_previous_period(period_type, start_date, end_date)

        buckets.reverse()
        return buckets

    @staticmethod
    def _rollup_to_buckets(
        *,
        buckets: list[PeriodBucket],
        daily_totals: dict[date, int],
    ) -> list[dict[str, object]]:
        data_dates = set(daily_totals.keys())
        points: list[dict[str, object]] = []

        for bucket in buckets:
            value_sum = 0
            coverage_days = 0
            current = bucket.period_start
            while current <= bucket.period_end:
                if current in data_dates:
                    coverage_days += 1
                    value_sum += int(daily_totals.get(current, 0))
                current += timedelta(days=1)

            expected_days = bucket.expected_days
            value_avg = (
                float(value_sum) if expected_days == 1 else (float(value_sum) / coverage_days if coverage_days else 0.0)
            )
            points.append(
                {
                    "period_start": bucket.period_start.isoformat(),
                    "period_end": bucket.period_end.isoformat(),
                    "value_avg": round(value_avg, 1) if expected_days != 1 else int(value_sum),
                    "value_sum": int(value_sum),
                    "coverage_days": coverage_days,
                    "expected_days": expected_days,
                },
            )

        return points

    def _fetch_rules_by_ids(self, rule_ids: list[int]) -> dict[int, ClassificationRule]:
        if not rule_ids:
            return {}
        rows = self._classifications_repository.fetch_rules_by_ids(rule_ids)
        return {int(rule.id): rule for rule in rows}
