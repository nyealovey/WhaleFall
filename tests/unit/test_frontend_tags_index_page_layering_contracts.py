from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_tags_index_page_template_must_load_store_before_views() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / "app/templates/tags/index.html"
    content = template_path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "js/modules/stores/tag_list_store.js" in content
    ), "TagsIndexPage 模板必须加载 tag_list_store.js"
    store_index = content.index("js/modules/stores/tag_list_store.js")
    modals_index = content.index("js/modules/views/tags/modals/tag-modals.js")
    page_index = content.index("js/modules/views/tags/index.js")
    assert store_index < modals_index, "tag_list_store.js 必须在 tag-modals.js 之前加载"
    assert store_index < page_index, "tag_list_store.js 必须在 index.js 之前加载"


@pytest.mark.unit
def test_tags_index_page_entry_must_use_tag_list_store() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/tags/index.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "createTagListStore" in content, "TagsIndexPage 必须引入并使用 createTagListStore"
    assert "getGridUrl(" not in content, "TagsIndexPage 不得直连 TagManagementService.getGridUrl"
    assert "deleteTag(" not in content, "TagsIndexPage 不得直连 TagManagementService.deleteTag"


@pytest.mark.unit
def test_tag_modals_must_not_construct_or_call_tag_service_directly() -> None:
    """TagModals 属于 views 层，必须通过 tag list store/actions 驱动。"""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/tags/modals/tag-modals.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "createTagListStore" not in content, "TagModals 不应自行创建 store（由 Page Entry 注入）"
    assert "new TagManagementService" not in content, "TagModals 不得自行 new TagManagementService"
    assert "tagService." not in content, "TagModals 不得直连 tagService"

