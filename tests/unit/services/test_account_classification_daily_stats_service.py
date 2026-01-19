from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import pytest

from app import create_app, db
from app.models.account_classification import AccountClassification, ClassificationRule
from app.models.account_classification_daily_stats import (
    AccountClassificationDailyClassificationMatchStat,
    AccountClassificationDailyRuleMatchStat,
)
from app.models.account_permission import AccountPermission
from app.models.instance import Instance, InstanceCreateParams
from app.repositories.account_classification_daily_stats_repository import (
    AccountClassificationDailyStatsRepository,
)
from app.services.account_classification.daily_stats_service import (
    AccountClassificationDailyStatsService,
)
from app.settings import Settings
from app.utils.time_utils import time_utils


@pytest.mark.unit
def test_build_daily_records_counts_rule_and_classification_distinct() -> None:
    computed_at = time_utils.now()
    stat_date = date(2026, 1, 19)

    classification_id = 1

    rule_superuser = ClassificationRule(
        classification_id=classification_id,
        db_type="postgresql",
        rule_name="is_superuser",
        rule_expression=json.dumps({"version": 4, "expr": {"fn": "is_superuser", "args": {}}}),
        rule_group_id=str(uuid4()),
        rule_version=1,
        is_active=True,
    )
    rule_superuser.id = 101

    rule_has_dba = ClassificationRule(
        classification_id=classification_id,
        db_type="postgresql",
        rule_name="has_role_dba",
        rule_expression=json.dumps(
            {"version": 4, "expr": {"fn": "has_role", "args": {"name": "dba"}}},
        ),
        rule_group_id=str(uuid4()),
        rule_version=1,
        is_active=True,
    )
    rule_has_dba.id = 102

    instance_id = 10

    account_1 = AccountPermission(
        instance_id=instance_id,
        db_type="postgresql",
        instance_account_id=1,
        username="u1",
        permission_facts={"capabilities": ["SUPERUSER"], "roles": ["dba"]},
    )
    account_1.id = 1

    account_2 = AccountPermission(
        instance_id=instance_id,
        db_type="postgresql",
        instance_account_id=2,
        username="u2",
        permission_facts={"capabilities": ["SUPERUSER"], "roles": []},
    )
    account_2.id = 2

    account_3 = AccountPermission(
        instance_id=instance_id,
        db_type="postgresql",
        instance_account_id=3,
        username="u3",
        permission_facts={"capabilities": [], "roles": ["dba"]},
    )
    account_3.id = 3

    rule_records, classification_records = AccountClassificationDailyStatsService.build_daily_records(
        accounts=[account_1, account_2, account_3],
        rules=[rule_superuser, rule_has_dba],
        stat_date=stat_date,
        computed_at=computed_at,
    )

    assert len(rule_records) == 2
    assert len(classification_records) == 1

    rule_counts = {record["rule_id"]: record["matched_accounts_count"] for record in rule_records}
    assert rule_counts == {101: 2, 102: 2}

    classification_payload = classification_records[0]
    assert classification_payload["classification_id"] == classification_id
    assert classification_payload["db_type"] == "postgresql"
    assert classification_payload["instance_id"] == instance_id
    assert classification_payload["matched_accounts_distinct_count"] == 3


@pytest.fixture(scope="function")
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True
    return app


def _ensure_stats_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["account_classifications"],
                db.metadata.tables["classification_rules"],
                db.metadata.tables["account_classification_daily_rule_match_stats"],
                db.metadata.tables["account_classification_daily_classification_match_stats"],
            ],
        )


@pytest.mark.unit
def test_daily_stats_repository_upsert_overwrites_same_key(app) -> None:
    _ensure_stats_tables(app)

    with app.app_context():
        instance = Instance(
            InstanceCreateParams(
                name="pg-1",
                db_type="postgresql",
                host="127.0.0.1",
                port=5432,
            ),
        )
        db.session.add(instance)

        classification = AccountClassification(
            name="PRIVILEGED",
            display_name="特权账户",
            description="",
            risk_level="high",
            color="danger",
            icon_name="fa-tag",
            priority=10,
        )
        db.session.add(classification)
        db.session.flush()

        rule = ClassificationRule(
            classification_id=classification.id,
            db_type="postgresql",
            rule_name="is_superuser",
            rule_expression=json.dumps({"version": 4, "expr": {"fn": "is_superuser", "args": {}}}),
            rule_group_id=str(uuid4()),
            rule_version=1,
            is_active=True,
        )
        db.session.add(rule)
        db.session.commit()

        computed_at = time_utils.now()
        stat_date = date(2026, 1, 19)

        repo = AccountClassificationDailyStatsRepository()
        repo.upsert_rule_match_stats(
            [
                {
                    "stat_date": stat_date,
                    "rule_id": rule.id,
                    "classification_id": classification.id,
                    "db_type": "postgresql",
                    "instance_id": instance.id,
                    "matched_accounts_count": 1,
                    "computed_at": computed_at,
                    "created_at": computed_at,
                    "updated_at": computed_at,
                },
            ],
            current_utc=computed_at,
        )

        repo.upsert_rule_match_stats(
            [
                {
                    "stat_date": stat_date,
                    "rule_id": rule.id,
                    "classification_id": classification.id,
                    "db_type": "postgresql",
                    "instance_id": instance.id,
                    "matched_accounts_count": 9,
                    "computed_at": computed_at,
                    "created_at": computed_at,
                    "updated_at": computed_at,
                },
            ],
            current_utc=computed_at,
        )

        rows = AccountClassificationDailyRuleMatchStat.query.all()
        assert len(rows) == 1
        assert rows[0].matched_accounts_count == 9

        repo.upsert_classification_match_stats(
            [
                {
                    "stat_date": stat_date,
                    "classification_id": classification.id,
                    "db_type": "postgresql",
                    "instance_id": instance.id,
                    "matched_accounts_distinct_count": 3,
                    "computed_at": computed_at,
                    "created_at": computed_at,
                    "updated_at": computed_at,
                },
            ],
            current_utc=computed_at,
        )
        repo.upsert_classification_match_stats(
            [
                {
                    "stat_date": stat_date,
                    "classification_id": classification.id,
                    "db_type": "postgresql",
                    "instance_id": instance.id,
                    "matched_accounts_distinct_count": 4,
                    "computed_at": computed_at,
                    "created_at": computed_at,
                    "updated_at": computed_at,
                },
            ],
            current_utc=computed_at,
        )

        class_rows = AccountClassificationDailyClassificationMatchStat.query.all()
        assert len(class_rows) == 1
        assert class_rows[0].matched_accounts_distinct_count == 4

