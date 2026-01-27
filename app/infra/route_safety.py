"""事务边界安全执行与结构化日志助手.

提供 `log_with_context` 与 `safe_route_call` 两个 helper,用于复用结构化日志字段,
并集中处理视图层的异常捕获,杜绝裸 `Exception` 与分散的 try/except 模板.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, TypedDict, TypeVar, Unpack, cast

from flask_login import current_user
from werkzeug.exceptions import HTTPException

from app import db
from app.core.exceptions import AppError, SystemError
from app.utils.structlog_config import get_logger

if TYPE_CHECKING:
    from app.core.types import ContextDict, ContextMapping, LoggerExtra, RouteSafetyOptions

R = TypeVar("R")
LogLevel = Literal["debug", "info", "warning", "error", "critical"]
DEFAULT_EXPECTED_EXCEPTIONS: tuple[type[BaseException], ...] = (AppError, HTTPException)


class LogContextOptions(TypedDict, total=False):
    """结构化日志可选参数."""

    context: ContextMapping | None
    extra: LoggerExtra | None
    include_actor: bool
    logger_name: str


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
        level: 日志级别,使用 structlog 的方法名,例如 "info", "error".
        event: 日志事件描述,建议使用动词短语.
        module: 所属模块或领域,用于快速过滤.
        action: 当前操作名称,通常对应视图或任务函数名.
        **options: 支持 context, extra, include_actor 选项以扩展日志内容.

    """
    logger_name = options.get("logger_name", "app")
    logger = get_logger(logger_name)
    payload: ContextDict = {"module": module, "action": action}

    include_actor = options.get("include_actor", True)
    if include_actor:
        try:
            actor_id = getattr(current_user, "id", None)
        except RuntimeError:
            actor_id = None
        if actor_id is not None:
            payload.setdefault("actor_id", actor_id)

    context_opt = cast("ContextMapping | None", options.get("context"))
    extra_opt = cast("LoggerExtra | None", options.get("extra"))
    if context_opt:
        payload.update(context_opt)
    if extra_opt:
        payload.update(extra_opt)

    log_method = getattr(logger, level, logger.error)
    log_method(event, **payload)


def log_fallback(
    level: LogLevel,
    event: str,
    *,
    module: str,
    action: str,
    fallback_reason: str,
    **options: Unpack[LogContextOptions],
) -> None:
    """记录降级/回退/Workaround 的结构化日志(强制 `fallback=true`).

    说明：
    - 该 helper 用于统一回退口径字段，避免各处自定义 key 导致不可检索。
    - 调用方仍需在 `context/extra` 中补充关键维度（instance_id/task/...）。
    """
    extra_opt = dict(cast("LoggerExtra | None", options.get("extra")) or {})
    extra_opt["fallback"] = True
    extra_opt["fallback_reason"] = fallback_reason

    log_with_context(
        level,
        event,
        module=module,
        action=action,
        context=cast("ContextMapping | None", options.get("context")),
        extra=extra_opt,
        include_actor=options.get("include_actor", True),
        logger_name=options.get("logger_name", "app"),
    )


def safe_route_call(
    func: Callable[[], R],
    *,
    module: str,
    action: str,
    public_error: str,
    **options: Unpack[RouteSafetyOptions],
) -> R:
    """安全执行视图逻辑,集中处理日志与异常转换.

    Args:
        func: 真实的业务函数,建议为局部闭包以捕获参数.
        module: 记录日志用的模块名称.
        action: 业务动作名称,例如 "get_account_permissions".
        public_error: 暴露给客户端的统一错误文案.
        **options: 安全包装配置,支持 context, extra, expected_exceptions,
            fallback_exception, log_event, include_actor 等键.

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
    context_payload: ContextDict = dict(cast("ContextMapping | None", options.get("context")) or {})
    extra_payload: LoggerExtra = dict(cast("LoggerExtra | None", options.get("extra")) or {})

    try:
        result = func()
    except handled_exceptions as exc:
        db.session.rollback()
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
        db.session.rollback()
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
    else:
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            log_with_context(
                "error",
                event,
                module=module,
                action=action,
                context=context_payload,
                extra={
                    **extra_payload,
                    "error_type": exc.__class__.__name__,
                    "unexpected": True,
                    "commit_failed": True,
                },
                include_actor=include_actor,
            )
            raise fallback_exception(public_error) from exc
        return result
