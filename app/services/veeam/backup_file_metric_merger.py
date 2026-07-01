"""Veeam backupFiles 指标合并."""

from __future__ import annotations

from dataclasses import replace

from app.services.veeam.types import VeeamBackupFileCollection, VeeamBackupFileRecord, VeeamMachineBackupRecord


class VeeamBackupFileMetricMerger:
    """把 backupFiles 指标补齐到 restorePoint 记录."""

    def summarize_coverage(
        self,
        *,
        records: list[VeeamMachineBackupRecord],
        backup_files_result: VeeamBackupFileCollection,
    ) -> dict[str, int]:
        expected_restore_point_ids_by_backup: dict[str, set[str]] = {}
        for record in records:
            backup_id = str(record.backup_id or "").strip()
            restore_point_id = str(record.source_record_id or "").strip()
            if not backup_id or not restore_point_id:
                continue
            expected_restore_point_ids_by_backup.setdefault(backup_id, set()).add(restore_point_id)

        matched_restore_point_ids_by_backup: dict[str, set[str]] = {
            backup_id: set() for backup_id in expected_restore_point_ids_by_backup
        }
        for backup_file in backup_files_result.records:
            backup_id = str(backup_file.backup_id or "").strip()
            if backup_id not in expected_restore_point_ids_by_backup:
                continue
            expected_restore_point_ids = expected_restore_point_ids_by_backup[backup_id]
            matched_restore_point_ids = matched_restore_point_ids_by_backup.setdefault(backup_id, set())
            for restore_point_id in backup_file.restore_point_ids:
                normalized_restore_point_id = str(restore_point_id or "").strip()
                if normalized_restore_point_id and normalized_restore_point_id in expected_restore_point_ids:
                    matched_restore_point_ids.add(normalized_restore_point_id)

        restore_points_expected_total = sum(
            len(restore_point_ids) for restore_point_ids in expected_restore_point_ids_by_backup.values()
        )
        restore_points_enriched_total = sum(
            len(restore_point_ids) for restore_point_ids in matched_restore_point_ids_by_backup.values()
        )
        backup_ids_fully_covered_total = 0
        backup_ids_partially_covered_total = 0
        for backup_id, expected_restore_point_ids in expected_restore_point_ids_by_backup.items():
            matched_count = len(matched_restore_point_ids_by_backup.get(backup_id, set()))
            expected_count = len(expected_restore_point_ids)
            if expected_count <= 0 or matched_count <= 0:
                continue
            if matched_count >= expected_count:
                backup_ids_fully_covered_total += 1
                continue
            backup_ids_partially_covered_total += 1

        return {
            "restore_points_expected_total": restore_points_expected_total,
            "restore_points_enriched_total": restore_points_enriched_total,
            "restore_points_missing_metrics_total": max(
                restore_points_expected_total - restore_points_enriched_total, 0
            ),
            "backup_ids_fully_covered_total": backup_ids_fully_covered_total,
            "backup_ids_partially_covered_total": backup_ids_partially_covered_total,
        }

    def merge_metrics_into_records(
        self,
        *,
        records: list[VeeamMachineBackupRecord],
        backup_files_result: VeeamBackupFileCollection,
    ) -> list[VeeamMachineBackupRecord]:
        if not records or not backup_files_result.records:
            return records

        backup_files_by_restore_point_id: dict[str, list[VeeamBackupFileRecord]] = {}
        for backup_file in backup_files_result.records:
            for restore_point_id in backup_file.restore_point_ids:
                normalized_restore_point_id = str(restore_point_id or "").strip()
                if not normalized_restore_point_id:
                    continue
                backup_files_by_restore_point_id.setdefault(normalized_restore_point_id, []).append(backup_file)

        merged_records: list[VeeamMachineBackupRecord] = []
        for record in records:
            restore_point_id = str(record.source_record_id or "").strip()
            candidates = backup_files_by_restore_point_id.get(restore_point_id, [])
            selected = self.select_best_backup_file_record(record=record, candidates=candidates)
            if selected is None:
                merged_records.append(record)
                continue
            merged_records.append(_merge_backup_file_metrics(record=record, selected=selected))
        return merged_records

    @staticmethod
    def select_best_backup_file_record(
        *,
        record: VeeamMachineBackupRecord,
        candidates: list[VeeamBackupFileRecord],
    ) -> VeeamBackupFileRecord | None:
        if not candidates:
            return None

        filtered_candidates = candidates
        if record.backup_file_id:
            exact_matches = [candidate for candidate in candidates if candidate.backup_file_id == record.backup_file_id]
            if exact_matches:
                filtered_candidates = exact_matches

        record_backup_at = record.backup_at
        if record_backup_at is not None:
            candidates_with_time = [candidate for candidate in filtered_candidates if candidate.backup_at is not None]
            if candidates_with_time:
                return min(
                    candidates_with_time,
                    key=lambda candidate: (
                        abs((candidate.backup_at - record_backup_at).total_seconds())
                        if candidate.backup_at is not None
                        else float("inf"),
                        0 if candidate.backup_file_id == record.backup_file_id else 1,
                        candidate.backup_file_id or "",
                    ),
                )

        return sorted(
            filtered_candidates,
            key=lambda candidate: (
                0 if candidate.backup_file_id == record.backup_file_id else 1,
                candidate.backup_file_id or "",
            ),
        )[0]


def extract_backup_metric_int(payload: object, keys: tuple[str, ...]) -> int | None:
    """从 payload 中按候选键提取整数指标."""
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _merge_backup_file_metrics(
    *,
    record: VeeamMachineBackupRecord,
    selected: VeeamBackupFileRecord,
) -> VeeamMachineBackupRecord:
    merged_payload = dict(record.raw_payload) if isinstance(record.raw_payload, dict) else {}
    if selected.object_id and not merged_payload.get("objectId"):
        merged_payload["objectId"] = selected.object_id
    if selected.restore_point_ids:
        merged_payload["restorePointIds"] = list(selected.restore_point_ids)
    if selected.data_size_bytes is not None:
        merged_payload["dataSize"] = selected.data_size_bytes
    if selected.backup_size_bytes is not None:
        merged_payload["backupSize"] = selected.backup_size_bytes
    if selected.dedup_ratio is not None:
        merged_payload["dedupRatio"] = selected.dedup_ratio
    if selected.compress_ratio is not None:
        merged_payload["compressRatio"] = selected.compress_ratio
    gfs_periods = selected.raw_payload.get("gfsPeriods")
    if isinstance(gfs_periods, list):
        merged_payload["gfsPeriods"] = list(gfs_periods)
    if selected.backup_file_id and not merged_payload.get("backupFileId"):
        merged_payload["backupFileId"] = selected.backup_file_id

    return replace(
        record,
        raw_payload=merged_payload,
        restore_point_size_bytes=selected.data_size_bytes or record.restore_point_size_bytes,
    )
