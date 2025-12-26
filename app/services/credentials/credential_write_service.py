"""凭据写操作 Service.

职责:
- 处理凭据的创建/更新/删除编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import DatabaseError, NotFoundError, ValidationError
from app.models.credential import Credential, CredentialCreateParams
from app.repositories.credentials_repository import CredentialsRepository
from app.types.converters import as_bool, as_optional_str, as_str
from app.utils.data_validator import DataValidator
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.types import MutablePayloadDict, PayloadMapping, ResourcePayload


@dataclass(slots=True)
class CredentialDeleteOutcome:
    credential_id: int
    credential_name: str
    credential_type: str


class CredentialWriteService:
    """凭据写操作服务."""

    def __init__(self, repository: CredentialsRepository | None = None) -> None:
        self._repository = repository or CredentialsRepository()

    def create(self, payload: ResourcePayload, *, operator_id: int | None = None) -> Credential:
        sanitized = self._sanitize(payload)
        self._validate_payload_fields(sanitized, require_password=True)
        normalized = self._normalize_payload(sanitized, resource=None)
        self._ensure_name_unique(cast(str, normalized["name"]), resource=None)

        params = CredentialCreateParams(
            name=cast(str, normalized["name"]),
            credential_type=cast(str, normalized["credential_type"]),
            username=cast(str, normalized["username"]),
            password=cast(str, normalized["password"]),
            db_type=cast("str | None", normalized["db_type"]),
            description=cast("str | None", normalized["description"]),
        )
        credential = Credential(params=params)
        credential.is_active = cast(bool, normalized["is_active"])

        try:
            self._repository.add(credential)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("创建凭据", exc), extra={"exception": str(exc)}) from exc

        self._log_create(credential, operator_id=operator_id)
        return credential

    def update(self, credential_id: int, payload: ResourcePayload, *, operator_id: int | None = None) -> Credential:
        credential = self._get_or_error(credential_id)
        sanitized = self._sanitize(payload)
        self._validate_payload_fields(sanitized, require_password=False)
        normalized = self._normalize_payload(sanitized, resource=credential)
        self._ensure_name_unique(cast(str, normalized["name"]), resource=credential)

        self._assign(credential, normalized)
        try:
            self._repository.add(credential)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("更新凭据", exc), extra={"exception": str(exc)}) from exc

        self._log_update(credential, operator_id=operator_id)
        return credential

    def delete(self, credential_id: int, *, operator_id: int | None = None) -> CredentialDeleteOutcome:
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
    def _sanitize(payload: PayloadMapping) -> MutablePayloadDict:
        return cast("MutablePayloadDict", DataValidator.sanitize_form_data(payload or {}))

    @staticmethod
    def _normalize_payload(data: PayloadMapping, *, resource: Credential | None) -> MutablePayloadDict:
        normalized: MutablePayloadDict = {}
        normalized["name"] = as_str(
            data.get("name"),
            default=resource.name if resource else "",
        ).strip()
        normalized["credential_type"] = as_str(
            data.get("credential_type"),
            default=resource.credential_type if resource else "",
        ).strip()
        normalized["username"] = as_str(
            data.get("username"),
            default=resource.username if resource else "",
        ).strip()

        db_type_raw = data.get("db_type") if data.get("db_type") is not None else resource.db_type if resource else ""
        normalized["db_type"] = as_optional_str(db_type_raw)

        description_raw = data.get("description")
        if description_raw is None and resource:
            description_raw = resource.description
        normalized["description"] = as_optional_str(description_raw)

        normalized["password"] = as_str(data.get("password"), default="").strip()
        normalized["is_active"] = as_bool(
            data.get("is_active"),
            default=resource.is_active if resource else True,
        )
        return normalized

    @staticmethod
    def _assign(credential: Credential, normalized: PayloadMapping) -> None:
        credential.name = as_str(normalized.get("name")).strip()
        credential.credential_type = as_str(normalized.get("credential_type")).strip()
        credential.username = as_str(normalized.get("username")).strip()
        credential.db_type = as_optional_str(normalized.get("db_type"))
        credential.description = as_optional_str(normalized.get("description"))
        credential.is_active = as_bool(normalized.get("is_active"), default=True)

        password_value = as_optional_str(normalized.get("password"))
        if password_value:
            credential.set_password(password_value)

    @staticmethod
    def _validate_payload_fields(data: PayloadMapping, *, require_password: bool) -> None:
        required_fields = ["name", "credential_type", "username"]
        if require_password:
            required_fields.append("password")

        message = DataValidator.validate_required_fields(data, required_fields)
        if message:
            raise ValidationError(message)

        username_error = DataValidator.validate_username(data.get("username"))
        if username_error:
            raise ValidationError(username_error)

        password_value = data.get("password")
        if require_password or password_value:
            password_error = DataValidator.validate_password(password_value)
            if password_error:
                raise ValidationError(password_error)

        db_type_value = data.get("db_type")
        if db_type_value:
            db_type_error = DataValidator.validate_db_type(db_type_value)
            if db_type_error:
                raise ValidationError(db_type_error)

        credential_type_error = DataValidator.validate_credential_type(data.get("credential_type"))
        if credential_type_error:
            raise ValidationError(credential_type_error)

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
