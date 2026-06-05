"""Auth namespace (Phase 3 全量覆盖 - 认证模块)."""

from __future__ import annotations

from typing import Any, cast

from flask import request
from flask_login import current_user, logout_user
from flask_restx import Namespace, fields
from flask_wtf.csrf import generate_csrf

from app import limiter
from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource, get_raw_payload
from app.api.v1.resources.decorators import api_login_required
from app.core.constants.system_constants import SuccessMessages
from app.infra.rate_limiting import build_login_rate_limit, login_rate_limit_key, password_reset_rate_limit_key
from app.models.user import User
from app.services.auth import AuthMeReadService, ChangePasswordService, LoginService
from app.utils.decorators import require_csrf
from app.utils.user_role_utils import get_user_role_permissions

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
        "auth_model": fields.String(description="认证模式", example="session"),
        "csrf_token": fields.String(description="CSRF token", example="csrf_token_example"),
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

SessionData = ns.model(
    "SessionData",
    {
        "authenticated": fields.Boolean(description="是否已通过 session 登录", example=True),
        "auth_model": fields.String(description="认证模式", example="session"),
        "csrf_token": fields.String(description="CSRF token", example="csrf_token_example"),
        "permissions": fields.List(fields.String, description="当前角色权限列表", example=["read", "admin"]),
        "user": fields.Raw(description="当前用户信息；未登录时为 null", example=None),
    },
)
SessionSuccessEnvelope = make_success_envelope_model(ns, "SessionSuccessEnvelope", SessionData)


def _build_session_payload() -> dict[str, object]:
    """构造前端启动所需的 session 认证状态."""
    if not current_user.is_authenticated:
        return {
            "authenticated": False,
            "auth_model": "session",
            "csrf_token": generate_csrf(),
            "permissions": [],
            "user": None,
        }

    user = cast(User, current_user._get_current_object())
    user_payload = AuthMeReadService.to_payload(user)
    role = str(user_payload.get("role") or "")
    return {
        "authenticated": True,
        "auth_model": "session",
        "csrf_token": generate_csrf(),
        "permissions": get_user_role_permissions(role),
        "user": user_payload,
    }


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
    @limiter.limit(build_login_rate_limit, key_func=login_rate_limit_key)
    @require_csrf
    def post(self):
        """执行登录."""

        def _execute():
            raw_payload: Any = get_raw_payload()
            result = LoginService().login_from_payload(raw_payload)
            payload = result.to_payload()
            payload["csrf_token"] = generate_csrf()
            return self.success(data=payload, message=SuccessMessages.LOGIN_SUCCESS)

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


@ns.route("/session")
class SessionResource(BaseResource):
    """当前 session 状态资源."""

    @ns.response(200, "OK", SessionSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取当前 session 认证状态."""

        def _execute():
            return self.success(
                data=_build_session_payload(),
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="auth",
            action="get_session",
            public_error="获取 session 状态失败",
            context={"route": "api_v1.auth.session"},
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
    @limiter.limit("3 per hour", key_func=password_reset_rate_limit_key)
    @require_csrf
    def post(self):
        """修改密码."""
        raw_payload: Any = get_raw_payload()

        def _execute():
            ChangePasswordService().change_password(raw_payload, user=current_user._get_current_object())
            return self.success(message=SuccessMessages.PASSWORD_CHANGED)

        return self.safe_call(
            _execute,
            module="auth",
            action="submit_change_password",
            public_error="密码修改失败",
            context={"user_id": getattr(current_user, "id", None)},
        )


@ns.route("/me")
class MeResource(BaseResource):
    """当前用户信息资源."""

    @ns.response(200, "OK", MeSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_login_required
    def get(self):
        """获取当前用户信息."""

        def _execute():
            payload = AuthMeReadService.to_payload(cast(User, current_user._get_current_object()))
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
