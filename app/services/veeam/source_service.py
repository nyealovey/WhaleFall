"""Veeam 数据源绑定服务."""

from __future__ import annotations

from typing import Any

from flask import current_app, has_app_context

from app import db
from app.core.exceptions import NotFoundError, ValidationError
from app.models.veeam_source_binding import VeeamSourceBinding
from app.repositories.credentials_repository import CredentialsRepository
from app.repositories.veeam_repository import VeeamRepository
from app.services.veeam.provider import HttpVeeamProvider, VeeamProvider
from app.settings import Settings


class VeeamSourceService:
    """管理 Veeam 数据源绑定与视图载荷."""

    def __init__(
        self,
        *,
        credentials_repository: CredentialsRepository | None = None,
        veeam_repository: VeeamRepository | None = None,
        provider: VeeamProvider | Any | None = None,
    ) -> None:
        self._credentials_repository = credentials_repository or CredentialsRepository()
        self._veeam_repository = veeam_repository or VeeamRepository()
        self._provider = provider or HttpVeeamProvider()

    def build_view_payload(self) -> dict[str, object]:
        """构建页面加载载荷."""
        binding = self._veeam_repository.get_binding()
        sources = self._veeam_repository.list_bindings()
        veeam_credentials = self._credentials_repository.list_active_veeam_credentials()
        return {
            "binding": self._serialize_binding(binding),
            "sources": [self._serialize_binding(source) for source in sources],
            "veeam_credentials": [self._serialize_credential(credential) for credential in veeam_credentials],
            "provider_ready": self._provider.is_configured(),
            "default_port": self._resolve_default_port(),
            "default_api_version": self._resolve_default_api_version(),
            "default_verify_ssl": self._resolve_default_verify_ssl(),
            "default_match_domains": [],
        }

    def list_sources_payload(self) -> dict[str, object]:
        """构建多 Veeam 数据源管理载荷."""
        return self.build_view_payload()

    def create_source(
        self,
        *,
        credential_id: int,
        server_host: str,
        server_port: int,
        api_version: str,
        name: str | None = None,
        verify_ssl: bool | None = None,
        match_domains: list[str] | None = None,
    ) -> VeeamSourceBinding:
        """新增 Veeam 数据源."""
        credential = self._credentials_repository.get_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在")
        self._ensure_bindable_credential(credential)

        binding = VeeamSourceBinding(
            name=self._resolve_source_name(name=name, credential=credential, server_host=server_host),
            credential_id=credential.id,
            server_host=server_host,
            server_port=server_port,
            api_version=api_version,
            verify_ssl=self._resolve_default_verify_ssl() if verify_ssl is None else bool(verify_ssl),
            match_domains=list(match_domains or []),
            is_enabled=True,
        )
        self._veeam_repository.add_binding(binding)
        db.session.commit()
        return binding

    def update_source(
        self,
        source_id: int,
        *,
        credential_id: int,
        server_host: str,
        server_port: int,
        api_version: str,
        name: str | None = None,
        verify_ssl: bool | None = None,
        match_domains: list[str] | None = None,
    ) -> VeeamSourceBinding:
        """更新 Veeam 数据源."""
        binding = self._get_binding_by_id_or_error(source_id)
        credential = self._credentials_repository.get_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在")
        self._ensure_bindable_credential(credential)

        binding.name = self._resolve_source_name(name=name, credential=credential, server_host=server_host)
        binding.credential_id = credential.id
        binding.server_host = server_host
        binding.server_port = server_port
        binding.api_version = api_version
        binding.verify_ssl = self._resolve_default_verify_ssl() if verify_ssl is None else bool(verify_ssl)
        binding.match_domains = list(match_domains or [])
        binding.last_error = None
        self._veeam_repository.add_binding(binding)
        db.session.commit()
        return binding

    def delete_source(self, source_id: int) -> None:
        """删除 Veeam 数据源并清空该源快照."""
        binding = self._get_binding_by_id_or_error(source_id)
        self._veeam_repository.clear_machine_backup_snapshots(source_binding_id=int(binding.id))
        self._veeam_repository.delete_binding(binding)
        db.session.commit()

    def set_source_enabled(self, source_id: int, *, is_enabled: bool) -> VeeamSourceBinding:
        """启用或停用 Veeam 数据源."""
        binding = self._get_binding_by_id_or_error(source_id)
        binding.is_enabled = bool(is_enabled)
        self._veeam_repository.add_binding(binding)
        db.session.commit()
        return binding

    def bind_source(
        self,
        *,
        credential_id: int,
        server_host: str,
        server_port: int,
        api_version: str,
        name: str | None = None,
        verify_ssl: bool | None = None,
        match_domains: list[str] | None = None,
    ) -> VeeamSourceBinding:
        """绑定 Veeam 凭据."""
        credential = self._credentials_repository.get_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在")
        self._ensure_bindable_credential(credential)

        binding = self._veeam_repository.get_binding()
        resolved_verify_ssl = self._resolve_default_verify_ssl() if verify_ssl is None else bool(verify_ssl)
        resolved_domains = list(match_domains or [])
        if binding is None:
            binding = VeeamSourceBinding(
                name=self._resolve_source_name(name=name, credential=credential, server_host=server_host),
                credential_id=credential.id,
                server_host=server_host,
                server_port=server_port,
                api_version=api_version,
                verify_ssl=resolved_verify_ssl,
                match_domains=resolved_domains,
            )
        else:
            binding.name = self._resolve_source_name(name=name, credential=credential, server_host=server_host)
            binding.credential_id = credential.id
            binding.server_host = server_host
            binding.server_port = server_port
            binding.api_version = api_version
            binding.verify_ssl = resolved_verify_ssl
            binding.match_domains = resolved_domains
            binding.is_enabled = True
            binding.last_error = None
        self._veeam_repository.add_binding(binding)
        db.session.commit()
        return binding

    def unbind_source(self) -> None:
        """解绑 Veeam 数据源并清空快照."""
        binding = self._veeam_repository.get_binding()
        if binding is not None:
            self._veeam_repository.delete_binding(binding)
        self._veeam_repository.clear_machine_backup_snapshots()
        db.session.commit()

    def get_binding_or_error(self, source_id: int | None = None) -> VeeamSourceBinding:
        """获取当前绑定."""
        binding = (
            self._veeam_repository.get_binding()
            if source_id is None
            else self._veeam_repository.get_binding_by_id(int(source_id))
        )
        if binding is None:
            raise ValidationError("请先绑定 Veeam 凭据")
        return binding

    def _get_binding_by_id_or_error(self, source_id: int) -> VeeamSourceBinding:
        binding = self._veeam_repository.get_binding_by_id(int(source_id))
        if binding is None:
            raise NotFoundError("Veeam 数据源不存在")
        return binding

    @staticmethod
    def _ensure_bindable_credential(credential: object) -> None:
        credential_type = str(getattr(credential, "credential_type", "") or "").strip().lower()
        if credential_type != "veeam":
            raise ValidationError("Veeam 仅支持绑定 Veeam 类型凭据")
        if not bool(getattr(credential, "is_active", False)):
            raise ValidationError("仅支持绑定启用中的 Veeam 凭据")

    @staticmethod
    def _serialize_credential(credential: object) -> dict[str, object]:
        return {
            "id": int(getattr(credential, "id", 0) or 0),
            "name": str(getattr(credential, "name", "") or ""),
            "description": str(getattr(credential, "description", "") or ""),
        }

    def _serialize_binding(self, binding: VeeamSourceBinding | None) -> dict[str, object] | None:
        if binding is None:
            return None
        data = binding.to_dict()
        credential = getattr(binding, "credential", None)
        if credential is not None:
            data["credential"] = self._serialize_credential(credential)
        return data

    @staticmethod
    def _resolve_source_name(*, name: str | None, credential: object, server_host: str) -> str:
        resolved_name = str(name or "").strip()
        if resolved_name:
            return resolved_name
        credential_name = str(getattr(credential, "name", "") or "").strip()
        if credential_name:
            return credential_name
        return str(server_host or "").strip() or "默认 Veeam"

    @staticmethod
    def _resolve_default_port() -> int:
        if has_app_context():
            return int(current_app.config.get("VEEAM_PORT", Settings.model_fields["veeam_port"].default))
        return int(Settings.load().veeam_port)

    @staticmethod
    def _resolve_default_api_version() -> str:
        if has_app_context():
            return str(
                current_app.config.get("VEEAM_API_VERSION", Settings.model_fields["veeam_api_version"].default) or ""
            ).strip()
        return str(Settings.load().veeam_api_version or "").strip()

    @staticmethod
    def _resolve_default_verify_ssl() -> bool:
        if has_app_context():
            return bool(current_app.config.get("VEEAM_VERIFY_SSL", Settings.model_fields["veeam_verify_ssl"].default))
        return bool(Settings.load().veeam_verify_ssl)
