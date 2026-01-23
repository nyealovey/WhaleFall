"""请求级别的上下文注入与 wide event 发射(Infra).

目标：
- 让 request_id/user_id 通过 contextvars 在整个请求生命周期可用（用于日志关联与错误封套）。
- 统一填充 `g` 上的 request 元信息，供日志 handler 落库到 UnifiedLog.context。
- 在请求完成时发射一条 canonical/wide event：每请求一次、字段稳定、可聚合。
"""

from __future__ import annotations

import re
import time
from contextlib import suppress
from typing import TYPE_CHECKING
from uuid import uuid4

from flask import Flask, g, request
from flask_login import current_user

from app.utils.logging.context_vars import request_id_var, user_id_var
from app.utils.structlog_config import get_logger

if TYPE_CHECKING:
    from contextvars import Token

    from werkzeug.wrappers.response import Response

_REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_MAX_LEN = 128
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _generate_request_id() -> str:
    # 带前缀便于在日志/排障中快速识别其语义（而不是误认为 error_id 等）。
    return f"req_{uuid4().hex}"


def _sanitize_request_id(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    value = raw_value.strip()
    if not value or len(value) > _REQUEST_ID_MAX_LEN:
        return None
    if not _REQUEST_ID_PATTERN.match(value):
        return None
    return value


def register_request_logging(app: Flask) -> None:
    """注册请求级别的上下文注入与 wide event."""

    @app.before_request
    def _bind_request_context() -> None:
        incoming_request_id = _sanitize_request_id(request.headers.get(_REQUEST_ID_HEADER))
        request_id = incoming_request_id or _generate_request_id()

        request_id_token: Token[str | None] = request_id_var.set(request_id)
        user_id_token: Token[int | None] = user_id_var.set(_resolve_user_id())

        # 保存 token，确保 teardown 时 reset（避免 contextvars 在同线程后续请求间泄漏）。
        g._request_id_token = request_id_token
        g._user_id_token = user_id_token

        # 统一的请求元信息（供 UnifiedLog.context 落库；避免把 querystring 原样写入日志）。
        g.request_id = request_id
        g.url = request.path
        g.method = request.method
        g.host = request.host
        g.ip_address = request.remote_addr
        user_agent = getattr(request, "user_agent", None)
        g.user_agent = getattr(user_agent, "string", None) if user_agent else None
        g.endpoint = request.endpoint
        url_rule = getattr(request, "url_rule", None)
        g.route = getattr(url_rule, "rule", None) if url_rule else None

        g._request_start_perf = time.perf_counter()

    @app.after_request
    def _emit_request_wide_event(response: Response) -> Response:
        request_id = request_id_var.get() or getattr(g, "request_id", None) or _generate_request_id()
        response.headers.setdefault(_REQUEST_ID_HEADER, request_id)

        duration_ms = None
        started_at = getattr(g, "_request_start_perf", None)
        if isinstance(started_at, (float, int)):
            duration_ms = round((time.perf_counter() - float(started_at)) * 1000)

        status_code = int(getattr(response, "status_code", 0) or 0)
        outcome = "success" if status_code and status_code < 400 else "error"

        logger = get_logger("http")
        logger.info(
            "http_request_completed",
            module="http",
            action=_format_action(),
            status_code=status_code,
            outcome=outcome,
            duration_ms=duration_ms,
            route=getattr(g, "route", None),
            endpoint=getattr(g, "endpoint", None),
            error_id=getattr(g, "_request_error_id", None),
            error_type=getattr(g, "_request_error_type", None),
        )
        return response

    @app.teardown_request
    def _reset_request_context(_exc: BaseException | None) -> None:
        # reset() 只接受 Token，因此必须从 g 取回；异常/提前返回路径下可能缺失。
        request_id_token = getattr(g, "_request_id_token", None)
        user_id_token = getattr(g, "_user_id_token", None)
        with suppress(LookupError, RuntimeError):
            if request_id_token is not None:
                request_id_var.reset(request_id_token)
                g._request_id_token = None
        with suppress(LookupError, RuntimeError):
            if user_id_token is not None:
                user_id_var.reset(user_id_token)
                g._user_id_token = None


def _resolve_user_id() -> int | None:
    with suppress(RuntimeError, AttributeError):
        if current_user and getattr(current_user, "is_authenticated", False):
            user_id = getattr(current_user, "id", None)
            return int(user_id) if isinstance(user_id, (int, str)) and str(user_id).isdigit() else None
    return None


def _format_action() -> str:
    method = request.method
    path = request.path
    return f"{method} {path}"


__all__ = ["register_request_logging"]
