from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.models.instance import Instance
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService
from app.services.veeam.sync_actions_service import VeeamSyncActionsService
from app.services.veeam.provider import VeeamMachineBackupCollection, VeeamMachineBackupRecord


@pytest.mark.unit
def test_prepare_background_sync_uses_system_settings_anchor(monkeypatch) -> None:
    captured: dict[str, object] = {}
    captured_items: list[tuple[str, str, str]] = []

    class _StubProvider:
        def is_configured(self) -> bool:
            return True

    class _StubCredential:
        id = 21

    class _StubBinding:
        credential_id = 21
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
        return "run-veeam-1"

    def _fake_init_items(_self: TaskRunsWriteService, run_id: str, *, items) -> None:
        assert run_id == "run-veeam-1"
        captured_items.extend((item.item_type, item.item_key, item.item_name) for item in items)

    monkeypatch.setattr(TaskRunsWriteService, "start_run", _fake_start_run, raising=True)
    monkeypatch.setattr(TaskRunsWriteService, "init_items", _fake_init_items, raising=True)

    service = VeeamSyncActionsService(
        source_service=_StubSourceService(),
        provider=_StubProvider(),
    )

    prepared = service.prepare_background_sync(created_by=1)

    assert prepared.run_id == "run-veeam-1"
    assert captured["task_key"] == "sync_veeam_backups"
    assert captured["result_url"] == "/admin/system-settings#system-settings-veeam"
    assert captured_items == [("step", "sync_backups", "同步 Veeam 备份")]


@pytest.mark.unit
def test_sync_once_writes_latest_machine_snapshots_updates_binding_and_finalizes_task_run() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["credentials"],
                db.metadata.tables["instances"],
                db.metadata.tables["veeam_source_bindings"],
                db.metadata.tables["veeam_machine_backup_snapshots"],
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
            ],
        )

        credential = Credential(
            name="veeam-admin",
            credential_type="veeam",
            username="backup-admin",
            password="VeeamPass123",
            description="Veeam",
            is_active=True,
        )
        instance = Instance(
            name="db01",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add_all([credential, instance])
        db.session.flush()

        binding = VeeamSourceBinding(
            credential_id=credential.id,
            server_host="10.0.0.10",
            server_port=9419,
            api_version="1.3-rev1",
            verify_ssl=False,
            match_domains=["domain.com"],
        )
        db.session.add(binding)
        db.session.commit()

        captured: dict[str, object] = {}

        class _StubProvider:
            def is_configured(self) -> bool:
                return True

            def list_machine_backups(
                self,
                *,
                server_host: str,
                server_port: int,
                username: str,
                password: str,
                api_version: str,
                verify_ssl: bool | None = None,
            ) -> VeeamMachineBackupCollection:
                captured["server_host"] = server_host
                captured["server_port"] = server_port
                captured["username"] = username
                captured["password"] = password
                captured["api_version"] = api_version
                captured["verify_ssl"] = verify_ssl
                return VeeamMachineBackupCollection(
                    records=[
                        VeeamMachineBackupRecord(
                            machine_name="db01.domain.com",
                            backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
                            backup_id="backup-1",
                            backup_file_id="file-1",
                            restore_point_name="rp-1",
                            source_record_id="rp-1",
                            raw_payload={"id": "rp-1"},
                        ),
                        VeeamMachineBackupRecord(
                            machine_name="db01.domain.com",
                            backup_at=datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                            backup_id="backup-1",
                            backup_file_id="file-2",
                            restore_point_name="rp-2",
                            source_record_id="rp-2",
                            raw_payload={"id": "rp-2"},
                        ),
                        VeeamMachineBackupRecord(
                            machine_name="db02",
                            backup_at=datetime(2026, 3, 24, 20, 0, tzinfo=UTC),
                            backup_id="backup-2",
                            backup_file_id="file-3",
                            restore_point_name="rp-3",
                            source_record_id="rp-3",
                            raw_payload={"id": "rp-3"},
                        ),
                    ],
                    received_total=3,
                    snapshots_written_total=2,
                    skipped_invalid=0,
                )

            def enrich_machine_backups(
                self,
                *,
                server_host: str,
                server_port: int,
                username: str,
                password: str,
                api_version: str,
                records: list[VeeamMachineBackupRecord],
                verify_ssl: bool | None = None,
            ) -> list[VeeamMachineBackupRecord]:
                captured["enriched_machine_names"] = [record.machine_name for record in records]
                captured["enriched_record_ids"] = [record.source_record_id for record in records]
                _ = (server_host, server_port, username, password, api_version, verify_ssl)
                return [
                    VeeamMachineBackupRecord(
                        machine_name=record.machine_name,
                        backup_at=record.backup_at,
                        backup_id=record.backup_id,
                        backup_file_id=record.backup_file_id,
                        job_name="daily-job",
                        restore_point_name=record.restore_point_name,
                        source_record_id=record.source_record_id,
                        restore_point_size_bytes=1024,
                        backup_chain_size_bytes=4096,
                        restore_point_count=3,
                        raw_payload=record.raw_payload,
                    )
                    for record in records
                ]

        service = VeeamSyncActionsService(provider=_StubProvider())

        prepared = service.prepare_background_sync(created_by=1)
        db.session.commit()

        service._sync_once(created_by=1, run_id=prepared.run_id, credential_id=credential.id)
        db.session.commit()

        assert captured["server_host"] == "10.0.0.10"
        assert captured["server_port"] == 9419
        assert captured["username"] == "backup-admin"
        assert captured["password"] == "VeeamPass123"
        assert captured["api_version"] == "1.3-rev1"
        assert captured["verify_ssl"] is False
        assert captured["enriched_machine_names"] == ["db01.domain.com"]
        assert captured["enriched_record_ids"] == ["rp-2"]

        snapshots = VeeamMachineBackupSnapshot.query.order_by(VeeamMachineBackupSnapshot.machine_name.asc()).all()
        assert len(snapshots) == 2
        assert snapshots[0].job_name == "daily-job"
        assert snapshots[0].restore_point_size_bytes == 1024
        assert snapshots[0].backup_chain_size_bytes == 4096
        assert snapshots[0].restore_point_count == 3
        assert snapshots[0].machine_name == "db01.domain.com"
        assert snapshots[0].restore_point_name == "rp-2"
        assert snapshots[1].machine_name == "db02"
        assert snapshots[1].job_name is None

        binding = VeeamSourceBinding.query.first()
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
        assert run.summary_json["ext"]["type"] == "sync_veeam_backups"
        assert run.summary_json["ext"]["data"]["backups"]["received_total"] == 3
        assert run.summary_json["ext"]["data"]["backups"]["snapshots_written_total"] == 2

        item = TaskRunItem.query.filter_by(run_id=prepared.run_id, item_type="step", item_key="sync_backups").first()
        assert item is not None
        assert item.status == "completed"
        assert item.metrics_json["snapshots_written_total"] == 2
