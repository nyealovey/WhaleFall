"""修改密码写服务.

职责:
- 执行修改密码的校验与落库
- 只做 flush,不 commit（由 safe_route_call 统一提交）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import AuthenticationError, ValidationError
from app.models.user import User
from app.schemas.auth import ChangePasswordPayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.types import PayloadMapping


class ChangePasswordService:
    """修改密码写服务."""

    def change_password(self, payload: PayloadMapping, *, user: User | None) -> User:
        """修改当前用户密码."""
        if user is None:
            raise ValidationError("用户未登录")

        sanitized = parse_payload(payload or {}, preserve_raw_fields=["old_password", "new_password", "confirm_password"])
        params = validate_or_raise(ChangePasswordPayload, sanitized)
        old_password = params.old_password
        new_password = params.new_password

        if not user.check_password(old_password):
            raise AuthenticationError("当前密码错误", message_key="INVALID_OLD_PASSWORD")

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
