from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import create_app, db
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.repositories.veeam_repository import VeeamRepository
from app.services.veeam.provider import VeeamMachineBackupRecord


def _create_veeam_tables() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["veeam_source_bindings"],
            db.metadata.tables["veeam_machine_backup_snapshots"],
        ],
    )


def _record(
    machine_name: str,
    backup_at: datetime,
    *,
    machine_ip: str | None = None,
    source_record_id: str = "rp-new",
) -> VeeamMachineBackupRecord:
    return VeeamMachineBackupRecord(
        machine_name=machine_name,
        machine_ip=machine_ip,
        backup_at=backup_at,
        source_record_id=source_record_id,
        raw_payload={"id": source_record_id},
    )


def _snapshot(
    machine_name: str,
    backup_at: datetime,
    *,
    source_binding_id: int = 1,
    raw_payload_id: str,
    sync_run_id: str,
) -> VeeamMachineBackupSnapshot:
    row = VeeamMachineBackupSnapshot()
    row.source_binding_id = source_binding_id
    row.machine_name = machine_name
    row.normalized_machine_name = machine_name
    row.latest_backup_at = backup_at
    row.raw_payload = {"id": raw_payload_id}
    row.sync_run_id = sync_run_id
    return row


def _binding(name: str, *, credential_id: int) -> VeeamSourceBinding:
    return VeeamSourceBinding(
        name=name,
        credential_id=credential_id,
        server_host=f"10.0.0.{credential_id}",
        server_port=9419,
        api_version="1.3-rev1",
        verify_ssl=False,
        match_domains=["domain.com"],
    )


@pytest.mark.unit
def test_upsert_machine_backup_snapshots_preserves_unrelated_snapshots() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_veeam_tables()
        binding = _binding("Veeam A", credential_id=1)
        db.session.add(binding)
        db.session.flush()
        db.session.add_all(
            [
                _snapshot(
                    machine_name="db01.domain.com",
                    backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
                    source_binding_id=binding.id,
                    raw_payload_id="rp-old-db01",
                    sync_run_id="old-run",
                ),
                _snapshot(
                    machine_name="db02.domain.com",
                    backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
                    source_binding_id=binding.id,
                    raw_payload_id="rp-old-db02",
                    sync_run_id="old-run",
                ),
            ]
        )
        db.session.commit()

        written = VeeamRepository.upsert_machine_backup_snapshots(
            [
                _record(
                    "db01.domain.com",
                    datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                    source_record_id="rp-new-db01",
                )
            ],
            source_binding_id=binding.id,
            sync_run_id="single-run",
            synced_at=datetime(2026, 3, 25, 2, 5, tzinfo=UTC),
        )
        db.session.commit()

        snapshots = {
            row.normalized_machine_name: row
            for row in VeeamMachineBackupSnapshot.query.order_by(VeeamMachineBackupSnapshot.machine_name.asc()).all()
        }
        assert written == 1
        assert set(snapshots) == {"db01.domain.com", "db02.domain.com"}
        assert snapshots["db01.domain.com"].source_record_id == "rp-new-db01"
        assert snapshots["db01.domain.com"].sync_run_id == "single-run"
        assert snapshots["db02.domain.com"].source_record_id is None
        assert snapshots["db02.domain.com"].sync_run_id == "old-run"


@pytest.mark.unit
def test_replace_machine_backup_snapshots_deduplicates_name_and_ip_and_stores_missing_ip_as_null() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_veeam_tables()
        binding = _binding("Veeam A", credential_id=1)
        db.session.add(binding)
        db.session.flush()

        written = VeeamRepository.replace_machine_backup_snapshots(
            [
                _record(
                    "db01.domain.com",
                    datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                    machine_ip="10.0.0.1",
                    source_record_id="rp-db01",
                ),
                _record(
                    "db02.domain.com",
                    datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                    source_record_id="rp-db02",
                ),
            ],
            source_binding_id=binding.id,
            sync_run_id="full-run",
            synced_at=datetime(2026, 3, 25, 2, 5, tzinfo=UTC),
        )
        db.session.commit()

        snapshots = {
            row.normalized_machine_name: row
            for row in VeeamMachineBackupSnapshot.query.order_by(VeeamMachineBackupSnapshot.machine_name.asc()).all()
        }
        assert written == 2
        assert set(snapshots) == {"db01.domain.com", "db02.domain.com"}
        assert snapshots["db01.domain.com"].machine_ip == "10.0.0.1"
        assert snapshots["db01.domain.com"].normalized_machine_ip == "10.0.0.1"
        assert snapshots["db02.domain.com"].machine_ip is None
        assert snapshots["db02.domain.com"].normalized_machine_ip is None


@pytest.mark.unit
def test_replace_machine_backup_snapshots_is_scoped_to_source_binding() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_veeam_tables()
        source_a = _binding("Veeam A", credential_id=1)
        source_b = _binding("Veeam B", credential_id=2)
        db.session.add_all([source_a, source_b])
        db.session.flush()
        db.session.add_all(
            [
                _snapshot(
                    machine_name="db01.domain.com",
                    backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
                    source_binding_id=source_a.id,
                    raw_payload_id="rp-a-old",
                    sync_run_id="old-a",
                ),
                _snapshot(
                    machine_name="db01.domain.com",
                    backup_at=datetime(2026, 3, 25, 1, 30, tzinfo=UTC),
                    source_binding_id=source_b.id,
                    raw_payload_id="rp-b-old",
                    sync_run_id="old-b",
                ),
            ]
        )
        db.session.commit()

        written = VeeamRepository.replace_machine_backup_snapshots(
            [
                _record(
                    "db02.domain.com",
                    datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                    source_record_id="rp-a-new",
                )
            ],
            source_binding_id=source_a.id,
            sync_run_id="run-a",
            synced_at=datetime(2026, 3, 25, 2, 5, tzinfo=UTC),
        )
        db.session.commit()

        rows = VeeamMachineBackupSnapshot.query.order_by(
            VeeamMachineBackupSnapshot.source_binding_id.asc(),
            VeeamMachineBackupSnapshot.machine_name.asc(),
        ).all()

        assert written == 1
        assert [(row.source_binding_id, row.machine_name, row.sync_run_id) for row in rows] == [
            (source_a.id, "db02.domain.com", "run-a"),
            (source_b.id, "db01.domain.com", "old-b"),
        ]


@pytest.mark.unit
def test_upsert_machine_backup_snapshots_allows_same_machine_name_across_sources() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_veeam_tables()
        source_a = _binding("Veeam A", credential_id=1)
        source_b = _binding("Veeam B", credential_id=2)
        db.session.add_all([source_a, source_b])
        db.session.flush()

        for source, run_id, source_record_id in (
            (source_a, "run-a", "rp-a"),
            (source_b, "run-b", "rp-b"),
        ):
            VeeamRepository.upsert_machine_backup_snapshots(
                [
                    _record(
                        "db01.domain.com",
                        datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                        source_record_id=source_record_id,
                    )
                ],
                source_binding_id=source.id,
                sync_run_id=run_id,
                synced_at=datetime(2026, 3, 25, 2, 5, tzinfo=UTC),
            )
        db.session.commit()

        rows = VeeamMachineBackupSnapshot.query.order_by(VeeamMachineBackupSnapshot.source_binding_id.asc()).all()

        assert [(row.source_binding_id, row.normalized_machine_name, row.source_record_id) for row in rows] == [
            (source_a.id, "db01.domain.com", "rp-a"),
            (source_b.id, "db01.domain.com", "rp-b"),
        ]
