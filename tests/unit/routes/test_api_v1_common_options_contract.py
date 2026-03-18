import pytest

from app import db
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.utils.time_utils import time_utils


@pytest.mark.unit
def test_api_v1_common_instances_options_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

    response = auth_client.get("/api/v1/instances/options")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False
    assert "message" in payload
    assert "timestamp" in payload

    data = payload.get("data")
    assert isinstance(data, dict)
    assert "instances" in data
    instances = data.get("instances")
    assert isinstance(instances, list)
    assert len(instances) == 1

    item = instances[0]
    assert isinstance(item, dict)
    assert {"id", "name", "db_type", "display_name"}.issubset(item.keys())

    filtered = auth_client.get("/api/v1/instances/options?db_type=MYSQL")
    assert filtered.status_code == 200


@pytest.mark.unit
def test_api_v1_common_instances_options_support_multiple_db_types(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )

        db.session.add_all(
            [
                Instance(name="mysql-1", db_type="mysql", host="127.0.0.1", port=3306, is_active=True),
                Instance(name="pg-1", db_type="postgresql", host="127.0.0.2", port=5432, is_active=True),
                Instance(name="sqlserver-1", db_type="sqlserver", host="127.0.0.3", port=1433, is_active=True),
            ],
        )
        db.session.commit()

    response = auth_client.get("/api/v1/instances/options?db_type=mysql&db_type=postgresql")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)

    instances = payload.get("data", {}).get("instances")
    assert isinstance(instances, list)
    names = {item.get("name") for item in instances if isinstance(item, dict)}
    assert names == {"mysql-1", "pg-1"}


@pytest.mark.unit
def test_api_v1_common_instances_options_include_disabled_and_exclude_deleted(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )

        db.session.add_all(
            [
                Instance(
                    name="instance-active",
                    db_type="mysql",
                    host="127.0.0.1",
                    port=3306,
                    is_active=True,
                ),
                Instance(
                    name="instance-disabled",
                    db_type="mysql",
                    host="127.0.0.2",
                    port=3307,
                    is_active=False,
                ),
                Instance(
                    name="instance-deleted",
                    db_type="mysql",
                    host="127.0.0.3",
                    port=3308,
                    is_active=True,
                    deleted_at=time_utils.now(),
                ),
            ],
        )
        db.session.commit()

    response = auth_client.get("/api/v1/instances/options")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    instances = payload.get("data", {}).get("instances")
    assert isinstance(instances, list)
    names = {item.get("name") for item in instances if isinstance(item, dict)}
    assert "instance-active" in names
    assert "instance-disabled" in names
    assert "instance-deleted" not in names


@pytest.mark.unit
def test_api_v1_common_databases_options_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_databases"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = int(instance.id)

        db1 = InstanceDatabase(instance_id=instance.id, database_name="db-a", is_active=True)
        db2 = InstanceDatabase(instance_id=instance.id, database_name="db-b", is_active=False)
        db.session.add_all([db1, db2])
        db.session.commit()

    response = auth_client.get(f"/api/v1/databases/options?instance_id={instance_id}&page=1&limit=100")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False
    assert "message" in payload
    assert "timestamp" in payload

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"databases", "total_count", "page", "pages", "limit"}.issubset(data.keys())

    databases = data.get("databases")
    assert isinstance(databases, list)
    assert len(databases) == 2

    item = databases[0]
    assert isinstance(item, dict)
    assert {
        "id",
        "database_name",
        "is_active",
        "first_seen_date",
        "last_seen_date",
        "deleted_at",
    }.issubset(item.keys())
