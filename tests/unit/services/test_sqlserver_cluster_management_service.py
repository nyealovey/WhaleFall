from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.core.exceptions import ConflictError, ValidationError
from app.core.types import JsonValue, SyncConnection
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.services.sqlserver_clusters.service import SQLServerClusterManagementService


def _create_schema() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["credentials"],
            db.metadata.tables["instances"],
            db.metadata.tables["sqlserver_clusters"],
            db.metadata.tables["sqlserver_cluster_instances"],
            db.metadata.tables["sqlserver_availability_groups"],
        ],
    )


@pytest.mark.unit
def test_create_cluster_rejects_duplicate_name() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        service = SQLServerClusterManagementService()
        created = service.create_cluster({"name": "cluster-a", "description": "主群集"})
        assert created["name"] == "cluster-a"

        with pytest.raises(ValidationError, match="群集名称已存在"):
            service.create_cluster({"name": "cluster-a"})


@pytest.mark.unit
def test_replace_instances_allows_only_existing_sqlserver_instances() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        sqlserver = Instance(name="sql-1", db_type=DatabaseType.SQLSERVER, host="127.0.0.1", port=1433)
        mysql = Instance(name="mysql-1", db_type=DatabaseType.MYSQL, host="127.0.0.1", port=3306)
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([sqlserver, mysql, cluster])
        db.session.commit()

        service = SQLServerClusterManagementService()
        result = service.replace_instances(cluster.id, {"instance_ids": [sqlserver.id]})
        assert [item["id"] for item in result["instances"]] == [sqlserver.id]

        with pytest.raises(ValidationError, match="只能绑定未删除的 SQL Server 实例"):
            service.replace_instances(cluster.id, {"instance_ids": [mysql.id]})


@pytest.mark.unit
def test_replace_instances_rejects_instance_bound_to_other_cluster() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        instance = Instance(name="sql-1", db_type=DatabaseType.SQLSERVER, host="127.0.0.1", port=1433)
        first = SQLServerCluster(name="cluster-a", description="")
        second = SQLServerCluster(name="cluster-b", description="")
        db.session.add_all([instance, first, second])
        db.session.commit()

        service = SQLServerClusterManagementService()
        service.replace_instances(first.id, {"instance_ids": [instance.id]})

        with pytest.raises(ConflictError, match="已绑定到群集 cluster-a"):
            service.replace_instances(second.id, {"instance_ids": [instance.id]})


@pytest.mark.unit
def test_availability_group_name_is_unique_within_cluster_only() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        first = SQLServerCluster(name="cluster-a", description="")
        second = SQLServerCluster(name="cluster-b", description="")
        db.session.add_all([first, second])
        db.session.commit()

        service = SQLServerClusterManagementService()
        payload = {"name": "ag-main", "listener_host": "ag.example.test"}
        created = service.create_availability_group(first.id, payload)
        assert created["name"] == "ag-main"

        with pytest.raises(ValidationError, match="AG 名称已存在"):
            service.create_availability_group(first.id, payload)

        other = service.create_availability_group(second.id, payload)
        assert other["name"] == "ag-main"


class _FakeAgDiscoveryConnection:
    def __init__(self, rows: list[Sequence[JsonValue]]) -> None:
        self.rows = rows
        self.disconnected = False

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        self.disconnected = True

    def execute_query(
        self,
        query: str,
        params: Sequence[JsonValue] | Mapping[str, JsonValue] | None = None,
    ) -> list[Sequence[JsonValue]]:
        _ = (query, params)
        return self.rows


class _FakeAgDiscoveryFactory:
    def __init__(self, rows: list[Sequence[JsonValue]]) -> None:
        self.connection = _FakeAgDiscoveryConnection(rows)
        self.targets: list[Any] = []

    def create_connection(self, instance: Instance) -> SyncConnection:
        self.targets.append(instance)
        return self.connection


@pytest.mark.unit
def test_sync_availability_groups_discovers_ags_from_bound_instance() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        credential = Credential(
            name="ag-sync-account",
            credential_type="database",
            db_type=DatabaseType.SQLSERVER,
            username="ag_reader",
            password="secret",
        )
        instance = Instance(name="sql-node-1", db_type=DatabaseType.SQLSERVER, host="10.0.0.11", port=1433)
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([credential, instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        db.session.commit()

        factory = _FakeAgDiscoveryFactory(
            [
                ("ag-main", "ag-main-lsn", "ag-main.example.test", 1433, True, "10.10.10.173"),
                ("ag-report", None, "ag-report.example.test", None, False),
            ]
        )
        service = SQLServerClusterManagementService(connection_factory=factory)

        result = service.sync_availability_groups(
            cluster.id,
            {"credential_id": credential.id, "connection_database": "master"},
        )

        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["total"] == 2
        assert result["source_instance"]["id"] == instance.id
        assert factory.targets[0].credential_id == credential.id
        assert factory.targets[0].credential == credential
        ags = SQLServerAvailabilityGroup.query.order_by(SQLServerAvailabilityGroup.name.asc()).all()
        assert [(ag.name, ag.listener_host, ag.listener_port, ag.contained_enabled) for ag in ags] == [
            ("ag-main", "10.10.10.173", 1433, True),
            ("ag-report", "ag-report.example.test", 1433, False),
        ]
        assert {ag.credential_id for ag in ags} == {credential.id}
        assert factory.connection.disconnected is True


@pytest.mark.unit
def test_sync_availability_groups_updates_existing_ag_without_duplicate() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        credential = Credential(
            name="ag-sync-account",
            credential_type="database",
            db_type=DatabaseType.SQLSERVER,
            username="ag_reader",
            password="secret",
        )
        instance = Instance(name="sql-node-1", db_type=DatabaseType.SQLSERVER, host="10.0.0.11", port=1433)
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([credential, instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        db.session.add(
            SQLServerAvailabilityGroup(
                cluster_id=cluster.id,
                name="ag-main",
                listener_name="old-listener",
                listener_host="old.example.test",
                listener_port=1433,
            )
        )
        db.session.commit()

        service = SQLServerClusterManagementService(
            connection_factory=_FakeAgDiscoveryFactory(
                [("ag-main", "ag-main-lsn", "ag-main.example.test", 1444, True)]
            )
        )

        result = service.sync_availability_groups(cluster.id, {"credential_id": credential.id})

        assert result["created"] == 0
        assert result["updated"] == 1
        assert SQLServerAvailabilityGroup.query.count() == 1
        ag = SQLServerAvailabilityGroup.query.one()
        assert ag.listener_name == "ag-main-lsn"
        assert ag.listener_host == "ag-main.example.test"
        assert ag.listener_port == 1444
        assert ag.credential_id == credential.id


@pytest.mark.unit
def test_sync_availability_groups_requires_bound_instance_and_credential() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        credential = Credential(
            name="ag-sync-account",
            credential_type="database",
            db_type=DatabaseType.SQLSERVER,
            username="ag_reader",
            password="secret",
        )
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([credential, cluster])
        db.session.commit()

        service = SQLServerClusterManagementService(connection_factory=_FakeAgDiscoveryFactory([]))

        with pytest.raises(ValidationError, match="请选择 AG 凭据"):
            service.sync_availability_groups(cluster.id, {})

        with pytest.raises(ValidationError, match="请先绑定 SQL Server 实例"):
            service.sync_availability_groups(cluster.id, {"credential_id": credential.id})
