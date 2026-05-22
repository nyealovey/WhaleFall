import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.user import User


@pytest.mark.unit
def test_api_v1_ad_domain_configs_create_and_list_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["ad_domain_configs"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        credential = Credential(
            name="ldap-admin",
            credential_type="ldap",
            username="CORP\\svc",
            password="TestPass1",
            is_active=True,
        )
        db.session.add_all([user, credential])
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        csrf_token = csrf_response.get_json()["data"]["csrf_token"]

        create_response = client.post(
            "/api/v1/ad-domain-configs",
            json={
                "name": "corp.example.com",
                "netbios_name": "CORP",
                "domain_controllers": ["dc01.corp.example.com"],
                "ldap_port": 636,
                "use_ssl": True,
                "verify_ssl": True,
                "base_dn": "DC=corp,DC=example,DC=com",
                "credential_id": credential.id,
                "is_enabled": True,
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert create_response.status_code == 200

        list_response = client.get("/api/v1/ad-domain-configs")
        assert list_response.status_code == 200
        payload = list_response.get_json()
        configs = payload.get("data", {}).get("configs")
        assert isinstance(configs, list)
        assert configs[0]["name"] == "corp.example.com"
        assert configs[0]["netbios_name"] == "CORP"
        assert configs[0]["domain_controllers"] == ["dc01.corp.example.com"]
        assert configs[0]["credential"]["name"] == "ldap-admin"
