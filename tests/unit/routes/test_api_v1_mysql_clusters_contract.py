import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.models.mysql_cluster import MySQLCluster, MySQLClusterInstance
from app.models.user import User


def _create_schema() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["users"],
            db.metadata.tables["instances"],
            db.metadata.tables["mysql_clusters"],
            db.metadata.tables["mysql_cluster_instances"],
        ],
    )


def _login(client, user: User) -> None:
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)


def _csrf(client) -> str:
    response = client.get("/api/v1/auth/csrf-token")
    assert response.status_code == 200
    payload = response.get_json()
    token = payload.get("data", {}).get("csrf_token")
    assert isinstance(token, str)
    return token


def _make_instance(*, name: str, db_type: str, host: str, port: int) -> Instance:
    instance = Instance()
    instance.name = name
    instance.db_type = db_type
    instance.host = host
    instance.port = port
    return instance


def _make_mysql_cluster(*, name: str, description: str = "") -> MySQLCluster:
    cluster = MySQLCluster()
    cluster.name = name
    cluster.description = description
    return cluster


def _make_mysql_cluster_instance(
    *,
    cluster_id: int,
    instance_id: int,
    replication_role: str,
    replication_status: str,
    seconds_behind_source: int | None = None,
    read_only: bool | None = None,
    super_read_only: bool | None = None,
) -> MySQLClusterInstance:
    binding = MySQLClusterInstance()
    binding.cluster_id = cluster_id
    binding.instance_id = instance_id
    binding.replication_role = replication_role
    binding.replication_status = replication_status
    binding.seconds_behind_source = seconds_behind_source
    binding.read_only = read_only
    binding.super_read_only = super_read_only
    return binding


@pytest.mark.unit
def test_api_v1_mysql_clusters_detail_returns_replication_diagnostic_fields() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    app.config["MYSQL_REPLICA_LAG_ABNORMAL_THRESHOLD_SECONDS"] = 600

    with app.app_context():
        _create_schema()
        user = User(username="viewer", password="TestPass1", role="user")
        instance = _make_instance(name="mysql-1", db_type=DatabaseType.MYSQL, host="10.0.0.2", port=3306)
        cluster = _make_mysql_cluster(name="mysql-cluster-a", description="")
        db.session.add_all([user, instance, cluster])
        db.session.flush()
        binding = _make_mysql_cluster_instance(
            cluster_id=cluster.id,
            instance_id=instance.id,
            replication_role="replica",
            replication_status="healthy",
            seconds_behind_source=601,
            read_only=True,
            super_read_only=True,
        )
        binding.id = 900
        db.session.add(binding)
        db.session.commit()

        client = app.test_client()
        _login(client, user)

        response = client.get(f"/api/v1/mysql-clusters/{cluster.id}")

        assert response.status_code == 200
        data = response.get_json()["data"]
        item = data["instances"][0]
        assert data["cluster"]["abnormal_replica_count"] == 1
        assert item["id"] == instance.id
        assert item["instance_id"] == instance.id
        assert item["binding_id"] == binding.id
        assert item["replication_status"] == "unhealthy"
        assert {
            "io_state",
            "source_log_file",
            "read_source_log_pos",
            "relay_source_log_file",
            "exec_source_log_pos",
            "sql_delay",
            "retrieved_gtid_set",
            "executed_gtid_set",
            "last_io_error",
            "last_sql_error",
            "read_only",
            "super_read_only",
        }.issubset(item.keys())
        assert item["lag_abnormal"] is True
        assert item["lag_threshold_seconds"] == 600


@pytest.mark.unit
def test_api_v1_mysql_clusters_sync_topology_envelope_contract(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        user = User(username="admin", password="TestPass1", role="admin")
        cluster = _make_mysql_cluster(name="mysql-cluster-a", description="")
        db.session.add_all([user, cluster])
        db.session.commit()

        def _fake_sync(self, cluster_id, *, operator_id=None):
            assert cluster_id == cluster.id
            assert operator_id == user.id
            return {
                "cluster_id": cluster_id,
                "status": "completed",
                "instances_total": 1,
                "instances_failed": 0,
                "abnormal_replica_count": 0,
                "abnormal_database_count": 0,
                "items": [{"name": "mysql-1", "replication_status": "healthy"}],
            }

        monkeypatch.setattr(
            "app.services.mysql_clusters.service.MySQLClusterManagementService.sync_topology",
            _fake_sync,
            raising=False,
        )

        client = app.test_client()
        _login(client, user)
        headers = {"X-CSRFToken": _csrf(client)}

        response = client.post(
            f"/api/v1/mysql-clusters/{cluster.id}/actions/sync-topology",
            json={},
            headers=headers,
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["data"]["sync_result"]["cluster_id"] == cluster.id
        assert payload["data"]["sync_result"]["items"][0]["replication_status"] == "healthy"
