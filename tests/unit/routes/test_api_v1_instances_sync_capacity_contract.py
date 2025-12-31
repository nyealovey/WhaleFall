from datetime import date, datetime

import pytest

from app import db
from app.constants import DatabaseType
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase


def _ensure_instances_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )


def _ensure_capacity_sync_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_databases"],
            ],
        )


@pytest.mark.unit
def test_api_v1_instances_sync_capacity_requires_auth(app, client) -> None:
    _ensure_instances_tables(app)

    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = client.post(
        "/api/v1/instances/1/actions/sync-capacity",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_instances_sync_capacity_contract(app, auth_client, monkeypatch) -> None:
    _ensure_instances_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    class _DummyCapacitySyncCoordinator:
        def __init__(self, instance):  # noqa: ANN001
            self.instance = instance

        def connect(self) -> bool:
            return True

        def synchronize_inventory(self) -> dict:  # noqa: PLR6301
            return {"active_databases": ["db1"]}

        def collect_capacity(self, target_databases=None):  # noqa: ANN001
            del target_databases
            return [
                {
                    "database_name": "db1",
                    "size_mb": 1,
                    "collected_date": date(2025, 1, 1),
                    "collected_at": datetime(2025, 1, 1, 0, 0, 0),
                },
            ]

        def save_database_stats(self, data):  # noqa: ANN001
            del data
            return 1

        def update_instance_total_size(self) -> bool:  # noqa: PLR6301
            return True

        def disconnect(self) -> None:  # noqa: PLR6301
            return None

    class _DummyAggregationService:
        def calculate_daily_database_aggregations_for_instance(self, instance_id: int) -> None:
            del instance_id

        def calculate_daily_aggregations_for_instance(self, instance_id: int) -> None:
            del instance_id

    import app.services.aggregation as aggregation_module
    import app.services.database_sync as database_sync_module

    monkeypatch.setattr(database_sync_module, "CapacitySyncCoordinator", _DummyCapacitySyncCoordinator)
    monkeypatch.setattr(aggregation_module, "AggregationService", _DummyAggregationService)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/actions/sync-capacity",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    result = data.get("result")
    assert isinstance(result, dict)
    assert {"status", "message"}.issubset(result.keys())
    databases = result.get("databases")
    assert isinstance(databases, list)
    assert databases[0].get("collected_date") == "2025-01-01"
    assert databases[0].get("collected_at") == "2025-01-01T00:00:00"


@pytest.mark.unit
def test_api_v1_instances_sync_capacity_failure_keeps_inventory(app, auth_client, monkeypatch) -> None:
    _ensure_capacity_sync_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    class _DummyCapacitySyncCoordinator:
        def __init__(self, instance):  # noqa: ANN001
            self.instance = instance

        def connect(self) -> bool:
            return True

        def synchronize_inventory(self) -> dict:  # noqa: PLR6301
            db.session.add(InstanceDatabase(instance_id=self.instance.id, database_name="db1"))
            return {"active_databases": ["db1"]}

        def collect_capacity(self, target_databases=None):  # noqa: ANN001
            del target_databases
            return []

        def disconnect(self) -> None:  # noqa: PLR6301
            return None

    import app.services.database_sync as database_sync_module

    monkeypatch.setattr(database_sync_module, "CapacitySyncCoordinator", _DummyCapacitySyncCoordinator)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/actions/sync-capacity",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 409

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True

    with app.app_context():
        records = InstanceDatabase.query.filter_by(instance_id=instance_id).all()
        assert len(records) == 1


@pytest.mark.unit
def test_api_v1_instances_sync_capacity_exception_returns_sync_error_and_keeps_inventory(
    app,
    auth_client,
    monkeypatch,
) -> None:
    _ensure_capacity_sync_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    class _DummyCapacitySyncCoordinator:
        def __init__(self, instance):  # noqa: ANN001
            self.instance = instance

        def connect(self) -> bool:
            return True

        def synchronize_inventory(self) -> dict:  # noqa: PLR6301
            db.session.add(InstanceDatabase(instance_id=self.instance.id, database_name="db1"))
            return {"active_databases": ["db1"]}

        def collect_capacity(self, target_databases=None):  # noqa: ANN001
            del target_databases
            msg = "capacity collection failed"
            raise RuntimeError(msg)

        def disconnect(self) -> None:  # noqa: PLR6301
            return None

    import app.services.database_sync as database_sync_module

    monkeypatch.setattr(database_sync_module, "CapacitySyncCoordinator", _DummyCapacitySyncCoordinator)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/actions/sync-capacity",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 409

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True
    assert payload.get("message_code") == "SYNC_DATA_ERROR"

    with app.app_context():
        records = InstanceDatabase.query.filter_by(instance_id=instance_id).all()
        assert len(records) == 1


@pytest.mark.unit
def test_api_v1_instances_sync_capacity_connect_failure_returns_connection_error(app, auth_client, monkeypatch) -> None:
    _ensure_instances_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    class _DummyCapacitySyncCoordinator:
        def __init__(self, instance):  # noqa: ANN001
            self.instance = instance

        def connect(self) -> bool:
            return False

        def disconnect(self) -> None:  # noqa: PLR6301
            return None

    import app.services.database_sync as database_sync_module

    monkeypatch.setattr(database_sync_module, "CapacitySyncCoordinator", _DummyCapacitySyncCoordinator)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/actions/sync-capacity",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 409

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True
    assert payload.get("message_code") == "DATABASE_CONNECTION_ERROR"
