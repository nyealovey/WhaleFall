from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.services.cluster_status_sync.issue_contract import (
    ClusterAbnormalIssue,
    ClusterStatusDetectionResult,
    build_failed_cluster_status_result,
)


@pytest.mark.unit
def test_cluster_status_detection_result_builds_mysql_alert_payload_and_task_metrics() -> None:
    result = ClusterStatusDetectionResult.from_result(
        cluster_type="mysql_cluster",
        cluster_id=7,
        cluster_name="mysql-prod",
        run_id="run-1",
        result={
            "status": "completed",
            "abnormal_database_count": 0,
            "abnormal_replica_count": 1,
            "items": [
                {
                    "name": "mysql-replica-1",
                    "replication_status": "unhealthy",
                    "last_error": "Got fatal error 1236 from master",
                    "seconds_behind_source": None,
                },
            ],
        },
    )

    assert result.is_abnormal is True
    assert result.task_metrics() == {
        "abnormal_database_count": 0,
        "abnormal_replica_count": 1,
    }
    assert result.alert_dedupe_key == "mysql_cluster:7"
    assert result.alert_payload() == {
        "cluster_id": 7,
        "cluster_name": "mysql-prod",
        "cluster_type": "mysql_cluster",
        "status": "completed",
        "error_message": None,
        "abnormal_database_count": 0,
        "abnormal_replica_count": 1,
        "run_id": "run-1",
        "summary_text": "mysql-replica-1: Got fatal error 1236 from master",
    }


@pytest.mark.unit
def test_cluster_status_detection_result_prefers_failed_error_message_and_builds_failed_result() -> None:
    failed_result = build_failed_cluster_status_result(
        cluster_id=8,
        error_message="driver boom sqlserver",
    )
    result = ClusterStatusDetectionResult.from_result(
        cluster_type="sqlserver_cluster",
        cluster_id=8,
        cluster_name="sql-broken",
        run_id="run-2",
        result=failed_result,
    )

    assert failed_result == {
        "cluster_id": 8,
        "status": "failed",
        "error_message": "driver boom sqlserver",
        "abnormal_database_count": 0,
        "abnormal_replica_count": 0,
        "items": [],
        "replicas": [],
    }
    assert result.is_failed is True
    assert result.is_abnormal is True
    assert result.task_error_message() == "driver boom sqlserver"
    assert result.summary_text() == "driver boom sqlserver"
    assert result.to_details_json() is failed_result


@pytest.mark.unit
def test_cluster_status_detection_result_summarizes_sqlserver_abnormal_rows() -> None:
    result = ClusterStatusDetectionResult.from_result(
        cluster_type="sqlserver_cluster",
        cluster_id=9,
        cluster_name="sql-ag-prod",
        run_id="run-3",
        result={
            "status": "completed",
            "abnormal_database_count": 1,
            "abnormal_replica_count": 1,
            "items": [
                {
                    "replica_server_name": "sql-secondary",
                    "database_name": "billing",
                    "is_abnormal": True,
                    "error_summary": "sync_state=NOT_SYNCHRONIZING",
                },
            ],
            "replicas": [
                {
                    "replica_server_name": "sql-secondary",
                    "is_abnormal": True,
                    "error_summary": "health=NOT_HEALTHY",
                },
            ],
        },
    )

    assert result.summary_text() == (
        "sql-secondary/billing: sync_state=NOT_SYNCHRONIZING; "
        "sql-secondary: health=NOT_HEALTHY"
    )


@pytest.mark.unit
def test_cluster_abnormal_issue_serializes_mysql_risk_payload() -> None:
    occurred_at = datetime(2026, 3, 17, 9, 0, tzinfo=UTC)
    issue = ClusterAbnormalIssue.mysql_replication(
        instance_id=12,
        cluster_name="mysql-prod",
        detail_suffix="Got fatal error 1236 from source",
        occurred_at=occurred_at,
    )

    assert issue.to_risk_kwargs() == {
        "rule_key": "cluster_abnormal",
        "category": "cluster",
        "severity": "medium",
        "label": "群集异常",
        "detail": "MySQL 群集 mysql-prod 副节点复制异常: Got fatal error 1236 from source",
        "occurred_at": occurred_at,
        "target_url": "/cluster/",
    }


@pytest.mark.unit
def test_cluster_abnormal_issue_resolves_sqlserver_secondary_replica_and_database() -> None:
    occurred_at = datetime(2026, 3, 17, 9, 0, tzinfo=UTC)
    replica = SimpleNamespace(
        cluster_id=3,
        ag_name="ag-main",
        replica_server_name="sql-secondary",
        role_desc="SECONDARY",
        is_primary=False,
        is_abnormal=True,
        error_summary="health=NOT_HEALTHY",
        last_checked_at=occurred_at,
    )
    database = SimpleNamespace(
        cluster_id=3,
        ag_name="ag-main",
        replica_server_name="sql-secondary",
        database_name="billing",
        error_summary="sync_state=NOT_SYNCHRONIZING",
        last_checked_at=occurred_at,
    )

    replica_issue = ClusterAbnormalIssue.sqlserver_replica(
        instance_id=21,
        cluster_name="sql-cluster",
        row=replica,
    )
    database_issue = ClusterAbnormalIssue.sqlserver_database(
        instance_id=21,
        cluster_name="sql-cluster",
        row=database,
    )

    assert replica_issue.to_risk_kwargs()["detail"] == (
        "SQL Server 群集 sql-cluster AG ag-main 副本 sql-secondary 异常: health=NOT_HEALTHY"
    )
    assert database_issue.to_risk_kwargs()["detail"] == (
        "SQL Server 群集 sql-cluster AG ag-main 数据库 billing 同步异常: sync_state=NOT_SYNCHRONIZING"
    )
