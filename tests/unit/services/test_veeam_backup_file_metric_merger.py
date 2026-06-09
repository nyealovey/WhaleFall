from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.veeam.backup_file_metric_merger import VeeamBackupFileMetricMerger
from app.services.veeam.provider import VeeamBackupFileCollection, VeeamBackupFileRecord, VeeamMachineBackupRecord


@pytest.mark.unit
def test_veeam_backup_file_metric_merger_enriches_records_and_summarizes_coverage() -> None:
    record = VeeamMachineBackupRecord(
        machine_name="db01.domain.com",
        backup_at=datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
        backup_id="backup-1",
        backup_file_id="file-exact",
        source_record_id="rp-1",
        raw_payload={"id": "rp-1"},
    )
    backup_files = VeeamBackupFileCollection(
        records=[
            VeeamBackupFileRecord(
                backup_id="backup-1",
                backup_file_id="file-other",
                object_id="object-other",
                restore_point_ids=["rp-1"],
                data_size_bytes=999,
                backup_size_bytes=555,
                backup_at=datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                raw_payload={"id": "file-other"},
            ),
            VeeamBackupFileRecord(
                backup_id="backup-1",
                backup_file_id="file-exact",
                object_id="object-1",
                restore_point_ids=["rp-1"],
                data_size_bytes=425819216,
                backup_size_bytes=117592064,
                dedup_ratio=36,
                compress_ratio=27,
                backup_at=datetime(2026, 3, 25, 2, 5, tzinfo=UTC),
                raw_payload={"id": "file-exact", "gfsPeriods": ["Weekly"]},
            ),
        ],
        received_total=2,
        backup_ids_total=1,
        backup_ids_completed=1,
    )

    merger = VeeamBackupFileMetricMerger()
    coverage = merger.summarize_coverage(records=[record], backup_files_result=backup_files)
    merged = merger.merge_metrics_into_records(records=[record], backup_files_result=backup_files)

    assert coverage == {
        "restore_points_expected_total": 1,
        "restore_points_enriched_total": 1,
        "restore_points_missing_metrics_total": 0,
        "backup_ids_fully_covered_total": 1,
        "backup_ids_partially_covered_total": 0,
    }
    assert len(merged) == 1
    assert merged[0].restore_point_size_bytes == 425819216
    assert merged[0].raw_payload["objectId"] == "object-1"
    assert merged[0].raw_payload["backupSize"] == 117592064
    assert merged[0].raw_payload["dedupRatio"] == 36
    assert merged[0].raw_payload["compressRatio"] == 27
    assert merged[0].raw_payload["gfsPeriods"] == ["Weekly"]
    assert merged[0].raw_payload["backupFileId"] == "file-exact"


@pytest.mark.unit
def test_veeam_backup_file_metric_merger_reports_partial_coverage() -> None:
    records = [
        VeeamMachineBackupRecord(
            machine_name="db01.domain.com",
            backup_at=datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
            backup_id="backup-1",
            source_record_id="rp-1",
            raw_payload={"id": "rp-1"},
        ),
        VeeamMachineBackupRecord(
            machine_name="db01.domain.com",
            backup_at=datetime(2026, 3, 25, 1, 0, tzinfo=UTC),
            backup_id="backup-1",
            source_record_id="rp-2",
            raw_payload={"id": "rp-2"},
        ),
    ]
    backup_files = VeeamBackupFileCollection(
        records=[
            VeeamBackupFileRecord(
                backup_id="backup-1",
                backup_file_id="file-1",
                restore_point_ids=["rp-1"],
                data_size_bytes=1024,
                raw_payload={"id": "file-1"},
            )
        ],
        received_total=1,
        backup_ids_total=1,
        backup_ids_completed=1,
    )

    coverage = VeeamBackupFileMetricMerger().summarize_coverage(
        records=records,
        backup_files_result=backup_files,
    )

    assert coverage["restore_points_expected_total"] == 2
    assert coverage["restore_points_enriched_total"] == 1
    assert coverage["restore_points_missing_metrics_total"] == 1
    assert coverage["backup_ids_fully_covered_total"] == 0
    assert coverage["backup_ids_partially_covered_total"] == 1
