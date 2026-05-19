import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.core.exceptions import ConflictError, ValidationError
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerCluster
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
