"""凭据写操作 Service.

职责:
- 处理凭据的创建/更新/删除编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import DatabaseError, NotFoundError, ValidationError
from app.models.credential import Credential, CredentialCreateParams
from app.repositories.credentials_repository import CredentialsRepository
from app.schemas.credentials import CredentialCreatePayload, CredentialUpdatePayload
from app.schemas.validation import validate_or_raise
from app.types.request_payload import parse_payload
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.types import ResourcePayload


@dataclass(slots=True)
class CredentialDeleteOutcome:
    """凭据删除结果."""

    credential_id: int
    credential_name: str
    credential_type: str


class CredentialWriteService:
    """凭据写操作服务."""

    def __init__(self, repository: CredentialsRepository | None = None) -> None:
        """初始化服务并注入凭据仓库."""
        self._repository = repository or CredentialsRepository()

    def create(self, payload: ResourcePayload, *, operator_id: int | None = None) -> Credential:
        """创建凭据."""
        sanitized = parse_payload(
            payload or {},
            preserve_raw_fields=["password"],
            boolean_fields_default_false=["is_active"],
        )
        parsed = validate_or_raise(CredentialCreatePayload, sanitized)
        self._ensure_name_unique(parsed.name, resource=None)

        params = CredentialCreateParams(
            name=parsed.name,
            credential_type=parsed.credential_type,
            username=parsed.username,
            password=parsed.password,
            db_type=parsed.db_type,
            description=parsed.description,
        )
        credential = Credential(params=params)
        credential.is_active = parsed.is_active

        try:
            self._repository.add(credential)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("创建凭据", exc), extra={"exception": str(exc)}) from exc

        self._log_create(credential, operator_id=operator_id)
        return credential

    def update(self, credential_id: int, payload: ResourcePayload, *, operator_id: int | None = None) -> Credential:
        """更新凭据."""
        credential = self._get_or_error(credential_id)
        sanitized = parse_payload(
            payload or {},
            preserve_raw_fields=["password"],
            boolean_fields_default_false=["is_active"],
        )
        parsed = validate_or_raise(CredentialUpdatePayload, sanitized)
        self._ensure_name_unique(parsed.name, resource=credential)

        credential.name = parsed.name
        credential.credential_type = parsed.credential_type
        credential.username = parsed.username

        if "db_type" in parsed.model_fields_set:
            credential.db_type = parsed.db_type
        if "description" in parsed.model_fields_set:
            credential.description = parsed.description
        if parsed.is_active is not None:
            credential.is_active = parsed.is_active
        if parsed.password is not None:
            credential.set_password(parsed.password)
        try:
            self._repository.add(credential)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("更新凭据", exc), extra={"exception": str(exc)}) from exc

        self._log_update(credential, operator_id=operator_id)
        return credential

    def delete(self, credential_id: int, *, operator_id: int | None = None) -> CredentialDeleteOutcome:
        """删除凭据."""
        credential = self._get_or_error(credential_id)
        outcome = CredentialDeleteOutcome(
            credential_id=credential.id,
            credential_name=credential.name,
            credential_type=credential.credential_type,
        )

        try:
            self._repository.delete(credential)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("删除凭据", exc), extra={"exception": str(exc)}) from exc

        self._log_delete(outcome, operator_id=operator_id)
        return outcome

    @staticmethod
    def _ensure_name_unique(name: str, *, resource: Credential | None) -> None:
        query = Credential.query.filter(Credential.name == name)
        if resource:
            query = query.filter(Credential.id != resource.id)
        if query.first():
            raise ValidationError("凭据名称已存在,请使用其他名称")

    def _get_or_error(self, credential_id: int) -> Credential:
        credential = self._repository.get_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在", extra={"credential_id": credential_id})
        return credential

    @staticmethod
    def _normalize_db_error(action: str, error: Exception) -> str:
        message = str(error)
        lowered = message.lower()
        if "unique constraint failed" in lowered or "duplicate key value" in lowered:
            return "凭据名称已存在,请使用其他名称"
        if "not null constraint failed" in lowered:
            return "必填字段不能为空"
        return f"{action}失败,请稍后重试"

    @staticmethod
    def _log_create(credential: Credential, *, operator_id: int | None) -> None:
        log_info(
            "创建数据库凭据",
            module="credentials",
            user_id=operator_id,
            credential_id=credential.id,
            credential_name=credential.name,
            credential_type=credential.credential_type,
            db_type=credential.db_type,
            is_active=credential.is_active,
        )

    @staticmethod
    def _log_update(credential: Credential, *, operator_id: int | None) -> None:
        log_info(
            "更新数据库凭据",
            module="credentials",
            user_id=operator_id,
            credential_id=credential.id,
            credential_name=credential.name,
            credential_type=credential.credential_type,
            db_type=credential.db_type,
            is_active=credential.is_active,
        )

    @staticmethod
    def _log_delete(outcome: CredentialDeleteOutcome, *, operator_id: int | None) -> None:
        log_info(
            "删除数据库凭据",
            module="credentials",
            user_id=operator_id,
            credential_id=outcome.credential_id,
            credential_name=outcome.credential_name,
            credential_type=outcome.credential_type,
        )
