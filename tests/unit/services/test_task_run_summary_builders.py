import pytest


@pytest.mark.unit
def test_build_sync_accounts_summary_has_common_metrics_and_ext_data() -> None:
    from app.services.task_runs.task_run_summary_builders import build_sync_accounts_summary

    payload = build_sync_accounts_summary(
        task_key="sync_accounts",
        inputs={"manual_run": True},
        instances_total=3,
        instances_successful=2,
        instances_failed=1,
        accounts_synced=120,
        accounts_created=3,
        accounts_updated=10,
        accounts_deactivated=1,
        session_id="s-1",
    )
    assert payload["ext"]["type"] == "sync_accounts"
    assert payload["ext"]["data"]["instances"]["failed"] == 1


@pytest.mark.unit
def test_build_sync_databases_summary_has_ext_data() -> None:
    from app.services.task_runs.task_run_summary_builders import build_sync_databases_summary

    payload = build_sync_databases_summary(
        task_key="sync_databases",
        inputs={"manual_run": False},
        instances_total=2,
        instances_successful=2,
        instances_failed=0,
        total_size_mb=123.4,
        session_id="s-2",
    )
    assert payload["ext"]["type"] == "sync_databases"
    assert payload["ext"]["data"]["instances"]["total"] == 2


@pytest.mark.unit
def test_build_calculate_database_aggregations_summary_has_periods() -> None:
    from app.services.task_runs.task_run_summary_builders import build_calculate_database_aggregations_summary

    payload = build_calculate_database_aggregations_summary(
        task_key="calculate_database_aggregations",
        inputs={"requested_periods": ["daily"]},
        periods_executed=["daily"],
        instances_total=1,
        instances_successful=1,
        instances_failed=0,
        record_instance=10,
        record_database=20,
        session_id="s-3",
    )
    assert payload["ext"]["type"] == "calculate_database_aggregations"
    assert payload["ext"]["data"]["periods_executed"] == ["daily"]


@pytest.mark.unit
def test_build_calculate_account_classification_summary_has_scope_time() -> None:
    from datetime import date

    from app.services.task_runs.task_run_summary_builders import build_calculate_account_classification_summary

    payload = build_calculate_account_classification_summary(
        task_key="calculate_account_classification",
        inputs={},
        stat_date=date(2026, 1, 22),
        computed_at=None,
        rules_count=1,
        accounts_count=2,
        rule_match_rows=3,
        classification_match_rows=4,
    )
    assert payload["ext"]["type"] == "calculate_account_classification"
    assert payload["common"]["scope"]["time"]["type"] == "date"
    assert payload["common"]["scope"]["time"]["date"] == "2026-01-22"


@pytest.mark.unit
def test_build_auto_classify_accounts_summary_has_ext_data() -> None:
    from app.services.task_runs.task_run_summary_builders import build_auto_classify_accounts_summary

    payload = build_auto_classify_accounts_summary(
        task_key="auto_classify_accounts",
        inputs={"instance_id": 1},
        rules_count=2,
        accounts_count=10,
        total_matches=3,
        total_classifications_added=4,
        failed_count=0,
        duration_ms=12,
    )
    assert payload["ext"]["type"] == "auto_classify_accounts"
    assert payload["ext"]["data"]["duration_ms"] == 12


@pytest.mark.unit
def test_build_capacity_aggregate_current_summary_has_ext_data() -> None:
    from datetime import date

    from app.services.task_runs.task_run_summary_builders import build_capacity_aggregate_current_summary

    payload = build_capacity_aggregate_current_summary(
        task_key="capacity_aggregate_current",
        inputs={"scope": "all"},
        scope="all",
        requested_period_type="daily",
        effective_period_type="daily",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 1),
        status="completed",
        message="ok",
    )
    assert payload["ext"]["type"] == "capacity_aggregate_current"
    assert payload["ext"]["data"]["scope"] == "all"
