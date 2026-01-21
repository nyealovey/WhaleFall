import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.user import User


@pytest.mark.unit
def test_api_v1_accounts_ledgers_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_classifications"],
                db.metadata.tables["classification_rules"],
                db.metadata.tables["account_classification_assignments"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
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
        db.session.flush()

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="demo",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        db.session.add(instance_account)
        db.session.flush()

        permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=instance_account.id,
            username="demo",
            permission_facts={
                "version": 2,
                "db_type": "mysql",
                "capabilities": [],
                "capability_reasons": {},
                "roles": [],
                "privileges": {},
                "errors": [],
                "meta": {},
            },
        )
        db.session.add(permission)

        assert AccountClassification.__tablename__ == "account_classifications"
        assert ClassificationRule.__tablename__ == "classification_rules"
        assert AccountClassificationAssignment.__tablename__ == "account_classification_assignments"
        classification_table = db.metadata.tables["account_classifications"]
        assert "code" in classification_table.columns
        assert "color" not in classification_table.columns

        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/accounts/ledgers")
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
        expected_keys = {
            "id",
            "username",
            "instance_name",
            "instance_host",
            "db_type",
            "is_locked",
            "is_superuser",
            "is_active",
            "is_deleted",
            "last_change_time",
            "tags",
            "classifications",
        }
        assert expected_keys.issubset(item.keys())
        assert isinstance(item.get("tags"), list)
        assert isinstance(item.get("classifications"), list)


@pytest.mark.unit
def test_api_v1_accounts_ledgers_mysql_roles_filtered_by_default() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_classifications"],
                db.metadata.tables["classification_rules"],
                db.metadata.tables["account_classification_assignments"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
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
        db.session.flush()

        user_instance_account = InstanceAccount(
            instance_id=instance.id,
            username="demo",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        role_instance_account = InstanceAccount(
            instance_id=instance.id,
            username="demo_role",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        db.session.add_all([user_instance_account, role_instance_account])
        db.session.flush()

        user_permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=user_instance_account.id,
            username="demo",
            type_specific={"version": 1, "account_kind": "user"},
            permission_facts={
                "version": 2,
                "db_type": "mysql",
                "capabilities": [],
                "capability_reasons": {},
                "roles": [],
                "privileges": {},
                "errors": [],
                "meta": {},
            },
        )
        role_permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=role_instance_account.id,
            username="demo_role",
            type_specific={"version": 1, "account_kind": "role"},
            permission_facts={
                "version": 2,
                "db_type": "mysql",
                "capabilities": [],
                "capability_reasons": {},
                "roles": [],
                "privileges": {},
                "errors": [],
                "meta": {},
            },
        )
        db.session.add_all([user_permission, role_permission])
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/accounts/ledgers")
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, dict)
        data = payload.get("data")
        assert isinstance(data, dict)

        items = data.get("items")
        assert isinstance(items, list)
        assert len(items) == 1
        assert items[0].get("username") == "demo"
        assert items[0].get("type_specific", {}).get("account_kind") == "user"

        response = client.get("/api/v1/accounts/ledgers?include_roles=true")
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, dict)
        data = payload.get("data")
        assert isinstance(data, dict)

        items = data.get("items")
        assert isinstance(items, list)
        assert {item.get("username") for item in items} == {"demo", "demo_role"}
        kind_by_username = {item.get("username"): item.get("type_specific", {}).get("account_kind") for item in items}
        assert kind_by_username == {"demo": "user", "demo_role": "role"}


@pytest.mark.unit
def test_api_v1_accounts_ledgers_permissions_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
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
        db.session.flush()

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="demo",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        db.session.add(instance_account)
        db.session.flush()

        permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=instance_account.id,
            username="demo",
            permission_facts={
                "version": 2,
                "db_type": "mysql",
                "capabilities": [],
                "capability_reasons": {},
                "roles": [],
                "privileges": {},
                "errors": [],
                "meta": {},
            },
            permission_snapshot={
                "version": 4,
                "categories": {
                    "global_privileges": ["SELECT"],
                    "database_privileges": {},
                },
                "type_specific": {},
                "extra": {},
                "errors": [],
                "meta": {},
            },
        )
        db.session.add(permission)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(f"/api/v1/accounts/ledgers/{permission.id}/permissions")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"permissions", "account"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_accounts_ledgers_requires_auth(client):
    response = client.get("/api/v1/accounts/ledgers")

    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"
