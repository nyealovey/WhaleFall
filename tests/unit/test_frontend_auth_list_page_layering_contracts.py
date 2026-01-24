from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_auth_list_page_template_must_load_store_before_views() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / "app/templates/auth/list.html"
    content = template_path.read_text(encoding="utf-8", errors="ignore")

    assert "js/modules/stores/users_store.js" in content, "AuthListPage 模板必须加载 users_store.js"
    store_index = content.index("js/modules/stores/users_store.js")
    modals_index = content.index("js/modules/views/auth/modals/user-modals.js")
    page_index = content.index("js/modules/views/auth/list.js")
    assert store_index < modals_index, "users_store.js 必须在 user-modals.js 之前加载"
    assert store_index < page_index, "users_store.js 必须在 list.js 之前加载"


@pytest.mark.unit
def test_auth_list_page_entry_must_use_users_store() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/auth/list.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "createUsersStore" in content, "AuthListPage 必须引入并使用 createUsersStore"
    assert "getGridUrl(" not in content, "AuthListPage 不得直连 UserService.getGridUrl"


@pytest.mark.unit
def test_user_modals_must_not_construct_or_call_user_service_directly() -> None:
    """UserModals 属于 views 层，必须通过 users store/actions 驱动。"""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/auth/modals/user-modals.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "createUsersStore" not in content, "UserModals 不应自行创建 store（由 Page Entry 注入）"
    assert "new UserService" not in content, "UserModals 不得自行 new UserService"
    assert "userService." not in content, "UserModals 不得直连 userService"

