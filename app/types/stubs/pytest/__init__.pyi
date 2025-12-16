from __future__ import annotations

from typing import Any, Callable, TypeVar

_T = TypeVar("_T")


class _MarkDecorator:
    def __getattr__(self, name: str) -> "_MarkDecorator": ...
    def __call__(self, obj: Callable[..., _T]) -> _T: ...


mark: _MarkDecorator

def fail(message: str | None = ...) -> None: ...
