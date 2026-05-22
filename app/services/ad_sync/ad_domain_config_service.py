"""AD 域配置管理服务."""

from __future__ import annotations

from app import db
from app.core.exceptions import NotFoundError, ValidationError
from app.models.ad_domain_config import AdDomainConfig
from app.repositories.ad_domain_config_repository import AdDomainConfigRepository
from app.repositories.credentials_repository import CredentialsRepository
from app.schemas.ad_domain_config import AdDomainConfigPayload
from app.services.ad_sync.ldap_provider import LdapProvider


class AdDomainConfigService:
    """管理 AD 域配置."""

    def __init__(
        self,
        *,
        repository: AdDomainConfigRepository | None = None,
        credentials_repository: CredentialsRepository | None = None,
        provider: LdapProvider | None = None,
    ) -> None:
        self._repository = repository or AdDomainConfigRepository()
        self._credentials_repository = credentials_repository or CredentialsRepository()
        self._provider = provider or LdapProvider()

    def list_configs(self) -> list[dict[str, object]]:
        return [self._serialize_config(config) for config in self._repository.list_configs()]

    def create(self, payload: AdDomainConfigPayload) -> AdDomainConfig:
        self._ensure_credential(payload.credential_id)
        self._ensure_netbios_available(payload.netbios_name, exclude_id=None, is_enabled=payload.is_enabled)
        config = AdDomainConfig(**payload.model_dump())
        self._repository.add(config)
        db.session.commit()
        return config

    def update(self, config_id: int, payload: AdDomainConfigPayload) -> AdDomainConfig:
        config = self._get_or_error(config_id)
        self._ensure_credential(payload.credential_id)
        self._ensure_netbios_available(payload.netbios_name, exclude_id=config.id, is_enabled=payload.is_enabled)
        for key, value in payload.model_dump().items():
            setattr(config, key, value)
        db.session.commit()
        return config

    def set_enabled(self, config_id: int, *, is_enabled: bool) -> AdDomainConfig:
        config = self._get_or_error(config_id)
        if is_enabled:
            self._ensure_netbios_available(config.netbios_name, exclude_id=config.id, is_enabled=True)
        config.is_enabled = bool(is_enabled)
        db.session.commit()
        return config

    def delete(self, config_id: int) -> None:
        config = self._get_or_error(config_id)
        self._repository.delete(config)
        db.session.commit()

    def test_connection(self, config_id: int) -> dict[str, object]:
        config = self._get_or_error(config_id)
        principals = self._provider.fetch_principals(config)
        return {"principal_count": len(principals)}

    def _get_or_error(self, config_id: int) -> AdDomainConfig:
        config = self._repository.get_by_id(config_id)
        if config is None:
            raise NotFoundError("AD 域配置不存在")
        return config

    def _ensure_credential(self, credential_id: int) -> None:
        credential = self._credentials_repository.get_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在")
        if str(credential.credential_type).lower() != "ldap":
            raise ValidationError("AD 域配置仅支持绑定 LDAP 类型凭据")
        if not bool(credential.is_active):
            raise ValidationError("仅支持绑定启用中的 LDAP 凭据")

    def _ensure_netbios_available(self, netbios_name: str, *, exclude_id: int | None, is_enabled: bool) -> None:
        if not is_enabled:
            return
        if self._repository.active_netbios_exists(netbios_name, exclude_id=exclude_id):
            raise ValidationError("已存在启用中的相同 NetBIOS 域配置")

    @staticmethod
    def _serialize_config(config: AdDomainConfig) -> dict[str, object]:
        data = config.to_dict()
        credential = getattr(config, "credential", None)
        if credential is not None:
            data["credential"] = {
                "id": credential.id,
                "name": credential.name,
                "description": credential.description,
            }
        return data
