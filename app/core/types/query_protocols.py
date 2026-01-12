"""SQLAlchemy Query 协议类型别名."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, TypeVar

# 协变会导致部分 SQLAlchemy stub 触发 pyright 协变警告,此处改为默认不变
T = TypeVar("T")


class QueryProtocol(Protocol[T]):
    """最小化的 SQLAlchemy Query 协议,用于类型标注."""

    def join(self, *args: object, **kwargs: object) -> QueryProtocol[T]:
        """协议方法: 关联查询."""
        ...

    def outerjoin(self, *args: object, **kwargs: object) -> QueryProtocol[T]:
        """协议方法: 左外连接记录."""
        ...

    def filter(self, *args: object, **kwargs: object) -> QueryProtocol[T]:
        """协议方法: 过滤记录."""
        ...

    def filter_by(self, **kwargs: object) -> QueryProtocol[T]:
        """协议方法: 按字段过滤记录."""
        ...

    def order_by(self, *args: object, **kwargs: object) -> QueryProtocol[T]:
        """协议方法: 排序记录."""
        ...

    def group_by(self, *args: object, **kwargs: object) -> QueryProtocol[T]:
        """协议方法: 分组记录."""
        ...

    def limit(self, count: int) -> QueryProtocol[T]:
        """协议方法: 限制返回条数."""
        ...

    def offset(self, count: int) -> QueryProtocol[T]:
        """协议方法: 设置查询偏移量."""
        ...

    def with_entities(self, *entities: object) -> QueryProtocol[Any]:
        """协议方法: 仅选择指定字段/实体."""
        ...

    def subquery(self) -> Any:
        """协议方法: 生成子查询表达式."""
        ...

    def all(self) -> list[T]:
        """协议方法: 返回全部记录."""
        ...

    def count(self) -> int:
        """协议方法: 统计数量."""
        ...

    def distinct(self, *args: object) -> QueryProtocol[T]:
        """协议方法: 去重记录."""
        ...

    def first(self) -> T | None:
        """协议方法: 返回首条记录."""
        ...

    def paginate(self, *, page: int, per_page: int, error_out: bool = ...) -> Any:
        """协议方法: 按页返回结果."""
        ...

    def scalar(self) -> T:
        """协议方法: 返回标量结果."""
        ...

    def iter_rows(self) -> Iterable[T]:
        """协议方法: 迭代结果行."""
        ...


__all__ = ["QueryProtocol"]
