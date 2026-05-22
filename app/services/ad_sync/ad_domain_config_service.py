"""AD 域配置管理服务."""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect

from app import db
from app.core.exceptions import NotFoundError, ValidationError
from app.models.ad_domain_config import AdDomainConfig
from app.models.task_run_item import TaskRunItem
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
        configs = self._repository.list_configs()
        metrics_by_config = self._latest_sync_metrics_by_config(configs)
        return [
            self._serialize_config(config, last_sync_metrics=metrics_by_config.get(int(config.id or 0)))
            for config in configs
        ]

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
    def _latest_sync_metrics_by_config(configs: list[AdDomainConfig]) -> dict[int, dict[str, int]]:
        if not inspect(db.engine).has_table(TaskRunItem.__tablename__):
            return {}
        run_id_by_config = {
            int(config.id): str(config.last_sync_run_id)
            for config in configs
            if config.id is not None and config.last_sync_run_id
        }
        if not run_id_by_config:
            return {}
        items = TaskRunItem.query.filter(
            TaskRunItem.item_type == "ad_domain",
            TaskRunItem.run_id.in_(set(run_id_by_config.values())),
            TaskRunItem.item_key.in_([str(config_id) for config_id in run_id_by_config]),
        ).all()
        metrics_by_config: dict[int, dict[str, int]] = {}
        for item in items:
            try:
                config_id = int(item.item_key)
            except (TypeError, ValueError):
                continue
            if item.run_id != run_id_by_config.get(config_id):
                continue
            metrics = AdDomainConfigService._normalize_sync_metrics(item.metrics_json)
            if metrics is not None:
                metrics_by_config[config_id] = metrics
        return metrics_by_config

    @staticmethod
    def _normalize_sync_metrics(raw_metrics: Any) -> dict[str, int] | None:
        if not isinstance(raw_metrics, dict):
            return None
        return {
            "total": int(raw_metrics.get("total") or 0),
            "normal": int(raw_metrics.get("normal") or 0),
            "disabled": int(raw_metrics.get("disabled") or 0),
            "orphaned": int(raw_metrics.get("orphaned") or 0),
            "updated": int(raw_metrics.get("updated") or 0),
            "ad_users_total": int(raw_metrics.get("ad_users_total") or 0),
            "ad_groups_total": int(raw_metrics.get("ad_groups_total") or 0),
            "ad_principals_total": int(raw_metrics.get("ad_principals_total") or 0),
        }

    @staticmethod
    def _serialize_config(
        config: AdDomainConfig,
        *,
        last_sync_metrics: dict[str, int] | None = None,
    ) -> dict[str, object]:
        data = config.to_dict()
        data["last_sync_metrics"] = last_sync_metrics
        credential = getattr(config, "credential", None)
        if credential is not None:
            data["credential"] = {
                "id": credential.id,
                "name": credential.name,
                "description": credential.description,
            }
        return data
