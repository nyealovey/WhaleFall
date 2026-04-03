"""Veeam 数据源与机器备份快照 Repository."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import inspect

from app import db
from app.models.instance import Instance
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.services.veeam.matching import (
    build_instance_ip_candidates,
    build_instance_match_candidates,
    normalize_ip_address,
    normalize_machine_name,
)
from app.services.veeam.provider import VeeamMachineBackupRecord


def _normalize_string(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _walk_key_values(payload: object):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield str(key), value
            yield from _walk_key_values(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk_key_values(item)


def _pick_nested_int(payload: object, keys: tuple[str, ...]) -> int | None:
    for key, value in _walk_key_values(payload):
        if key not in keys:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _pick_string(payload: object, keys: tuple[str, ...]) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = _normalize_string(payload.get(key))
        if value:
            return value
    return None


def _pick_string_list(payload: object, keys: tuple[str, ...]) -> list[str]:
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, list):
            continue
        normalized = [cleaned for item in value if (cleaned := _normalize_string(item))]
        if normalized:
            return normalized
    return []


def _normalize_restore_points(raw_payload: dict[str, object]) -> list[dict[str, object]]:
    items = raw_payload.get("restore_points")
    if not isinstance(items, list):
        return []

    normalized_items: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized = {
            "id": _pick_string(item, ("id", "restorePointId", "restore_point_id")),
            "name": _pick_string(item, ("name", "restorePointName", "restore_point_name")),
            "type": _pick_string(item, ("type",)),
            "backup_id": _pick_string(item, ("backupId", "backup_id")),
            "object_id": _pick_string(item, ("objectId", "object_id")),
            "restore_point_ids": _pick_string_list(item, ("restorePointIds", "restore_point_ids")),
            "data_size_bytes": _pick_nested_int(
                item,
                ("dataSize", "data_size", "dataSizeBytes", "data_size_bytes"),
            ),
            "backup_size_bytes": _pick_nested_int(
                item,
                ("backupSize", "backup_size", "backupSizeBytes", "backup_size_bytes"),
            ),
            "compress_ratio": _pick_nested_int(item, ("compressRatio", "compress_ratio")),
            "creation_time": _pick_string(
                item,
                ("creationTime", "creation_time", "backupTime", "backup_time"),
            ),
        }
        if any(value not in (None, [], "") for value in normalized.values()):
            normalized_items.append(normalized)
    return normalized_items


def _build_backup_metrics_coverage(
    *,
    restore_points: list[dict[str, object]],
    restore_point_count: int,
    restore_point_times_count: int,
) -> dict[str, object]:
    expected_restore_point_count = len(restore_points) or restore_point_count or restore_point_times_count
    enriched_restore_point_count = sum(1 for item in restore_points if isinstance(item.get("backup_size_bytes"), int))
    missing_restore_point_count = max(expected_restore_point_count - enriched_restore_point_count, 0)
    return {
        "expected_restore_point_count": expected_restore_point_count,
        "enriched_restore_point_count": enriched_restore_point_count,
        "missing_restore_point_count": missing_restore_point_count,
        "partial": expected_restore_point_count > 0 and missing_restore_point_count > 0,
    }


def _serialize_snapshot_row(row: VeeamMachineBackupSnapshot) -> dict[str, object]:
    raw_payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
    restore_points = _normalize_restore_points(raw_payload)
    restore_point_times = raw_payload.get("restore_point_times")
    normalized_restore_point_times = (
        [str(item).strip() for item in restore_point_times if isinstance(item, str) and item.strip()]
        if isinstance(restore_point_times, list)
        else []
    )
    if not normalized_restore_point_times and restore_points:
        normalized_restore_point_times = [
            creation_time for item in restore_points if (creation_time := _normalize_string(item.get("creation_time")))
        ]
    backup_size_values = [value for item in restore_points if isinstance((value := item.get("backup_size_bytes")), int)]
    resolved_restore_point_count = len(restore_points) or row.restore_point_count or len(normalized_restore_point_times)
    return {
        "machine_name": row.machine_name,
        "normalized_machine_name": row.normalized_machine_name,
        "machine_ip": row.machine_ip,
        "normalized_machine_ip": row.normalized_machine_ip,
        "latest_backup_at": row.latest_backup_at.isoformat() if row.latest_backup_at else None,
        "backup_id": row.backup_id,
        "backup_file_id": row.backup_file_id,
        "job_name": row.job_name,
        "restore_point_name": row.restore_point_name,
        "source_record_id": row.source_record_id,
        "restore_point_size_bytes": row.restore_point_size_bytes,
        "backup_chain_size_bytes": sum(backup_size_values) if backup_size_values else row.backup_chain_size_bytes,
        "restore_point_count": resolved_restore_point_count,
        "backup_metrics_coverage": _build_backup_metrics_coverage(
            restore_points=restore_points,
            restore_point_count=int(resolved_restore_point_count or 0),
            restore_point_times_count=len(normalized_restore_point_times),
        ),
        "restore_point_times": normalized_restore_point_times,
        "restore_points": restore_points,
        "sync_run_id": row.sync_run_id,
        "synced_at": row.synced_at.isoformat() if row.synced_at else None,
    }


class VeeamRepository:
    """Veeam 绑定与快照访问."""

    @staticmethod
    def _has_machine_backup_snapshot_table() -> bool:
        inspector = inspect(db.engine)
        return inspector.has_table(VeeamMachineBackupSnapshot.__tablename__)

    @staticmethod
    def get_binding() -> VeeamSourceBinding | None:
        """获取当前全局绑定."""
        return VeeamSourceBinding.query.order_by(VeeamSourceBinding.id.asc()).first()

    @staticmethod
    def add_binding(binding: VeeamSourceBinding) -> VeeamSourceBinding:
        """新增或更新绑定."""
        db.session.add(binding)
        db.session.flush()
        return binding

    @staticmethod
    def delete_binding(binding: VeeamSourceBinding) -> None:
        """删除绑定."""
        db.session.delete(binding)

    @staticmethod
    def clear_machine_backup_snapshots() -> None:
        """清空全部机器备份快照."""
        if not VeeamRepository._has_machine_backup_snapshot_table():
            return
        VeeamMachineBackupSnapshot.query.delete()

    @staticmethod
    def replace_machine_backup_snapshots(
        records: Iterable[VeeamMachineBackupRecord],
        *,
        sync_run_id: str,
        synced_at: datetime,
    ) -> int:
        """以本同步结果替换机器备份快照内容,支持机器名/IP 双通道匹配."""
        latest_by_key: dict[str, VeeamMachineBackupRecord] = {}
        for record in records:
            if not isinstance(record, VeeamMachineBackupRecord):
                continue
            normalized_machine_name = normalize_machine_name(record.machine_name)
            normalized_machine_ip = normalize_ip_address(record.machine_ip) if record.machine_ip else None

            key_name = normalized_machine_name if normalized_machine_name else None
            key_ip = normalized_machine_ip if normalized_machine_ip else None

            if key_name:
                current = latest_by_key.get(key_name)
                if current is None or record.backup_at > current.backup_at:
                    latest_by_key[key_name] = record
            if key_ip:
                current = latest_by_key.get(key_ip)
                if current is None or record.backup_at > current.backup_at:
                    latest_by_key[key_ip] = record

        existing_name = {
            row.normalized_machine_name: row
            for row in VeeamMachineBackupSnapshot.query.filter(
                VeeamMachineBackupSnapshot.normalized_machine_name.isnot(None)
            ).all()
        }
        existing_ip = {
            row.normalized_machine_ip: row
            for row in VeeamMachineBackupSnapshot.query.filter(
                VeeamMachineBackupSnapshot.normalized_machine_ip.isnot(None)
            ).all()
        }

        keep_keys: set[str] = set()
        for key, record in latest_by_key.items():
            keep_keys.add(key)
            normalized_machine_name = normalize_machine_name(record.machine_name)
            normalized_machine_ip = normalize_ip_address(record.machine_ip) if record.machine_ip else None

            row = None
            if normalized_machine_name and normalized_machine_name in existing_name:
                row = existing_name[normalized_machine_name]
            elif normalized_machine_ip and normalized_machine_ip in existing_ip:
                row = existing_ip[normalized_machine_ip]

            if row is None:
                row = VeeamMachineBackupSnapshot(
                    machine_name=record.machine_name,
                    normalized_machine_name=normalized_machine_name or "",
                    latest_backup_at=record.backup_at,
                )

            row.machine_name = record.machine_name
            row.normalized_machine_name = normalized_machine_name or ""
            row.machine_ip = record.machine_ip
            row.normalized_machine_ip = normalized_machine_ip or ""
            row.latest_backup_at = record.backup_at
            row.backup_id = record.backup_id
            row.backup_file_id = record.backup_file_id
            row.job_name = record.job_name
            row.restore_point_name = record.restore_point_name
            row.source_record_id = record.source_record_id
            row.restore_point_size_bytes = record.restore_point_size_bytes
            row.backup_chain_size_bytes = record.backup_chain_size_bytes
            row.restore_point_count = record.restore_point_count
            row.raw_payload = record.raw_payload
            row.sync_run_id = sync_run_id
            row.synced_at = synced_at
            db.session.add(row)

        for row in existing_name.values():
            if row.normalized_machine_name not in keep_keys:
                db.session.delete(row)
        for row in existing_ip.values():
            if row.normalized_machine_ip not in keep_keys:
                db.session.delete(row)

        db.session.flush()
        return len(keep_keys)

    @staticmethod
    def find_best_backup_for_instance_name(
        instance_name: str, instance_host: str | None = None
    ) -> dict[str, object] | None:
        """按实例名称与全局域名候选匹配最新备份快照,支持机器名/IP 双通道."""
        if not VeeamRepository._has_machine_backup_snapshot_table():
            return None
        binding = VeeamRepository.get_binding()
        domains = binding.match_domains if binding and isinstance(binding.match_domains, list) else []

        name_candidates = build_instance_match_candidates(instance_name, domains)
        ip_candidates = build_instance_ip_candidates(instance_host)

        all_candidates = set(name_candidates)
        all_candidates.update(ip_candidates)
        if not all_candidates:
            return None

        rows = (
            VeeamMachineBackupSnapshot.query.filter(
                (VeeamMachineBackupSnapshot.normalized_machine_name.in_(name_candidates))
                | (VeeamMachineBackupSnapshot.normalized_machine_ip.in_(ip_candidates))
            )
            .order_by(VeeamMachineBackupSnapshot.latest_backup_at.desc(), VeeamMachineBackupSnapshot.id.desc())
            .all()
        )
        if not rows:
            return None
        best = rows[0]
        payload = _serialize_snapshot_row(best)
        payload["matched_machine_name"] = best.machine_name
        payload["matched_machine_ip"] = best.machine_ip
        payload["match_candidates"] = list(all_candidates)
        payload["last_sync_time"] = binding.last_sync_at.isoformat() if binding and binding.last_sync_at else None
        return payload

    @staticmethod
    def fetch_backup_summary_map(instances: list[Instance]) -> dict[int, dict[str, object]]:
        """批量按实例名称/主机匹配 Veeam 机器备份快照,支持机器名/IP 双通道."""
        if not instances or not VeeamRepository._has_machine_backup_snapshot_table():
            return {}

        binding = VeeamRepository.get_binding()
        domains = binding.match_domains if binding and isinstance(binding.match_domains, list) else []

        candidate_name_map: dict[int, list[str]] = {}
        candidate_ip_map: dict[int, list[str]] = {}
        all_name_candidates: set[str] = set()
        all_ip_candidates: set[str] = set()

        for instance in instances:
            name_candidates = build_instance_match_candidates(getattr(instance, "name", None), domains)
            ip_candidates = build_instance_ip_candidates(getattr(instance, "host", None))

            if name_candidates:
                candidate_name_map[int(instance.id)] = name_candidates
                all_name_candidates.update(name_candidates)
            if ip_candidates:
                candidate_ip_map[int(instance.id)] = ip_candidates
                all_ip_candidates.update(ip_candidates)

        if not all_name_candidates and not all_ip_candidates:
            return {}

        name_rows = (
            VeeamMachineBackupSnapshot.query.filter(
                VeeamMachineBackupSnapshot.normalized_machine_name.in_(sorted(all_name_candidates))
            ).all()
            if all_name_candidates
            else []
        )
        ip_rows = (
            VeeamMachineBackupSnapshot.query.filter(
                VeeamMachineBackupSnapshot.normalized_machine_ip.in_(sorted(all_ip_candidates))
            ).all()
            if all_ip_candidates
            else []
        )

        name_row_map = {row.normalized_machine_name: row for row in name_rows}
        ip_row_map = {row.normalized_machine_ip: row for row in ip_rows}

        summary_map: dict[int, dict[str, object]] = {}
        for instance in instances:
            instance_id = int(instance.id)
            name_candidates = candidate_name_map.get(instance_id, [])
            ip_candidates = candidate_ip_map.get(instance_id, [])

            matched_rows = []
            for candidate in name_candidates:
                if candidate in name_row_map:
                    matched_rows.append(name_row_map[candidate])
            for candidate in ip_candidates:
                if candidate in ip_row_map:
                    matched_rows.append(ip_row_map[candidate])

            if not matched_rows:
                continue
            matched_rows.sort(key=lambda item: (item.latest_backup_at, item.id), reverse=True)
            best = matched_rows[0]
            payload = _serialize_snapshot_row(best)
            payload["matched_machine_name"] = best.machine_name
            payload["matched_machine_ip"] = best.machine_ip
            payload["match_candidates"] = name_candidates + ip_candidates
            payload["last_sync_time"] = binding.last_sync_at.isoformat() if binding and binding.last_sync_at else None
            summary_map[instance_id] = payload
        return summary_map
