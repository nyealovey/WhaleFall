"""鲸落 - 统一响应工具.

提供统一的成功/错误响应结构,避免在业务层散落 JSON 拼装逻辑.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from flask import Response, jsonify

from app.constants import HttpStatus
from app.constants.system_constants import ErrorCategory, ErrorSeverity, SuccessMessages
from app.errors import AppError, map_exception_to_status
from app.utils.structlog_config import ErrorContext, enhanced_error_handler
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Mapping

    from app.types import JsonDict, JsonValue


def unified_success_response(
    data: object | None = None,
    message: object | None = None,
    *,
    status: int = HttpStatus.OK,
    meta: Mapping[str, object] | None = None,
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
        "message": str(message) if message is not None else SuccessMessages.OPERATION_SUCCESS,
        "timestamp": time_utils.now().isoformat(),
    }
    if data is not None:
        payload["data"] = cast("JsonValue | JsonDict | list[JsonDict]", data)
    if meta:
        payload["meta"] = cast("JsonDict", dict(meta))
    return payload, status


def unified_error_response(
    error: BaseException | Exception,
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
    safe_error = error if isinstance(error, Exception) else Exception(str(error))
    context = context or ErrorContext(safe_error)
    payload = cast("JsonDict", enhanced_error_handler(safe_error, context, extra=extra))
    final_status = status_code or map_exception_to_status(safe_error, default=HttpStatus.INTERNAL_SERVER_ERROR)
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
    payload, status = unified_error_response(*args, **kwargs)  # type: ignore[arg-type]
    return jsonify(payload), status


def jsonify_unified_error_message(
    message: str,
    *,
    status_code: int = HttpStatus.BAD_REQUEST,
    message_key: str = "INVALID_REQUEST",
    **options: Mapping[str, object],
) -> tuple[Response, int]:
    """基于简单消息快速生成错误响应.

    Args:
        message: 错误消息.
        status_code: HTTP 状态码,默认为 400.
        message_key: 消息键,默认为 'INVALID_REQUEST'.
        **options: 兼容 category/severity/extra 等可选元数据.

    Returns:
        Flask Response 对象和 HTTP 状态码的元组.

    """
    category_value = options.get("category")
    if isinstance(category_value := options.get("category"), ErrorCategory):
        category_cast = category_value
    else:
        category_cast = ErrorCategory.SYSTEM

    severity_value = options.get("severity")
    if isinstance(severity_value, ErrorSeverity):
        severity_cast = severity_value
    else:
        severity_cast = ErrorSeverity.MEDIUM

    extra_mapping = options.get("extra")
    extra_cast = cast("Mapping[str, JsonValue] | None", extra_mapping) if isinstance(extra_mapping, Mapping) else None

    error = AppError(
        message=message,
        message_key=message_key,
        status_code=status_code,
        category=category_cast,
        severity=severity_cast,
        extra=extra_cast,
    )
    payload, status = unified_error_response(
        error,
        status_code=status_code,
        extra=cast("Mapping[str, JsonValue] | None", options.get("extra")),
    )
    return jsonify(payload), status
