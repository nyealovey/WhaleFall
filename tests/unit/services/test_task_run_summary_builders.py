from datetime import date

import pytest

from app.services.task_runs.task_run_summary_builders import (
    build_auto_classify_accounts_summary,
    build_calculate_account_classification_summary,
    build_calculate_database_aggregations_summary,
    build_capacity_aggregate_current_summary,
    build_sync_ad_accounts_summary,
    build_sync_accounts_summary,
    build_sync_cluster_status_summary,
    build_sync_databases_summary,
    build_sync_jumpserver_assets_summary,
    build_sync_veeam_backups_summary,
    merge_sync_veeam_sources_summary,
)


@pytest.mark.unit
def test_build_sync_accounts_summary_has_common_metrics_and_ext_data() -> None:
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
def test_build_sync_cluster_status_summary_has_common_metrics_and_ext_data() -> None:
    payload = build_sync_cluster_status_summary(
        inputs={"manual_run": True},
        mysql_clusters_total=2,
        sqlserver_clusters_total=3,
        clusters_successful=4,
        clusters_failed=1,
        abnormal_database_count=5,
        abnormal_replica_count=6,
    )

    metrics = {metric["key"]: metric["value"] for metric in payload["common"]["metrics"]}
    assert payload["ext"]["type"] == "sync_cluster_status"
    assert payload["ext"]["data"]["clusters"] == {
        "mysql_total": 2,
        "sqlserver_total": 3,
        "successful": 4,
        "failed": 1,
    }
    assert payload["ext"]["data"]["abnormal"] == {
        "database_count": 5,
        "replica_count": 6,
    }
    assert metrics["clusters_failed"] == 1


@pytest.mark.unit
def test_build_sync_ad_accounts_summary_has_common_metrics_and_ext_data() -> None:
    payload = build_sync_ad_accounts_summary(
        inputs={"manual_run": True},
        domains_total=2,
        domains_successful=1,
        domains_failed=1,
        accounts_total=10,
        accounts_normal=7,
        accounts_disabled=2,
        accounts_orphaned=1,
        accounts_updated=4,
        ad_users_total=8,
        ad_groups_total=3,
        ad_principals_total=11,
    )

    metrics = {metric["key"]: metric["value"] for metric in payload["common"]["metrics"]}
    assert payload["ext"]["type"] == "sync_ad_accounts"
    assert payload["ext"]["data"]["domains"] == {"total": 2, "successful": 1, "failed": 1}
    assert payload["ext"]["data"]["accounts"]["updated"] == 4
    assert payload["ext"]["data"]["ad_principals"] == {
        "users_total": 8,
        "groups_total": 3,
        "principals_total": 11,
    }
    assert metrics["ad_principals_total"] == 11


@pytest.mark.unit
def test_build_calculate_database_aggregations_summary_has_periods() -> None:
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


@pytest.mark.unit
def test_build_sync_jumpserver_assets_summary_has_asset_counts() -> None:
    payload = build_sync_jumpserver_assets_summary(
        task_key="sync_jumpserver_assets",
        inputs={"manual_run": True},
        received_total=5,
        supported_total=3,
        snapshots_written_total=3,
        skipped_unsupported=1,
        skipped_invalid=1,
        skipped=False,
        skip_reason=None,
        error_message=None,
    )

    assert payload["ext"]["type"] == "sync_jumpserver_assets"
    assert payload["ext"]["data"]["assets"]["received_total"] == 5
    assert payload["ext"]["data"]["assets"]["snapshots_written_total"] == 3


@pytest.mark.unit
def test_build_sync_veeam_backups_summary_has_coverage_counts() -> None:
    payload = build_sync_veeam_backups_summary(
        task_key="sync_veeam_backups",
        inputs={"manual_run": True},
        received_total=2090,
        snapshots_written_total=67,
        skipped_invalid=0,
        timed_out_backup_objects_total=0,
        backup_files_scanned_total=3896,
        backup_ids_total=34,
        backup_ids_completed=26,
        timed_out_backup_ids_total=1,
        failed_backup_ids_total=7,
        restore_points_expected_total=2090,
        restore_points_enriched_total=949,
        restore_points_missing_metrics_total=1141,
        backup_ids_fully_covered_total=18,
        backup_ids_partially_covered_total=8,
        partial_success=True,
        sources=[
            {
                "source_binding_id": 1,
                "source_name": "Veeam A",
                "status": "completed",
                "snapshots_written_total": 67,
                "error_message": None,
            },
            {
                "source_binding_id": 2,
                "source_name": "Veeam B",
                "status": "failed",
                "snapshots_written_total": 0,
                "error_message": "token error",
            },
        ],
        error_message=None,
    )

    assert payload["ext"]["type"] == "sync_veeam_backups"
    assert payload["ext"]["data"]["backups"]["backup_files_scanned_total"] == 3896
    assert payload["ext"]["data"]["backups"]["restore_points_expected_total"] == 2090
    assert payload["ext"]["data"]["backups"]["restore_points_enriched_total"] == 949
    assert payload["ext"]["data"]["backups"]["restore_points_missing_metrics_total"] == 1141
    assert payload["ext"]["data"]["backups"]["backup_ids_fully_covered_total"] == 18
    assert payload["ext"]["data"]["backups"]["backup_ids_partially_covered_total"] == 8
    assert payload["ext"]["data"]["sources"] == [
        {
            "source_binding_id": 1,
            "source_name": "Veeam A",
            "status": "completed",
            "snapshots_written_total": 67,
            "error_message": None,
        },
        {
            "source_binding_id": 2,
            "source_name": "Veeam B",
            "status": "failed",
            "snapshots_written_total": 0,
            "error_message": "token error",
        },
    ]


@pytest.mark.unit
def test_merge_sync_veeam_sources_summary_preserves_envelope_and_common_metrics() -> None:
    payload = build_sync_veeam_backups_summary(
        task_key="sync_veeam_backups",
        inputs={"manual_run": True},
        received_total=3,
        snapshots_written_total=1,
        skipped_invalid=0,
        partial_success=False,
    )

    merged = merge_sync_veeam_sources_summary(
        payload,
        sources=[
            {
                "source_binding_id": 1,
                "source_name": "Veeam A",
                "status": "completed",
                "snapshots_written_total": 1,
                "error_message": None,
            }
        ],
        partial_success=True,
    )

    assert merged["version"] == 1
    assert merged["ext"]["type"] == "sync_veeam_backups"
    assert isinstance(merged["common"]["metrics"], list)
    assert merged["ext"]["data"]["sources"] == [
        {
            "source_binding_id": 1,
            "source_name": "Veeam A",
            "status": "completed",
            "snapshots_written_total": 1,
            "error_message": None,
        }
    ]
    assert merged["ext"]["data"]["partial_success"] is True
