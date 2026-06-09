"""Veeam 同步内部数据类型."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class VeeamMachineBackupRecord:
    """标准化后的 Veeam 机器备份记录."""

    machine_name: str
    backup_at: datetime
    machine_ip: str | None = None
    backup_id: str | None = None
    backup_file_id: str | None = None
    job_name: str | None = None
    restore_point_name: str | None = None
    source_record_id: str | None = None
    restore_point_size_bytes: int | None = None
    backup_chain_size_bytes: int | None = None
    restore_point_count: int | None = None
    raw_payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VeeamMachineBackupCollection:
    """本次备份拉取的标准化结果."""

    records: list[VeeamMachineBackupRecord]
    received_total: int
    snapshots_written_total: int
    skipped_invalid: int
    backups_received_total: int = 0
    backups_matched_total: int = 0
    backups_unmatched_total: int = 0
    backups_missing_machine_name: int = 0
    matched_backup_ids_sample: list[str] = field(default_factory=list)
    unmatched_backup_ids_sample: list[str] = field(default_factory=list)
    unmatched_machine_names_sample: list[str] = field(default_factory=list)
    missing_machine_name_backup_ids_sample: list[str] = field(default_factory=list)
    missing_machine_name_backup_names_sample: list[str] = field(default_factory=list)
    restore_points_backup_objects_total: int = 0
    restore_points_backup_objects_completed: int = 0
    timed_out_backup_objects_total: int = 0
    timed_out_backup_ids_sample: list[str] = field(default_factory=list)
    timed_out_machine_names_sample: list[str] = field(default_factory=list)
    timed_out_urls_sample: list[str] = field(default_factory=list)
    timed_out_reason_types_sample: list[str] = field(default_factory=list)
    timed_out_elapsed_ms_sample: list[int] = field(default_factory=list)
    failed_backup_objects_total: int = 0
    failed_backup_ids_sample: list[str] = field(default_factory=list)
    failed_machine_names_sample: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VeeamBackupFileRecord:
    """标准化后的 Veeam backupFile 记录."""

    backup_id: str
    backup_file_id: str | None = None
    object_id: str | None = None
    restore_point_ids: list[str] = field(default_factory=list)
    data_size_bytes: int | None = None
    backup_size_bytes: int | None = None
    dedup_ratio: int | None = None
    compress_ratio: int | None = None
    backup_at: datetime | None = None
    raw_payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VeeamBackupFileCollection:
    """本次 backupFiles 拉取结果."""

    records: list[VeeamBackupFileRecord]
    received_total: int
    backup_ids_total: int
    backup_ids_completed: int
    timed_out_backup_ids_total: int = 0
    timed_out_backup_ids_sample: list[str] = field(default_factory=list)
    timed_out_urls_sample: list[str] = field(default_factory=list)
    timed_out_reason_types_sample: list[str] = field(default_factory=list)
    timed_out_elapsed_ms_sample: list[int] = field(default_factory=list)
    failed_backup_ids_total: int = 0
    failed_backup_ids_sample: list[str] = field(default_factory=list)
    failed_urls_sample: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VeeamProviderSession:
    """Veeam 同步会话上下文."""

    base_url: str
    access_token: str
    api_version: str
    verify_ssl: bool


@dataclass(frozen=True, slots=True)
class VeeamMatchedBackupObject:
    """匹配后的 backupObject."""

    backup_object_id: str
    machine_name: str | None = None
    backup_item: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VeeamBackupObjectMatchResult:
    """backupObjects 匹配统计结果."""

    matched_backup_objects: list[VeeamMatchedBackupObject]
    backups_received_total: int
    backups_matched_total: int
    backups_unmatched_total: int
    backups_missing_machine_name: int
    matched_backup_ids_sample: list[str] = field(default_factory=list)
    unmatched_backup_ids_sample: list[str] = field(default_factory=list)
    unmatched_machine_names_sample: list[str] = field(default_factory=list)
    missing_machine_name_backup_ids_sample: list[str] = field(default_factory=list)
    missing_machine_name_backup_names_sample: list[str] = field(default_factory=list)


class VeeamRestorePointsFetchError(RuntimeError):
    """restorePoints 拉取失败时携带阶段进度."""

    def __init__(
        self,
        message: str,
        *,
        matched_backup_objects_total: int,
        completed_backup_objects_total: int,
        failed_backup_object_id: str | None,
        failed_machine_name: str | None,
        failed_url: str,
    ) -> None:
        super().__init__(message)
        self.matched_backup_objects_total = matched_backup_objects_total
        self.completed_backup_objects_total = completed_backup_objects_total
        self.failed_backup_object_id = failed_backup_object_id
        self.failed_machine_name = failed_machine_name
        self.failed_url = failed_url


class VeeamRequestTimeoutError(RuntimeError):
    """Veeam 单次请求超时."""

    def __init__(
        self,
        message: str,
        *,
        url: str,
        timeout_seconds: int,
        elapsed_ms: int,
        reason_type: str | None,
        reason_repr: str | None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.elapsed_ms = elapsed_ms
        self.reason_type = reason_type
        self.reason_repr = reason_repr
