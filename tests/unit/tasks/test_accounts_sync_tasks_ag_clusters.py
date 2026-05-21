from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerCluster, SQLServerClusterInstance
from app.models.task_run_item import TaskRunItem
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

accounts_tasks_module = importlib.import_module("app.tasks.accounts_sync_tasks")


class _DummyLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return None

    def exception(self, *_args: object, **_kwargs: object) -> None:
        return None


@dataclass(slots=True)
class _DummySession:
    session_id: str


@pytest.mark.unit
def test_accounts_sync_task_syncs_ag_accounts_once_per_cluster_after_instances(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_cluster_instances"],
            ],
        )
        first_instance = Instance(
            name="node-a",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        second_instance = Instance(
            name="node-b",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.12",
            port=1433,
            is_active=True,
        )
        mysql_instance = Instance(
            name="mysql-a",
            db_type=DatabaseType.MYSQL,
            host="10.0.0.13",
            port=3306,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-a", description="", is_enabled=True)
        db.session.add_all([first_instance, second_instance, mysql_instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=first_instance.id))
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=second_instance.id))
        db.session.commit()

        calls: list[int] = []

        class _FakeAgSyncService:
            def sync_for_cluster(self, cluster_id: int, *, session_id: str | None = None) -> dict[str, Any]:
                calls.append(cluster_id)
                assert session_id == "session-1"
                return {"status": "completed", "processed_records": 2}

        monkeypatch.setattr(accounts_tasks_module, "SQLServerAgAccountsSyncService", _FakeAgSyncService)

        totals = accounts_tasks_module._sync_ag_clusters(
            sync_logger=_DummyLogger(),
            session=_DummySession(session_id="session-1"),
            instances=[first_instance, second_instance, mysql_instance],
        )

        assert calls == [cluster.id]
        assert totals.clusters_synced == 1
        assert totals.clusters_failed == 0
        assert totals.accounts_synced == 2


@pytest.mark.unit
def test_accounts_sync_task_writes_ag_cluster_task_run_item_status(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
                db.metadata.tables["instances"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_cluster_instances"],
            ],
        )
        instance = Instance(
            name="node-a",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-a", description="", is_enabled=True)
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        task_runs_service = TaskRunsWriteService()
        run_id = task_runs_service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="scheduled",
        )
        db.session.commit()

        ag_clusters = accounts_tasks_module._resolve_ag_clusters([instance])
        accounts_tasks_module._init_items(
            task_runs_service=task_runs_service,
            run_id=run_id,
            instances=[instance],
            ag_clusters=ag_clusters,
        )

        class _FakeAgSyncService:
            def sync_for_cluster(self, cluster_id: int, *, session_id: str | None = None) -> dict[str, Any]:
                assert cluster_id == cluster.id
                assert session_id == "session-1"
                return {"status": "completed", "processed_records": 3, "total_ag": 2, "failed_ag": 0}

        monkeypatch.setattr(accounts_tasks_module, "SQLServerAgAccountsSyncService", _FakeAgSyncService)

        totals = accounts_tasks_module._sync_ag_clusters(
            sync_logger=_DummyLogger(),
            task_runs_service=task_runs_service,
            run_id=run_id,
            session=_DummySession(session_id="session-1"),
            ag_clusters=ag_clusters,
        )

        item = TaskRunItem.query.filter_by(
            run_id=run_id,
            item_type="sqlserver_ag_cluster",
            item_key=str(cluster.id),
        ).one()
        assert item.status == "completed"
        assert item.item_name == "cluster-a AG账户同步"
        assert item.metrics_json == {"ag_accounts_synced": 3, "total_ag": 2, "failed_ag": 0}
        assert item.details_json["summary"] == "AG账户同步完成：处理 3 个账户，失败 AG 0 个"
        assert totals.clusters_synced == 1
        assert totals.clusters_failed == 0
        assert totals.accounts_synced == 3


@pytest.mark.unit
def test_accounts_sync_task_marks_ag_cluster_item_failed_when_service_fails(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
                db.metadata.tables["instances"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_cluster_instances"],
            ],
        )
        instance = Instance(
            name="node-a",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-a", description="", is_enabled=True)
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        task_runs_service = TaskRunsWriteService()
        run_id = task_runs_service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="scheduled",
        )
        db.session.commit()

        ag_clusters = accounts_tasks_module._resolve_ag_clusters([instance])
        accounts_tasks_module._init_items(
            task_runs_service=task_runs_service,
            run_id=run_id,
            instances=[instance],
            ag_clusters=ag_clusters,
        )

        class _FakeAgSyncService:
            def sync_for_cluster(self, cluster_id: int, *, session_id: str | None = None) -> dict[str, Any]:
                assert cluster_id == cluster.id
                assert session_id == "session-1"
                return {"status": "failed", "processed_records": 1, "total_ag": 2, "failed_ag": 1}

        monkeypatch.setattr(accounts_tasks_module, "SQLServerAgAccountsSyncService", _FakeAgSyncService)

        totals = accounts_tasks_module._sync_ag_clusters(
            sync_logger=_DummyLogger(),
            task_runs_service=task_runs_service,
            run_id=run_id,
            session=_DummySession(session_id="session-1"),
            ag_clusters=ag_clusters,
        )

        item = TaskRunItem.query.filter_by(
            run_id=run_id,
            item_type="sqlserver_ag_cluster",
            item_key=str(cluster.id),
        ).one()
        assert item.status == "failed"
        assert item.error_message == "AG账户同步失败"
        assert item.details_json["summary"] == "AG账户同步失败：处理 1 个账户，失败 AG 1 个"
        assert totals.clusters_synced == 0
        assert totals.clusters_failed == 1
