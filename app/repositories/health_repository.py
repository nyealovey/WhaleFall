"""健康检查 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from sqlalchemy import text

from app import db


class HealthRepository:
    """健康检查读模型 Repository."""

    @staticmethod
    def ping_database() -> None:
        db.session.execute(text("SELECT 1"))

