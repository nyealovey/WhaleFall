"""Veeam backupObject 匹配与采样."""

from __future__ import annotations

from typing import Any

from app.infra.route_safety import log_with_context
from app.services.veeam.matching import normalize_ip_address, normalize_machine_name
from app.services.veeam.types import VeeamBackupObjectMatchResult, VeeamMatchedBackupObject

_SAMPLE_LIMIT = 20


class VeeamMatchSampler:
    """匹配目标 backupObjects 并维护诊断样本."""

    def match_backup_objects(
        self,
        *,
        backup_items: list[dict[str, Any]],
        match_machine_names: set[str] | None = None,
        match_machine_ips: set[str] | None = None,
    ) -> VeeamBackupObjectMatchResult:
        backups_received_total = len(backup_items)
        backups_matched_total = 0
        backups_unmatched_total = 0
        backups_missing_machine_name = 0
        matched_backup_ids_sample: list[str] = []
        unmatched_backup_ids_sample: list[str] = []
        unmatched_machine_names_sample: list[str] = []
        missing_machine_name_backup_ids_sample: list[str] = []
        missing_machine_name_backup_names_sample: list[str] = []
        matched_backup_objects: list[VeeamMatchedBackupObject] = []

        for backup_item in backup_items:
            backup_object_id = _pick_string(backup_item, ("id", "backupObjectId", "backup_object_id"))
            if not backup_object_id:
                continue
            backup_machine_name = resolve_backup_machine_name(backup_item)
            backup_machine_ip = resolve_backup_machine_ip(backup_item)
            if not match_machine_names and not match_machine_ips:
                continue

            normalized_backup_machine_name = normalize_machine_name(backup_machine_name)
            backup_name_as_ip = normalize_ip_address(backup_machine_name)
            normalized_backup_machine_ip = normalize_ip_address(backup_machine_ip) if backup_machine_ip else None
            if backup_name_as_ip and not normalized_backup_machine_ip:
                normalized_backup_machine_ip = backup_name_as_ip

            name_matched = normalized_backup_machine_name in match_machine_names if match_machine_names else False
            ip_matched = (
                normalized_backup_machine_ip in match_machine_ips
                if match_machine_ips and normalized_backup_machine_ip
                else False
            )

            if match_machine_names and not normalized_backup_machine_name:
                backups_missing_machine_name += 1
                _append_sample(missing_machine_name_backup_ids_sample, backup_object_id)
                backup_name = _pick_string(backup_item, ("name", "jobName", "backupName"))
                if backup_name:
                    _append_sample(missing_machine_name_backup_names_sample, backup_name)

            if not name_matched and not ip_matched:
                backups_unmatched_total += 1
                _append_sample(unmatched_backup_ids_sample, backup_object_id)
                if backup_machine_name:
                    _append_sample(unmatched_machine_names_sample, str(backup_machine_name))
                continue

            backups_matched_total += 1
            _append_sample(matched_backup_ids_sample, backup_object_id)
            matched_backup_objects.append(
                VeeamMatchedBackupObject(
                    backup_object_id=backup_object_id,
                    machine_name=backup_machine_name,
                    backup_item=dict(backup_item),
                )
            )

        if unmatched_machine_names_sample:
            log_with_context(
                "info",
                "Veeam 备份未匹配到实例",
                module="veeam",
                action="match_backup_objects",
                extra={
                    "unmatched_count": backups_unmatched_total,
                    "unmatched_machine_names": sorted(unmatched_machine_names_sample)[:_SAMPLE_LIMIT],
                },
                include_actor=False,
            )

        return VeeamBackupObjectMatchResult(
            matched_backup_objects=matched_backup_objects,
            backups_received_total=backups_received_total,
            backups_matched_total=backups_matched_total,
            backups_unmatched_total=backups_unmatched_total,
            backups_missing_machine_name=backups_missing_machine_name,
            matched_backup_ids_sample=matched_backup_ids_sample,
            unmatched_backup_ids_sample=unmatched_backup_ids_sample,
            unmatched_machine_names_sample=unmatched_machine_names_sample,
            missing_machine_name_backup_ids_sample=missing_machine_name_backup_ids_sample,
            missing_machine_name_backup_names_sample=missing_machine_name_backup_names_sample,
        )


def resolve_backup_machine_name(item: dict[str, Any]) -> str | None:
    """从 backupObject payload 提取机器名."""

    return _pick_string(
        item,
        (
            "name",
            "machineName",
            "machine_name",
            "objectName",
            "object_name",
            "workloadName",
            "workload_name",
            "computerName",
            "computer_name",
            "vmName",
            "vm_name",
            "hostName",
            "host_name",
        ),
    )


def resolve_backup_machine_ip(item: dict[str, Any]) -> str | None:
    """从 backupObject payload 提取机器 IP."""

    return _pick_string(
        item,
        (
            "ipAddress",
            "ip_address",
            "hostIp",
            "host_ip",
            "guestIp",
            "guest_ip",
            "ip",
            "ipAddress1",
            "ip_address_1",
            "networkIp",
            "network_ip",
        ),
    )


def _append_sample(sample: list[str], value: str) -> None:
    if len(sample) < _SAMPLE_LIMIT:
        sample.append(value)


def _pick_string(item: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
