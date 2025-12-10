"""鲸落 - 统一响应工具
提供统一的成功/错误响应结构,避免在业务层散落 JSON 拼装逻辑.
"""

from __future__ import annotations

from typing import Mapping

from flask import Response, jsonify

from app.constants import HttpStatus
from app.constants.system_constants import ErrorCategory, ErrorSeverity, SuccessMessages
from app.errors import AppError, map_exception_to_status
from app.types import JsonDict, JsonValue
from app.utils.structlog_config import ErrorContext, enhanced_error_handler
from app.utils.time_utils import time_utils


def unified_success_response(
    data: JsonValue | JsonDict | list[JsonDict] | None = None,
    message: str | None = None,
    *,
    status: int = HttpStatus.OK,
    meta: Mapping[str, JsonValue] | None = None,
) -> tuple[JsonDict, int]:
    """生成统一的成功响应载荷.

    Args:
        data: 响应数据,可选.
        message: 成功消息,可选,默认为"操作成功".
        status: HTTP 状态码,默认为 200.
        meta: 元数据,可选.

    Returns:
        包含两个元素的元组:
        - 响应载荷字典
        - HTTP 状态码

    """
    payload: JsonDict = {
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
    extra: Mapping[str, JsonValue] | None = None,
    context: ErrorContext | None = None,
) -> tuple[JsonDict, int]:
    """生成统一的错误响应载荷.

    Args:
        error: 异常对象.
        status_code: HTTP 状态码,可选,默认根据异常类型自动映射.
        extra: 额外的错误信息,可选.
        context: 错误上下文,可选.

    Returns:
        包含两个元素的元组:
        - 错误响应载荷字典
        - HTTP 状态码

    """
    context = context or ErrorContext(error)
    payload = enhanced_error_handler(error, context, extra=extra)
    final_status = status_code or map_exception_to_status(error, default=HttpStatus.INTERNAL_SERVER_ERROR)
    payload.setdefault("success", False)
    return payload, final_status


def jsonify_unified_success(*args: object, **kwargs: object) -> tuple[Response, int]:
    """返回 Flask Response 对象的成功响应便捷函数.

    Args:
        *args: 传递给 unified_success_response 的位置参数.
        **kwargs: 传递给 unified_success_response 的关键字参数.

    Returns:
        Flask Response 对象和 HTTP 状态码的元组.

    """
    payload, status = unified_success_response(*args, **kwargs)
    return jsonify(payload), status


def jsonify_unified_error(*args: object, **kwargs: object) -> tuple[Response, int]:
    """返回 Flask Response 对象的错误响应便捷函数.

    Args:
        *args: 传递给 unified_error_response 的位置参数.
        **kwargs: 传递给 unified_error_response 的关键字参数.

    Returns:
        Flask Response 对象和 HTTP 状态码的元组.

    """
    payload, status = unified_error_response(*args, **kwargs)
    return jsonify(payload), status


def jsonify_unified_error_message(
    message: str,
    *,
    status_code: int = HttpStatus.BAD_REQUEST,
    message_key: str = "INVALID_REQUEST",
    category: ErrorCategory | None = None,
    severity: ErrorSeverity | None = None,
    extra: Mapping[str, JsonValue] | None = None,
) -> tuple[Response, int]:
    """基于简单消息快速生成错误响应.

    Args:
        message: 错误消息.
        status_code: HTTP 状态码,默认为 400.
        message_key: 消息键,默认为 'INVALID_REQUEST'.
        category: 错误类别,可选.
        severity: 错误严重程度,可选.
        extra: 额外的错误信息,可选.

    Returns:
        Flask Response 对象和 HTTP 状态码的元组.

    """
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
