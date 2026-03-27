"""Veeam Provider 抽象与 HTTP 实现."""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from flask import current_app, has_app_context

from app.settings import Settings
from app.services.veeam.matching import normalize_machine_name
from app.utils.time_utils import time_utils

VEEAM_TOKEN_PATH = "/api/oauth2/token"
VEEAM_RESTORE_POINTS_PATH = "/api/v1/restorePoints"
VEEAM_BACKUP_OBJECTS_PATH = "/api/v1/backupObjects"
VEEAM_BACKUPS_PATH = "/api/v1/backups"
VEEAM_ACCEPT_HEADER = "application/json"


def _default_open(request: Request, *, timeout: int, context: ssl.SSLContext):
    return urlopen(request, timeout=timeout, context=context)


@dataclass(frozen=True, slots=True)
class VeeamMachineBackupRecord:
    """标准化后的 Veeam 机器备份记录."""

    machine_name: str
    backup_at: datetime
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


class VeeamProvider(Protocol):
    """Veeam 数据拉取接口."""

    def is_configured(self) -> bool:
        """返回 provider 是否已具备真实可用实现."""

    def create_session(
        self,
        *,
        server_host: str,
        server_port: int,
        username: str,
        password: str,
        api_version: str,
        verify_ssl: bool | None = None,
    ) -> VeeamProviderSession:
        """创建同步会话."""

    def fetch_backup_objects(self, *, session: VeeamProviderSession) -> list[dict[str, Any]]:
        """拉取 backupObjects."""

    def match_backup_objects(
        self,
        *,
        backup_items: list[dict[str, Any]],
        match_machine_names: set[str] | None = None,
    ) -> VeeamBackupObjectMatchResult:
        """匹配目标 backupObjects 并返回统计."""

    def fetch_restore_point_records(
        self,
        *,
        session: VeeamProviderSession,
        match_result: VeeamBackupObjectMatchResult,
    ) -> VeeamMachineBackupCollection:
        """按匹配结果拉取 restorePoints."""

    def fetch_backup_file_records(
        self,
        *,
        session: VeeamProviderSession,
        backup_ids: list[str],
    ) -> VeeamBackupFileCollection:
        """按 backupId 拉取 backupFiles."""

    def list_machine_backups(
        self,
        *,
        server_host: str,
        server_port: int,
        username: str,
        password: str,
        api_version: str,
        match_machine_names: set[str] | None = None,
        verify_ssl: bool | None = None,
    ) -> VeeamMachineBackupCollection:
        """返回机器级备份列表与统计."""


class HttpVeeamProvider:
    """VBR HTTP Provider."""

    def __init__(
        self,
        *,
        timeout_seconds: int | None = None,
        verify_ssl: bool | None = None,
        opener=_default_open,
    ) -> None:
        resolved_settings = self._resolve_settings()
        self._timeout_seconds = int(timeout_seconds or resolved_settings["timeout_seconds"])
        self._backup_objects_limit = int(resolved_settings["backup_objects_limit"])
        self._verify_ssl = bool(resolved_settings["verify_ssl"] if verify_ssl is None else verify_ssl)
        self._opener = opener

    @staticmethod
    def _resolve_settings() -> dict[str, object]:
        if has_app_context():
            return {
                "timeout_seconds": current_app.config.get(
                    "VEEAM_REQUEST_TIMEOUT_SECONDS",
                    Settings.model_fields["veeam_request_timeout_seconds"].default,
                ),
                "backup_objects_limit": current_app.config.get(
                    "VEEAM_BACKUP_OBJECTS_LIMIT",
                    Settings.model_fields["veeam_backup_objects_limit"].default,
                ),
                "verify_ssl": current_app.config.get(
                    "VEEAM_VERIFY_SSL",
                    Settings.model_fields["veeam_verify_ssl"].default,
                ),
            }
        settings = Settings.load()
        return {
            "timeout_seconds": settings.veeam_request_timeout_seconds,
            "backup_objects_limit": settings.veeam_backup_objects_limit,
            "verify_ssl": settings.veeam_verify_ssl,
        }

    def is_configured(self) -> bool:
        return self._timeout_seconds > 0

    def create_session(
        self,
        *,
        server_host: str,
        server_port: int,
        username: str,
        password: str,
        api_version: str,
        verify_ssl: bool | None = None,
    ) -> VeeamProviderSession:
        base_url = self._build_base_url(server_host=server_host, server_port=server_port)
        resolved_verify_ssl = self._verify_ssl if verify_ssl is None else bool(verify_ssl)
        access_token = self._request_access_token(
            base_url=base_url,
            username=username,
            password=password,
            api_version=api_version,
            verify_ssl=resolved_verify_ssl,
        )
        return VeeamProviderSession(
            base_url=base_url,
            access_token=access_token,
            api_version=api_version,
            verify_ssl=resolved_verify_ssl,
        )

    def fetch_backup_objects(self, *, session: VeeamProviderSession) -> list[dict[str, Any]]:
        return self._collect_paginated_items(
            url=self._build_backup_objects_url(base_url=session.base_url, limit=self._backup_objects_limit),
            access_token=session.access_token,
            api_version=session.api_version,
            verify_ssl=session.verify_ssl,
        )

    def match_backup_objects(
        self,
        *,
        backup_items: list[dict[str, Any]],
        match_machine_names: set[str] | None = None,
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
            backup_object_id = self._pick_string(backup_item, ("id", "backupObjectId", "backup_object_id"))
            if not backup_object_id:
                continue
            backup_machine_name = self._resolve_backup_machine_name(backup_item)
            if match_machine_names:
                normalized_backup_machine_name = normalize_machine_name(backup_machine_name)
                if not normalized_backup_machine_name:
                    backups_missing_machine_name += 1
                    if len(missing_machine_name_backup_ids_sample) < 20:
                        missing_machine_name_backup_ids_sample.append(backup_object_id)
                    backup_name = self._pick_string(backup_item, ("name", "jobName", "backupName"))
                    if backup_name and len(missing_machine_name_backup_names_sample) < 20:
                        missing_machine_name_backup_names_sample.append(backup_name)
                    continue
                if normalized_backup_machine_name not in match_machine_names:
                    backups_unmatched_total += 1
                    if len(unmatched_backup_ids_sample) < 20:
                        unmatched_backup_ids_sample.append(backup_object_id)
                    if backup_machine_name and len(unmatched_machine_names_sample) < 20:
                        unmatched_machine_names_sample.append(str(backup_machine_name))
                    continue
            backups_matched_total += 1
            if len(matched_backup_ids_sample) < 20:
                matched_backup_ids_sample.append(backup_object_id)
            matched_backup_objects.append(
                VeeamMatchedBackupObject(
                    backup_object_id=backup_object_id,
                    machine_name=backup_machine_name,
                    backup_item=dict(backup_item),
                )
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

    def fetch_restore_point_records(
        self,
        *,
        session: VeeamProviderSession,
        match_result: VeeamBackupObjectMatchResult,
    ) -> VeeamMachineBackupCollection:
        records: list[VeeamMachineBackupRecord] = []
        skipped_invalid = 0
        received_total = 0
        matched_backup_objects_total = len(match_result.matched_backup_objects)
        completed_backup_objects_total = 0
        timed_out_backup_objects_total = 0
        timed_out_backup_ids_sample: list[str] = []
        timed_out_machine_names_sample: list[str] = []

        for matched_backup_object in match_result.matched_backup_objects:
            failed_url = self._build_backup_restore_points_url(
                base_url=session.base_url,
                backup_object_id=matched_backup_object.backup_object_id,
            )
            try:
                restore_point_items = self._collect_paginated_items(
                    url=failed_url,
                    access_token=session.access_token,
                    api_version=session.api_version,
                    verify_ssl=session.verify_ssl,
                )
            except VeeamRequestTimeoutError:
                timed_out_backup_objects_total += 1
                if len(timed_out_backup_ids_sample) < 20:
                    timed_out_backup_ids_sample.append(matched_backup_object.backup_object_id)
                if matched_backup_object.machine_name and len(timed_out_machine_names_sample) < 20:
                    timed_out_machine_names_sample.append(str(matched_backup_object.machine_name))
                continue
            except Exception as exc:
                raise VeeamRestorePointsFetchError(
                    str(exc),
                    matched_backup_objects_total=matched_backup_objects_total,
                    completed_backup_objects_total=completed_backup_objects_total,
                    failed_backup_object_id=matched_backup_object.backup_object_id,
                    failed_machine_name=matched_backup_object.machine_name,
                    failed_url=failed_url,
                ) from exc
            received_total += len(restore_point_items)
            completed_backup_objects_total += 1
            for item in restore_point_items:
                record = self._normalize_backup_record(
                    item,
                    backup_item=matched_backup_object.backup_item,
                    backup_machine_name=matched_backup_object.machine_name,
                )
                if record is None:
                    skipped_invalid += 1
                    continue
                records.append(record)

        return VeeamMachineBackupCollection(
            records=records,
            received_total=received_total,
            snapshots_written_total=len(records),
            skipped_invalid=skipped_invalid,
            backups_received_total=match_result.backups_received_total,
            backups_matched_total=match_result.backups_matched_total,
            backups_unmatched_total=match_result.backups_unmatched_total,
            backups_missing_machine_name=match_result.backups_missing_machine_name,
            matched_backup_ids_sample=match_result.matched_backup_ids_sample,
            unmatched_backup_ids_sample=match_result.unmatched_backup_ids_sample,
            unmatched_machine_names_sample=match_result.unmatched_machine_names_sample,
            missing_machine_name_backup_ids_sample=match_result.missing_machine_name_backup_ids_sample,
            missing_machine_name_backup_names_sample=match_result.missing_machine_name_backup_names_sample,
            restore_points_backup_objects_total=matched_backup_objects_total,
            restore_points_backup_objects_completed=completed_backup_objects_total,
            timed_out_backup_objects_total=timed_out_backup_objects_total,
            timed_out_backup_ids_sample=timed_out_backup_ids_sample,
            timed_out_machine_names_sample=timed_out_machine_names_sample,
        )

    def list_machine_backups(
        self,
        *,
        server_host: str,
        server_port: int,
        username: str,
        password: str,
        api_version: str,
        match_machine_names: set[str] | None = None,
        verify_ssl: bool | None = None,
    ) -> VeeamMachineBackupCollection:
        session = self.create_session(
            server_host=server_host,
            server_port=server_port,
            username=username,
            password=password,
            api_version=api_version,
            verify_ssl=verify_ssl,
        )
        backup_items = self.fetch_backup_objects(session=session)
        match_result = self.match_backup_objects(
            backup_items=backup_items,
            match_machine_names=match_machine_names,
        )
        return self.fetch_restore_point_records(session=session, match_result=match_result)

    def fetch_backup_file_records(
        self,
        *,
        session: VeeamProviderSession,
        backup_ids: list[str],
    ) -> VeeamBackupFileCollection:
        normalized_backup_ids: list[str] = []
        for backup_id in backup_ids:
            normalized = str(backup_id or "").strip()
            if not normalized or normalized in normalized_backup_ids:
                continue
            normalized_backup_ids.append(normalized)

        records: list[VeeamBackupFileRecord] = []
        received_total = 0
        backup_ids_completed = 0
        timed_out_backup_ids_sample: list[str] = []
        failed_backup_ids_sample: list[str] = []
        failed_urls_sample: list[str] = []

        for backup_id in normalized_backup_ids:
            failed_url = self._build_backup_files_url(base_url=session.base_url, backup_id=backup_id)
            try:
                backup_file_items = self._collect_paginated_items(
                    url=failed_url,
                    access_token=session.access_token,
                    api_version=session.api_version,
                    verify_ssl=session.verify_ssl,
                )
            except VeeamRequestTimeoutError:
                if len(timed_out_backup_ids_sample) < 20:
                    timed_out_backup_ids_sample.append(backup_id)
                continue
            except Exception:
                if len(failed_backup_ids_sample) < 20:
                    failed_backup_ids_sample.append(backup_id)
                if len(failed_urls_sample) < 20:
                    failed_urls_sample.append(failed_url)
                continue

            received_total += len(backup_file_items)
            backup_ids_completed += 1
            for item in backup_file_items:
                record = self._normalize_backup_file_record(item, backup_id=backup_id)
                if record is not None:
                    records.append(record)

        return VeeamBackupFileCollection(
            records=records,
            received_total=received_total,
            backup_ids_total=len(normalized_backup_ids),
            backup_ids_completed=backup_ids_completed,
            timed_out_backup_ids_total=len(timed_out_backup_ids_sample),
            timed_out_backup_ids_sample=timed_out_backup_ids_sample,
            failed_backup_ids_total=len(failed_backup_ids_sample),
            failed_backup_ids_sample=failed_backup_ids_sample,
            failed_urls_sample=failed_urls_sample,
        )

    def _collect_paginated_items(
        self,
        *,
        url: str,
        access_token: str,
        api_version: str,
        verify_ssl: bool,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = url
        while next_url:
            payload = self._request_json(
                url=next_url,
                access_token=access_token,
                api_version=api_version,
                verify_ssl=verify_ssl,
            )
            page_items = self._parse_page_payload(payload)
            items.extend(page_items)
            next_url = self._resolve_next_url(base_url=url, current_url=next_url, payload=payload)
        return items

    @staticmethod
    def _build_base_url(*, server_host: str, server_port: int) -> str:
        host = str(server_host or "").strip()
        if host.startswith(("http://", "https://")):
            parsed = urlsplit(host)
            scheme = parsed.scheme or "https"
            netloc = parsed.netloc or parsed.path
            return f"{scheme}://{netloc}".rstrip("/")
        return f"https://{host}:{int(server_port)}"

    def _request_access_token(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        api_version: str,
        verify_ssl: bool,
    ) -> str:
        payload = urlencode(
            {
                "grant_type": "password",
                "username": username,
                "password": password,
            }
        ).encode("utf-8")
        request = Request(
            url=f"{base_url}{VEEAM_TOKEN_PATH}",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": VEEAM_ACCEPT_HEADER,
                "x-api-version": api_version,
            },
            data=payload,
            method="POST",
        )
        response_payload = self._read_json_response(request=request, verify_ssl=verify_ssl)
        if not isinstance(response_payload, dict):
            raise TypeError("Veeam token 响应格式不受支持")
        access_token = str(response_payload.get("access_token") or "").strip()
        if not access_token:
            raise ValueError("Veeam token 响应缺少 access_token")
        return access_token

    def _request_json(
        self,
        *,
        url: str,
        access_token: str,
        api_version: str,
        verify_ssl: bool,
    ) -> object:
        request = Request(
            url=url,
            headers={
                "Accept": VEEAM_ACCEPT_HEADER,
                "x-api-version": api_version,
                "Authorization": f"Bearer {access_token}",
            },
            method="GET",
        )
        return self._read_json_response(request=request, verify_ssl=verify_ssl)

    def _read_json_response(self, *, request: Request, verify_ssl: bool) -> object:
        context = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
        try:
            with self._opener(request, timeout=self._timeout_seconds, context=context) as response:
                payload_bytes = response.read()
        except TimeoutError as exc:
            raise VeeamRequestTimeoutError(
                f"Veeam API 请求超时: timeout={self._timeout_seconds}s url={request.full_url}"
            ) from exc
        except HTTPError as exc:
            raise RuntimeError(self._build_http_error_message(exc)) from exc
        except URLError as exc:
            if self._is_timeout_url_error(exc):
                raise VeeamRequestTimeoutError(
                    f"Veeam API 请求超时: timeout={self._timeout_seconds}s url={request.full_url}"
                ) from exc
            raise RuntimeError(self._build_url_error_message(url=request.full_url, error=exc)) from exc
        return json.loads(payload_bytes.decode("utf-8"))

    @staticmethod
    def _build_http_error_message(error: HTTPError) -> str:
        payload = getattr(error, "fp", None)
        body = ""
        if payload is not None:
            try:
                raw = payload.read()
            except Exception:
                raw = b""
            if isinstance(raw, bytes):
                body = raw.decode("utf-8", errors="replace").strip()[:300]
        message = f"Veeam API 请求失败: {error.code} {error.reason} url={error.url}"
        if body:
            message = f"{message} body={body}"
        return message

    @staticmethod
    def _build_url_error_message(*, url: str, error: URLError) -> str:
        reason = getattr(error, "reason", error)
        return f"Veeam API 网络连接失败: url={url} reason={reason}"

    @staticmethod
    def _is_timeout_url_error(error: URLError) -> bool:
        reason = getattr(error, "reason", None)
        if isinstance(reason, TimeoutError):
            return True
        if isinstance(reason, str) and "timed out" in reason.lower():
            return True
        return reason is not None and "timed out" in str(reason).lower()

    @staticmethod
    def _parse_page_payload(payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            data_value = payload.get("data")
            if isinstance(data_value, list):
                return [item for item in data_value if isinstance(item, dict)]
            if isinstance(data_value, dict):
                for key in ("items", "results"):
                    nested_items = data_value.get(key)
                    if isinstance(nested_items, list):
                        return [item for item in nested_items if isinstance(item, dict)]
            for key in ("data", "results", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        raise ValueError("Veeam 备份列表响应格式不受支持")

    @staticmethod
    def _build_backup_restore_points_url(*, base_url: str, backup_object_id: str) -> str:
        return f"{base_url}{VEEAM_BACKUP_OBJECTS_PATH}/{str(backup_object_id).strip()}/restorePoints"

    @staticmethod
    def _build_backup_objects_url(*, base_url: str, limit: int) -> str:
        return f"{base_url}{VEEAM_BACKUP_OBJECTS_PATH}?limit={int(limit)}"

    @staticmethod
    def _build_backup_files_url(*, base_url: str, backup_id: str) -> str:
        return f"{base_url}{VEEAM_BACKUPS_PATH}/{str(backup_id).strip()}/backupFiles"

    @staticmethod
    def _resolve_next_url(*, base_url: str, current_url: str, payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None

        direct_next = HttpVeeamProvider._extract_next_link(payload)
        if direct_next:
            return HttpVeeamProvider._normalize_next_url(base_url=base_url, next_url=direct_next)

        pagination_next = HttpVeeamProvider._resolve_next_url_from_pagination(
            current_url=current_url,
            payload=payload,
        )
        if pagination_next:
            return pagination_next
        return None

    @staticmethod
    def _extract_next_link(payload: dict[str, Any]) -> str | None:  # noqa: PLR0912
        for key in ("next", "nextLink", "next_link"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for container_key in ("data", "paging", "pagination", "links", "meta"):
            container = payload.get(container_key)
            if not isinstance(container, dict):
                continue
            for key in ("next", "nextLink", "next_link"):
                value = container.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    for href_key in ("href", "url"):
                        href_value = value.get(href_key)
                        if isinstance(href_value, str) and href_value.strip():
                            return href_value.strip()
            if container_key == "links":
                next_value = container.get("next")
                if isinstance(next_value, list):
                    for item in next_value:
                        if isinstance(item, dict):
                            href_value = item.get("href") or item.get("url")
                            if isinstance(href_value, str) and href_value.strip():
                                return href_value.strip()
        return None

    @staticmethod
    def _normalize_next_url(*, base_url: str, next_url: str) -> str:
        stripped = next_url.strip()
        if stripped.startswith(("http://", "https://")):
            return stripped
        resolved_base = urlsplit(base_url)
        if stripped.startswith("/"):
            return urlunsplit((resolved_base.scheme, resolved_base.netloc, stripped, "", ""))
        return f"{base_url.rstrip('/')}/{stripped.lstrip('/')}"

    @staticmethod
    def _resolve_next_url_from_pagination(*, current_url: str, payload: dict[str, Any]) -> str | None:
        pagination_candidates = [payload]
        for key in ("data", "paging", "pagination", "meta"):
            value = payload.get(key)
            if isinstance(value, dict):
                pagination_candidates.append(value)

        for candidate in pagination_candidates:
            next_url = HttpVeeamProvider._build_next_url_from_page_fields(current_url=current_url, payload=candidate)
            if next_url:
                return next_url
            next_url = HttpVeeamProvider._build_next_url_from_offset_fields(current_url=current_url, payload=candidate)
            if next_url:
                return next_url
        return None

    @staticmethod
    def _build_next_url_from_page_fields(*, current_url: str, payload: dict[str, Any]) -> str | None:
        page = HttpVeeamProvider._pick_int(payload, ("page", "pageNumber", "page_number", "currentPage", "current_page"))
        page_size = HttpVeeamProvider._pick_int(payload, ("pageSize", "page_size", "limit", "perPage", "per_page"))
        total = HttpVeeamProvider._pick_int(payload, ("total", "totalCount", "total_count", "count"))
        if page is None or page_size is None or total is None:
            return None
        if page <= 0 or page_size <= 0 or total <= page * page_size:
            return None

        parsed = urlsplit(current_url)
        query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
        for key in ("page", "pageSize", "page_size", "perPage", "per_page", "skip", "offset", "limit"):
            query_items.pop(key, None)
        next_page = page + 1
        query_items["page"] = str(next_page)
        if any(key in payload for key in ("pageSize", "page_size")):
            query_items["pageSize"] = str(page_size)
        elif "limit" in payload:
            query_items["limit"] = str(page_size)
        elif any(key in payload for key in ("perPage", "per_page")):
            query_items["perPage"] = str(page_size)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query_items), parsed.fragment))

    @staticmethod
    def _build_next_url_from_offset_fields(*, current_url: str, payload: dict[str, Any]) -> str | None:
        offset = HttpVeeamProvider._pick_int(payload, ("offset", "skip"))
        limit = HttpVeeamProvider._pick_int(payload, ("limit", "pageSize", "page_size"))
        total = HttpVeeamProvider._pick_int(payload, ("total", "totalCount", "total_count", "count"))
        if offset is None or limit is None or total is None:
            return None
        if offset < 0 or limit <= 0 or total <= offset + limit:
            return None

        parsed = urlsplit(current_url)
        query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
        for key in ("page", "pageSize", "page_size", "perPage", "per_page", "skip", "offset", "limit"):
            query_items.pop(key, None)
        if "skip" in payload and "offset" not in payload:
            query_items["skip"] = str(offset + limit)
        else:
            query_items["offset"] = str(offset + limit)
        query_items["limit"] = str(limit)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query_items), parsed.fragment))

    @staticmethod
    def _pick_int(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
        for key in keys:
            value = payload.get(key)
            if value is None or value == "":
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _normalize_backup_record(
        item: dict[str, Any],
        *,
        backup_item: dict[str, Any] | None = None,
        backup_machine_name: str | None = None,
    ) -> VeeamMachineBackupRecord | None:
        machine_name = backup_machine_name or HttpVeeamProvider._resolve_machine_name(item)
        backup_at = HttpVeeamProvider._resolve_backup_at(item)
        if not machine_name or backup_at is None:
            return None
        return VeeamMachineBackupRecord(
            machine_name=machine_name,
            backup_at=backup_at,
            backup_id=HttpVeeamProvider._pick_string(item, ("backupId", "backup_id"))
            or HttpVeeamProvider._pick_string(backup_item or {}, ("backupId", "backup_id")),
            backup_file_id=HttpVeeamProvider._pick_string(item, ("backupFileId", "backup_file_id")),
            job_name=HttpVeeamProvider._pick_string(item, ("jobName", "job_name", "backupName", "backup_name"))
            or HttpVeeamProvider._pick_string(backup_item or {}, ("jobName", "job_name", "backupName", "backup_name")),
            restore_point_name=HttpVeeamProvider._pick_string(
                item,
                ("restorePointName", "restore_point_name", "name"),
            ),
            source_record_id=HttpVeeamProvider._pick_string(item, ("id", "restorePointId", "restore_point_id")),
            restore_point_size_bytes=HttpVeeamProvider._pick_nested_int(
                item,
                ("restorePointSizeBytes", "restore_point_size_bytes", "sizeBytes", "size_bytes"),
            ),
            backup_chain_size_bytes=HttpVeeamProvider._pick_nested_int(
                item,
                ("backupChainSizeBytes", "backup_chain_size_bytes", "totalSizeBytes", "total_size_bytes"),
            ) or HttpVeeamProvider._pick_nested_int(
                backup_item or {},
                ("backupChainSizeBytes", "backup_chain_size_bytes", "totalSizeBytes", "total_size_bytes", "sizeBytes", "size_bytes", "size"),
            ),
            restore_point_count=HttpVeeamProvider._pick_nested_int(
                item,
                ("restorePointCount", "restore_point_count", "restorePointsCount", "restore_points_count"),
            ) or HttpVeeamProvider._pick_nested_int(
                backup_item or {},
                ("restorePointCount", "restore_point_count", "restorePointsCount", "restore_points_count", "pointCount"),
            ),
            raw_payload=dict(item),
        )

    @staticmethod
    def _normalize_backup_file_record(item: dict[str, Any], *, backup_id: str) -> VeeamBackupFileRecord | None:
        resolved_backup_id = HttpVeeamProvider._pick_string(item, ("backupId", "backup_id")) or str(backup_id).strip()
        if not resolved_backup_id:
            return None
        creation_time = HttpVeeamProvider._pick_string(item, ("creationTime", "creation_time"))
        resolved_backup_at = time_utils.to_utc(creation_time) if creation_time else None
        return VeeamBackupFileRecord(
            backup_id=resolved_backup_id,
            backup_file_id=HttpVeeamProvider._pick_string(item, ("backupFileId", "backup_file_id", "id")),
            object_id=HttpVeeamProvider._pick_string(item, ("objectId", "object_id")),
            restore_point_ids=HttpVeeamProvider._pick_string_list(item, ("restorePointIds", "restore_point_ids")),
            data_size_bytes=HttpVeeamProvider._pick_nested_int(
                item,
                ("dataSize", "data_size", "dataSizeBytes", "data_size_bytes"),
            ),
            backup_size_bytes=HttpVeeamProvider._pick_nested_int(
                item,
                ("backupSize", "backup_size", "backupSizeBytes", "backup_size_bytes"),
            ),
            dedup_ratio=HttpVeeamProvider._pick_nested_int(item, ("dedupRatio", "dedup_ratio")),
            compress_ratio=HttpVeeamProvider._pick_nested_int(item, ("compressRatio", "compress_ratio")),
            backup_at=resolved_backup_at,
            raw_payload=dict(item),
        )

    @staticmethod
    def _resolve_backup_machine_name(item: dict[str, Any]) -> str | None:
        return HttpVeeamProvider._pick_string(
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

    @staticmethod
    def _resolve_machine_name(item: dict[str, Any]) -> str | None:
        direct = HttpVeeamProvider._pick_string(
            item,
            ("machineName", "machine_name", "objectName", "object_name", "workloadName", "workload_name"),
        )
        if direct:
            return direct
        raw_name = HttpVeeamProvider._pick_string(item, ("name",))
        if not raw_name:
            return None
        if "@" in raw_name:
            return raw_name.split("@", 1)[0].strip() or None
        return raw_name

    @staticmethod
    def _resolve_backup_at(item: dict[str, Any]) -> datetime | None:
        for key in (
            "backupTime",
            "backup_time",
            "creationTime",
            "creation_time",
            "restorePointDate",
            "restore_point_date",
            "latestBackupAt",
            "latest_backup_at",
        ):
            value = item.get(key)
            if not value:
                continue
            resolved = time_utils.to_utc(str(value))
            if resolved is not None:
                return resolved
        return None

    @staticmethod
    def _pick_string(item: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _pick_string_list(item: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
        for key in keys:
            value = item.get(key)
            if not isinstance(value, list):
                continue
            normalized = [
                str(entry).strip()
                for entry in value
                if isinstance(entry, str) and str(entry).strip()
            ]
            if normalized:
                return normalized
        return []

    @staticmethod
    def _pick_nested_int(payload: object, keys: tuple[str, ...]) -> int | None:
        for key, value in HttpVeeamProvider._walk_key_values(payload):
            if key not in keys:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _walk_key_values(payload: object) -> list[tuple[str, object]]:
        pairs: list[tuple[str, object]] = []

        def _walk(value: object) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    pairs.append((str(key), item))
                    _walk(item)
            elif isinstance(value, list):
                for item in value:
                    _walk(item)

        _walk(payload)
        return pairs
