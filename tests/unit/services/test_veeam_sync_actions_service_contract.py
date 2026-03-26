from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

import app.services.veeam.sync_actions_service as sync_actions_service_module
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
    assert captured_items == [
        ("step", "fetch_backup_objects", "获取 backupObjects"),
        ("step", "match_backup_objects", "匹配目标备份对象"),
        ("step", "fetch_restore_points", "拉取 restorePoints"),
        ("step", "write_snapshots", "写入快照"),
    ]


@pytest.mark.unit
def test_launch_background_sync_runs_sync_task_with_prepared_run_id(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_task(*, manual_run: bool, created_by: int | None, run_id: str) -> None:
        captured["manual_run"] = manual_run
        captured["created_by"] = created_by
        captured["run_id"] = run_id

    class _DummyThread:
        name = "sync_veeam_backups_manual"

    def _fake_launch_background_sync(*, created_by: int | None, run_id: str, task):
        task(manual_run=True, created_by=created_by, run_id=run_id)
        return _DummyThread()

    monkeypatch.setattr(sync_actions_service_module, "_launch_background_sync", _fake_launch_background_sync)

    service = VeeamSyncActionsService(task=_fake_task)
    result = service.launch_background_sync(
        created_by=1,
        prepared=sync_actions_service_module.VeeamSyncPreparedRun(run_id="run-veeam-1", credential_id=21),
    )

    assert result.run_id == "run-veeam-1"
    assert result.thread_name == "sync_veeam_backups_manual"
    assert captured == {
        "manual_run": True,
        "created_by": 1,
        "run_id": "run-veeam-1",
    }


@pytest.mark.unit
def test_sync_once_writes_latest_machine_snapshots_updates_binding_and_finalizes_task_run() -> None:  # noqa: PLR0915
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

            def create_session(
                self,
                *,
                server_host: str,
                server_port: int,
                username: str,
                password: str,
                api_version: str,
                verify_ssl: bool | None = None,
            ) -> object:
                captured["server_host"] = server_host
                captured["server_port"] = server_port
                captured["username"] = username
                captured["password"] = password
                captured["api_version"] = api_version
                captured["verify_ssl"] = verify_ssl
                return object()

            def fetch_backup_objects(self, *, session: object) -> list[dict[str, object]]:
                captured["session_used_for_fetch"] = session is not None
                return [
                    {"id": "backup-1", "name": "db01.domain.com"},
                    {"id": "backup-2", "name": "unmatched.domain.com"},
                ]

            def match_backup_objects(
                self,
                *,
                backup_items: list[dict[str, object]],
                match_machine_names: set[str] | None = None,
            ) -> object:
                captured["match_machine_names"] = set(match_machine_names or set())
                captured["backup_items_total"] = len(backup_items)

                class _MatchResult:
                    matched_backup_objects = [
                        type(
                            "MatchedBackupObject",
                            (),
                            {
                                "backup_object_id": "backup-1",
                                "machine_name": "db01.domain.com",
                                "backup_item": {"id": "backup-1", "name": "db01.domain.com"},
                            },
                        )()
                    ]
                    backups_received_total = 2
                    backups_matched_total = 1
                    backups_unmatched_total = 1
                    backups_missing_machine_name = 0
                    matched_backup_ids_sample = ["backup-1"]
                    unmatched_backup_ids_sample = ["backup-2"]
                    unmatched_machine_names_sample = ["unmatched.domain.com"]
                    missing_machine_name_backup_ids_sample: list[str] = []
                    missing_machine_name_backup_names_sample: list[str] = []

                return _MatchResult()

            def fetch_restore_point_records(self, *, session: object, match_result: object) -> object:
                captured["restore_session_used"] = session is not None
                captured["matched_backup_objects_total"] = len(getattr(match_result, "matched_backup_objects", []))

                class _RestorePointsResult:
                    records = [
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
                            machine_name="db01.domain.com",
                            backup_at=datetime(2026, 3, 25, 1, 30, tzinfo=UTC),
                            backup_id="backup-1",
                            backup_file_id="file-1b",
                            restore_point_name="rp-1b",
                            source_record_id="rp-1b",
                            raw_payload={"id": "rp-1b"},
                        ),
                    ]
                    received_total = 3
                    snapshots_written_total = 3
                    skipped_invalid = 0
                    restore_points_backup_objects_total = 1
                    restore_points_backup_objects_completed = 1

                return _RestorePointsResult()

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
        assert captured["match_machine_names"] == {"db01", "db01.domain.com"}
        assert captured["verify_ssl"] is False

        snapshots = VeeamMachineBackupSnapshot.query.order_by(VeeamMachineBackupSnapshot.machine_name.asc()).all()
        assert len(snapshots) == 1
        assert snapshots[0].job_name is None
        assert snapshots[0].restore_point_size_bytes is None
        assert snapshots[0].backup_chain_size_bytes is None
        assert snapshots[0].restore_point_count == 3
        assert snapshots[0].machine_name == "db01.domain.com"
        assert snapshots[0].restore_point_name == "rp-2"
        assert snapshots[0].raw_payload["restore_point_ids"] == ["rp-2", "rp-1b", "rp-1"]
        assert snapshots[0].raw_payload["restore_point_times"] == [
            "2026-03-25T02:00:00+00:00",
            "2026-03-25T01:30:00+00:00",
            "2026-03-25T01:00:00+00:00",
        ]

        binding = VeeamSourceBinding.query.first()
        assert binding is not None
        assert binding.last_sync_status == "completed"
        assert binding.last_sync_run_id == prepared.run_id
        assert binding.last_error is None

        run = TaskRun.query.filter_by(run_id=prepared.run_id).first()
        assert run is not None
        assert run.status == "completed"
        assert run.progress_total == 4
        assert run.progress_completed == 4
        assert run.progress_failed == 0
        assert run.summary_json["ext"]["type"] == "sync_veeam_backups"
        assert run.summary_json["ext"]["data"]["backups"]["received_total"] == 3
        assert run.summary_json["ext"]["data"]["backups"]["snapshots_written_total"] == 1

        items = {
            item.item_key: item
            for item in TaskRunItem.query.filter_by(run_id=prepared.run_id, item_type="step").all()
        }
        assert set(items) == {"fetch_backup_objects", "match_backup_objects", "fetch_restore_points", "write_snapshots"}
        assert items["fetch_backup_objects"].status == "completed"
        assert items["fetch_backup_objects"].metrics_json["backup_objects_received_total"] == 2
        assert "共拉取 2 个 backupObjects" in items["fetch_backup_objects"].details_json["summary"]
        assert items["match_backup_objects"].status == "completed"
        assert items["match_backup_objects"].metrics_json["matched_backup_objects_total"] == 1
        assert items["fetch_restore_points"].status == "completed"
        assert items["fetch_restore_points"].metrics_json["restore_points_backup_objects_completed"] == 1
        assert items["write_snapshots"].status == "completed"
        assert items["write_snapshots"].metrics_json["snapshots_written_total"] == 1


@pytest.mark.unit
def test_sync_once_logs_candidate_pool_and_unmatched_backup_summary(monkeypatch) -> None:
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

        calls: list[tuple[str, str, dict[str, object]]] = []

        def _fake_log_with_context(level: str, message: str, **kwargs: object) -> None:
            calls.append((level, message, dict(kwargs)))

        monkeypatch.setattr(sync_actions_service_module, "log_with_context", _fake_log_with_context)

        class _StubProvider:
            def is_configured(self) -> bool:
                return True

            def create_session(
                self,
                *,
                server_host: str,
                server_port: int,
                username: str,
                password: str,
                api_version: str,
                verify_ssl: bool | None = None,
            ) -> object:
                _ = (server_host, server_port, username, password, api_version, verify_ssl)
                return object()

            def fetch_backup_objects(self, *, session: object) -> list[dict[str, object]]:
                _ = session
                return [
                    {"id": "backup-1", "name": "db01.domain.com"},
                    {"id": "backup-2", "name": "unmatched.domain.com"},
                ]

            def match_backup_objects(
                self,
                *,
                backup_items: list[dict[str, object]],
                match_machine_names: set[str] | None = None,
            ) -> object:
                _ = (backup_items, match_machine_names)

                class _MatchResult:
                    matched_backup_objects: list[object] = []
                    backups_received_total = 2
                    backups_matched_total = 0
                    backups_unmatched_total = 1
                    backups_missing_machine_name = 1
                    matched_backup_ids_sample: list[str] = []
                    unmatched_backup_ids_sample = ["backup-2"]
                    unmatched_machine_names_sample = ["unmatched.domain.com"]
                    missing_machine_name_backup_ids_sample = ["backup-1"]
                    missing_machine_name_backup_names_sample = ["daily-job-1"]

                return _MatchResult()

            def fetch_restore_point_records(self, *, session: object, match_result: object) -> object:
                _ = (session, match_result)

                class _RestorePointsResult:
                    records: list[VeeamMachineBackupRecord] = []
                    received_total = 0
                    snapshots_written_total = 0
                    skipped_invalid = 0
                    restore_points_backup_objects_total = 0
                    restore_points_backup_objects_completed = 0

                return _RestorePointsResult()

        service = VeeamSyncActionsService(provider=_StubProvider())
        prepared = service.prepare_background_sync(created_by=1)
        db.session.commit()

        service._sync_once(created_by=1, run_id=prepared.run_id, credential_id=credential.id)

        assert calls
        assert any(message == "Veeam 候选机器池已构建" for _, message, _ in calls)
        assert any(message == "Veeam 备份链匹配完成" for _, message, _ in calls)
        assert any(message == "Veeam 未命中任何备份链" for _, message, _ in calls)
        match_call = next(kwargs for _, message, kwargs in calls if message == "Veeam 备份链匹配完成")
        context = cast(dict[str, object], match_call["context"])
        extra = cast(dict[str, object], match_call["extra"])
        assert context["run_id"] == prepared.run_id
        assert extra["backups_received_total"] == 2
        assert extra["backups_matched_total"] == 0
        assert extra["backups_unmatched_total"] == 1
        assert extra["backups_missing_machine_name"] == 1
        assert extra["unmatched_backup_ids_sample"] == ["backup-2"]
        assert extra["unmatched_machine_names_sample"] == ["unmatched.domain.com"]
        assert extra["missing_machine_name_backup_ids_sample"] == ["backup-1"]
        assert extra["missing_machine_name_backup_names_sample"] == ["daily-job-1"]


@pytest.mark.unit
def test_sync_once_accepts_snapshot_without_enrichment_fields() -> None:
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

        class _StubProvider:
            def is_configured(self) -> bool:
                return True

            def create_session(
                self,
                *,
                server_host: str,
                server_port: int,
                username: str,
                password: str,
                api_version: str,
                verify_ssl: bool | None = None,
            ) -> object:
                _ = (server_host, server_port, username, password, api_version, verify_ssl)
                return object()

            def fetch_backup_objects(self, *, session: object) -> list[dict[str, object]]:
                _ = session
                return [{"id": "backup-1", "name": "db01.domain.com"}]

            def match_backup_objects(
                self,
                *,
                backup_items: list[dict[str, object]],
                match_machine_names: set[str] | None = None,
            ) -> object:
                _ = (backup_items, match_machine_names)

                class _MatchResult:
                    matched_backup_objects = [
                        type(
                            "MatchedBackupObject",
                            (),
                            {
                                "backup_object_id": "backup-1",
                                "machine_name": "db01.domain.com",
                                "backup_item": {"id": "backup-1", "name": "db01.domain.com"},
                            },
                        )()
                    ]
                    backups_received_total = 1
                    backups_matched_total = 1
                    backups_unmatched_total = 0
                    backups_missing_machine_name = 0
                    matched_backup_ids_sample = ["backup-1"]
                    unmatched_backup_ids_sample: list[str] = []
                    unmatched_machine_names_sample: list[str] = []
                    missing_machine_name_backup_ids_sample: list[str] = []
                    missing_machine_name_backup_names_sample: list[str] = []

                return _MatchResult()

            def fetch_restore_point_records(self, *, session: object, match_result: object) -> object:
                _ = (session, match_result)

                class _RestorePointsResult:
                    records = [
                        VeeamMachineBackupRecord(
                            machine_name="db01.domain.com",
                            backup_at=datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                            backup_id="backup-1",
                            backup_file_id="file-1",
                            restore_point_name="rp-1",
                            source_record_id="rp-1",
                            raw_payload={"id": "rp-1"},
                        )
                    ]
                    received_total = 1
                    snapshots_written_total = 1
                    skipped_invalid = 0
                    restore_points_backup_objects_total = 1
                    restore_points_backup_objects_completed = 1

                return _RestorePointsResult()

        service = VeeamSyncActionsService(provider=_StubProvider())
        prepared = service.prepare_background_sync(created_by=1)
        db.session.commit()

        service._sync_once(created_by=1, run_id=prepared.run_id, credential_id=credential.id)

        snapshots = VeeamMachineBackupSnapshot.query.all()
        assert len(snapshots) == 1
        assert snapshots[0].job_name is None
        assert snapshots[0].restore_point_size_bytes is None
        assert snapshots[0].backup_chain_size_bytes is None
        assert snapshots[0].restore_point_count == 1
        assert snapshots[0].raw_payload["restore_point_times"] == ["2026-03-25T02:00:00+00:00"]


@pytest.mark.unit
def test_sync_once_marks_restore_points_stage_failed_with_progress_details() -> None:
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

        class _RestorePointsError(RuntimeError):
            def __init__(self) -> None:
                super().__init__("Veeam API 请求超时: timeout=60s url=https://10.0.0.10:9419/api/v1/backupObjects/backup-2/restorePoints")
                self.matched_backup_objects_total = 2
                self.completed_backup_objects_total = 1
                self.failed_backup_object_id = "backup-2"
                self.failed_machine_name = "db02.domain.com"
                self.failed_url = "https://10.0.0.10:9419/api/v1/backupObjects/backup-2/restorePoints"

        class _StubProvider:
            def is_configured(self) -> bool:
                return True

            def create_session(
                self,
                *,
                server_host: str,
                server_port: int,
                username: str,
                password: str,
                api_version: str,
                verify_ssl: bool | None = None,
            ) -> object:
                _ = (server_host, server_port, username, password, api_version, verify_ssl)
                return object()

            def fetch_backup_objects(self, *, session: object) -> list[dict[str, object]]:
                _ = session
                return [
                    {"id": "backup-1", "name": "db01.domain.com"},
                    {"id": "backup-2", "name": "db02.domain.com"},
                ]

            def match_backup_objects(
                self,
                *,
                backup_items: list[dict[str, object]],
                match_machine_names: set[str] | None = None,
            ) -> object:
                _ = (backup_items, match_machine_names)

                class _MatchResult:
                    matched_backup_objects = [
                        type(
                            "MatchedBackupObject",
                            (),
                            {
                                "backup_object_id": "backup-1",
                                "machine_name": "db01.domain.com",
                                "backup_item": {"id": "backup-1", "name": "db01.domain.com"},
                            },
                        )(),
                        type(
                            "MatchedBackupObject",
                            (),
                            {
                                "backup_object_id": "backup-2",
                                "machine_name": "db02.domain.com",
                                "backup_item": {"id": "backup-2", "name": "db02.domain.com"},
                            },
                        )(),
                    ]
                    backups_received_total = 2
                    backups_matched_total = 2
                    backups_unmatched_total = 0
                    backups_missing_machine_name = 0
                    matched_backup_ids_sample = ["backup-1", "backup-2"]
                    unmatched_backup_ids_sample: list[str] = []
                    unmatched_machine_names_sample: list[str] = []
                    missing_machine_name_backup_ids_sample: list[str] = []
                    missing_machine_name_backup_names_sample: list[str] = []

                return _MatchResult()

            def fetch_restore_point_records(self, *, session: object, match_result: object) -> object:
                _ = (session, match_result)
                raise _RestorePointsError()

        service = VeeamSyncActionsService(provider=_StubProvider())
        prepared = service.prepare_background_sync(created_by=1)
        db.session.commit()

        with pytest.raises(RuntimeError, match="timeout=60s"):
            service._sync_once(created_by=1, run_id=prepared.run_id, credential_id=credential.id)

        run = TaskRun.query.filter_by(run_id=prepared.run_id).first()
        assert run is not None
        assert run.status == "failed"
        assert run.progress_total == 4
        assert run.progress_completed == 2
        assert run.progress_failed == 1

        items = {
            item.item_key: item
            for item in TaskRunItem.query.filter_by(run_id=prepared.run_id, item_type="step").all()
        }
        assert items["fetch_backup_objects"].status == "completed"
        assert items["match_backup_objects"].status == "completed"
        assert items["fetch_restore_points"].status == "failed"
        assert items["fetch_restore_points"].started_at is not None
        assert items["fetch_restore_points"].details_json["restore_points_backup_objects_completed"] == 1
        assert items["fetch_restore_points"].details_json["matched_backup_objects_total"] == 2
        assert items["fetch_restore_points"].details_json["failed_backup_object_id"] == "backup-2"
        assert items["fetch_restore_points"].details_json["failed_url"].endswith("/backup-2/restorePoints")
        assert items["write_snapshots"].status == "pending"
