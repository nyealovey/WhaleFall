from __future__ import annotations

from app.core.constants.database_types import DatabaseType


def test_oracle_display_name_uses_oracle_short_label() -> None:
    assert DatabaseType.DISPLAY_NAMES[DatabaseType.ORACLE] == "Oracle"
