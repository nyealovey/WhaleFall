from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_ops_volume_manager_no_userdata_migration_command() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts/ops/docker/volume_manager.sh"
    content = script.read_text(encoding="utf-8", errors="ignore")

    legacy_markers = [
        "从userdata迁移到卷",
        "migrate [dev|prod]",
        "migrate dev --force",
        "migrate_volumes()",
        "./userdata",
    ]
    hits = [marker for marker in legacy_markers if marker in content]
    assert not hits, f"发现 userdata->volume 迁移脚本残留: {hits}"


@pytest.mark.unit
def test_ops_makefile_prod_no_migrate_volumes_target() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    makefile = repo_root / "Makefile.prod"
    content = makefile.read_text(encoding="utf-8", errors="ignore")

    legacy_markers = [
        "migrate-volumes:",
        "volume_manager.sh migrate",
        "迁移数据到卷",
    ]
    hits = [marker for marker in legacy_markers if marker in content]
    assert not hits, f"发现 migrate-volumes 残留: {hits}"
