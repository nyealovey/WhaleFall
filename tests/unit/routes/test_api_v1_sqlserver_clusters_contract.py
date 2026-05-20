import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerCluster
from app.models.user import User


def _create_schema() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["users"],
            db.metadata.tables["credentials"],
            db.metadata.tables["instances"],
            db.metadata.tables["sqlserver_clusters"],
            db.metadata.tables["sqlserver_cluster_instances"],
            db.metadata.tables["sqlserver_availability_groups"],
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


@pytest.mark.unit
def test_api_v1_sqlserver_clusters_requires_auth(client) -> None:
    response = client.get("/api/v1/sqlserver-clusters")

    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_sqlserver_clusters_list_and_detail_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        user = User(username="admin", password="TestPass1", role="admin")
        cluster = SQLServerCluster(name="cluster-a", description="主群集", is_enabled=True)
        db.session.add_all([user, cluster])
        db.session.commit()

        client = app.test_client()
        _login(client, user)

        list_response = client.get("/api/v1/sqlserver-clusters")
        assert list_response.status_code == 200
        list_payload = list_response.get_json()
        data = list_payload.get("data")
        assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
        item = data["items"][0]
        assert {
            "id",
            "name",
            "description",
            "is_enabled",
            "instance_count",
            "availability_group_count",
            "contained_ag_count",
            "last_ag_sync_status",
        }.issubset(item.keys())

        detail_response = client.get(f"/api/v1/sqlserver-clusters/{cluster.id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.get_json().get("data")
        assert {"cluster", "instances", "availability_groups"}.issubset(detail_data.keys())
        assert detail_data["cluster"]["name"] == "cluster-a"


@pytest.mark.unit
def test_api_v1_sqlserver_clusters_create_bind_and_ag_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        user = User(username="admin", password="TestPass1", role="admin")
        instance = Instance(name="sql-1", db_type=DatabaseType.SQLSERVER, host="127.0.0.1", port=1433)
        db.session.add_all([user, instance])
        db.session.commit()

        client = app.test_client()
        _login(client, user)
        headers = {"X-CSRFToken": _csrf(client)}

        create_response = client.post(
            "/api/v1/sqlserver-clusters",
            json={"name": "cluster-a", "description": "主群集", "is_enabled": True},
            headers=headers,
        )
        assert create_response.status_code == 201
        cluster = create_response.get_json()["data"]["cluster"]
        assert cluster["name"] == "cluster-a"

        bind_response = client.put(
            f"/api/v1/sqlserver-clusters/{cluster['id']}/instances",
            json={"instance_ids": [instance.id]},
            headers=headers,
        )
        assert bind_response.status_code == 200
        assert bind_response.get_json()["data"]["instances"][0]["id"] == instance.id

        ag_response = client.post(
            f"/api/v1/sqlserver-clusters/{cluster['id']}/availability-groups",
            json={
                "name": "ag-main",
                "listener_name": "ag-listener",
                "listener_host": "ag.example.test",
                "listener_port": 1433,
                "contained_enabled": True,
                "is_enabled": False,
            },
            headers=headers,
        )
        assert ag_response.status_code == 201
        ag = ag_response.get_json()["data"]["availability_group"]
        assert ag["name"] == "ag-main"
        assert ag["contained_enabled"] is True
        assert "account_credential_id" in ag
        assert "account_credential_name" in ag

        patch_response = client.patch(
            f"/api/v1/sqlserver-clusters/{cluster['id']}/availability-groups/{ag['id']}",
            json={"is_enabled": False},
            headers=headers,
        )
        assert patch_response.status_code == 200
        assert patch_response.get_json()["data"]["availability_group"]["is_enabled"] is False


@pytest.mark.unit
def test_api_v1_sqlserver_clusters_sync_ag_contract(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        user = User(username="admin", password="TestPass1", role="admin")
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([user, cluster])
        db.session.commit()

        def _fake_sync(self, cluster_id, payload, *, operator_id=None):
            assert cluster_id == cluster.id
            assert payload == {}
            assert operator_id == user.id
            return {
                "cluster_id": cluster_id,
                "created": 1,
                "updated": 0,
                "deleted": 1,
                "total": 1,
                "items": [{"name": "ag-main", "listener_host": "ag.example.test"}],
            }

        monkeypatch.setattr(
            "app.services.sqlserver_clusters.service.SQLServerClusterManagementService.sync_availability_groups",
            _fake_sync,
            raising=False,
        )

        client = app.test_client()
        _login(client, user)
        headers = {"X-CSRFToken": _csrf(client)}

        response = client.post(
            f"/api/v1/sqlserver-clusters/{cluster.id}/availability-groups/actions/sync",
            json={},
            headers=headers,
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["data"]["sync_result"]["created"] == 1
        assert payload["data"]["sync_result"]["deleted"] == 1
        assert payload["data"]["sync_result"]["items"][0]["name"] == "ag-main"


@pytest.mark.unit
def test_api_v1_sqlserver_clusters_write_requires_admin_permission() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        user = User(username="operator", password="TestPass1", role="user")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        _login(client, user)
        headers = {"X-CSRFToken": _csrf(client)}

        read_response = client.get("/api/v1/sqlserver-clusters")
        assert read_response.status_code == 200

        write_response = client.post(
            "/api/v1/sqlserver-clusters",
            json={"name": "cluster-a"},
            headers=headers,
        )
        assert write_response.status_code == 403
