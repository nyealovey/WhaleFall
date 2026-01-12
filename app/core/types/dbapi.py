"""DB-API 协议定义,供连接适配器复用."""

from __future__ import annotations

from typing import Protocol


class DBAPICursor(Protocol):
    """最小化 DB-API 游标协议."""

    def execute(self, query: str, params: object = ...) -> object:  # pragma: no cover - protocol
        """执行 SQL 语句."""
        ...

    def fetchall(self) -> object:  # pragma: no cover - protocol
        """返回查询结果."""
        ...

    def close(self) -> None:  # pragma: no cover - protocol
        """关闭游标."""
        ...


class DBAPIConnection(Protocol):
    """最小化 DB-API 连接协议."""

    def cursor(self, *args: object, **kwargs: object) -> object:  # pragma: no cover - protocol
        """获取游标."""
        ...

    def close(self) -> None:  # pragma: no cover - protocol
        """关闭连接."""
        ...


__all__ = ["DBAPIConnection", "DBAPICursor"]
