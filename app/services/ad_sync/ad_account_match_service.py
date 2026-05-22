"""AD 账户匹配服务."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import func

from app.models.ad_domain_config import AdDomainConfig
from app.models.instance_account import InstanceAccount
from app.services.ad_sync.ldap_provider import AdPrincipal
from app.utils.time_utils import time_utils


@dataclass(frozen=True, slots=True)
class AdDomainMatchResult:
    """单个 AD 域匹配结果."""

    total: int
    normal: int
    disabled: int
    orphaned: int
    updated: int


class AdAccountMatchService:
    """将 AD 主体状态更新到 SQL Server InstanceAccount 风险标记."""

    SUPPORTED_OWNER_TYPES = ("instance", "sqlserver_ag")

    def match_and_update(
        self,
        *,
        domain_config: AdDomainConfig,
        principals: dict[str, AdPrincipal],
    ) -> AdDomainMatchResult:
        """匹配并更新该域的 SQL Server 域账户."""
        accounts = self._list_domain_accounts(domain_config)
        now = time_utils.now()
        normal = disabled = orphaned = updated = 0

        normalized_principals = {str(key).strip().lower(): value for key, value in principals.items()}
        for account in accounts:
            name_part = self._extract_name_part(str(account.username), str(domain_config.netbios_name))
            principal = normalized_principals.get(name_part)
            old_state = (account.ad_domain_config_id, account.ad_disabled_at, account.ad_orphaned_at)
            account.ad_domain_config_id = domain_config.id

            if principal is None:
                orphaned += 1
                account.ad_disabled_at = None
                if account.ad_orphaned_at is None:
                    account.ad_orphaned_at = now
            elif principal.object_kind == "user" and principal.is_disabled is True:
                disabled += 1
                if account.ad_disabled_at is None:
                    account.ad_disabled_at = now
                account.ad_orphaned_at = None
            else:
                normal += 1
                account.ad_disabled_at = None
                account.ad_orphaned_at = None

            if old_state != (account.ad_domain_config_id, account.ad_disabled_at, account.ad_orphaned_at):
                updated += 1

        return AdDomainMatchResult(
            total=len(accounts),
            normal=normal,
            disabled=disabled,
            orphaned=orphaned,
            updated=updated,
        )

    @classmethod
    def _list_domain_accounts(cls, domain_config: AdDomainConfig) -> list[InstanceAccount]:
        prefix = f"{str(domain_config.netbios_name).strip().lower()}\\"
        return cast(
            list[InstanceAccount],
            InstanceAccount.query.filter(
                func.lower(InstanceAccount.db_type) == "sqlserver",
                func.lower(InstanceAccount.username).like(f"{prefix}%"),
                InstanceAccount.owner_type.in_(cls.SUPPORTED_OWNER_TYPES),
            ).all(),
        )

    @staticmethod
    def _extract_name_part(username: str, netbios_name: str) -> str:
        prefix = f"{netbios_name}\\"
        if username.lower().startswith(prefix.lower()):
            return username[len(prefix) :].strip().lower()
        if "\\" in username:
            return username.split("\\", 1)[1].strip().lower()
        return username.strip().lower()
