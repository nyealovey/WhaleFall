"""Auth namespace (Phase 3 全量覆盖 - 认证模块)."""

from __future__ import annotations

from typing import Any

from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flask_login import current_user, logout_user
from flask_restx import Namespace, fields
from flask_wtf.csrf import generate_csrf

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required
from app.core.constants import TimeConstants
from app.core.constants.system_constants import SuccessMessages
from app.services.auth import AuthMeReadService, ChangePasswordService, LoginService
from app.utils.decorators import require_csrf
from app.utils.request_payload import parse_payload
from app.utils.rate_limiter import login_rate_limit, password_reset_rate_limit

ns = Namespace("auth", description="认证")

ErrorEnvelope = get_error_envelope_model(ns)

CsrfTokenData = ns.model(
    "CsrfTokenData",
    {
        "csrf_token": fields.String(
            required=True,
            description="CSRF token",
            example="csrf_token_example",
        ),
    },
)
CsrfTokenSuccessEnvelope = make_success_envelope_model(ns, "CsrfTokenSuccessEnvelope", CsrfTokenData)

LoginPayload = ns.model(
    "LoginPayload",
    {
        "username": fields.String(required=True, description="用户名", example="alice"),
        "password": fields.String(required=True, description="密码", example="your_password"),
    },
)

AuthUserData = ns.model(
    "AuthUserData",
    {
        "id": fields.Integer(description="用户 ID", example=1),
        "username": fields.String(description="用户名", example="alice"),
        "role": fields.String(description="角色(admin/user)", example="admin"),
        "is_active": fields.Boolean(description="是否启用", example=True),
    },
)

LoginData = ns.model(
    "LoginData",
    {
        "access_token": fields.String(
            description="JWT access token",
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
        "refresh_token": fields.String(
            description="JWT refresh token",
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
        "user": fields.Nested(AuthUserData, description="当前用户信息"),
    },
)
LoginSuccessEnvelope = make_success_envelope_model(ns, "LoginSuccessEnvelope", LoginData)

EmptyData = ns.model("EmptyData", {})
EmptySuccessEnvelope = make_success_envelope_model(ns, "EmptySuccessEnvelope", EmptyData)

ChangePasswordPayload = ns.model(
    "ChangePasswordPayload",
    {
        "old_password": fields.String(required=True, description="旧密码", example="old_password"),
        "new_password": fields.String(required=True, description="新密码", example="new_password"),
        "confirm_password": fields.String(required=True, description="确认新密码", example="new_password"),
    },
)

RefreshData = ns.model(
    "RefreshData",
    {
        "access_token": fields.String(
            description="JWT access token",
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
        "token_type": fields.String(description="token 类型", example="Bearer"),
        "expires_in": fields.Integer(description="过期时间(秒)", example=3600),
    },
)
RefreshSuccessEnvelope = make_success_envelope_model(ns, "RefreshSuccessEnvelope", RefreshData)

MeData = ns.model(
    "MeData",
    {
        "id": fields.Integer(description="用户 ID", example=1),
        "username": fields.String(description="用户名", example="alice"),
        "email": fields.String(required=False, description="邮箱(可选)", example="alice@example.com"),
        "role": fields.String(description="角色(admin/user)", example="admin"),
        "is_active": fields.Boolean(description="是否启用", example=True),
        "created_at": fields.String(required=False, description="ISO8601 时间戳", example="2025-01-01T00:00:00"),
        "last_login": fields.String(required=False, description="ISO8601 时间戳", example="2025-01-02T00:00:00"),
    },
)
MeSuccessEnvelope = make_success_envelope_model(ns, "MeSuccessEnvelope", MeData)


def _parse_payload() -> dict[str, Any]:
    if request.is_json:
        payload = request.get_json(silent=True)
        raw: object = payload if isinstance(payload, dict) else {}
    else:
        raw = request.form

    return parse_payload(
        raw,
        preserve_raw_fields=["password", "old_password", "new_password", "confirm_password"],
    )


@ns.route("/csrf-token")
class CsrfTokenResource(BaseResource):
    """CSRF Token 资源."""

    @ns.response(200, "OK", CsrfTokenSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取 CSRF Token."""

        def _execute():
            return self.success(
                data={"csrf_token": generate_csrf()},
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="auth",
            action="get_csrf_token",
            public_error="获取 CSRF Token 失败",
            context={"route": "api_v1.auth.csrf_token"},
        )


@ns.route("/login")
class LoginResource(BaseResource):
    """登录资源."""

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
        """执行登录."""

        def _execute():
            if request.is_json:
                parsed_json = request.get_json(silent=True)
                raw_payload: object = parsed_json if isinstance(parsed_json, dict) else {}
            else:
                raw_payload = request.form
            result = LoginService().login_from_payload(raw_payload)
            return self.success(
                data=result.to_payload(),
                message=SuccessMessages.LOGIN_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="auth",
            action="login",
            public_error="登录失败",
            context={"route": "api_v1.auth.login", "ip_address": request.remote_addr},
        )


@ns.route("/logout")
class LogoutResource(BaseResource):
    """登出资源."""

    @ns.response(200, "OK", EmptySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_login_required
    @require_csrf
    def post(self):
        """执行登出."""

        def _execute():
            logout_user()
            return self.success(message=SuccessMessages.LOGOUT_SUCCESS)

        return self.safe_call(
            _execute,
            module="auth",
            action="logout",
            public_error="登出失败",
            context={"user_id": getattr(current_user, "id", None), "route": "api_v1.auth.logout"},
        )


@ns.route("/change-password")
class ChangePasswordResource(BaseResource):
    """修改密码资源."""

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
        """修改密码."""
        payload = _parse_payload()

        def _execute():
            ChangePasswordService().change_password(payload, user=current_user._get_current_object())
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
    """刷新 Token 资源."""

    @ns.response(200, "OK", RefreshSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    @jwt_required(refresh=True)
    def post(self):
        """刷新访问 Token."""

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
    """当前用户信息资源."""

    @ns.response(200, "OK", MeSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @jwt_required()
    def get(self):
        """获取当前用户信息."""

        def _execute():
            payload = AuthMeReadService().get_me(identity=get_jwt_identity())
            return self.success(
                data=payload,
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="auth",
            action="get_me",
            public_error="获取当前用户信息失败",
            context={"route": "api_v1.auth.me"},
        )
