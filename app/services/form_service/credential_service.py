"""凭据资源表单服务."""

from __future__ import annotations

import os
import secrets
from typing import TYPE_CHECKING, Any, cast

from flask_login import current_user

from app.constants import CREDENTIAL_TYPES, DATABASE_TYPES
from app.models.credential import Credential, CredentialCreateParams
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.types.converters import as_bool, as_optional_str, as_str
from app.utils.data_validator import DataValidator
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.types import ContextDict, MutablePayloadDict, PayloadMapping, PayloadValue
else:
    ContextDict = dict[str, Any]
    MutablePayloadDict = dict[str, Any]
    PayloadMapping = dict[str, Any]
    PayloadValue = Any


class CredentialFormService(BaseResourceService[Credential]):
    """负责凭据创建与编辑的服务.

    提供凭据的表单校验、数据规范化和保存功能.

    Attributes:
        model: 关联的 Credential 模型类.

    """

    model = Credential

    def sanitize(self, payload: PayloadMapping) -> MutablePayloadDict:
        """清理表单数据.

        Args:
            payload: 原始表单数据.

        Returns:
            清理后的数据字典.

        """
        # DataValidator 返回的值类型为 dict[str, object],此处收窄为 MutablePayloadDict 以便后续类型校验
        return cast("MutablePayloadDict", DataValidator.sanitize_form_data(payload or {}))

    def validate(self, data: MutablePayloadDict, *, resource: Credential | None) -> ServiceResult[MutablePayloadDict]:
        """校验凭据数据.

        校验必填字段、用户名格式、密码强度、数据库类型和凭据类型.

        Args:
            data: 清理后的数据.
            resource: 已存在的凭据实例(编辑场景),创建时为 None.

        Returns:
            校验结果,成功时返回规范化的数据,失败时返回错误信息.

        """
        require_password = resource is None

        failure = self._validate_payload_fields(data, require_password=require_password)
        if failure:
            return failure

        normalized = self._normalize_payload(data, resource)

        query = Credential.query.filter(Credential.name == normalized["name"])
        if resource:
            query = query.filter(Credential.id != resource.id)
        if query.first():
            return ServiceResult.fail("凭据名称已存在,请使用其他名称")

        return ServiceResult.ok(normalized)

    def assign(self, instance: Credential, data: MutablePayloadDict) -> None:
        """将数据赋值给凭据实例.

        Args:
            instance: 凭据实例.
            data: 已校验的数据.

        Returns:
            None: 凭据字段赋值完成后返回.

        """
        instance.name = as_str(data.get("name"))
        instance.credential_type = as_str(data.get("credential_type"))
        instance.username = as_str(data.get("username"))
        instance.db_type = as_optional_str(data.get("db_type"))
        instance.description = as_optional_str(data.get("description"))
        instance.is_active = as_bool(data.get("is_active"), default=True)

        password_value = as_optional_str(data.get("password"))
        if password_value:
            instance.set_password(password_value)

    def after_save(self, instance: Credential, data: MutablePayloadDict) -> None:
        """保存后记录日志.

        Args:
            instance: 已保存的凭据实例.
            data: 已校验的数据.

        Returns:
            None: 日志记录完成后返回.

        """
        action = "创建数据库凭据" if data.get("_is_create") else "更新数据库凭据"
        log_info(
            action,
            module="credentials",
            user_id=getattr(current_user, "id", None),
            credential_id=instance.id,
            credential_name=instance.name,
            credential_type=instance.credential_type,
            db_type=instance.db_type,
            is_active=instance.is_active,
        )

    def build_context(self, *, resource: Credential | None) -> ContextDict:
        """构建模板渲染上下文.

        Args:
            resource: 凭据实例,创建时为 None.

        Returns:
            包含凭据类型和数据库类型选项的上下文字典.

        """
        del resource
        return {
            "credential_type_options": CREDENTIAL_TYPES,
            "db_type_options": DATABASE_TYPES,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _validate_payload_fields(
        self,
        data: PayloadMapping,
        *,
        require_password: bool,
    ) -> ServiceResult[MutablePayloadDict] | None:
        """对凭据表单的核心字段执行逐项校验."""
        required_fields = ["name", "credential_type", "username"]
        if require_password:
            required_fields.append("password")

        message = DataValidator.validate_required_fields(data, required_fields)
        if message:
            return ServiceResult.fail(message)

        username_error = DataValidator.validate_username(data.get("username"))
        if username_error:
            return ServiceResult.fail(username_error)

        password_value = data.get("password")
        if require_password or password_value:
            password_error = DataValidator.validate_password(password_value)
            if password_error:
                return ServiceResult.fail(password_error)

        db_type_value = data.get("db_type")
        if db_type_value:
            db_type_error = DataValidator.validate_db_type(db_type_value)
            if db_type_error:
                return ServiceResult.fail(db_type_error)

        credential_type_error = DataValidator.validate_credential_type(data.get("credential_type"))
        if credential_type_error:
            return ServiceResult.fail(credential_type_error)

        return None

    def _normalize_payload(self, data: PayloadMapping, resource: Credential | None) -> MutablePayloadDict:
        """规范化表单数据.

        Args:
            data: 原始数据.
            resource: 已存在的凭据实例,创建时为 None.

        Returns:
            规范化后的数据字典.

        """
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

        normalized["_is_create"] = resource is None
        return normalized

    def _create_instance(self) -> Credential:
        """为凭据创建空白实例.

        Credential 模型的构造函数要求 name/credential_type/username/password
        四个必填参数.表单服务在赋值阶段才会写入真实数据,因此这里
        提供占位值以便复用基类的 upsert 流程.
        """
        placeholder = CredentialCreateParams(
            name="__pending__",
            credential_type="database",
            username="__pending__",
            password=self._placeholder_secret(),
        )
        return Credential(params=placeholder)

    def _placeholder_secret(self) -> str:
        """生成占位密码,优先使用环境变量以避免硬编码."""
        env_secret = os.getenv("WHF_PLACEHOLDER_CREDENTIAL_SECRET")
        if env_secret:
            return env_secret
        return secrets.token_urlsafe(16)

    def upsert(self, payload: PayloadMapping, resource: Credential | None = None) -> ServiceResult[Credential]:
        """执行凭据创建或更新操作.

        Args:
            payload: 原始表单数据.
            resource: 已存在的凭据实例(编辑场景),创建时为 None.

        Returns:
            操作结果,成功时返回凭据实例,失败时返回错误信息.

        """
        result = super().upsert(payload, resource)
        if not result.success and result.extra.get("exception"):
            # 将数据库异常转换为用户可读的信息
            message = self._normalize_db_error(str(result.extra["exception"]))
            return ServiceResult.fail(message)
        return result

    def _normalize_db_error(self, message: str) -> str:
        """将数据库异常转换为用户可读的错误信息.

        Args:
            message: 数据库异常信息.

        Returns:
            用户可读的错误信息.

        """
        lowered = message.lower()
        if "unique constraint failed" in lowered or "duplicate key value" in lowered:
            return "凭据名称已存在,请使用其他名称"
        if "not null constraint failed" in lowered:
            return "必填字段不能为空"
        return "保存凭据失败,请稍后再试"
