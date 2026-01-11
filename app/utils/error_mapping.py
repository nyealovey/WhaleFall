"""WhaleFall - 异常与 HTTP 状态码映射.

该模块属于 HTTP 边界适配层,用于将异常转换为对外 HTTP 状态码.
`app/errors` 只负责定义异常类型与元数据,不感知 Flask/Werkzeug 等框架细节.
"""

from __future__ import annotations

from werkzeug.exceptions import HTTPException

from app.constants import HttpStatus
from app.errors import AppError


def map_exception_to_status(error: Exception, default: int = HttpStatus.INTERNAL_SERVER_ERROR) -> int:
    """根据异常类型推导 HTTP 状态码.

    Args:
        error: 捕获到的异常对象.
        default: 无法匹配时的默认状态码.

    Returns:
        int: 与异常对应的 HTTP 状态码.

    """
    if isinstance(error, AppError):
        return error.status_code

    if isinstance(error, HTTPException):
        code = getattr(error, "code", None)
        if code is not None:
            return int(code)

    return default


__all__ = ["map_exception_to_status"]

