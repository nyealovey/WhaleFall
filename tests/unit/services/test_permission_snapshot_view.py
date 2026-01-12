from typing import Any, cast

import pytest

from app.core.exceptions import AppError
from app.models.account_permission import AccountPermission  # noqa: E402


def _require_snapshot_view():
    try:
        from app.services.accounts_permissions import snapshot_view as snapshot_view_module
    except ModuleNotFoundError:
        pytest.skip("snapshot_view not implemented yet")
    return snapshot_view_module


@pytest.mark.unit
def test_permission_snapshot_view_returns_snapshot_when_present() -> None:
    snapshot_view = _require_snapshot_view()
    if not hasattr(AccountPermission, "permission_snapshot"):
        pytest.skip("permission_snapshot columns not implemented yet")

    class _StubAccount:
        permission_snapshot = {"version": 4, "categories": {"global_privileges": {"granted": ["SELECT"]}}}

    account = _StubAccount()

    view = snapshot_view.build_permission_snapshot_view(cast(Any, account))
    assert view["categories"]["global_privileges"]["granted"] == ["SELECT"]


@pytest.mark.unit
def test_permission_snapshot_view_does_not_fallback_to_legacy_columns() -> None:
    snapshot_view = _require_snapshot_view()
    if not hasattr(AccountPermission, "permission_snapshot"):
        pytest.skip("permission_snapshot columns not implemented yet")

    class _StubAccount:
        permission_snapshot = None

    account = _StubAccount()

    with pytest.raises(AppError) as excinfo:
        snapshot_view.build_permission_snapshot_view(cast(Any, account))

    assert excinfo.value.message_key == "SNAPSHOT_MISSING"


@pytest.mark.unit
def test_permission_snapshot_view_raises_when_missing() -> None:
    snapshot_view = _require_snapshot_view()
    if not hasattr(AccountPermission, "permission_snapshot"):
        pytest.skip("permission_snapshot columns not implemented yet")

    class _StubAccount:
        permission_snapshot = None

    with pytest.raises(AppError) as excinfo:
        snapshot_view.build_permission_snapshot_view(cast(Any, _StubAccount()))

    assert excinfo.value.message_key == "SNAPSHOT_MISSING"
