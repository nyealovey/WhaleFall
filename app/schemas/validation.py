"""Schema 校验与错误映射."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.errors import ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


class SchemaMessageKeyError(ValueError):
    """用于从 schema validator 透传 message_key 的错误类型."""

    def __init__(self, message: str, *, message_key: str) -> None:
        """构造错误并携带 message_key."""
        super().__init__(message)
        self.message_key = message_key


def validate_or_raise(
    model: type[ModelT],
    payload: object,
    *,
    message_key: str | None = None,
    message_key_by_field: Mapping[str, str] | None = None,
) -> ModelT:
    """执行 schema 校验并抛出项目的 ValidationError.

    Args:
        model: pydantic model.
        payload: 待校验的 payload(通常来自 request payload adapter).
        message_key: 默认 message_key, 当无法按字段映射时使用.
        message_key_by_field: 按字段映射 message_key 的字典.

    """
    try:
        return model.model_validate(payload)
    except PydanticValidationError as exc:
        message, field, schema_message_key = _extract_first_error(exc)
        resolved_key = schema_message_key or message_key
        if field and message_key_by_field:
            resolved_key = message_key_by_field.get(field, resolved_key)
        raise ValidationError(message, message_key=resolved_key) from None


def _extract_first_error(exc: PydanticValidationError) -> tuple[str, str | None, str | None]:
    errors = exc.errors()
    if not errors:
        return "参数校验失败", None, None

    first = errors[0]
    field = None
    loc = first.get("loc")
    if isinstance(loc, tuple) and loc and isinstance(loc[0], str):
        field = loc[0]

    ctx = first.get("ctx")
    if isinstance(ctx, dict) and "error" in ctx:
        raw_error = ctx.get("error")
        if isinstance(raw_error, SchemaMessageKeyError):
            return str(raw_error), field, raw_error.message_key
        if isinstance(raw_error, BaseException):
            return str(raw_error), field, None

    msg = first.get("msg")
    if isinstance(msg, str) and msg.strip():
        return msg, field, None

    return "参数校验失败", field, None
