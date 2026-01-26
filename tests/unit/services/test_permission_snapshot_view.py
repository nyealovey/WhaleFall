from typing import Any, cast

import pytest

from app.core.exceptions import AppError
from app.models.account_permission import AccountPermission
from app.services.accounts_permissions import snapshot_view


@pytest.mark.unit
def test_permission_snapshot_view_returns_snapshot_when_present() -> None:
    assert hasattr(AccountPermission, "permission_snapshot")

    class _StubAccount:
        permission_snapshot = {"version": 4, "categories": {"mysql_global_privileges": {"granted": ["SELECT"]}}}

    account = _StubAccount()

    view = snapshot_view.build_permission_snapshot_view(cast(Any, account))
    assert view["categories"]["mysql_global_privileges"]["granted"] == ["SELECT"]


@pytest.mark.unit
def test_permission_snapshot_view_does_not_fallback_to_legacy_columns() -> None:
    assert hasattr(AccountPermission, "permission_snapshot")

    class _StubAccount:
        permission_snapshot = None

    account = _StubAccount()

    with pytest.raises(AppError) as excinfo:
        snapshot_view.build_permission_snapshot_view(cast(Any, account))

    assert excinfo.value.message_key == "SNAPSHOT_MISSING"
