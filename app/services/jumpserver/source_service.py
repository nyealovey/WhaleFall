"""JumpServer 数据源绑定服务."""

from __future__ import annotations

from app import db
from app.core.exceptions import NotFoundError, ValidationError
from app.models.jumpserver_source_binding import JumpServerSourceBinding
from app.repositories.credentials_repository import CredentialsRepository
from app.repositories.jumpserver_repository import JumpServerRepository
from app.services.jumpserver.provider import HttpJumpServerProvider, JumpServerProvider


class JumpServerSourceService:
    """管理 JumpServer 数据源绑定与视图载荷."""

    def __init__(
        self,
        *,
        credentials_repository: CredentialsRepository | None = None,
        jumpserver_repository: JumpServerRepository | None = None,
        provider: JumpServerProvider | None = None,
    ) -> None:
        self._credentials_repository = credentials_repository or CredentialsRepository()
        self._jumpserver_repository = jumpserver_repository or JumpServerRepository()
        self._provider = provider or HttpJumpServerProvider()

    def build_view_payload(self) -> dict[str, object]:
        """构建页面加载载荷."""
        binding = self._jumpserver_repository.get_binding()
        api_credentials = self._credentials_repository.list_active_api_credentials()
        return {
            "binding": self._serialize_binding(binding),
            "api_credentials": [self._serialize_credential(credential) for credential in api_credentials],
            "provider_ready": self._provider.is_configured(),
        }

    def bind_source(self, *, credential_id: int, base_url: str) -> JumpServerSourceBinding:
        """绑定 JumpServer API 凭据."""
        credential = self._credentials_repository.get_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在")
        self._ensure_bindable_credential(credential)

        binding = self._jumpserver_repository.get_binding()
        if binding is None:
            binding = JumpServerSourceBinding(credential_id=credential.id, base_url=base_url)
        else:
            binding.credential_id = credential.id
            binding.base_url = base_url
            binding.is_enabled = True
            binding.last_error = None
        self._jumpserver_repository.add_binding(binding)
        db.session.commit()
        return binding

    def unbind_source(self) -> None:
        """解绑 JumpServer 数据源并清空快照."""
        binding = self._jumpserver_repository.get_binding()
        if binding is not None:
            self._jumpserver_repository.delete_binding(binding)
        self._jumpserver_repository.clear_asset_snapshots()
        db.session.commit()

    def get_binding_or_error(self) -> JumpServerSourceBinding:
        """获取当前绑定."""
        binding = self._jumpserver_repository.get_binding()
        if binding is None:
            raise ValidationError("请先绑定 JumpServer API 凭据")
        return binding

    @staticmethod
    def _ensure_bindable_credential(credential: object) -> None:
        credential_type = str(getattr(credential, "credential_type", "") or "").strip().lower()
        if credential_type != "api":
            raise ValidationError("JumpServer 仅支持绑定 API 类型凭据")
        if not bool(getattr(credential, "is_active", False)):
            raise ValidationError("仅支持绑定启用中的 API 凭据")

    @staticmethod
    def _serialize_credential(credential: object) -> dict[str, object]:
        return {
            "id": int(credential.id),
            "name": str(getattr(credential, "name", "") or ""),
            "description": str(getattr(credential, "description", "") or ""),
        }

    def _serialize_binding(self, binding: JumpServerSourceBinding | None) -> dict[str, object] | None:
        if binding is None:
            return None
        data = binding.to_dict()
        credential = getattr(binding, "credential", None)
        if credential is not None:
            data["credential"] = self._serialize_credential(credential)
        return data
