"""Veeam 数据源与机器备份快照 Repository."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class _SnapshotWriteRecord:
    record: VeeamMachineBackupRecord
    normalized_machine_name: str
    machine_ip: str | None
    normalized_machine_ip: str | None


@dataclass(frozen=True, slots=True)
class _SnapshotCandidateBatch:
    name_map: dict[int, list[str]]
    ip_map: dict[int, list[str]]
    all_names: set[str]
    all_ips: set[str]


@dataclass(frozen=True, slots=True)
class _SnapshotSummaryMatch:
    row: VeeamMachineBackupSnapshot
    binding: VeeamSourceBinding
    name_candidates: list[str]
    ip_candidates: list[str]


def _normalize_string(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _resolve_snapshot_machine_ip(record: VeeamMachineBackupRecord) -> tuple[str | None, str | None]:
    normalized_machine_ip = normalize_ip_address(record.machine_ip) if record.machine_ip else None
    if normalized_machine_ip:
        return normalized_machine_ip, normalized_machine_ip
    machine_name_as_ip = normalize_ip_address(record.machine_name)
    if machine_name_as_ip:
        return machine_name_as_ip, machine_name_as_ip
    return None, None


def _build_snapshot_write_records(records: Iterable[VeeamMachineBackupRecord]) -> list[_SnapshotWriteRecord]:
    valid_records = [record for record in records if isinstance(record, VeeamMachineBackupRecord)]
    selected: list[_SnapshotWriteRecord] = []
    seen_names: set[str] = set()
    seen_ips: set[str] = set()

    for record in sorted(
        valid_records,
        key=lambda item: (item.backup_at, item.source_record_id or ""),
        reverse=True,
    ):
        normalized_machine_name = normalize_machine_name(record.machine_name)
        machine_ip, normalized_machine_ip = _resolve_snapshot_machine_ip(record)
        if not normalized_machine_name and not normalized_machine_ip:
            continue
        if normalized_machine_name and normalized_machine_name in seen_names:
            continue
        if normalized_machine_ip and normalized_machine_ip in seen_ips:
            continue

        selected.append(
            _SnapshotWriteRecord(
                record=record,
                normalized_machine_name=normalized_machine_name,
                machine_ip=machine_ip,
                normalized_machine_ip=normalized_machine_ip,
            )
        )
        if normalized_machine_name:
            seen_names.add(normalized_machine_name)
        if normalized_machine_ip:
            seen_ips.add(normalized_machine_ip)

    return selected


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
        platform_name = _pick_string(item, ("platformName", "platform_name"))
        if platform_name:
            normalized["platform_name"] = platform_name
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


def _build_snapshot_candidate_batch(instances: list[Instance], domains: list[str]) -> _SnapshotCandidateBatch:
    candidate_name_map: dict[int, list[str]] = {}
    candidate_ip_map: dict[int, list[str]] = {}
    all_name_candidates: set[str] = set()
    all_ip_candidates: set[str] = set()

    for instance in instances:
        instance_id = int(instance.id)
        name_candidates = build_instance_match_candidates(getattr(instance, "name", None), domains)
        ip_candidates = build_instance_ip_candidates(getattr(instance, "host", None))

        if name_candidates:
            candidate_name_map[instance_id] = name_candidates
            all_name_candidates.update(name_candidates)
        if ip_candidates:
            candidate_ip_map[instance_id] = ip_candidates
            all_ip_candidates.update(ip_candidates)

    return _SnapshotCandidateBatch(
        name_map=candidate_name_map,
        ip_map=candidate_ip_map,
        all_names=all_name_candidates,
        all_ips=all_ip_candidates,
    )


def _fetch_snapshot_rows_by_names(
    binding_id: int,
    candidates: set[str],
) -> list[VeeamMachineBackupSnapshot]:
    if not candidates:
        return []
    return VeeamMachineBackupSnapshot.query.filter(
        VeeamMachineBackupSnapshot.source_binding_id == binding_id,
        VeeamMachineBackupSnapshot.normalized_machine_name.in_(sorted(candidates)),
    ).all()


def _fetch_snapshot_rows_by_ips(
    binding_id: int,
    candidates: set[str],
) -> list[VeeamMachineBackupSnapshot]:
    if not candidates:
        return []
    return VeeamMachineBackupSnapshot.query.filter(
        VeeamMachineBackupSnapshot.source_binding_id == binding_id,
        VeeamMachineBackupSnapshot.normalized_machine_ip.in_(sorted(candidates)),
    ).all()


def _collect_matched_snapshot_rows(
    *,
    name_candidates: list[str],
    ip_candidates: list[str],
    name_row_map: dict[str, VeeamMachineBackupSnapshot],
    ip_row_map: dict[str, VeeamMachineBackupSnapshot],
) -> list[VeeamMachineBackupSnapshot]:
    return [
        *(name_row_map[candidate] for candidate in name_candidates if candidate in name_row_map),
        *(ip_row_map[candidate] for candidate in ip_candidates if candidate in ip_row_map),
    ]


def _is_newer_snapshot(
    row: VeeamMachineBackupSnapshot,
    current: _SnapshotSummaryMatch | None,
) -> bool:
    return current is None or (row.latest_backup_at, row.id) > (current.row.latest_backup_at, current.row.id)


class VeeamRepository:
    """Veeam 绑定与快照访问."""

    @staticmethod
    def _has_machine_backup_snapshot_table() -> bool:
        inspector = inspect(db.engine)
        return inspector.has_table(VeeamMachineBackupSnapshot.__tablename__)

    @staticmethod
    def get_binding() -> VeeamSourceBinding | None:
        """获取第一个绑定,兼容单源调用."""
        return VeeamSourceBinding.query.order_by(VeeamSourceBinding.id.asc()).first()

    @staticmethod
    def list_bindings() -> list[VeeamSourceBinding]:
        """获取全部 Veeam 数据源绑定."""
        return VeeamSourceBinding.query.order_by(VeeamSourceBinding.id.asc()).all()

    @staticmethod
    def list_enabled_bindings() -> list[VeeamSourceBinding]:
        """获取启用中的 Veeam 数据源绑定."""
        return (
            VeeamSourceBinding.query.filter(VeeamSourceBinding.is_enabled.is_(True))
            .order_by(VeeamSourceBinding.id.asc())
            .all()
        )

    @staticmethod
    def get_binding_by_id(binding_id: int) -> VeeamSourceBinding | None:
        """按 ID 获取 Veeam 数据源绑定."""
        return VeeamSourceBinding.query.filter(VeeamSourceBinding.id == int(binding_id)).first()

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
    def delete_binding_by_id(binding_id: int) -> None:
        """按 ID 删除绑定."""
        binding = VeeamRepository.get_binding_by_id(binding_id)
        if binding is not None:
            db.session.delete(binding)

    @staticmethod
    def clear_machine_backup_snapshots(source_binding_id: int | None = None) -> None:
        """清空机器备份快照."""
        if not VeeamRepository._has_machine_backup_snapshot_table():
            return
        query = VeeamMachineBackupSnapshot.query
        if source_binding_id is not None:
            query = query.filter(VeeamMachineBackupSnapshot.source_binding_id == int(source_binding_id))
        query.delete()

    @staticmethod
    def replace_machine_backup_snapshots(
        records: Iterable[VeeamMachineBackupRecord],
        *,
        source_binding_id: int,
        sync_run_id: str,
        synced_at: datetime,
    ) -> int:
        """以本同步结果替换机器备份快照内容,支持机器名/IP 双通道匹配."""
        return VeeamRepository._write_machine_backup_snapshots(
            records,
            source_binding_id=source_binding_id,
            sync_run_id=sync_run_id,
            synced_at=synced_at,
            delete_missing=True,
        )

    @staticmethod
    def upsert_machine_backup_snapshots(
        records: Iterable[VeeamMachineBackupRecord],
        *,
        source_binding_id: int,
        sync_run_id: str,
        synced_at: datetime,
    ) -> int:
        """写入本次机器备份快照,不删除其它机器快照."""
        return VeeamRepository._write_machine_backup_snapshots(
            records,
            source_binding_id=source_binding_id,
            sync_run_id=sync_run_id,
            synced_at=synced_at,
            delete_missing=False,
        )

    @staticmethod
    def _write_machine_backup_snapshots(
        records: Iterable[VeeamMachineBackupRecord],
        *,
        source_binding_id: int,
        sync_run_id: str,
        synced_at: datetime,
        delete_missing: bool,
    ) -> int:
        selected_records = _build_snapshot_write_records(records)
        existing_rows = VeeamMachineBackupSnapshot.query.filter(
            VeeamMachineBackupSnapshot.source_binding_id == int(source_binding_id)
        ).all()
        existing_name = {
            row.normalized_machine_name: row for row in existing_rows if row.normalized_machine_name
        }
        existing_ip = {row.normalized_machine_ip: row for row in existing_rows if row.normalized_machine_ip}

        kept_existing_object_ids: set[int] = set()
        for selected in selected_records:
            row = VeeamRepository._find_snapshot_row(
                selected,
                existing_name=existing_name,
                existing_ip=existing_ip,
            )
            if row is None:
                row = VeeamMachineBackupSnapshot()
                row.source_binding_id = int(source_binding_id)

            VeeamRepository._apply_snapshot_write_record(
                row,
                selected,
                source_binding_id=int(source_binding_id),
                sync_run_id=sync_run_id,
                synced_at=synced_at,
            )
            db.session.add(row)
            kept_existing_object_ids.add(id(row))

        if delete_missing:
            for row in existing_rows:
                if id(row) not in kept_existing_object_ids:
                    db.session.delete(row)

        db.session.flush()
        return len(selected_records)

    @staticmethod
    def _find_snapshot_row(
        selected: _SnapshotWriteRecord,
        *,
        existing_name: dict[str, VeeamMachineBackupSnapshot],
        existing_ip: dict[str, VeeamMachineBackupSnapshot],
    ) -> VeeamMachineBackupSnapshot | None:
        name_row = existing_name.get(selected.normalized_machine_name)
        ip_row = existing_ip.get(selected.normalized_machine_ip) if selected.normalized_machine_ip else None

        if name_row is not None and ip_row is not None and name_row is not ip_row:
            ip_row.machine_ip = None
            ip_row.normalized_machine_ip = None
            db.session.delete(ip_row)
            return name_row
        return name_row or ip_row

    @staticmethod
    def _apply_snapshot_write_record(
        row: VeeamMachineBackupSnapshot,
        selected: _SnapshotWriteRecord,
        *,
        source_binding_id: int,
        sync_run_id: str,
        synced_at: datetime,
    ) -> None:
        record = selected.record
        row.source_binding_id = int(source_binding_id)
        row.machine_name = record.machine_name
        row.normalized_machine_name = selected.normalized_machine_name
        row.machine_ip = selected.machine_ip
        row.normalized_machine_ip = selected.normalized_machine_ip
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

    @staticmethod
    def find_best_backup_for_instance_name(
        instance_name: str, instance_host: str | None = None
    ) -> dict[str, object] | None:
        """按实例名称与各启用源域名候选匹配最新备份快照,支持机器名/IP 双通道."""
        if not VeeamRepository._has_machine_backup_snapshot_table():
            return None

        candidates: list[tuple[VeeamSourceBinding, list[str], list[str]]] = []
        for binding in VeeamRepository.list_enabled_bindings():
            domains = binding.match_domains if isinstance(binding.match_domains, list) else []
            name_candidates = build_instance_match_candidates(instance_name, domains)
            ip_candidates = build_instance_ip_candidates(instance_host)
            if name_candidates or ip_candidates:
                candidates.append((binding, name_candidates, ip_candidates))

        if not candidates:
            return None

        best_row: VeeamMachineBackupSnapshot | None = None
        best_binding: VeeamSourceBinding | None = None
        best_name_candidates: list[str] = []
        best_ip_candidates: list[str] = []
        for binding, name_candidates, ip_candidates in candidates:
            filters = []
            if name_candidates:
                filters.append(VeeamMachineBackupSnapshot.normalized_machine_name.in_(name_candidates))
            if ip_candidates:
                filters.append(VeeamMachineBackupSnapshot.normalized_machine_ip.in_(ip_candidates))
            rows = (
                VeeamMachineBackupSnapshot.query.filter(
                    VeeamMachineBackupSnapshot.source_binding_id == int(binding.id),
                    filters[0] if len(filters) == 1 else filters[0] | filters[1],
                )
                .order_by(VeeamMachineBackupSnapshot.latest_backup_at.desc(), VeeamMachineBackupSnapshot.id.desc())
                .all()
            )
            if not rows:
                continue
            row = rows[0]
            if best_row is None or (row.latest_backup_at, row.id) > (best_row.latest_backup_at, best_row.id):
                best_row = row
                best_binding = binding
                best_name_candidates = name_candidates
                best_ip_candidates = ip_candidates

        if best_row is None or best_binding is None:
            return None
        best = best_row
        payload = _serialize_snapshot_row(best)
        payload["matched_machine_name"] = best.machine_name
        payload["matched_machine_ip"] = best.machine_ip
        if best.normalized_machine_name in best_name_candidates:
            payload["match_candidates"] = best_name_candidates
        else:
            payload["match_candidates"] = best_name_candidates + best_ip_candidates
        payload["source_binding_id"] = int(best_binding.id)
        payload["source_name"] = str(best_binding.name or "")
        payload["source_server_host"] = str(best_binding.server_host or "")
        payload["last_sync_time"] = best_binding.last_sync_at.isoformat() if best_binding.last_sync_at else None
        return payload

    @staticmethod
    def fetch_backup_summary_map(instances: list[Instance]) -> dict[int, dict[str, object]]:
        """批量按实例名称/主机匹配 Veeam 机器备份快照,支持机器名/IP 双通道."""
        if not instances or not VeeamRepository._has_machine_backup_snapshot_table():
            return {}

        bindings = VeeamRepository.list_enabled_bindings()
        if not bindings:
            return {}

        best_by_instance: dict[int, _SnapshotSummaryMatch] = {}

        for binding in bindings:
            domains = binding.match_domains if isinstance(binding.match_domains, list) else []
            candidate_batch = _build_snapshot_candidate_batch(instances, domains)

            if not candidate_batch.all_names and not candidate_batch.all_ips:
                continue

            binding_id = int(binding.id)
            name_rows = _fetch_snapshot_rows_by_names(binding_id, candidate_batch.all_names)
            ip_rows = _fetch_snapshot_rows_by_ips(binding_id, candidate_batch.all_ips)

            name_row_map = {row.normalized_machine_name: row for row in name_rows}
            ip_row_map = {row.normalized_machine_ip: row for row in ip_rows}

            for instance in instances:
                instance_id = int(instance.id)
                name_candidates = candidate_batch.name_map.get(instance_id, [])
                ip_candidates = candidate_batch.ip_map.get(instance_id, [])
                matched_rows = _collect_matched_snapshot_rows(
                    name_candidates=name_candidates,
                    ip_candidates=ip_candidates,
                    name_row_map=name_row_map,
                    ip_row_map=ip_row_map,
                )

                if not matched_rows:
                    continue
                row = max(matched_rows, key=lambda item: (item.latest_backup_at, item.id))
                current = best_by_instance.get(instance_id)
                if _is_newer_snapshot(row, current):
                    best_by_instance[instance_id] = _SnapshotSummaryMatch(
                        row=row,
                        binding=binding,
                        name_candidates=name_candidates,
                        ip_candidates=ip_candidates,
                    )

        summary_map: dict[int, dict[str, object]] = {}
        for instance_id, match in best_by_instance.items():
            best = match.row
            payload = _serialize_snapshot_row(best)
            payload["matched_machine_name"] = best.machine_name
            payload["matched_machine_ip"] = best.machine_ip
            payload["match_candidates"] = match.name_candidates + match.ip_candidates
            payload["source_binding_id"] = int(match.binding.id)
            payload["source_name"] = str(match.binding.name or "")
            payload["source_server_host"] = str(match.binding.server_host or "")
            payload["last_sync_time"] = match.binding.last_sync_at.isoformat() if match.binding.last_sync_at else None
            summary_map[instance_id] = payload
        return summary_map
