import pytest

from app import create_app, db
from app.models.credential import Credential
from datetime import UTC, datetime

from app.models.instance import Instance
from app.models.user import User
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.repositories.veeam_repository import VeeamRepository
from app.services.veeam.provider import VeeamMachineBackupRecord
from app.services.veeam.sync_actions_service import VeeamSyncPreparedRun


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
        assert data.get("default_api_version") == "1.3-rev1"
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
def test_api_v1_veeam_single_instance_sync_preserves_unrelated_snapshots(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["credentials"],
                db.metadata.tables["instances"],
                db.metadata.tables["veeam_source_bindings"],
                db.metadata.tables["veeam_machine_backup_snapshots"],
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
        veeam_credential = Credential(
            name="veeam-admin",
            credential_type="veeam",
            username="backup-admin",
            password="VeeamPass123",
            description="Veeam",
            is_active=True,
        )
        db.session.add_all([user, instance, veeam_credential])
        db.session.flush()
        db.session.add(
            VeeamSourceBinding(
                credential_id=veeam_credential.id,
                server_host="10.0.0.10",
                server_port=9419,
                api_version="1.3-rev1",
                verify_ssl=False,
                match_domains=["domain.com"],
            )
        )
        db.session.add_all(
            [
                VeeamMachineBackupSnapshot(
                    machine_name="db01.domain.com",
                    normalized_machine_name="db01.domain.com",
                    latest_backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
                    raw_payload={"id": "rp-old-db01"},
                    sync_run_id="old-run",
                ),
                VeeamMachineBackupSnapshot(
                    machine_name="db02.domain.com",
                    normalized_machine_name="db02.domain.com",
                    latest_backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
                    raw_payload={"id": "rp-old-db02"},
                    sync_run_id="old-run",
                ),
            ]
        )
        db.session.commit()

        class _FakeSession:
            base_url = "https://veeam.example.com:9419"
            access_token = "token"
            api_version = "1.3-rev1"
            verify_ssl = False

        class _FakeProvider:
            def is_configured(self) -> bool:
                return True

            def create_session(self, **kwargs):
                del kwargs
                return _FakeSession()

            def fetch_backup_objects(self, *, session) -> list[dict[str, object]]:
                del session
                return [{"id": "backup-db01", "name": "db01.domain.com"}]

            @staticmethod
            def _pick_string(item: dict[str, object], keys: tuple[str, ...]) -> str | None:
                for key in keys:
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                return None

            @staticmethod
            def _resolve_backup_machine_ip(item: dict[str, object]) -> str | None:
                del item
                return None

            @staticmethod
            def _build_backup_restore_points_url(*, base_url: str, backup_object_id: str | None) -> str:
                return f"{base_url}/api/v1/backupObjects/{backup_object_id}/restorePoints"

            @staticmethod
            def _collect_paginated_items(**kwargs) -> list[dict[str, object]]:
                del kwargs
                return [{"id": "rp-new-db01"}]

            @staticmethod
            def _normalize_backup_record(
                item: dict[str, object],
                *,
                backup_item: dict[str, object] | None = None,
                backup_machine_name: str | None = None,
            ) -> VeeamMachineBackupRecord:
                del item, backup_item
                return VeeamMachineBackupRecord(
                    machine_name=backup_machine_name or "db01.domain.com",
                    backup_at=datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                    source_record_id="rp-new-db01",
                    raw_payload={"id": "rp-new-db01"},
                )

        captured_upsert: dict[str, object] = {}
        original_upsert = VeeamRepository.upsert_machine_backup_snapshots

        def _capturing_upsert(records, *, sync_run_id: str, synced_at: datetime) -> int:
            records_list = list(records)
            captured_upsert["records"] = records_list
            captured_upsert["sync_run_id"] = sync_run_id
            return original_upsert(records_list, sync_run_id=sync_run_id, synced_at=synced_at)

        def _forbid_replace(*args, **kwargs) -> int:
            del args, kwargs
            raise AssertionError("单实例同步禁止调用全量快照替换")

        monkeypatch.setattr("app.api.v1.namespaces.veeam.HttpVeeamProvider", _FakeProvider)
        monkeypatch.setattr(VeeamRepository, "upsert_machine_backup_snapshots", _capturing_upsert)
        monkeypatch.setattr(VeeamRepository, "replace_machine_backup_snapshots", _forbid_replace)

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

        records = captured_upsert.get("records")
        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0].source_record_id == "rp-new-db01"
        assert captured_upsert["sync_run_id"] == f"single_sync_{instance.id}"
