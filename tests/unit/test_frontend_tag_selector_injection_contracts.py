from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_tag_selector_controller_must_not_construct_service_or_store() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root
        / "app/static/js/modules/views/components/tags/tag-selector-controller.js"
    )
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "new TagManagementService" not in content, (
        "tag-selector-controller 组件不得自行 new TagManagementService（必须由 Page Entry 注入 store/service）"
    )
    assert "createTagManagementStore" not in content, (
        "tag-selector-controller 组件不得自行 createTagManagementStore（必须由 Page Entry 注入 store/service）"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "relative_path",
    [
        "app/static/js/modules/views/accounts/ledgers.js",
        "app/static/js/modules/views/databases/ledgers.js",
        "app/static/js/modules/views/instances/list.js",
    ],
)
def test_pages_using_tag_selector_must_inject_store(relative_path: str) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / relative_path
    content = path.read_text(encoding="utf-8", errors="ignore")

    pattern = re.compile(
        r"TagSelectorHelper\.setupForForm\(\{[\s\S]*?\bstore\s*:",
        re.MULTILINE,
    )
    assert pattern.search(content), f"{relative_path}: TagSelectorHelper.setupForForm 必须注入 store"
