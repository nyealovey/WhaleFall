"""Veeam 数据源与机器备份快照 Repository."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import inspect

from app import db
from app.models.instance import Instance
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.services.veeam.matching import build_instance_match_candidates, normalize_machine_name


def _serialize_snapshot_row(row: VeeamMachineBackupSnapshot) -> dict[str, object]:
    return {
        "machine_name": row.machine_name,
        "normalized_machine_name": row.normalized_machine_name,
        "latest_backup_at": row.latest_backup_at.isoformat() if row.latest_backup_at else None,
        "job_name": row.job_name,
        "restore_point_name": row.restore_point_name,
        "source_record_id": row.source_record_id,
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
        records: Iterable["VeeamMachineBackupRecord"],
        *,
        sync_run_id: str,
        synced_at: datetime,
    ) -> int:
        """以本次同步结果替换机器备份快照内容."""
        from app.services.veeam.provider import VeeamMachineBackupRecord

        latest_by_machine: dict[str, VeeamMachineBackupRecord] = {}
        for record in records:
            if not isinstance(record, VeeamMachineBackupRecord):
                continue
            normalized_machine_name = normalize_machine_name(record.machine_name)
            if not normalized_machine_name:
                continue
            current = latest_by_machine.get(normalized_machine_name)
            if current is None or record.backup_at > current.backup_at:
                latest_by_machine[normalized_machine_name] = record

        existing = {
            row.normalized_machine_name: row
            for row in VeeamMachineBackupSnapshot.query.order_by(VeeamMachineBackupSnapshot.id.asc()).all()
        }
        keep_machine_names: set[str] = set()
        for normalized_machine_name, record in latest_by_machine.items():
            keep_machine_names.add(normalized_machine_name)
            row = existing.get(normalized_machine_name)
            if row is None:
                row = VeeamMachineBackupSnapshot(
                    machine_name=record.machine_name,
                    normalized_machine_name=normalized_machine_name,
                    latest_backup_at=record.backup_at,
                )
            row.machine_name = record.machine_name
            row.normalized_machine_name = normalized_machine_name
            row.latest_backup_at = record.backup_at
            row.job_name = record.job_name
            row.restore_point_name = record.restore_point_name
            row.source_record_id = record.source_record_id
            row.raw_payload = record.raw_payload
            row.sync_run_id = sync_run_id
            row.synced_at = synced_at
            db.session.add(row)

        for normalized_machine_name, row in existing.items():
            if normalized_machine_name not in keep_machine_names:
                db.session.delete(row)

        db.session.flush()
        return len(keep_machine_names)

    @staticmethod
    def find_best_backup_for_instance_name(instance_name: str) -> dict[str, object] | None:
        """按实例名称与全局域名候选匹配最新备份快照."""
        if not VeeamRepository._has_machine_backup_snapshot_table():
            return None
        binding = VeeamRepository.get_binding()
        domains = binding.match_domains if binding and isinstance(binding.match_domains, list) else []
        candidates = build_instance_match_candidates(instance_name, domains)
        if not candidates:
            return None

        rows = (
            VeeamMachineBackupSnapshot.query.filter(
                VeeamMachineBackupSnapshot.normalized_machine_name.in_(candidates)
            )
            .order_by(VeeamMachineBackupSnapshot.latest_backup_at.desc(), VeeamMachineBackupSnapshot.id.desc())
            .all()
        )
        if not rows:
            return None
        best = rows[0]
        payload = _serialize_snapshot_row(best)
        payload["matched_machine_name"] = best.machine_name
        payload["match_candidates"] = candidates
        payload["last_sync_time"] = binding.last_sync_at.isoformat() if binding and binding.last_sync_at else None
        return payload

    @staticmethod
    def fetch_backup_summary_map(instances: list[Instance]) -> dict[int, dict[str, object]]:
        """批量按实例名称匹配 Veeam 机器备份快照."""
        if not instances or not VeeamRepository._has_machine_backup_snapshot_table():
            return {}

        binding = VeeamRepository.get_binding()
        domains = binding.match_domains if binding and isinstance(binding.match_domains, list) else []
        candidate_map: dict[int, list[str]] = {}
        all_candidates: set[str] = set()
        for instance in instances:
            candidates = build_instance_match_candidates(getattr(instance, "name", None), domains)
            if not candidates:
                continue
            candidate_map[int(instance.id)] = candidates
            all_candidates.update(candidates)

        if not all_candidates:
            return {}

        rows = (
            VeeamMachineBackupSnapshot.query.filter(
                VeeamMachineBackupSnapshot.normalized_machine_name.in_(sorted(all_candidates))
            )
            .order_by(VeeamMachineBackupSnapshot.latest_backup_at.desc(), VeeamMachineBackupSnapshot.id.desc())
            .all()
        )
        row_map = {row.normalized_machine_name: row for row in rows}
        summary_map: dict[int, dict[str, object]] = {}
        for instance_id, candidates in candidate_map.items():
            matched_rows = [row_map[candidate] for candidate in candidates if candidate in row_map]
            if not matched_rows:
                continue
            matched_rows.sort(key=lambda item: (item.latest_backup_at, item.id), reverse=True)
            best = matched_rows[0]
            payload = _serialize_snapshot_row(best)
            payload["matched_machine_name"] = best.machine_name
            payload["match_candidates"] = candidates
            payload["last_sync_time"] = binding.last_sync_at.isoformat() if binding and binding.last_sync_at else None
            summary_map[instance_id] = payload
        return summary_map
