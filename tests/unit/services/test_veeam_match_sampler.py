from __future__ import annotations

import pytest

from app.services.veeam.match_sampler import VeeamMatchSampler


@pytest.mark.unit
def test_veeam_match_sampler_matches_backup_objects_by_name_and_ip_with_samples() -> None:
    result = VeeamMatchSampler().match_backup_objects(
        backup_items=[
            {"id": "backup-name", "name": "DB01.DOMAIN.COM"},
            {"id": "backup-ip", "name": "10.0.0.8"},
            {"id": "backup-missing", "jobName": "daily-job-1"},
            {"id": "backup-unmatched", "name": "unmatched.domain.com"},
            {"name": "missing-id"},
        ],
        match_machine_names={"db01.domain.com"},
        match_machine_ips={"10.0.0.8"},
    )

    assert result.backups_received_total == 5
    assert result.backups_matched_total == 2
    assert result.backups_unmatched_total == 2
    assert result.backups_missing_machine_name == 1
    assert [item.backup_object_id for item in result.matched_backup_objects] == ["backup-name", "backup-ip"]
    assert result.matched_backup_ids_sample == ["backup-name", "backup-ip"]
    assert result.unmatched_backup_ids_sample == ["backup-missing", "backup-unmatched"]
    assert result.unmatched_machine_names_sample == ["unmatched.domain.com"]
    assert result.missing_machine_name_backup_ids_sample == ["backup-missing"]
    assert result.missing_machine_name_backup_names_sample == ["daily-job-1"]


@pytest.mark.unit
def test_veeam_match_sampler_caps_unmatched_samples_without_losing_counts() -> None:
    result = VeeamMatchSampler().match_backup_objects(
        backup_items=[{"id": f"backup-{index}", "name": f"db{index}.example.com"} for index in range(25)],
        match_machine_names={"db99.example.com"},
    )

    assert result.backups_received_total == 25
    assert result.backups_matched_total == 0
    assert result.backups_unmatched_total == 25
    assert result.unmatched_backup_ids_sample == [f"backup-{index}" for index in range(20)]
    assert len(result.unmatched_machine_names_sample) == 20
