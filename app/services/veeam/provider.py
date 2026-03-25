"""Veeam Provider 抽象与 HTTP 实现."""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from flask import current_app, has_app_context

from app.settings import Settings
from app.utils.time_utils import time_utils

VEEAM_TOKEN_PATH = "/api/oauth2/token"
VEEAM_RESTORE_POINTS_PATH = "/api/v1/restorePoints"
VEEAM_ACCEPT_HEADER = "application/json"


def _default_open(request: Request, *, timeout: int, context: ssl.SSLContext):
    return urlopen(request, timeout=timeout, context=context)


@dataclass(frozen=True, slots=True)
class VeeamMachineBackupRecord:
    """标准化后的 Veeam 机器备份记录."""

    machine_name: str
    backup_at: datetime
    job_name: str | None
    restore_point_name: str | None
    source_record_id: str | None
    raw_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class VeeamMachineBackupCollection:
    """本次备份拉取的标准化结果."""

    records: list[VeeamMachineBackupRecord]
    received_total: int
    snapshots_written_total: int
    skipped_invalid: int


class VeeamProvider(Protocol):
    """Veeam 数据拉取接口."""

    def is_configured(self) -> bool:
        """返回 provider 是否已具备真实可用实现."""

    def list_machine_backups(
        self,
        *,
        server_host: str,
        server_port: int,
        username: str,
        password: str,
        api_version: str,
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
                "verify_ssl": current_app.config.get(
                    "VEEAM_VERIFY_SSL",
                    Settings.model_fields["veeam_verify_ssl"].default,
                ),
            }
        settings = Settings.load()
        return {
            "timeout_seconds": settings.veeam_request_timeout_seconds,
            "verify_ssl": settings.veeam_verify_ssl,
        }

    def is_configured(self) -> bool:
        return self._timeout_seconds > 0

    def list_machine_backups(
        self,
        *,
        server_host: str,
        server_port: int,
        username: str,
        password: str,
        api_version: str,
        verify_ssl: bool | None = None,
    ) -> VeeamMachineBackupCollection:
        base_url = self._build_base_url(server_host=server_host, server_port=server_port)
        resolved_verify_ssl = self._verify_ssl if verify_ssl is None else bool(verify_ssl)
        access_token = self._request_access_token(
            base_url=base_url,
            username=username,
            password=password,
            api_version=api_version,
            verify_ssl=resolved_verify_ssl,
        )
        payload = self._request_json(
            url=f"{base_url}{VEEAM_RESTORE_POINTS_PATH}",
            access_token=access_token,
            api_version=api_version,
            verify_ssl=resolved_verify_ssl,
        )
        page_items = self._parse_page_payload(payload)
        received_total = len(page_items)
        records: list[VeeamMachineBackupRecord] = []
        skipped_invalid = 0
        for item in page_items:
            record = self._normalize_backup_record(item)
            if record is None:
                skipped_invalid += 1
                continue
            records.append(record)
        return VeeamMachineBackupCollection(
            records=records,
            received_total=received_total,
            snapshots_written_total=len(records),
            skipped_invalid=skipped_invalid,
        )

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
            raise ValueError("Veeam token 响应格式不受支持")
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
        except HTTPError as exc:
            raise RuntimeError(self._build_http_error_message(exc)) from exc
        except URLError as exc:
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
    def _parse_page_payload(payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("data", "results", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        raise ValueError("Veeam 备份列表响应格式不受支持")

    @staticmethod
    def _normalize_backup_record(item: dict[str, Any]) -> VeeamMachineBackupRecord | None:
        machine_name = HttpVeeamProvider._resolve_machine_name(item)
        backup_at = HttpVeeamProvider._resolve_backup_at(item)
        if not machine_name or backup_at is None:
            return None
        return VeeamMachineBackupRecord(
            machine_name=machine_name,
            backup_at=backup_at,
            job_name=HttpVeeamProvider._pick_string(item, ("jobName", "job_name", "backupName", "backup_name")),
            restore_point_name=HttpVeeamProvider._pick_string(
                item,
                ("restorePointName", "restore_point_name", "name"),
            ),
            source_record_id=HttpVeeamProvider._pick_string(item, ("id", "restorePointId", "restore_point_id")),
            raw_payload=dict(item),
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
