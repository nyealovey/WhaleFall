from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerCluster, SQLServerClusterInstance

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
