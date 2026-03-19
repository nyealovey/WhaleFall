"""JumpServer Provider 抽象.

说明:
- 当前先建立稳定的 provider 边界, 后续再接入真实 JumpServer API.
- v1 认证方式约定为 Access Key, 对应凭据中的 username/password.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class JumpServerDatabaseAsset:
    """标准化后的 JumpServer 数据库资产."""

    external_id: str
    name: str
    db_type: str
    host: str
    port: int
    raw_payload: dict[str, object]


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
    ) -> list[JumpServerDatabaseAsset]:
        """返回数据库类资产列表."""


class DeferredJumpServerProvider:
    """占位 provider.

    真实 JumpServer 资产 API 接口路径与返回结构后续接入，
    当前只提供稳定接口，不直接把未确认 API 细节写入业务代码。
    """

    def is_configured(self) -> bool:
        return False

    def list_database_assets(
        self,
        *,
        base_url: str,
        access_key_id: str,
        access_key_secret: str,
    ) -> list[JumpServerDatabaseAsset]:
        raise NotImplementedError("JumpServer Provider 尚未接入真实 API")
