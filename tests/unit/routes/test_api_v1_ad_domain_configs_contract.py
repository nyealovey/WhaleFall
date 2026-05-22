import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.task_run_item import TaskRunItem
from app.models.user import User
from app.utils.time_utils import time_utils


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
        assert configs[0]["last_sync_metrics"] is None


@pytest.mark.unit
def test_api_v1_ad_domain_configs_list_includes_last_sync_metrics() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["ad_domain_configs"],
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
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
        db.session.flush()
        config = db.metadata.tables["ad_domain_configs"]
        db.session.execute(
            config.insert().values(
                name="corp.example.com",
                netbios_name="CORP",
                domain_controllers=["dc01.corp.example.com"],
                ldap_port=636,
                use_ssl=True,
                verify_ssl=True,
                base_dn="DC=corp,DC=example,DC=com",
                credential_id=credential.id,
                is_enabled=True,
                last_sync_status="success",
                last_sync_run_id="run-ad-1",
            )
        )
        db.session.flush()
        task_run = db.metadata.tables["task_runs"]
        db.session.execute(
            task_run.insert().values(
                run_id="run-ad-1",
                task_key="sync_ad_accounts",
                task_name="AD 域账户同步",
                task_category="ad_sync",
                trigger_source="manual",
                status="completed",
                started_at=time_utils.now(),
            )
        )
        created_config_id = db.session.execute(
            db.select(config.c.id).where(config.c.name == "corp.example.com")
        ).scalar_one()
        db.session.add(
            TaskRunItem(
                run_id="run-ad-1",
                item_type="ad_domain",
                item_key=str(created_config_id),
                item_name="corp.example.com",
                status="completed",
                metrics_json={"total": 10, "normal": 7, "disabled": 1, "orphaned": 2, "updated": 3},
            )
        )
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/ad-domain-configs")

        assert response.status_code == 200
        configs = response.get_json()["data"]["configs"]
        assert configs[0]["last_sync_metrics"] == {
            "total": 10,
            "normal": 7,
            "disabled": 1,
            "orphaned": 2,
            "updated": 3,
        }
