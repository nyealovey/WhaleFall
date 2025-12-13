"""SQLAlchemy Query 协议类型别名."""

from __future__ import annotations

from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class QueryProtocol(Protocol[T_co]):
    """最小化的 SQLAlchemy Query 协议,用于类型标注."""

    def join(self, *args: object, **kwargs: object) -> QueryProtocol[T_co]:
        """协议方法: 关联查询."""
        ...

    def filter(self, *args: object, **kwargs: object) -> QueryProtocol[T_co]:
        """协议方法: 过滤记录."""
        ...

    def filter_by(self, **kwargs: object) -> QueryProtocol[T_co]:
        """协议方法: 按字段过滤记录."""
        ...

    def order_by(self, *args: object, **kwargs: object) -> QueryProtocol[T_co]:
        """协议方法: 排序记录."""
        ...

    def limit(self, count: int) -> QueryProtocol[T_co]:
        """协议方法: 限制返回条数."""
        ...

    def all(self) -> list[T_co]:
        """协议方法: 返回全部记录."""
        ...

    def count(self) -> int:
        """协议方法: 统计数量."""
        ...

    def first(self) -> T_co | None:
        """协议方法: 返回首条记录."""
        ...


__all__ = ["QueryProtocol"]
