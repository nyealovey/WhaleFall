from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import create_app, db
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.repositories.veeam_repository import VeeamRepository
from app.services.veeam.provider import VeeamMachineBackupRecord


def _create_snapshot_tables() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[db.metadata.tables["veeam_machine_backup_snapshots"]],
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
    raw_payload_id: str,
    sync_run_id: str,
) -> VeeamMachineBackupSnapshot:
    row = VeeamMachineBackupSnapshot()
    row.machine_name = machine_name
    row.normalized_machine_name = machine_name
    row.latest_backup_at = backup_at
    row.raw_payload = {"id": raw_payload_id}
    row.sync_run_id = sync_run_id
    return row


@pytest.mark.unit
def test_upsert_machine_backup_snapshots_preserves_unrelated_snapshots() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_snapshot_tables()
        db.session.add_all(
            [
                _snapshot(
                    machine_name="db01.domain.com",
                    backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
                    raw_payload_id="rp-old-db01",
                    sync_run_id="old-run",
                ),
                _snapshot(
                    machine_name="db02.domain.com",
                    backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
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
        _create_snapshot_tables()

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
