"""路由安全执行与结构化日志助手.

提供 `log_with_context` 与 `safe_route_call` 两个 helper,用于复用结构化日志字段,
并集中处理视图层的异常捕获,杜绝裸 `Exception` 与分散的 try/except 模板.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Literal, TypedDict, TypeVar, Unpack, cast

from flask_login import current_user
from werkzeug.exceptions import HTTPException

from app.errors import AppError, SystemError
from app.utils.structlog_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.types import ContextDict, LoggerExtra, RouteSafetyOptions

R = TypeVar("R")
LogLevel = Literal["debug", "info", "warning", "error", "critical"]
DEFAULT_EXPECTED_EXCEPTIONS: tuple[type[BaseException], ...] = (AppError, HTTPException)


class LogContextOptions(TypedDict, total=False):
    """结构化日志可选参数."""

    context: ContextDict | None
    extra: LoggerExtra | None
    include_actor: bool


def log_with_context(
    level: LogLevel,
    event: str,
    *,
    module: str,
    action: str,
    **options: Unpack[LogContextOptions],
) -> None:
    """记录带有统一上下文字段的结构化日志.

    Args:
        level: 日志级别,使用 structlog 的方法名,例如 "info"、"error".
        event: 日志事件描述,建议使用动词短语.
        module: 所属模块或领域,用于快速过滤.
        action: 当前操作名称,通常对应视图或任务函数名.
        **options: 支持 context、extra、include_actor 选项以扩展日志内容.

    """
    logger = get_logger("app")
    payload: ContextDict = {"module": module, "action": action}

    include_actor = options.get("include_actor", True)
    if include_actor:
        try:
            actor_id = getattr(current_user, "id", None)
        except RuntimeError:
            actor_id = None
        if actor_id is not None:
            payload.setdefault("actor_id", actor_id)

    context_opt = cast("ContextDict | None", options.get("context"))
    extra_opt = cast("LoggerExtra | None", options.get("extra"))
    if context_opt:
        payload.update(context_opt)
    if extra_opt:
        payload.update(extra_opt)

    log_method = getattr(logger, level, logger.error)
    log_method(event, **payload)


def safe_route_call(
    func: Callable[..., R],
    *,
    module: str,
    action: str,
    public_error: str,
    func_args: tuple[Any, ...] | None = None,
    func_kwargs: dict[str, Any] | None = None,
    **options: Unpack[RouteSafetyOptions],
) -> R:
    """安全执行视图逻辑,集中处理日志与异常转换.

    Args:
        func: 真实的业务函数,建议为局部闭包以捕获参数.
        *func_args: 传入业务函数的可变位置参数.
        module: 记录日志用的模块名称.
        action: 业务动作名称,例如 "get_account_permissions".
        public_error: 暴露给客户端的统一错误文案.
        func_kwargs: 传入业务函数的命名参数字典.
        **options: 安全包装配置,支持 context、extra、expected_exceptions、
            fallback_exception、log_event、include_actor 等键.

    Returns:
        业务函数的执行结果,通常是 Flask 的响应对象.

    Raises:
        AppError: 当业务逻辑主动抛出或 fallback_exception 包装时.

    """
    handled_exceptions = DEFAULT_EXPECTED_EXCEPTIONS
    expected_exceptions = options.get("expected_exceptions")
    if expected_exceptions:
        handled_exceptions += expected_exceptions

    fallback_exception = options.get("fallback_exception", SystemError)
    event = options.get("log_event") or f"{action}执行失败"
    include_actor = options.get("include_actor", True)
    context_payload: ContextDict = dict(cast("ContextDict | None", options.get("context")) or {})
    extra_payload: LoggerExtra = dict(cast("LoggerExtra | None", options.get("extra")) or {})

    try:
        call_kwargs = func_kwargs or {}
        call_args = func_args or ()
        return func(*call_args, **call_kwargs)
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
