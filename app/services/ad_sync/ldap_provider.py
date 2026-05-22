"""AD LDAP provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ldap3 import ALL, Connection, Server, Tls  # type: ignore[import-untyped]

from app.core.exceptions import ValidationError
from app.models.ad_domain_config import AdDomainConfig
from app.schemas.ad_domain_config import validate_ad_base_dn
from app.utils.structlog_config import log_warning

UF_ACCOUNTDISABLE = 0x0002
LDAP_PAGED_SIZE = 500
LDAP_PAGED_RESULT_CONTROL = "1.2.840.113556.1.4.319"


@dataclass(frozen=True, slots=True)
class AdPrincipal:
    """AD 中可匹配 SQL Server 登录名的用户或组主体."""

    sam_account_name: str
    object_kind: str
    is_disabled: bool | None
    attributes: dict[str, object]


@dataclass(frozen=True, slots=True)
class AdPrincipalsFetchResult:
    """AD 主体拉取结果和计数."""

    principals: dict[str, AdPrincipal]
    users_total: int
    groups_total: int

    @property
    def principals_total(self) -> int:
        return self.users_total + self.groups_total


class LdapProvider:
    """连接 AD 并拉取可匹配的用户/组主体."""

    def fetch_principals(self, config: AdDomainConfig) -> dict[str, AdPrincipal]:
        """拉取域内用户/组,返回 lower(sAMAccountName) 映射."""
        return self.fetch_principals_with_stats(config).principals

    def fetch_principals_with_stats(self, config: AdDomainConfig) -> AdPrincipalsFetchResult:
        """拉取域内用户/组,返回主体映射和分类型计数."""
        controllers = self._normalize_controllers(config.domain_controllers)
        if not controllers:
            raise ValidationError("AD 域配置缺少域控地址")
        credential = getattr(config, "credential", None)
        if credential is None:
            raise ValidationError("AD 域配置缺少 LDAP 凭据")
        try:
            base_dn = validate_ad_base_dn(str(config.base_dn))
        except ValueError as exc:
            raise ValidationError(str(exc)) from None

        last_error: Exception | None = None
        for controller in controllers:
            ldap_host = controller
            try:
                tls = Tls(validate=0) if config.verify_ssl is False else None
                server = Server(
                    controller,
                    port=int(config.ldap_port),
                    use_ssl=bool(config.use_ssl),
                    get_info=ALL,
                    tls=tls,
                )
                ldap_host = str(getattr(server, "host", controller))
                connection = Connection(
                    server,
                    user=str(credential.username),
                    password=credential.get_plain_password(),
                    auto_bind=True,
                    auto_referrals=False,
                    receive_timeout=30,
                )
                try:
                    return self._fetch_with_connection(connection, base_dn)
                finally:
                    connection.unbind()
            except Exception as exc:
                last_error = exc
                log_warning(
                    "AD 域控连接失败,尝试下一个域控",
                    module="ad_sync",
                    controller=controller,
                    ldap_host=ldap_host,
                    port=int(config.ldap_port),
                    use_ssl=bool(config.use_ssl),
                    verify_ssl=bool(config.verify_ssl) if config.verify_ssl is not None else None,
                    error=str(exc),
                )
                continue

        detail = f"域控全部连接失败: controllers={controllers}, port={config.ldap_port}, use_ssl={config.use_ssl}, verify_ssl={config.verify_ssl}"
        if last_error is not None:
            detail = f"{detail}, error={last_error}"
        raise RuntimeError(detail)

    @classmethod
    def _fetch_with_connection(cls, connection: Any, base_dn: str) -> AdPrincipalsFetchResult:
        principals: dict[str, AdPrincipal] = {}
        users_total = cls._search_principals(
            connection,
            base_dn,
            "(&(objectClass=user)(objectCategory=person))",
            object_kind="user",
            target=principals,
        )
        groups_total = cls._search_principals(
            connection,
            base_dn,
            "(objectClass=group)",
            object_kind="group",
            target=principals,
        )
        return AdPrincipalsFetchResult(principals=principals, users_total=users_total, groups_total=groups_total)

    @classmethod
    def _search_principals(
        cls,
        connection: Any,
        base_dn: str,
        search_filter: str,
        *,
        object_kind: str,
        target: dict[str, AdPrincipal],
    ) -> int:
        attributes = [
            "sAMAccountName",
            "userAccountControl",
            "objectClass",
            "displayName",
            "mail",
            "whenChanged",
            "distinguishedName",
        ]
        count = 0
        cookie: bytes | str | None = None
        while True:
            search_ok = connection.search(
                base_dn,
                search_filter,
                search_scope="SUBTREE",
                attributes=attributes,
                paged_size=LDAP_PAGED_SIZE,
                paged_cookie=cookie,
            )
            if search_ok is False:
                raise RuntimeError(f"LDAP 查询失败: {cls._search_error_detail(connection)}")
            count += cls._consume_entries(connection, object_kind=object_kind, target=target)
            next_cookie = cls._paged_cookie(connection)
            if not next_cookie:
                return count
            if next_cookie == cookie:
                raise RuntimeError("LDAP 查询失败: paged cookie 未推进")
            cookie = next_cookie

    @classmethod
    def _consume_entries(cls, connection: Any, *, object_kind: str, target: dict[str, AdPrincipal]) -> int:
        count = 0
        for entry in list(getattr(connection, "entries", []) or []):
            data = entry.entry_attributes_as_dict
            raw_name = cls._first_value(data.get("sAMAccountName"))
            if not raw_name:
                continue
            disabled = cls._disabled_from_uac(data.get("userAccountControl")) if object_kind == "user" else None
            target[raw_name.lower()] = AdPrincipal(
                sam_account_name=raw_name,
                object_kind=object_kind,
                is_disabled=disabled,
                attributes={key: value for key, value in data.items() if key != "userAccountControl"},
            )
            count += 1
        return count

    @staticmethod
    def _paged_cookie(connection: Any) -> bytes | str | None:
        result = getattr(connection, "result", None)
        if not isinstance(result, dict):
            return None
        controls = result.get("controls")
        if not isinstance(controls, dict):
            return None
        paged = controls.get(LDAP_PAGED_RESULT_CONTROL)
        if not isinstance(paged, dict):
            return None
        value = paged.get("value")
        if not isinstance(value, dict):
            return None
        cookie = value.get("cookie")
        return cookie if cookie else None

    @staticmethod
    def _normalize_controllers(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @staticmethod
    def _first_value(value: object) -> str:
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value or "").strip()

    @staticmethod
    def _search_error_detail(connection: Any) -> str:
        result = getattr(connection, "result", None)
        if not isinstance(result, dict):
            return "unknown"
        parts: list[str] = []
        for key in ("description", "message"):
            value = str(result.get(key) or "").strip()
            if value:
                parts.append(f"{key}={value}")
        referrals = result.get("referrals")
        if referrals:
            parts.append(f"referrals={referrals}")
        return ", ".join(parts) if parts else "unknown"

    @classmethod
    def _disabled_from_uac(cls, value: object) -> bool:
        if isinstance(value, list):
            value = value[0] if value else 0
        try:
            uac = int(str(value or 0))
        except (TypeError, ValueError):
            uac = 0
        return bool(uac & UF_ACCOUNTDISABLE)
