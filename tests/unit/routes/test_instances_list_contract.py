import pytest

from app import create_app, db
from app.constants import DatabaseType
from app.models.instance import Instance
from app.models.user import User


@pytest.mark.unit
def test_instances_list_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["instance_tags"],
                db.metadata.tables["instance_databases"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["sync_instance_records"],
                db.metadata.tables["tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

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

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/instances/api/instances")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False
        assert "message" in payload
        assert "timestamp" in payload

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())

        items = data.get("items")
        assert isinstance(items, list)
        assert len(items) == 1

        item = items[0]
        assert isinstance(item, dict)
        expected_item_keys = {
            "id",
            "name",
            "db_type",
            "host",
            "port",
            "description",
            "is_active",
            "deleted_at",
            "status",
            "main_version",
            "active_db_count",
            "active_account_count",
            "last_sync_time",
            "tags",
        }
        assert expected_item_keys.issubset(item.keys())
        assert isinstance(item.get("tags"), list)
