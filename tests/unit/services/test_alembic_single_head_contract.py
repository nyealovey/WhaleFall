from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


@pytest.mark.unit
def test_alembic_migration_history_has_single_head() -> None:
    project_root = Path(__file__).resolve().parents[3]
    config = Config()
    config.set_main_option("script_location", str(project_root / "migrations"))

    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()

    assert len(heads) == 1
