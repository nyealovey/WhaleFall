"""账户分类每日统计 Repository.

职责:
- 封装每日统计表的 upsert 细节(同一天重复执行覆盖而不是累加)
- 不做业务编排、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.postgresql.dml import Insert as PostgresInsert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.sqlite.dml import Insert as SqliteInsert

from app import db
from app.models.account_classification_daily_stats import (
    AccountClassificationDailyClassificationMatchStat,
    AccountClassificationDailyRuleMatchStat,
)

InsertStatement = PostgresInsert | SqliteInsert


class AccountClassificationDailyStatsRepository:
    """账户分类每日统计 Repository."""

    @staticmethod
    def _resolve_insert_stmt(table: Table) -> InsertStatement:
        dialect = getattr(getattr(db.session, "bind", None), "dialect", None)
        dialect_name = getattr(dialect, "name", "")
        if dialect_name == "sqlite":
            return sqlite_insert(table)
        return pg_insert(table)

    @classmethod
    def upsert_rule_match_stats(cls, records: list[dict[str, object]], *, current_utc: datetime) -> None:
        """批量 upsert 分类规则命中统计(B 口径)."""
        if not records:
            return

        table = cast(Table, getattr(AccountClassificationDailyRuleMatchStat, "__table__"))
        insert_stmt = cls._resolve_insert_stmt(table).values(records)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                table.c.stat_date,
                table.c.rule_id,
                table.c.db_type,
                table.c.instance_id,
            ],
            set_={
                "matched_accounts_count": insert_stmt.excluded.matched_accounts_count,
                "computed_at": insert_stmt.excluded.computed_at,
                "updated_at": current_utc,
            },
        )

        with db.session.begin_nested():
            db.session.execute(stmt)
            db.session.flush()

    @classmethod
    def upsert_classification_match_stats(cls, records: list[dict[str, object]], *, current_utc: datetime) -> None:
        """批量 upsert 分类命中去重账号数."""
        if not records:
            return

        table = cast(Table, getattr(AccountClassificationDailyClassificationMatchStat, "__table__"))
        insert_stmt = cls._resolve_insert_stmt(table).values(records)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                table.c.stat_date,
                table.c.classification_id,
                table.c.db_type,
                table.c.instance_id,
            ],
            set_={
                "matched_accounts_distinct_count": insert_stmt.excluded.matched_accounts_distinct_count,
                "computed_at": insert_stmt.excluded.computed_at,
                "updated_at": current_utc,
            },
        )

        with db.session.begin_nested():
            db.session.execute(stmt)
            db.session.flush()
