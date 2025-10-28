"""
鲸落 - 统一响应工具
提供统一的成功/错误响应结构，避免在业务层散落 JSON 拼装逻辑
"""

from __future__ import annotations

from typing import Any, Mapping

from flask import jsonify

from app.constants import HttpStatus, TaskStatus
from app.constants.system_constants import ErrorCategory, ErrorSeverity, SuccessMessages
from app.errors import AppError, map_exception_to_status
from app.utils.structlog_config import ErrorContext, enhanced_error_handler
from app.utils.time_utils import time_utils


def unified_success_response(
    data: Any | None = None,
    message: str | None = None,
    *,
    status: int = HttpStatus.OK,
    meta: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """生成统一的成功响应载荷"""
    payload: dict[str, Any] = {
        "success": True,
        "error": False,
        "message": message or SuccessMessages.OPERATION_SUCCESS,
        "timestamp": time_utils.now().isoformat(),
    }
    if data is not None:
        payload["data"] = data
    if meta:
        payload["meta"] = dict(meta)
    return payload, status


def unified_error_response(
    error: Exception,
    *,
    status_code: int | None = None,
    extra: Mapping[str, Any] | None = None,
    context: ErrorContext | None = None,
) -> tuple[dict[str, Any], int]:
    """生成统一的错误响应载荷"""
    context = context or ErrorContext(error)
    payload = enhanced_error_handler(error, context, extra=extra)
    final_status = status_code or map_exception_to_status(error, default=HttpStatus.INTERNAL_SERVER_ERROR)
    payload.setdefault("success", False)
    return payload, final_status


def jsonify_unified_success(*args, **kwargs):
    """返回 Flask Response 对象的成功响应便捷函数"""
    payload, status = unified_success_response(*args, **kwargs)
    return jsonify(payload), status


def jsonify_unified_error(*args, **kwargs):
    """返回 Flask Response 对象的错误响应便捷函数"""
    payload, status = unified_error_response(*args, **kwargs)
    return jsonify(payload), status


def jsonify_unified_error_message(
    message: str,
    *,
    status_code: int = HttpStatus.BAD_REQUEST,
    message_key: str = "INVALID_REQUEST",
    category: ErrorCategory | None = None,
    severity: ErrorSeverity | None = None,
    extra: Mapping[str, Any] | None = None,
):
    """基于简单消息快速生成错误响应"""
    error = AppError(
        message=message,
        message_key=message_key,
        status_code=status_code,
        category=category or ErrorCategory.SYSTEM,
        severity=severity or ErrorSeverity.MEDIUM,
        extra=extra,
    )
    payload, status = unified_error_response(error, status_code=status_code, extra=extra)
    return jsonify(payload), status
