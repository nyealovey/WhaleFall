import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.user import User
from app.services.veeam.sync_actions_service import VeeamInstanceSyncResult, VeeamSyncPreparedRun
from app.settings import DEFAULT_VEEAM_API_VERSION


@pytest.mark.unit
def test_api_v1_veeam_source_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["veeam_source_bindings"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        veeam_credential = Credential(
            name="veeam-admin",
            credential_type="veeam",
            username="backup-admin",
            password="VeeamPass123",
            description="Veeam",
            is_active=True,
        )
        db.session.add(veeam_credential)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/integrations/veeam/source")
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, dict)
        data = payload.get("data")
        assert isinstance(data, dict)
        assert "binding" in data
        assert "veeam_credentials" in data
        assert data.get("provider_ready") is True
        assert data.get("default_port") == 9419
        assert data.get("default_api_version") == DEFAULT_VEEAM_API_VERSION
        assert data.get("default_verify_ssl") is True
        assert data.get("default_match_domains") == []
        veeam_credentials = data.get("veeam_credentials")
        assert isinstance(veeam_credentials, list)
        assert veeam_credentials[0]["name"] == "veeam-admin"


@pytest.mark.unit
def test_api_v1_veeam_source_bind_and_unbind_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["veeam_source_bindings"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        veeam_credential = Credential(
            name="veeam-admin",
            credential_type="veeam",
            username="backup-admin",
            password="VeeamPass123",
            description="Veeam",
            is_active=True,
        )
        db.session.add(veeam_credential)
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
            "/api/v1/integrations/veeam/source",
            json={
                "credential_id": veeam_credential.id,
                "server_host": "10.0.0.10",
                "server_port": 9419,
                "api_version": "1.3-rev1",
                "verify_ssl": False,
                "match_domains": ["domain.com", "corp.local"],
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert bind_response.status_code == 200
        bind_payload = bind_response.get_json()
        assert isinstance(bind_payload, dict)
        binding = bind_payload.get("data", {}).get("binding")
        assert isinstance(binding, dict)
        assert binding.get("credential_id") == veeam_credential.id
        assert binding.get("server_host") == "10.0.0.10"
        assert binding.get("server_port") == 9419
        assert binding.get("api_version") == "1.3-rev1"
        assert binding.get("verify_ssl") is False
        assert binding.get("match_domains") == ["domain.com", "corp.local"]

        delete_response = client.delete(
            "/api/v1/integrations/veeam/source",
            headers={"X-CSRFToken": csrf_token},
        )
        assert delete_response.status_code == 200
        delete_payload = delete_response.get_json()
        assert isinstance(delete_payload, dict)
        delete_data = delete_payload.get("data")
        assert isinstance(delete_data, dict)
        assert delete_data.get("binding") is None


@pytest.mark.unit
def test_api_v1_veeam_sources_crud_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["veeam_source_bindings"],
                db.metadata.tables["veeam_machine_backup_snapshots"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        credential_a = Credential(
            name="veeam-admin-a",
            credential_type="veeam",
            username="backup-admin-a",
            password="VeeamPass123",
            is_active=True,
        )
        credential_b = Credential(
            name="veeam-admin-b",
            credential_type="veeam",
            username="backup-admin-b",
            password="VeeamPass123",
            is_active=True,
        )
        db.session.add_all([user, credential_a, credential_b])
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_token = csrf_response.get_json().get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        create_a = client.post(
            "/api/v1/integrations/veeam/sources",
            json={
                "name": "Veeam A",
                "credential_id": credential_a.id,
                "server_host": "10.0.0.10",
                "server_port": 9419,
                "api_version": "1.3-rev1",
                "verify_ssl": False,
                "match_domains": ["domain.com"],
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert create_a.status_code == 200
        source_a = create_a.get_json().get("data", {}).get("source")
        assert source_a["name"] == "Veeam A"
        assert source_a["credential_id"] == credential_a.id

        create_b = client.post(
            "/api/v1/integrations/veeam/sources",
            json={
                "name": "Veeam B",
                "credential_id": credential_b.id,
                "server_host": "10.0.0.11",
                "server_port": 9419,
                "api_version": "1.3-rev1",
                "verify_ssl": True,
                "match_domains": ["corp.local"],
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert create_b.status_code == 200
        source_b = create_b.get_json().get("data", {}).get("source")

        list_response = client.get("/api/v1/integrations/veeam/sources")
        assert list_response.status_code == 200
        sources = list_response.get_json().get("data", {}).get("sources")
        assert [source["name"] for source in sources] == ["Veeam A", "Veeam B"]

        update_response = client.put(
            f"/api/v1/integrations/veeam/sources/{source_b['id']}",
            json={
                "name": "Veeam B Updated",
                "credential_id": credential_b.id,
                "server_host": "10.0.0.12",
                "server_port": 9419,
                "api_version": "1.3-rev2",
                "verify_ssl": False,
                "match_domains": ["corp.local", "db.local"],
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert update_response.status_code == 200
        updated = update_response.get_json().get("data", {}).get("source")
        assert updated["name"] == "Veeam B Updated"
        assert updated["server_host"] == "10.0.0.12"
        assert updated["match_domains"] == ["corp.local", "db.local"]

        disable_response = client.post(
            f"/api/v1/integrations/veeam/sources/{source_a['id']}/actions/disable",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert disable_response.status_code == 200
        assert disable_response.get_json().get("data", {}).get("source", {}).get("is_enabled") is False

        delete_response = client.delete(
            f"/api/v1/integrations/veeam/sources/{source_b['id']}",
            headers={"X-CSRFToken": csrf_token},
        )
        assert delete_response.status_code == 200

        list_after_delete = client.get("/api/v1/integrations/veeam/sources")
        sources_after_delete = list_after_delete.get_json().get("data", {}).get("sources")
        assert [source["id"] for source in sources_after_delete] == [source_a["id"]]


@pytest.mark.unit
def test_api_v1_veeam_sync_action_contract(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        captured: dict[str, object] = {}

        def _fake_prepare(
            _self,
            *,
            created_by: int | None,
            trigger_source: str = "manual",
            result_url: str = "/admin/system-settings#system-settings-veeam",
        ):
            captured["created_by"] = created_by
            captured["trigger_source"] = trigger_source
            captured["result_url"] = result_url
            return VeeamSyncPreparedRun(run_id="run-veeam-sync-1", credential_id=1)

        def _fake_launch(_self, *, created_by: int | None, prepared: VeeamSyncPreparedRun):
            captured["launch_created_by"] = created_by
            captured["launch_run_id"] = prepared.run_id

        monkeypatch.setattr(
            "app.api.v1.namespaces.veeam.VeeamSyncActionsService.prepare_background_sync", _fake_prepare
        )
        monkeypatch.setattr("app.api.v1.namespaces.veeam.VeeamSyncActionsService.launch_background_sync", _fake_launch)

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_token = csrf_response.get_json().get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.post(
            "/api/v1/integrations/veeam/actions/sync",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("data", {}).get("run_id") == "run-veeam-sync-1"
        assert captured["trigger_source"] == "manual"
        assert captured["result_url"] == "/admin/system-settings#system-settings-veeam"


@pytest.mark.unit
def test_api_v1_veeam_single_instance_sync_delegates_to_actions_service(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        instance = Instance(
            name="db01",
            db_type="mysql",
            host="10.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add_all([user, instance])
        db.session.commit()

        captured: dict[str, object] = {}

        def _fake_sync(self, *, instance_id: int, created_by: int | None) -> VeeamInstanceSyncResult:
            del self
            captured["instance_id"] = instance_id
            captured["created_by"] = created_by
            return VeeamInstanceSyncResult(
                data={
                    "instance_id": instance_id,
                    "instance_name": "db01",
                    "backup_info": {"machine_name": "db01.domain.com"},
                    "matched": True,
                },
                message="实例 db01 备份同步成功",
            )

        monkeypatch.setattr("app.api.v1.namespaces.veeam.VeeamSyncActionsService.sync_instance_now", _fake_sync)

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_token = csrf_response.get_json().get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.post(
            f"/api/v1/integrations/veeam/actions/sync-instance/{instance.id}",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200

        assert captured == {"instance_id": instance.id, "created_by": user.id}
        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("message") == "实例 db01 备份同步成功"
        assert payload.get("data", {}).get("matched") is True
        assert payload.get("data", {}).get("backup_info") == {"machine_name": "db01.domain.com"}


@pytest.mark.unit
def test_api_v1_veeam_source_instance_sync_passes_source_id(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        instance = Instance(
            name="db01",
            db_type="mysql",
            host="10.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add_all([user, instance])
        db.session.commit()

        captured: dict[str, object] = {}

        def _fake_sync(
            self,
            *,
            instance_id: int,
            created_by: int | None,
            source_binding_id: int | None = None,
        ) -> VeeamInstanceSyncResult:
            del self
            captured["instance_id"] = instance_id
            captured["created_by"] = created_by
            captured["source_binding_id"] = source_binding_id
            return VeeamInstanceSyncResult(
                data={
                    "instance_id": instance_id,
                    "instance_name": "db01",
                    "backup_info": {"source_binding_id": source_binding_id},
                    "matched": True,
                },
                message="实例 db01 备份同步成功",
            )

        monkeypatch.setattr("app.api.v1.namespaces.veeam.VeeamSyncActionsService.sync_instance_now", _fake_sync)

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_token = csrf_response.get_json().get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.post(
            f"/api/v1/integrations/veeam/sources/42/instances/{instance.id}/actions/sync",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )

        assert response.status_code == 200
        assert captured == {"instance_id": instance.id, "created_by": user.id, "source_binding_id": 42}
