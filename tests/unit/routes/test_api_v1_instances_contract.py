from datetime import date, datetime

import pytest

from app import create_app, db
from app.constants import DatabaseType
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.database_size_stat import DatabaseSizeStat
from app.models.database_table_size_stat import DatabaseTableSizeStat
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.user import User


@pytest.mark.unit
def test_api_v1_instances_list_contract() -> None:
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

        response = client.get("/api/v1/instances")
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


@pytest.mark.unit
def test_api_v1_instances_detail_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
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
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(f"/api/v1/instances/{instance.id}")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)

        instance_data = data.get("instance")
        assert isinstance(instance_data, dict)
        assert instance_data.get("id") == instance.id
        assert instance_data.get("name") == instance.name


@pytest.mark.unit
def test_api_v1_instances_requires_auth(client):
    response = client.get("/api/v1/instances")

    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_instances_create_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.post(
            "/api/v1/instances",
            json={
                "name": "instance-new",
                "db_type": DatabaseType.MYSQL,
                "host": "127.0.0.1",
                "port": 3306,
                "description": "demo",
                "is_active": True,
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 201

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        instance_data = data.get("instance")
        assert isinstance(instance_data, dict)
        assert instance_data.get("name") == "instance-new"


@pytest.mark.unit
def test_api_v1_instances_update_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
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
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.put(
            f"/api/v1/instances/{instance.id}",
            json={
                "name": "instance-renamed",
                "db_type": DatabaseType.MYSQL,
                "host": "127.0.0.1",
                "port": 3306,
                "description": "updated",
                "is_active": True,
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        instance_data = data.get("instance")
        assert isinstance(instance_data, dict)
        assert instance_data.get("id") == instance.id
        assert instance_data.get("name") == "instance-renamed"


@pytest.mark.unit
def test_api_v1_instances_soft_delete_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
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
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.post(
            f"/api/v1/instances/{instance.id}/delete",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("instance_id") == instance.id
        assert data.get("deletion_mode") == "soft"


@pytest.mark.unit
def test_api_v1_instances_restore_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
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
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        delete_response = client.post(
            f"/api/v1/instances/{instance.id}/delete",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert delete_response.status_code == 200

        restore_response = client.post(
            f"/api/v1/instances/{instance.id}/restore",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert restore_response.status_code == 200

        payload = restore_response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        instance_data = data.get("instance")
        assert isinstance(instance_data, dict)
        assert instance_data.get("id") == instance.id


@pytest.mark.unit
def test_api_v1_instances_accounts_list_contract() -> None:
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

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="root",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        db.session.add(instance_account)
        db.session.commit()

        account_permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=instance_account.id,
            username="root",
            type_specific={"host": "%", "plugin": ""},
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
                "type_specific": {"mysql": {"host": "%", "plugin": ""}},
                "extra": {},
                "errors": [],
                "meta": {},
            },
        )
        db.session.add(account_permission)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(f"/api/v1/instances/{instance.id}/accounts")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"items", "total", "page", "pages", "limit", "summary"}.issubset(data.keys())

        items = data.get("items")
        assert isinstance(items, list)
        assert len(items) == 1


@pytest.mark.unit
def test_api_v1_instances_account_permissions_contract() -> None:
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

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="root",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        db.session.add(instance_account)
        db.session.commit()

        account_permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=instance_account.id,
            username="root",
            type_specific={"host": "%", "plugin": ""},
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
                "type_specific": {"mysql": {"host": "%", "plugin": ""}},
                "extra": {},
                "errors": [],
                "meta": {},
            },
        )
        db.session.add(account_permission)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(
            f"/api/v1/instances/{instance.id}/accounts/{account_permission.id}/permissions",
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"permissions", "account"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_instances_account_change_history_contract() -> None:
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
                db.metadata.tables["account_change_log"],
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

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="root",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        db.session.add(instance_account)
        db.session.commit()

        account_permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=instance_account.id,
            username="root",
            type_specific={"host": "%", "plugin": ""},
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
        db.session.add(account_permission)
        db.session.commit()

        change_log = AccountChangeLog(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            username="root",
            change_type="add",
            status="success",
            message="created",
            privilege_diff=None,
            other_diff=None,
            session_id="session-1",
        )
        db.session.add(change_log)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(
            f"/api/v1/instances/{instance.id}/accounts/{account_permission.id}/change-history",
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"account", "history"}.issubset(data.keys())
        history = data.get("history")
        assert isinstance(history, list)
        assert len(history) == 1


@pytest.mark.unit
def test_api_v1_instances_database_sizes_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["database_size_stats"],
                db.metadata.tables["instance_databases"],
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

        stat = DatabaseSizeStat(
            id=1,
            instance_id=instance.id,
            database_name="db1",
            size_mb=123,
            collected_date=date.today(),
        )
        db.session.add(stat)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(f"/api/v1/instances/{instance.id}/databases/sizes")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"total", "limit", "offset", "databases"}.issubset(data.keys())

        databases = data.get("databases")
        assert isinstance(databases, list)
        assert len(databases) == 1

        entry = databases[0]
        assert isinstance(entry, dict)
        assert {"database_name", "size_mb", "collected_date"}.issubset(entry.keys())


@pytest.mark.unit
def test_api_v1_instances_database_table_sizes_snapshot_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["database_table_size_stats"],
            ],
        )

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

        collected_at = datetime(2026, 1, 2, 0, 0, 0)
        db.session.add_all(
            [
                DatabaseTableSizeStat(
                    instance_id=instance.id,
                    database_name="db1",
                    schema_name="public",
                    table_name="users",
                    size_mb=12,
                    data_size_mb=9,
                    index_size_mb=3,
                    row_count=1000,
                    collected_at=collected_at,
                ),
                DatabaseTableSizeStat(
                    instance_id=instance.id,
                    database_name="db1",
                    schema_name="public",
                    table_name="orders",
                    size_mb=5,
                    data_size_mb=5,
                    index_size_mb=0,
                    row_count=10,
                    collected_at=collected_at,
                ),
            ],
        )
        db.session.commit()

    response = auth_client.get(f"/api/v1/instances/{instance_id}/databases/db1/tables/sizes?limit=200")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"total", "limit", "offset", "collected_at", "tables"}.issubset(data.keys())
    assert data.get("total") == 2

    tables = data.get("tables")
    assert isinstance(tables, list)
    assert len(tables) == 2
    assert {"schema_name", "table_name", "size_mb"}.issubset(tables[0].keys())


@pytest.mark.unit
def test_api_v1_instances_database_table_sizes_refresh_contract(app, auth_client, monkeypatch) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["database_table_size_stats"],
            ],
        )

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

    class _DummyTableSizeCoordinator:
        def __init__(self, instance):  # noqa: ANN001
            self.instance = instance

        def connect(self, database_name: str) -> bool:
            del database_name
            return True

        def refresh_snapshot(self, database_name: str):  # noqa: ANN001
            del database_name
            db.session.add(
                DatabaseTableSizeStat(
                    instance_id=self.instance.id,
                    database_name="db1",
                    schema_name="public",
                    table_name="users",
                    size_mb=12,
                    data_size_mb=9,
                    index_size_mb=3,
                    row_count=1000,
                    collected_at=datetime(2026, 1, 2, 0, 0, 0),
                ),
            )

            return type(
                "Outcome",
                (),
                {"saved_count": 1, "deleted_count": 0, "elapsed_ms": 1},
            )()

        def disconnect(self) -> None:  # noqa: PLR6301
            return None

    import app.services.database_sync as database_sync_module

    monkeypatch.setattr(database_sync_module, "TableSizeCoordinator", _DummyTableSizeCoordinator)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/databases/db1/tables/sizes/actions/refresh",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"tables", "saved_count", "deleted_count", "elapsed_ms"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_instances_database_table_sizes_refresh_conflict_returns_reason(app, auth_client, monkeypatch) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["database_table_size_stats"],
            ],
        )

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

    class _FailingTableSizeCoordinator:
        def __init__(self, instance):  # noqa: ANN001
            self.instance = instance

        def connect(self, database_name: str) -> bool:
            del database_name
            return True

        def refresh_snapshot(self, database_name: str):  # noqa: ANN001
            del database_name
            raise ValueError("Oracle 当前账号缺少读取表段信息的权限")

        def disconnect(self) -> None:  # noqa: PLR6301
            return None

    import app.services.database_sync as database_sync_module

    monkeypatch.setattr(database_sync_module, "TableSizeCoordinator", _FailingTableSizeCoordinator)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/databases/db1/tables/sizes/actions/refresh",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 409

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("message") == "Oracle 当前账号缺少读取表段信息的权限"
