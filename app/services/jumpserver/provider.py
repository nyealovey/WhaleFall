"""JumpServer Provider 抽象与 v3 HTTP 实现.

说明:
- v1 认证方式约定为 Access Key, 对应凭据中的 username/password.
- 按 JumpServer v3 文档使用 HTTP Signature 访问 `/api/v1/assets/assets/`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import ssl
from dataclasses import dataclass
from email.utils import formatdate
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from flask import current_app, has_app_context

from app.core.constants.database_types import DatabaseType
from app.settings import Settings
from app.utils.database_type_utils import normalize_database_type

JUMPSERVER_DATABASE_ASSETS_PATH = "/api/v1/assets/assets/"
JUMPSERVER_PAGE_LIMIT = 200
JUMPSERVER_ACCEPT_HEADER = "application/json"
JUMPSERVER_SIGNATURE_HEADERS = "(request-target) accept date"


def _default_open(request: Request, *, timeout: int, context: ssl.SSLContext):
    return urlopen(request, timeout=timeout, context=context)


@dataclass(frozen=True, slots=True)
class JumpServerDatabaseAsset:
    """标准化后的 JumpServer 数据库资产."""

    external_id: str
    name: str
    db_type: str
    host: str
    port: int
    raw_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class JumpServerAssetCollection:
    """本次资产拉取的标准化结果."""

    assets: list[JumpServerDatabaseAsset]
    received_total: int
    supported_total: int
    skipped_unsupported: int
    skipped_invalid: int


class JumpServerProvider(Protocol):
    """JumpServer 资产拉取接口."""

    def is_configured(self) -> bool:
        """返回 provider 是否已具备真实可用实现."""

    def list_database_assets(
        self,
        *,
        base_url: str,
        access_key_id: str,
        access_key_secret: str,
        org_id: str | None = None,
        verify_ssl: bool | None = None,
    ) -> JumpServerAssetCollection:
        """返回数据库类资产列表与统计."""


class DeferredJumpServerProvider:
    """占位 provider.

    保留该类是为了兼容旧导出；默认实现已切换为真实 HTTP Provider。
    """

    def is_configured(self) -> bool:
        return False

    def list_database_assets(
        self,
        *,
        base_url: str,
        access_key_id: str,
        access_key_secret: str,
        org_id: str | None = None,
        verify_ssl: bool | None = None,
    ) -> JumpServerAssetCollection:
        _ = (org_id, verify_ssl)
        raise NotImplementedError("JumpServer Provider 尚未接入真实 API")


class HttpJumpServerProvider:
    """JumpServer v3 HTTP Provider."""

    def __init__(
        self,
        *,
        org_id: str | None = None,
        timeout_seconds: int | None = None,
        verify_ssl: bool | None = None,
        opener=_default_open,
    ) -> None:
        resolved_settings = self._resolve_settings()
        self._org_id = str(org_id or resolved_settings["org_id"]).strip()
        self._timeout_seconds = int(timeout_seconds or resolved_settings["timeout_seconds"])
        self._verify_ssl = bool(resolved_settings["verify_ssl"] if verify_ssl is None else verify_ssl)
        self._opener = opener

    @staticmethod
    def _resolve_settings() -> dict[str, object]:
        if has_app_context():
            return {
                "org_id": current_app.config.get(
                    "JUMPSERVER_ORG_ID", Settings.model_fields["jumpserver_org_id"].default
                ),
                "timeout_seconds": current_app.config.get(
                    "JUMPSERVER_REQUEST_TIMEOUT_SECONDS",
                    Settings.model_fields["jumpserver_request_timeout_seconds"].default,
                ),
                "verify_ssl": current_app.config.get(
                    "JUMPSERVER_VERIFY_SSL",
                    Settings.model_fields["jumpserver_verify_ssl"].default,
                ),
            }
        settings = Settings.load()
        return {
            "org_id": settings.jumpserver_org_id,
            "timeout_seconds": settings.jumpserver_request_timeout_seconds,
            "verify_ssl": settings.jumpserver_verify_ssl,
        }

    def is_configured(self) -> bool:
        return self._timeout_seconds > 0

    def list_database_assets(
        self,
        *,
        base_url: str,
        access_key_id: str,
        access_key_secret: str,
        org_id: str | None = None,
        verify_ssl: bool | None = None,
    ) -> JumpServerAssetCollection:
        assets: list[JumpServerDatabaseAsset] = []
        received_total = 0
        skipped_unsupported = 0
        skipped_invalid = 0
        next_url = self._build_initial_url(base_url)
        while next_url:
            payload = self._request_json(
                url=next_url,
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                org_id=org_id,
                verify_ssl=verify_ssl,
            )
            page_items, raw_next_url = self._parse_page_payload(payload)
            received_total += len(page_items)
            for item in page_items:
                asset, reason = self._normalize_asset(item)
                if asset is not None:
                    assets.append(asset)
                    continue
                if reason == "unsupported":
                    skipped_unsupported += 1
                else:
                    skipped_invalid += 1
            next_url = self._resolve_next_url(base_url, raw_next_url)
        return JumpServerAssetCollection(
            assets=assets,
            received_total=received_total,
            supported_total=len(assets),
            skipped_unsupported=skipped_unsupported,
            skipped_invalid=skipped_invalid,
        )

    @staticmethod
    def _build_initial_url(base_url: str) -> str:
        resolved_base_url = HttpJumpServerProvider._normalize_base_url(base_url)
        return f"{resolved_base_url}{JUMPSERVER_DATABASE_ASSETS_PATH}?limit={JUMPSERVER_PAGE_LIMIT}&offset=0"

    @staticmethod
    def _resolve_next_url(base_url: str, next_url: object) -> str | None:
        if not isinstance(next_url, str) or not next_url.strip():
            return None
        stripped = next_url.strip()
        if stripped.startswith(("http://", "https://")):
            return stripped
        return urljoin(f"{HttpJumpServerProvider._normalize_base_url(base_url)}/", stripped.lstrip("/"))

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        parsed = urlsplit(str(base_url or "").strip())
        if not parsed.scheme or not parsed.netloc:
            return str(base_url or "").rstrip("/")
        normalized_path = parsed.path.rstrip("/")
        if normalized_path.endswith("/api/docs"):
            normalized_path = normalized_path[: -len("/api/docs")]
        return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"

    def _request_json(
        self,
        *,
        url: str,
        access_key_id: str,
        access_key_secret: str,
        org_id: str | None = None,
        verify_ssl: bool | None = None,
    ) -> object:
        request_target = self._build_request_target(url)
        date_header = formatdate(usegmt=True)
        signing_string = "\n".join(
            (
                f"(request-target): {request_target}",
                f"accept: {JUMPSERVER_ACCEPT_HEADER}",
                f"date: {date_header}",
            )
        )
        signature = base64.b64encode(
            hmac.new(
                str(access_key_secret).encode("utf-8"),
                signing_string.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        authorization = (
            f'Signature keyId="{access_key_id}",'
            'algorithm="hmac-sha256",'
            f'headers="{JUMPSERVER_SIGNATURE_HEADERS}",'
            f'signature="{signature}"'
        )
        request = Request(
            url=url,
            headers={
                "Accept": JUMPSERVER_ACCEPT_HEADER,
                "Date": date_header,
                "X-JMS-ORG": str(org_id or self._org_id).strip(),
                "Authorization": authorization,
            },
            method="GET",
        )
        resolved_verify_ssl = self._verify_ssl if verify_ssl is None else bool(verify_ssl)
        context = ssl.create_default_context() if resolved_verify_ssl else ssl._create_unverified_context()
        try:
            with self._opener(request, timeout=self._timeout_seconds, context=context) as response:
                payload_bytes = response.read()
        except HTTPError as exc:
            raise RuntimeError(self._build_http_error_message(exc)) from exc
        except URLError as exc:
            raise RuntimeError(self._build_url_error_message(url=url, error=exc)) from exc
        return json.loads(payload_bytes.decode("utf-8"))

    @staticmethod
    def _build_http_error_message(error: HTTPError) -> str:
        response_body = HttpJumpServerProvider._read_http_error_body(error)
        message = f"JumpServer API 请求失败: {error.code} {error.reason} url={error.url}"
        if response_body:
            message = f"{message} body={response_body}"
        return message

    @staticmethod
    def _read_http_error_body(error: HTTPError) -> str:
        payload = getattr(error, "fp", None)
        if payload is None:
            return ""
        try:
            raw = payload.read()
        except Exception:
            return ""
        if not isinstance(raw, bytes):
            return ""
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return ""
        return text[:300]

    @staticmethod
    def _build_url_error_message(*, url: str, error: URLError) -> str:
        reason = getattr(error, "reason", error)
        return f"JumpServer API 网络连接失败: url={url} reason={reason}"

    @staticmethod
    def _build_request_target(url: str) -> str:
        parsed = urlsplit(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return f"get {path}"

    @staticmethod
    def _parse_page_payload(payload: object) -> tuple[list[dict[str, Any]], object]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)], None
        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list):
                return [item for item in results if isinstance(item, dict)], payload.get("next")
        raise ValueError("JumpServer 资产列表响应格式不受支持")

    @staticmethod
    def _normalize_asset(item: dict[str, Any]) -> tuple[JumpServerDatabaseAsset | None, str]:
        db_type = HttpJumpServerProvider._resolve_db_type(item)
        if db_type is None:
            return None, "unsupported"

        external_id = HttpJumpServerProvider._pick_string(item, ("id", "uuid"))
        name = HttpJumpServerProvider._pick_string(item, ("name",))
        host = HttpJumpServerProvider._pick_string(item, ("address", "ip", "ip_address", "host", "hostname"))
        port = HttpJumpServerProvider._resolve_port(item, db_type=db_type)
        if not external_id or not name or not host or port is None:
            return None, "invalid"

        return (
            JumpServerDatabaseAsset(
                external_id=external_id,
                name=name,
                db_type=db_type,
                host=host,
                port=port,
                raw_payload=dict(item),
            ),
            "supported",
        )

    @staticmethod
    def _resolve_db_type(item: dict[str, Any]) -> str | None:
        def _map_candidate(candidate: str) -> str | None:
            normalized = normalize_database_type(candidate)
            if normalized == "mariadb":
                return DatabaseType.MYSQL
            if normalized in DatabaseType.RELATIONAL:
                return normalized

            lowered = candidate.strip().lower()
            alias_rules = (
                (("mariadb", "mysql"), DatabaseType.MYSQL),
                (("postgres",), DatabaseType.POSTGRESQL),
                (("sql server", "mssql"), DatabaseType.SQLSERVER),
                (("oracle",), DatabaseType.ORACLE),
            )
            for keywords, target in alias_rules:
                if any(keyword in lowered for keyword in keywords):
                    return target
            return None

        platform = item.get("platform")
        candidates: list[str] = []
        if isinstance(platform, dict):
            for key in ("name", "type", "slug"):
                value = platform.get(key)
                if isinstance(value, str) and value.strip():
                    candidates.append(value)
        for key in ("db_type", "database_type", "platform_name", "protocol", "type"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value)

        for candidate in candidates:
            mapped = _map_candidate(candidate)
            if mapped is not None:
                return mapped
        return None

    @staticmethod
    def _resolve_port(item: dict[str, Any], *, db_type: str) -> int | None:
        for key in ("port", "protocol_port", "service_port"):
            value = item.get(key)
            try:
                if value is not None:
                    return int(value)
            except (TypeError, ValueError):
                continue
        default_ports = {
            DatabaseType.MYSQL: 3306,
            DatabaseType.POSTGRESQL: 5432,
            DatabaseType.SQLSERVER: 1433,
            DatabaseType.ORACLE: 1521,
        }
        return default_ports.get(db_type)

    @staticmethod
    def _pick_string(item: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            resolved = str(value).strip()
            if resolved:
                return resolved
        return None
