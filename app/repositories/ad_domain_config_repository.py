"""AD 域配置 Repository."""

from __future__ import annotations

from typing import cast

from app import db
from app.models.ad_domain_config import AdDomainConfig


class AdDomainConfigRepository:
    """AD 域配置读写."""

    @staticmethod
    def list_configs(*, enabled_only: bool = False) -> list[AdDomainConfig]:
        query = AdDomainConfig.query
        if enabled_only:
            query = query.filter(AdDomainConfig.is_enabled.is_(True))
        return cast(list[AdDomainConfig], query.order_by(AdDomainConfig.name.asc()).all())

    @staticmethod
    def get_by_id(config_id: int) -> AdDomainConfig | None:
        return cast(AdDomainConfig | None, AdDomainConfig.query.get(config_id))

    @staticmethod
    def get_by_name(name: str) -> AdDomainConfig | None:
        return cast(AdDomainConfig | None, AdDomainConfig.query.filter(AdDomainConfig.name == name).first())

    @staticmethod
    def active_netbios_exists(netbios_name: str, *, exclude_id: int | None = None) -> bool:
        query = AdDomainConfig.query.filter(
            AdDomainConfig.is_enabled.is_(True),
            db.func.lower(AdDomainConfig.netbios_name) == netbios_name.strip().lower(),
        )
        if exclude_id is not None:
            query = query.filter(AdDomainConfig.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def add(config: AdDomainConfig) -> AdDomainConfig:
        db.session.add(config)
        db.session.flush()
        return config

    @staticmethod
    def delete(config: AdDomainConfig) -> None:
        db.session.delete(config)
