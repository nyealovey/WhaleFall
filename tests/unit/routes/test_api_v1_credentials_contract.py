import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.user import User


@pytest.mark.unit
def test_api_v1_credentials_list_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["instances"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        credential = Credential(
            name="cred-1",
            credential_type="database",
            db_type="mysql",
            username="root",
            password="TestPass1",
            description="示例凭据",
            is_active=True,
        )
        db.session.add(credential)
        db.session.commit()

        instance = Instance(
            name="instance-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            credential_id=credential.id,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/credentials")
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
            "credential_type",
            "db_type",
            "username",
            "category_id",
            "created_at",
            "updated_at",
            "password",
            "description",
            "is_active",
            "instance_count",
            "created_at_display",
        }
        assert expected_item_keys.issubset(item.keys())


@pytest.mark.unit
def test_api_v1_credential_detail_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["instances"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        credential = Credential(
            name="cred-1",
            credential_type="database",
            db_type="mysql",
            username="root",
            password="TestPass1",
            description="示例凭据",
            is_active=True,
        )
        db.session.add(credential)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(f"/api/v1/credentials/{credential.id}")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        credential_data = data.get("credential")
        assert isinstance(credential_data, dict)
        assert credential_data.get("id") == credential.id
        assert credential_data.get("name") == credential.name


@pytest.mark.unit
def test_api_v1_credentials_requires_auth(client):
    response = client.get("/api/v1/credentials")

    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_credentials_create_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["instances"],
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
            "/api/v1/credentials",
            json={
                "name": "cred-new",
                "credential_type": "database",
                "db_type": "mysql",
                "username": "root",
                "password": "TestPass1",
                "description": "示例凭据",
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
        credential_data = data.get("credential")
        assert isinstance(credential_data, dict)
        assert credential_data.get("name") == "cred-new"


@pytest.mark.unit
def test_api_v1_credentials_update_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        credential = Credential(
            name="cred-1",
            credential_type="database",
            db_type="mysql",
            username="root",
            password="TestPass1",
            description="示例凭据",
            is_active=True,
        )
        db.session.add(credential)
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
            f"/api/v1/credentials/{credential.id}",
            json={
                "name": "cred-renamed",
                "credential_type": "database",
                "db_type": "mysql",
                "username": "root",
                "description": "更新后的描述",
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
        credential_data = data.get("credential")
        assert isinstance(credential_data, dict)
        assert credential_data.get("id") == credential.id
        assert credential_data.get("name") == "cred-renamed"


@pytest.mark.unit
def test_api_v1_credentials_delete_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["instances"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        credential = Credential(
            name="cred-1",
            credential_type="database",
            db_type="mysql",
            username="root",
            password="TestPass1",
            description="示例凭据",
            is_active=True,
        )
        db.session.add(credential)
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

        response = client.delete(
            f"/api/v1/credentials/{credential.id}",
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
        assert data.get("credential_id") == credential.id
