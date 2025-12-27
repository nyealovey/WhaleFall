"""Auth namespace (Phase 3 全量覆盖 - 认证模块)."""

from __future__ import annotations

from typing import Any

from flask import request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from flask_login import current_user, login_user, logout_user
from flask_restx import Namespace, fields
from flask_wtf.csrf import generate_csrf

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required
from app.constants import TimeConstants
from app.constants.system_constants import ErrorMessages, SuccessMessages
from app.errors import AuthenticationError, AuthorizationError, NotFoundError, ValidationError
from app.models.user import User
from app.services.auth import ChangePasswordService
from app.utils.decorators import require_csrf
from app.utils.rate_limiter import login_rate_limit, password_reset_rate_limit

ns = Namespace("auth", description="认证")

ErrorEnvelope = get_error_envelope_model(ns)

CsrfTokenData = ns.model(
    "CsrfTokenData",
    {
        "csrf_token": fields.String(),
    },
)
CsrfTokenSuccessEnvelope = make_success_envelope_model(ns, "CsrfTokenSuccessEnvelope", CsrfTokenData)

LoginPayload = ns.model(
    "LoginPayload",
    {
        "username": fields.String(required=True),
        "password": fields.String(required=True),
    },
)

AuthUserData = ns.model(
    "AuthUserData",
    {
        "id": fields.Integer(),
        "username": fields.String(),
        "role": fields.String(),
        "is_active": fields.Boolean(),
    },
)

LoginData = ns.model(
    "LoginData",
    {
        "access_token": fields.String(),
        "refresh_token": fields.String(),
        "user": fields.Nested(AuthUserData),
    },
)
LoginSuccessEnvelope = make_success_envelope_model(ns, "LoginSuccessEnvelope", LoginData)

EmptyData = ns.model("EmptyData", {})
EmptySuccessEnvelope = make_success_envelope_model(ns, "EmptySuccessEnvelope", EmptyData)

ChangePasswordPayload = ns.model(
    "ChangePasswordPayload",
    {
        "old_password": fields.String(required=True),
        "new_password": fields.String(required=True),
        "confirm_password": fields.String(required=True),
    },
)

RefreshData = ns.model(
    "RefreshData",
    {
        "access_token": fields.String(),
        "token_type": fields.String(),
        "expires_in": fields.Integer(),
    },
)
RefreshSuccessEnvelope = make_success_envelope_model(ns, "RefreshSuccessEnvelope", RefreshData)

MeData = ns.model(
    "MeData",
    {
        "id": fields.Integer(),
        "username": fields.String(),
        "email": fields.String(required=False),
        "role": fields.String(),
        "is_active": fields.Boolean(),
        "created_at": fields.String(required=False, description="ISO8601 时间戳"),
        "last_login": fields.String(required=False, description="ISO8601 时间戳"),
    },
)
MeSuccessEnvelope = make_success_envelope_model(ns, "MeSuccessEnvelope", MeData)


def _parse_payload() -> Any:
    if request.is_json:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}
    return request.form


@ns.route("/csrf-token")
class CsrfTokenResource(BaseResource):
    @ns.response(200, "OK", CsrfTokenSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        return self.success(
            data={"csrf_token": generate_csrf()},
            message=SuccessMessages.OPERATION_SUCCESS,
        )


@ns.route("/login")
class LoginResource(BaseResource):
    @ns.expect(LoginPayload, validate=False)
    @ns.response(200, "OK", LoginSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(429, "Too Many Requests", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @login_rate_limit()
    @require_csrf
    def post(self):
        payload = _parse_payload()
        username = (payload.get("username") or "").strip() if hasattr(payload, "get") else ""
        password = payload.get("password") if hasattr(payload, "get") else None

        if not username or not password:
            raise ValidationError(message="用户名和密码不能为空")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                raise AuthorizationError(
                    message=ErrorMessages.ACCOUNT_DISABLED,
                    message_key="ACCOUNT_DISABLED",
                )

            login_user(user, remember=True)
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            return self.success(
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "is_active": user.is_active,
                    },
                },
                message=SuccessMessages.LOGIN_SUCCESS,
            )

        raise AuthenticationError(
            message=ErrorMessages.INVALID_CREDENTIALS,
            message_key="INVALID_CREDENTIALS",
        )


@ns.route("/logout")
class LogoutResource(BaseResource):
    @ns.response(200, "OK", EmptySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_login_required
    @require_csrf
    def post(self):
        logout_user()
        return self.success(message=SuccessMessages.LOGOUT_SUCCESS)


@ns.route("/change-password")
class ChangePasswordResource(BaseResource):
    @ns.expect(ChangePasswordPayload, validate=False)
    @ns.response(200, "OK", EmptySuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(429, "Too Many Requests", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_login_required
    @password_reset_rate_limit()
    @require_csrf
    def post(self):
        payload = _parse_payload()

        def _execute():
            ChangePasswordService().change_password(payload, user=current_user)
            return self.success(message=SuccessMessages.PASSWORD_CHANGED)

        return self.safe_call(
            _execute,
            module="auth",
            action="submit_change_password",
            public_error="密码修改失败",
            context={"user_id": getattr(current_user, "id", None)},
        )


@ns.route("/refresh")
class RefreshResource(BaseResource):
    @ns.response(200, "OK", RefreshSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    @jwt_required(refresh=True)
    def post(self):
        def _execute():
            current_user_id = get_jwt_identity()
            access_token = create_access_token(identity=str(current_user_id))
            return self.success(
                data={
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": TimeConstants.ONE_HOUR,
                },
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="auth",
            action="refresh",
            public_error="刷新token失败",
            context={"route": "api_v1.auth.refresh"},
        )


@ns.route("/me")
class MeResource(BaseResource):
    @ns.response(200, "OK", MeSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        try:
            user_id = int(current_user_id)
        except (TypeError, ValueError) as exc:
            raise AuthenticationError(
                message=ErrorMessages.INVALID_CREDENTIALS,
                message_key="INVALID_CREDENTIALS",
            ) from exc

        user = User.query.get(user_id)
        if not user:
            raise NotFoundError(message="用户不存在")

        return self.success(
            data={
                "id": user.id,
                "username": user.username,
                "email": getattr(user, "email", None),
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            message=SuccessMessages.OPERATION_SUCCESS,
        )
