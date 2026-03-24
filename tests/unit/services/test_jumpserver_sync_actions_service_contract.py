from __future__ import annotations

import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.jumpserver_asset_snapshot import JumpServerAssetSnapshot
from app.models.jumpserver_source_binding import JumpServerSourceBinding
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.services.jumpserver.provider import JumpServerAssetCollection, JumpServerDatabaseAsset
from app.services.jumpserver.sync_actions_service import JumpServerSyncActionsService
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService


@pytest.mark.unit
def test_prepare_background_sync_uses_system_settings_anchor(monkeypatch) -> None:
    captured: dict[str, object] = {}
    captured_items: list[tuple[str, str, str]] = []

    class _StubProvider:
        def is_configured(self) -> bool:
            return True

    class _StubCredential:
        id = 11

    class _StubBinding:
        credential_id = 11
        credential = _StubCredential()

    class _StubSourceService:
        def get_binding_or_error(self) -> _StubBinding:
            return _StubBinding()

    def _fake_start_run(
        _self: TaskRunsWriteService,
        *,
        task_key: str,
        task_name: str,
        task_category: str,
        trigger_source: str,
        created_by: int | None = None,
        summary_json: dict[str, object] | None = None,
        result_url: str | None = None,
    ) -> str:
        _ = (task_name, task_category, trigger_source, created_by, summary_json)
        captured["result_url"] = result_url
        captured["task_key"] = task_key
        return "run-jumpserver-1"

    def _fake_init_items(_self: TaskRunsWriteService, run_id: str, *, items) -> None:
        assert run_id == "run-jumpserver-1"
        captured_items.extend((item.item_type, item.item_key, item.item_name) for item in items)

    monkeypatch.setattr(TaskRunsWriteService, "start_run", _fake_start_run, raising=True)
    monkeypatch.setattr(TaskRunsWriteService, "init_items", _fake_init_items, raising=True)

    service = JumpServerSyncActionsService(
        source_service=_StubSourceService(),
        provider=_StubProvider(),
    )

    prepared = service.prepare_background_sync(created_by=1)

    assert prepared.run_id == "run-jumpserver-1"
    assert captured["task_key"] == "sync_jumpserver_assets"
    assert captured["result_url"] == "/admin/system-settings#system-settings-jumpserver"
    assert captured_items == [("step", "sync_assets", "同步 JumpServer 资产")]


@pytest.mark.unit
def test_sync_once_writes_snapshots_updates_binding_and_finalizes_task_run() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["credentials"],
                db.metadata.tables["jumpserver_source_bindings"],
                db.metadata.tables["jumpserver_asset_snapshots"],
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
            ],
        )

        credential = Credential(
            name="jumpserver-ak",
            credential_type="api",
            username="AccessKeyID",
            password="AccessKeySecret",
            description="JumpServer",
            is_active=True,
        )
        db.session.add(credential)
        db.session.flush()

        binding = JumpServerSourceBinding(
            credential_id=credential.id,
            base_url="https://demo.jumpserver.org",
        )
        db.session.add(binding)
        db.session.commit()

        class _StubProvider:
            def is_configured(self) -> bool:
                return True

            def list_database_assets(self, *, base_url: str, access_key_id: str, access_key_secret: str):
                _ = (base_url, access_key_id, access_key_secret)
                return JumpServerAssetCollection(
                    assets=[
                        JumpServerDatabaseAsset(
                            external_id="asset-1",
                            name="mysql-prod-1",
                            db_type="mysql",
                            host="10.0.0.10",
                            port=3306,
                            raw_payload={"id": "asset-1"},
                        )
                    ],
                    received_total=2,
                    supported_total=1,
                    skipped_unsupported=1,
                    skipped_invalid=0,
                )

        service = JumpServerSyncActionsService(provider=_StubProvider())

        prepared = service.prepare_background_sync(created_by=1)
        db.session.commit()

        service._sync_once(created_by=1, run_id=prepared.run_id, credential_id=credential.id)
        db.session.commit()

        snapshot = JumpServerAssetSnapshot.query.filter_by(external_id="asset-1").first()
        assert snapshot is not None
        assert snapshot.host == "10.0.0.10"

        binding = JumpServerSourceBinding.query.first()
        assert binding is not None
        assert binding.last_sync_status == "completed"
        assert binding.last_sync_run_id == prepared.run_id
        assert binding.last_error is None

        run = TaskRun.query.filter_by(run_id=prepared.run_id).first()
        assert run is not None
        assert run.status == "completed"
        assert run.progress_total == 1
        assert run.progress_completed == 1
        assert run.progress_failed == 0
        assert run.summary_json["ext"]["type"] == "sync_jumpserver_assets"
        assert run.summary_json["ext"]["data"]["assets"]["received_total"] == 2
        assert run.summary_json["ext"]["data"]["assets"]["snapshots_written_total"] == 1

        item = TaskRunItem.query.filter_by(run_id=prepared.run_id, item_type="step", item_key="sync_assets").first()
        assert item is not None
        assert item.status == "completed"
        assert item.metrics_json["snapshots_written_total"] == 1


@pytest.mark.unit
def test_sync_once_failure_marks_binding_and_task_run_failed_and_preserves_existing_snapshots() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["credentials"],
                db.metadata.tables["jumpserver_source_bindings"],
                db.metadata.tables["jumpserver_asset_snapshots"],
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
            ],
        )

        credential = Credential(
            name="jumpserver-ak",
            credential_type="api",
            username="AccessKeyID",
            password="AccessKeySecret",
            description="JumpServer",
            is_active=True,
        )
        db.session.add(credential)
        db.session.flush()

        db.session.add(
            JumpServerAssetSnapshot(
                external_id="existing-asset",
                name="mysql-old",
                db_type="mysql",
                host="10.0.0.9",
                port=3306,
                raw_payload={"id": "existing-asset"},
            )
        )
        binding = JumpServerSourceBinding(
            credential_id=credential.id,
            base_url="https://demo.jumpserver.org",
        )
        db.session.add(binding)
        db.session.commit()

        class _StubProvider:
            def is_configured(self) -> bool:
                return True

            def list_database_assets(self, *, base_url: str, access_key_id: str, access_key_secret: str):
                _ = (base_url, access_key_id, access_key_secret)
                raise RuntimeError("provider boom")

        service = JumpServerSyncActionsService(provider=_StubProvider())

        prepared = service.prepare_background_sync(created_by=1)
        db.session.commit()

        with pytest.raises(RuntimeError, match="provider boom"):
            service._sync_once(created_by=1, run_id=prepared.run_id, credential_id=credential.id)
        db.session.commit()

        assert JumpServerAssetSnapshot.query.filter_by(external_id="existing-asset").count() == 1

        binding = JumpServerSourceBinding.query.first()
        assert binding is not None
        assert binding.last_sync_status == "failed"
        assert binding.last_sync_run_id == prepared.run_id
        assert binding.last_error == "provider boom"

        run = TaskRun.query.filter_by(run_id=prepared.run_id).first()
        assert run is not None
        assert run.status == "failed"
        assert run.progress_total == 1
        assert run.progress_completed == 0
        assert run.progress_failed == 1
        assert run.error_message == "provider boom"
        assert run.summary_json["ext"]["data"]["error_message"] == "provider boom"

        item = TaskRunItem.query.filter_by(run_id=prepared.run_id, item_type="step", item_key="sync_assets").first()
        assert item is not None
        assert item.status == "failed"
        assert item.error_message == "provider boom"
