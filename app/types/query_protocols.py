"""SQLAlchemy Query 协议类型别名."""

from __future__ import annotations

from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class QueryProtocol(Protocol[T_co]):
    """最小化的 SQLAlchemy Query 协议,用于类型标注."""

    def join(self, *args: object, **kwargs: object) -> "QueryProtocol[T_co]":
        ...

    def filter(self, *args: object, **kwargs: object) -> "QueryProtocol[T_co]":
        ...

    def filter_by(self, **kwargs: object) -> "QueryProtocol[T_co]":
        ...

    def order_by(self, *args: object, **kwargs: object) -> "QueryProtocol[T_co]":
        ...

    def limit(self, count: int) -> "QueryProtocol[T_co]":
        ...

    def all(self) -> list[T_co]:
        ...

    def count(self) -> int:
        ...

    def first(self) -> T_co | None:
        ...


__all__ = ["QueryProtocol"]
