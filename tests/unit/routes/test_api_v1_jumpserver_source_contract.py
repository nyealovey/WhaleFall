import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.user import User


@pytest.mark.unit
def test_api_v1_jumpserver_source_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["jumpserver_source_bindings"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        api_credential = Credential(
            name="jumpserver-ak",
            credential_type="api",
            username="AccessKeyID",
            password="AccessKeySecret",
            description="JumpServer",
            is_active=True,
        )
        db.session.add(api_credential)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/integrations/jumpserver/source")
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, dict)
        data = payload.get("data")
        assert isinstance(data, dict)
        assert "binding" in data
        assert "api_credentials" in data
        assert data.get("provider_ready") is True
        assert data.get("default_verify_ssl") is True
        api_credentials = data.get("api_credentials")
        assert isinstance(api_credentials, list)
        assert api_credentials[0]["name"] == "jumpserver-ak"
        assert "base_url" not in api_credentials[0]


@pytest.mark.unit
def test_api_v1_jumpserver_source_bind_and_unbind_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["jumpserver_source_bindings"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        api_credential = Credential(
            name="jumpserver-ak",
            credential_type="api",
            username="AccessKeyID",
            password="AccessKeySecret",
            description="JumpServer",
            is_active=True,
        )
        db.session.add(api_credential)
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

        bind_response = client.put(
            "/api/v1/integrations/jumpserver/source",
            json={
                "credential_id": api_credential.id,
                "base_url": "https://demo.jumpserver.org",
                "verify_ssl": False,
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert bind_response.status_code == 200
        bind_payload = bind_response.get_json()
        assert isinstance(bind_payload, dict)
        binding = bind_payload.get("data", {}).get("binding")
        assert isinstance(binding, dict)
        assert binding.get("credential_id") == api_credential.id
        assert binding.get("base_url") == "https://demo.jumpserver.org"
        assert binding.get("verify_ssl") is False

        delete_response = client.delete(
            "/api/v1/integrations/jumpserver/source",
            headers={"X-CSRFToken": csrf_token},
        )
        assert delete_response.status_code == 200
        delete_payload = delete_response.get_json()
        assert isinstance(delete_payload, dict)
        delete_data = delete_payload.get("data")
        assert isinstance(delete_data, dict)
        assert delete_data.get("binding") is None
