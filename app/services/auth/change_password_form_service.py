"""
修改密码表单服务
"""

from __future__ import annotations

from typing import Any, Mapping

from flask_login import current_user

from app import db
from app.models.user import User
from app.services.resource_form_service import BaseResourceService, ServiceResult
from app.utils.data_validator import sanitize_form_data, validate_password
from app.utils.structlog_config import log_info


class ChangePasswordFormService(BaseResourceService[User]):
    """负责编排修改密码表单的校验与提交。"""

    model = User

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return sanitize_form_data(payload or {})

    def validate(self, data: dict[str, Any], *, resource: User | None) -> ServiceResult[dict[str, Any]]:
        if resource is None:
            return ServiceResult.fail("用户未登录")

        old_password = (data.get("old_password") or "").strip()
        new_password = (data.get("new_password") or "").strip()
        confirm_password = (data.get("confirm_password") or "").strip()

        if not old_password or not new_password or not confirm_password:
            return ServiceResult.fail("所有字段都不能为空", message_key="VALIDATION_ERROR")

        if new_password != confirm_password:
            return ServiceResult.fail("两次输入的新密码不一致", message_key="PASSWORD_MISMATCH")

        if not resource.check_password(old_password):
            return ServiceResult.fail("当前密码错误", message_key="INVALID_OLD_PASSWORD")

        if new_password == old_password:
            return ServiceResult.fail("新密码不能与当前密码相同", message_key="PASSWORD_DUPLICATED")

        password_error = validate_password(new_password)
        if password_error:
            return ServiceResult.fail(password_error, message_key="PASSWORD_INVALID")

        return ServiceResult.ok({"new_password": new_password})

    def assign(self, instance: User, data: dict[str, Any]) -> None:
        instance.set_password(data["new_password"])

    def after_save(self, instance: User, data: dict[str, Any]) -> None:
        log_info(
            "用户修改密码成功",
            module="auth",
            operator_id=getattr(current_user, "id", None),
        )

    def upsert(self, payload: Mapping[str, Any], resource: User | None = None) -> ServiceResult[User]:
        sanitized = self.sanitize(payload)
        validation = self.validate(sanitized, resource=resource)
        if not validation.success:
            return ServiceResult.fail(validation.message or "验证失败", message_key=validation.message_key, extra=validation.extra)

        instance = resource
        if instance is None:
            return ServiceResult.fail("用户未登录")

        self.assign(instance, validation.data or sanitized)

        try:
            db.session.add(instance)
            db.session.commit()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            return ServiceResult.fail("密码修改失败，请稍后再试", extra={"exception": str(exc)})

        self.after_save(instance, validation.data or sanitized)
        return ServiceResult.ok(instance)
