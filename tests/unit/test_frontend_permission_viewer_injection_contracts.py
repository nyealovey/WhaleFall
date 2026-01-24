from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_permission_viewer_must_not_construct_permission_service() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root
        / "app/static/js/modules/views/components/permissions/permission-viewer.js"
    )
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "new PermissionService" not in content, "PermissionViewer 不得在组件内部 new PermissionService"


@pytest.mark.unit
def test_accounts_ledgers_must_configure_permission_viewer() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/accounts/ledgers.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "configurePermissionViewer" in content, "AccountsLedgers 页面必须配置 PermissionViewer"
    assert "global.viewAccountPermissions" not in content, "不得再使用 legacy global.viewAccountPermissions"


@pytest.mark.unit
def test_instance_detail_must_configure_permission_viewer() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/detail.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "configurePermissionViewer" in content, "InstanceDetail 页面必须配置 PermissionViewer"
    assert "window.viewAccountPermissions" not in content, "不得再使用 legacy window.viewAccountPermissions"

