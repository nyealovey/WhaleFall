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


@pytest.mark.unit
def test_docs_do_not_reference_removed_route_doc_tooling_scripts() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    checks = [
        (
            repo_root / "docs/reference/api/api-routes-documentation.md",
            "scripts/dev/docs/check_api_routes_reference.py",
        ),
        (
            repo_root / "docs/standards/backend/api-naming-standards.md",
            "scripts/dev/docs/generate_api_routes_inventory.py",
        ),
        (
            repo_root / "docs/changes/refactor/004-flask-restx-openapi-migration-plan.md",
            "scripts/dev/docs/generate_api_routes_inventory.py",
        ),
        (
            repo_root / "docs/changes/refactor/004-flask-restx-openapi-migration-plan.md",
            "scripts/dev/docs/check_api_routes_reference.py",
        ),
        (
            repo_root / "docs/changes/refactor/004-flask-restx-openapi-migration-progress.md",
            "scripts/dev/docs/generate_api_routes_inventory.py",
        ),
    ]

    hits: list[str] = []
    for path, marker in checks:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if marker in content:
            hits.append(f"{path.relative_to(repo_root)} contains {marker}")

    assert not hits, "发现迁移期 doc tooling 引用残留:\n" + "\n".join(hits)
