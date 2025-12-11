"""路由安全执行与结构化日志助手.

提供 `log_with_context` 与 `safe_route_call` 两个 helper,用于复用结构化日志字段,
并集中处理视图层的异常捕获,杜绝裸 `Exception` 与分散的 try/except 模板.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, ParamSpec, TypeVar

from flask_login import current_user
from werkzeug.exceptions import HTTPException

from app.errors import AppError, SystemError
from app.utils.structlog_config import get_logger

if TYPE_CHECKING:
    from app.types import ContextDict, LoggerExtra

P = ParamSpec("P")
R = TypeVar("R")
LogLevel = Literal["debug", "info", "warning", "error", "critical"]
DEFAULT_EXPECTED_EXCEPTIONS: tuple[type[BaseException], ...] = (AppError, HTTPException)


def log_with_context(
    level: LogLevel,
    event: str,
    *,
    module: str,
    action: str,
    context: ContextDict | None = None,
    extra: LoggerExtra | None = None,
    include_actor: bool = True,
) -> None:
    """记录带有统一上下文字段的结构化日志.

    Args:
        level: 日志级别,使用 structlog 的方法名,例如 "info"、"error".
        event: 日志事件描述,建议使用动词短语.
        module: 所属模块或领域,用于快速过滤.
        action: 当前操作名称,通常对应视图或任务函数名.
        context: 额外的业务上下文字段,会直接展开到日志中.
        extra: 自定义补充字段,例如错误类型、计数等.
        include_actor: 是否自动附加当前用户 ID,默认为 True.

    """

    logger = get_logger("app")
    payload: ContextDict = {"module": module, "action": action}

    if include_actor:
        try:
            actor_id = getattr(current_user, "id", None)
        except RuntimeError:
            actor_id = None
        if actor_id is not None:
            payload.setdefault("actor_id", actor_id)

    if context:
        payload.update(context)
    if extra:
        payload.update(extra)

    log_method = getattr(logger, level, logger.error)
    log_method(event, **payload)


def safe_route_call(
    func: Callable[P, R],
    *func_args: P.args,
    module: str,
    action: str,
    public_error: str,
    context: ContextDict | None = None,
    extra: LoggerExtra | None = None,
    expected_exceptions: tuple[type[BaseException], ...] | None = None,
    fallback_exception: type[AppError] = SystemError,
    log_event: str | None = None,
    include_actor: bool = True,
    **func_kwargs: P.kwargs,
) -> R:
    """安全执行视图逻辑,集中处理日志与异常转换.

    Args:
        func: 真实的业务函数,建议为局部闭包以捕获参数.
        *func_args: 传入业务函数的可变位置参数.
        module: 记录日志用的模块名称.
        action: 业务动作名称,例如 "get_account_permissions".
        public_error: 暴露给客户端的统一错误文案.
        context: 日志上下文字段,如 `{"account_id": 1}`.
        extra: 额外的日志字段,通常承载统计值.
        expected_exceptions: 允许直接透传并记录的异常类型集合.
        fallback_exception: 将未知异常转换成的业务异常类型,默认为 SystemError.
        log_event: 自定义日志事件文案,缺省为 ``f"{action}执行失败"``.
        include_actor: 是否在日志中注入当前用户 ID.
        **func_kwargs: 传入业务函数的命名参数.

    Returns:
        业务函数的执行结果,通常是 Flask 的响应对象.

    Raises:
        AppError: 当业务逻辑主动抛出或 fallback_exception 包装时.

    """

    handled_exceptions = DEFAULT_EXPECTED_EXCEPTIONS
    if expected_exceptions:
        handled_exceptions += expected_exceptions

    event = log_event or f"{action}执行失败"
    context_payload: ContextDict = dict(context or {})
    extra_payload: LoggerExtra = dict(extra or {})

    try:
        return func(*func_args, **func_kwargs)
    except handled_exceptions as exc:
        log_with_context(
            "warning",
            event,
            module=module,
            action=action,
            context=context_payload,
            extra={**extra_payload, "error_type": exc.__class__.__name__, "error_message": str(exc)},
            include_actor=include_actor,
        )
        raise
    except Exception as exc:
        log_with_context(
            "error",
            event,
            module=module,
            action=action,
            context=context_payload,
            extra={**extra_payload, "error_type": exc.__class__.__name__, "unexpected": True},
            include_actor=include_actor,
        )
        raise fallback_exception(public_error) from exc
