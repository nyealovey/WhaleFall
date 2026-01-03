"""修改密码写服务.

职责:
- 执行修改密码的校验与落库
- 只做 flush,不 commit（由 safe_route_call 统一提交）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import AuthenticationError, ValidationError
from app.models.user import User
from app.types.converters import as_str
from app.utils.data_validator import DataValidator
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.types import MutablePayloadDict, PayloadMapping


class ChangePasswordService:
    """修改密码写服务."""

    def change_password(self, payload: PayloadMapping, *, user: User | None) -> User:
        """修改当前用户密码."""
        if user is None:
            raise ValidationError("用户未登录")

        sanitized = cast(MutablePayloadDict, DataValidator.sanitize_form_data(payload or {}))
        old_password = as_str(sanitized.get("old_password"), default="").strip()
        new_password = as_str(sanitized.get("new_password"), default="").strip()
        confirm_password = as_str(sanitized.get("confirm_password"), default="").strip()

        if not old_password or not new_password or not confirm_password:
            raise ValidationError("所有字段都不能为空", message_key="VALIDATION_ERROR")

        if new_password != confirm_password:
            raise ValidationError("两次输入的新密码不一致", message_key="PASSWORD_MISMATCH")

        if not user.check_password(old_password):
            raise AuthenticationError("当前密码错误", message_key="INVALID_OLD_PASSWORD")

        if new_password == old_password:
            raise ValidationError("新密码不能与当前密码相同", message_key="PASSWORD_DUPLICATED")

        password_error = DataValidator.validate_password(new_password)
        if password_error:
            raise ValidationError(password_error, message_key="PASSWORD_INVALID")

        try:
            user.set_password(new_password)
        except ValueError as exc:
            raise ValidationError(str(exc), message_key="PASSWORD_INVALID") from exc

        try:
            with db.session.begin_nested():
                db.session.add(user)
                db.session.flush()
        except SQLAlchemyError as exc:
            raise ValidationError("密码修改失败,请稍后再试", extra={"exception": str(exc)}) from exc

        log_info(
            "用户修改密码成功",
            module="auth",
            operator_id=getattr(user, "id", None),
        )
        return user
