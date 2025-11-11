"""Context variables shared across structured logging modules."""

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)

__all__ = ["request_id_var", "user_id_var"]
