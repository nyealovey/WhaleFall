from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app import create_app, db
from app.core.constants.status_types import TaskRunStatus
from app.models.mysql_cluster import MySQLCluster
from app.models.sqlserver_cluster import SQLServerCluster
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem


def _create_schema() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["mysql_clusters"],
            db.metadata.tables["sqlserver_clusters"],
            db.metadata.tables["task_runs"],
            db.metadata.tables["task_run_items"],
        ],
    )


@dataclass(slots=True)
class _StubClusterStatusSyncService:
    mysql_results: dict[int, dict[str, Any]]
    sqlserver_results: dict[int, dict[str, Any]]

    def list_enabled_mysql_clusters(self) -> list[MySQLCluster]:
        return MySQLCluster.query.order_by(MySQLCluster.id.asc()).all()

    def list_enabled_sqlserver_clusters(self) -> list[SQLServerCluster]:
        return SQLServerCluster.query.order_by(SQLServerCluster.id.asc()).all()

    def sync_mysql_cluster(self, cluster_id: int) -> dict[str, Any]:
        return self.mysql_results[cluster_id]

    def sync_sqlserver_cluster(self, cluster_id: int) -> dict[str, Any]:
        return self.sqlserver_results[cluster_id]


@dataclass(slots=True)
class _MixedClusterStatusSyncService:
    mysql_clusters: list[MySQLCluster]
    sqlserver_clusters: list[SQLServerCluster]
    mysql_results: dict[int, dict[str, Any] | Exception]
    sqlserver_results: dict[int, dict[str, Any] | Exception]

    def list_enabled_mysql_clusters(self) -> list[MySQLCluster]:
        return self.mysql_clusters

    def list_enabled_sqlserver_clusters(self) -> list[SQLServerCluster]:
        return self.sqlserver_clusters

    def sync_mysql_cluster(self, cluster_id: int) -> dict[str, Any]:
        result = self.mysql_results[cluster_id]
        if isinstance(result, Exception):
            raise result
        return result

    def sync_sqlserver_cluster(self, cluster_id: int) -> dict[str, Any]:
        result = self.sqlserver_results[cluster_id]
        if isinstance(result, Exception):
            raise result
        return result


class _ListClustersError(RuntimeError):
    pass


class _ListFailingClusterStatusSyncService:
    def list_enabled_mysql_clusters(self) -> list[MySQLCluster]:
        raise _ListClustersError("list clusters boom")

    def list_enabled_sqlserver_clusters(self) -> list[SQLServerCluster]:
        return []

    def sync_mysql_cluster(self, cluster_id: int) -> dict[str, Any]:
        del cluster_id
        raise AssertionError("should not sync when listing failed")

    def sync_sqlserver_cluster(self, cluster_id: int) -> dict[str, Any]:
        del cluster_id
        raise AssertionError("should not sync when listing failed")


def _make_mysql_cluster(*, name: str) -> MySQLCluster:
    cluster = MySQLCluster()
    cluster.name = name
    return cluster


def _metric_values(summary_json: dict[str, Any]) -> dict[str, object]:
    return {metric["key"]: metric["value"] for metric in summary_json["common"]["metrics"]}


@pytest.mark.unit
def test_sync_cluster_status_writes_items_and_completed_with_errors(monkeypatch) -> None:
    from app.tasks import cluster_status_sync_tasks

    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    monkeypatch.setattr(cluster_status_sync_tasks, "create_app", lambda **_: app)

    with app.app_context():
        _create_schema()
        mysql = _make_mysql_cluster(name="mysql-a")
        sqlserver = SQLServerCluster(name="sql-a", domain_name="wz.dc", description="")
        db.session.add_all([mysql, sqlserver])
        db.session.commit()

        stub = _StubClusterStatusSyncService(
            mysql_results={
                mysql.id: {
                    "status": "completed",
                    "abnormal_database_count": 0,
                    "abnormal_replica_count": 0,
                    "items": [],
                },
            },
            sqlserver_results={
                sqlserver.id: {
                    "status": "failed",
                    "error_message": "connection failed",
                    "abnormal_database_count": 0,
                    "abnormal_replica_count": 0,
                },
            },
        )
        monkeypatch.setattr(cluster_status_sync_tasks, "ClusterStatusSyncService", lambda: stub)
        cluster_alert_calls: list[dict[str, Any]] = []

        class _StubEmailAlertEventService:
            def record_cluster_status_event(self, **kwargs: Any) -> bool:
                cluster_alert_calls.append(dict(kwargs))
                return True

        monkeypatch.setattr(
            cluster_status_sync_tasks, "EmailAlertEventService", lambda: _StubEmailAlertEventService(), raising=False
        )

        cluster_status_sync_tasks.sync_cluster_status(manual_run=True)

        run = TaskRun.query.filter_by(task_key="sync_cluster_status").one()
        assert run.task_name == "群集同步状态检测"
        assert run.task_category == "cluster"
        assert run.status == TaskRunStatus.COMPLETED_WITH_ERRORS
        assert run.summary_json["ext"]["type"] == "sync_cluster_status"
        assert run.summary_json["ext"]["data"]["clusters"] == {
            "mysql_total": 1,
            "sqlserver_total": 1,
            "successful": 1,
            "failed": 1,
        }
        assert _metric_values(run.summary_json)["clusters_failed"] == 1

        item_types = {item.item_type for item in TaskRunItem.query.filter_by(run_id=run.run_id).all()}
        assert item_types == {"mysql_cluster", "sqlserver_cluster"}
        assert cluster_alert_calls == [
            {
                "cluster_type": "mysql_cluster",
                "cluster_id": mysql.id,
                "cluster_name": "mysql-a",
                "run_id": run.run_id,
                "result": {
                    "status": "completed",
                    "abnormal_database_count": 0,
                    "abnormal_replica_count": 0,
                    "items": [],
                },
            },
            {
                "cluster_type": "sqlserver_cluster",
                "cluster_id": sqlserver.id,
                "cluster_name": "sql-a",
                "run_id": run.run_id,
                "result": {
                    "status": "failed",
                    "error_message": "connection failed",
                    "abnormal_database_count": 0,
                    "abnormal_replica_count": 0,
                },
            },
        ]


@pytest.mark.unit
def test_sync_cluster_status_marks_unexpected_cluster_exception_failed_and_continues(monkeypatch) -> None:
    from app.tasks import cluster_status_sync_tasks

    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    monkeypatch.setattr(cluster_status_sync_tasks, "create_app", lambda **_: app)

    with app.app_context():
        _create_schema()
        broken = SQLServerCluster(name="sql-broken", domain_name="wz.dc", description="")
        healthy = SQLServerCluster(name="sql-healthy", domain_name="wz.dc", description="")
        db.session.add_all([broken, healthy])
        db.session.commit()

        stub = _MixedClusterStatusSyncService(
            mysql_clusters=[],
            sqlserver_clusters=[broken, healthy],
            mysql_results={},
            sqlserver_results={
                broken.id: Exception("driver boom sqlserver"),
                healthy.id: {
                    "status": "completed",
                    "abnormal_database_count": 0,
                    "abnormal_replica_count": 0,
                    "items": [],
                    "replicas": [],
                },
            },
        )
        monkeypatch.setattr(cluster_status_sync_tasks, "ClusterStatusSyncService", lambda: stub)
        cluster_alert_calls: list[dict[str, Any]] = []

        class _StubEmailAlertEventService:
            def record_cluster_status_event(self, **kwargs: Any) -> bool:
                cluster_alert_calls.append(dict(kwargs))
                return True

        monkeypatch.setattr(
            cluster_status_sync_tasks, "EmailAlertEventService", lambda: _StubEmailAlertEventService(), raising=False
        )

        cluster_status_sync_tasks.sync_cluster_status(manual_run=True)

        run = TaskRun.query.filter_by(task_key="sync_cluster_status").one()
        assert run.status == TaskRunStatus.COMPLETED_WITH_ERRORS
        metrics = _metric_values(run.summary_json)
        assert metrics["clusters_failed"] == 1
        assert metrics["clusters_successful"] == 1
        assert run.summary_json["ext"]["data"]["clusters"]["failed"] == 1
        assert run.summary_json["ext"]["data"]["clusters"]["successful"] == 1
        failed_item = TaskRunItem.query.filter_by(
            run_id=run.run_id,
            item_type="sqlserver_cluster",
            item_key=str(broken.id),
        ).one()
        completed_item = TaskRunItem.query.filter_by(
            run_id=run.run_id,
            item_type="sqlserver_cluster",
            item_key=str(healthy.id),
        ).one()
        assert failed_item.status == TaskRunStatus.FAILED
        assert "driver boom sqlserver" in (failed_item.error_message or "")
        assert completed_item.status == TaskRunStatus.COMPLETED
        assert [call["cluster_name"] for call in cluster_alert_calls] == ["sql-broken", "sql-healthy"]


@pytest.mark.unit
def test_sync_cluster_status_marks_run_failed_when_listing_clusters_crashes(monkeypatch) -> None:
    from app.tasks import cluster_status_sync_tasks

    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    monkeypatch.setattr(cluster_status_sync_tasks, "create_app", lambda **_: app)

    with app.app_context():
        _create_schema()
        monkeypatch.setattr(
            cluster_status_sync_tasks,
            "ClusterStatusSyncService",
            lambda: _ListFailingClusterStatusSyncService(),
        )

        cluster_status_sync_tasks.sync_cluster_status(manual_run=True)

        run = TaskRun.query.filter_by(task_key="sync_cluster_status").one()
        assert run.status == TaskRunStatus.FAILED
        assert "list clusters boom" in (run.error_message or "")
