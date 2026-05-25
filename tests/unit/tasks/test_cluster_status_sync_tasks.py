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


@pytest.mark.unit
def test_sync_cluster_status_writes_items_and_completed_with_errors(monkeypatch) -> None:
    from app.tasks import cluster_status_sync_tasks

    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    monkeypatch.setattr(cluster_status_sync_tasks, "create_app", lambda **_: app)

    with app.app_context():
        _create_schema()
        mysql = MySQLCluster(name="mysql-a")
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

        cluster_status_sync_tasks.sync_cluster_status(manual_run=True)

        run = TaskRun.query.filter_by(task_key="sync_cluster_status").one()
        assert run.task_name == "群集同步状态检测"
        assert run.task_category == "cluster"
        assert run.status == TaskRunStatus.COMPLETED_WITH_ERRORS
        assert run.summary_json["metrics"]["mysql_clusters_total"] == 1
        assert run.summary_json["metrics"]["sqlserver_clusters_total"] == 1
        assert run.summary_json["metrics"]["clusters_failed"] == 1

        item_types = {item.item_type for item in TaskRunItem.query.filter_by(run_id=run.run_id).all()}
        assert item_types == {"mysql_cluster", "sqlserver_cluster"}
