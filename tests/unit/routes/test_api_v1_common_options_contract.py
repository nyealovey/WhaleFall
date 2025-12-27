import pytest

from app import db
from app.models.database_type_config import DatabaseTypeConfig
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase


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

    response = auth_client.get("/api/v1/common/instances/options")
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

    filtered = auth_client.get("/api/v1/common/instances/options?db_type=MYSQL")
    assert filtered.status_code == 200


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

    response = auth_client.get(f"/api/v1/common/databases/options?instance_id={instance_id}&limit=100&offset=0")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False
    assert "message" in payload
    assert "timestamp" in payload

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"databases", "total_count", "limit", "offset"}.issubset(data.keys())

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


@pytest.mark.unit
def test_api_v1_common_database_types_options_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["database_type_configs"],
            ],
        )

        config = DatabaseTypeConfig(
            name="mysql",
            display_name="MySQL",
            driver="mysql+pymysql",
            default_port=3306,
            default_schema="mysql",
            icon="fa-database",
            color="primary",
            sort_order=1,
            is_active=True,
            is_system=True,
        )
        db.session.add(config)
        db.session.commit()

    response = auth_client.get("/api/v1/common/database-types/options")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False
    assert "message" in payload
    assert "timestamp" in payload

    data = payload.get("data")
    assert isinstance(data, dict)
    assert "options" in data

    options = data.get("options")
    assert isinstance(options, list)
    assert len(options) >= 1

    item = options[0]
    assert isinstance(item, dict)
    assert {"value", "text", "icon", "color"}.issubset(item.keys())

