from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_repo_does_not_keep_migration_route_doc_tooling_scripts() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    scripts = [
        repo_root / "scripts/dev/docs/check_api_routes_reference.py",
        repo_root / "scripts/dev/docs/generate_api_routes_inventory.py",
    ]
    existing = [str(path.relative_to(repo_root)) for path in scripts if path.exists()]

    assert not existing, f"发现迁移期 doc tooling 残留脚本: {existing}"
