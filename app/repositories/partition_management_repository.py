"""分区管理 Repository.

职责:
- 封装分区相关 SQL 执行与查询
- 不做业务编排、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.sql import table

from app import db


class PartitionManagementRepository:
    """分区管理 Repository(PostgreSQL)."""

    @staticmethod
    def create_partition_table(
        *,
        partition_name: str,
        base_table_name: str,
        month_start: date,
        month_end: date,
        comment: str,
    ) -> None:
        """创建分区表并添加注释."""
        create_sql = (
            f"CREATE TABLE {partition_name} "
            f"PARTITION OF {base_table_name} "
            f"FOR VALUES FROM ('{month_start}') TO ('{month_end}');"
        )
        comment_sql = f"COMMENT ON TABLE {partition_name} IS '{comment}';"

        db.session.execute(text(create_sql))
        db.session.execute(text(comment_sql))

    @staticmethod
    def drop_partition_table(*, partition_name: str) -> None:
        """删除分区表."""
        drop_sql = f"DROP TABLE IF EXISTS {partition_name};"
        db.session.execute(text(drop_sql))

    @staticmethod
    def fetch_partition_rows(*, pattern: str) -> list[Any]:
        """查询 pg_tables 中匹配 pattern 的分区行(含 size)."""
        query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
        FROM pg_tables
        WHERE tablename LIKE :pattern
        ORDER BY tablename;
        """
        return list(db.session.execute(text(query), {"pattern": pattern}).fetchall())

    @staticmethod
    def partition_exists(*, partition_name: str) -> bool:
        """检查分区表是否存在."""
        query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :partition_name
        );
        """
        result = db.session.execute(text(query), {"partition_name": partition_name}).scalar()
        return bool(result)

    @staticmethod
    def fetch_partition_names(*, pattern: str) -> list[str]:
        """查询候选分区名称列表."""
        query = """
        SELECT tablename
        FROM pg_tables
        WHERE tablename LIKE :pattern
        ORDER BY tablename;
        """
        rows = db.session.execute(text(query), {"pattern": pattern}).fetchall()
        return [row.tablename for row in rows]

    @staticmethod
    def get_partition_record_count(*, partition_name: str) -> int:
        """查询分区表记录数."""
        partition_table = table(partition_name)
        stmt = select(func.count()).select_from(partition_table)
        result = db.session.execute(stmt).scalar()
        return int(result or 0)
