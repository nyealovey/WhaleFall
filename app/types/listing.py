"""列表/分页通用结构类型."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class PaginatedResult(Generic[T]):
    """通用分页结果结构."""

    items: list[T]
    total: int
    page: int
    pages: int
    limit: int
