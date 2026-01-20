"""账户分类每日统计计算服务.

说明:
- 统计口径与 `assignments` 解耦，直接基于规则表达式评估账户 facts 计算。
- 同一天重复执行：通过 upsert 覆盖同一维度键，最终只保留最后一次结果。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from app.models.account_classification import ClassificationRule
from app.models.account_permission import AccountPermission
from app.repositories.account_classification_daily_stats_repository import (
    AccountClassificationDailyStatsRepository,
)
from app.repositories.account_classification_repository import ClassificationRepository
from app.services.account_classification.dsl_v4 import DslV4Evaluator
from app.utils.time_utils import time_utils


@dataclass(slots=True)
class AccountClassificationDailyStatsPersistResult:
    """每日统计落库结果摘要."""

    stat_date: date
    computed_at: datetime
    rules_count: int
    accounts_count: int
    rule_match_rows: int
    classification_match_rows: int


class AccountClassificationDailyStatsService:
    """账户分类每日统计计算服务."""

    def __init__(
        self,
        *,
        classification_repository: ClassificationRepository | None = None,
        daily_stats_repository: AccountClassificationDailyStatsRepository | None = None,
    ) -> None:
        """初始化服务并注入依赖."""
        self._classification_repository = classification_repository or ClassificationRepository()
        self._daily_stats_repository = daily_stats_repository or AccountClassificationDailyStatsRepository()

    def compute_and_persist(self, *, stat_date: date | None = None) -> AccountClassificationDailyStatsPersistResult:
        """计算并落库每日统计."""
        resolved_date = stat_date or time_utils.now_china().date()
        computed_at = time_utils.now()

        rules = self._classification_repository.fetch_active_rules()
        accounts = self._classification_repository.fetch_accounts()

        rule_records, classification_records = self.build_daily_records(
            accounts=accounts,
            rules=rules,
            stat_date=resolved_date,
            computed_at=computed_at,
        )

        self._daily_stats_repository.upsert_rule_match_stats(rule_records, current_utc=computed_at)
        self._daily_stats_repository.upsert_classification_match_stats(classification_records, current_utc=computed_at)

        return AccountClassificationDailyStatsPersistResult(
            stat_date=resolved_date,
            computed_at=computed_at,
            rules_count=len(rules),
            accounts_count=len(accounts),
            rule_match_rows=len(rule_records),
            classification_match_rows=len(classification_records),
        )

    @staticmethod
    def build_daily_records(
        *,
        accounts: Sequence[AccountPermission],
        rules: Sequence[ClassificationRule],
        stat_date: date,
        computed_at: datetime,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        """基于规则表达式评估 accounts，构建两张日表的 records."""
        accounts_by_db_type: dict[str, list[AccountPermission]] = defaultdict(list)
        instance_ids_by_db_type: dict[str, set[int]] = defaultdict(set)

        for account in accounts:
            db_type = account.db_type.strip().lower()
            accounts_by_db_type[db_type].append(account)
            instance_ids_by_db_type[db_type].add(account.instance_id)

        classification_db_types: dict[int, set[str]] = defaultdict(set)
        for rule in rules:
            classification_db_types[rule.classification_id].add(rule.db_type.strip().lower())

        matched_accounts_by_rule_instance: dict[tuple[int, str, int], set[int]] = defaultdict(set)
        matched_accounts_by_classification_instance: dict[tuple[int, str, int], set[int]] = defaultdict(set)

        for rule in rules:
            rule_id = int(rule.id)
            classification_id = rule.classification_id
            db_type = rule.db_type.strip().lower()

            candidate_accounts = accounts_by_db_type.get(db_type) or []
            if not candidate_accounts:
                continue

            expression = rule.get_rule_expression()

            for account in candidate_accounts:
                account_id = int(account.id)
                instance_id = account.instance_id
                raw_facts = account.permission_facts
                facts: Mapping[str, object] = raw_facts if isinstance(raw_facts, Mapping) else {}
                merged_facts = dict(facts)
                merged_facts["db_type"] = db_type

                outcome = DslV4Evaluator(facts=merged_facts).evaluate(expression)
                if not outcome.matched:
                    continue

                matched_accounts_by_rule_instance[(rule_id, db_type, instance_id)].add(account_id)
                matched_accounts_by_classification_instance[(classification_id, db_type, instance_id)].add(account_id)

        rule_records: list[dict[str, object]] = []
        for rule in rules:
            rule_id = int(rule.id)
            classification_id = rule.classification_id
            db_type = rule.db_type.strip().lower()
            instance_ids = sorted(instance_ids_by_db_type.get(db_type) or [])
            if not instance_ids:
                continue

            for instance_id in instance_ids:
                matched = matched_accounts_by_rule_instance.get((rule_id, db_type, instance_id)) or set()
                rule_records.append(
                    {
                        "stat_date": stat_date,
                        "rule_id": rule_id,
                        "classification_id": classification_id,
                        "db_type": db_type,
                        "instance_id": instance_id,
                        "matched_accounts_count": len(matched),
                        "computed_at": computed_at,
                        "created_at": computed_at,
                        "updated_at": computed_at,
                    },
                )

        classification_records: list[dict[str, object]] = []
        for classification_id, db_types in classification_db_types.items():
            for db_type in sorted(db_types):
                instance_ids = sorted(instance_ids_by_db_type.get(db_type) or [])
                if not instance_ids:
                    continue
                for instance_id in instance_ids:
                    matched = (
                        matched_accounts_by_classification_instance.get(
                            (classification_id, db_type, instance_id),
                        )
                        or set()
                    )
                    classification_records.append(
                        {
                            "stat_date": stat_date,
                            "classification_id": classification_id,
                            "db_type": db_type,
                            "instance_id": instance_id,
                            "matched_accounts_distinct_count": len(matched),
                            "computed_at": computed_at,
                            "created_at": computed_at,
                            "updated_at": computed_at,
                        },
                    )

        return rule_records, classification_records
