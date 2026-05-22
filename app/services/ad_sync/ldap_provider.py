"""AD LDAP provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ldap3 import ALL, Connection, Server, Tls  # type: ignore[import-untyped]

from app.core.exceptions import ValidationError
from app.models.ad_domain_config import AdDomainConfig
from app.utils.structlog_config import log_warning

UF_ACCOUNTDISABLE = 0x0002


@dataclass(frozen=True, slots=True)
class AdPrincipal:
    """AD 中可匹配 SQL Server 登录名的用户或组主体."""

    sam_account_name: str
    object_kind: str
    is_disabled: bool | None
    attributes: dict[str, object]


class LdapProvider:
    """连接 AD 并拉取可匹配的用户/组主体."""

    def fetch_principals(self, config: AdDomainConfig) -> dict[str, AdPrincipal]:
        """拉取域内用户/组,返回 lower(sAMAccountName) 映射."""
        controllers = self._normalize_controllers(config.domain_controllers)
        if not controllers:
            raise ValidationError("AD 域配置缺少域控地址")
        credential = getattr(config, "credential", None)
        if credential is None:
            raise ValidationError("AD 域配置缺少 LDAP 凭据")

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
                    receive_timeout=30,
                )
                try:
                    return self._fetch_with_connection(connection, str(config.base_dn))
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
    def _fetch_with_connection(cls, connection: Any, base_dn: str) -> dict[str, AdPrincipal]:
        principals: dict[str, AdPrincipal] = {}
        cls._search_principals(
            connection,
            base_dn,
            "(&(objectClass=user)(objectCategory=person))",
            object_kind="user",
            target=principals,
        )
        cls._search_principals(connection, base_dn, "(objectClass=group)", object_kind="group", target=principals)
        return principals

    @classmethod
    def _search_principals(
        cls,
        connection: Any,
        base_dn: str,
        search_filter: str,
        *,
        object_kind: str,
        target: dict[str, AdPrincipal],
    ) -> None:
        attributes = ["sAMAccountName", "userAccountControl", "objectClass", "displayName", "mail", "whenChanged", "distinguishedName"]
        connection.search(base_dn, search_filter, attributes=attributes)
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

    @classmethod
    def _disabled_from_uac(cls, value: object) -> bool:
        if isinstance(value, list):
            value = value[0] if value else 0
        try:
            uac = int(str(value or 0))
        except (TypeError, ValueError):
            uac = 0
        return bool(uac & UF_ACCOUNTDISABLE)
