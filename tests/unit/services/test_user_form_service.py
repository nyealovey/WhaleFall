import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.constants import UserRole
from app.models.user import User
from app.services.form_service.user_service import UserFormService


class _DummyQuery:
    def filter(self, *args, **kwargs):  # noqa: ANN401
        return self

    def filter_by(self, *args, **kwargs):  # noqa: ANN401
        return self

    def first(self):
        return None


@pytest.mark.unit
def test_validate_prevents_disabling_last_admin(monkeypatch) -> None:
    service = UserFormService()
    admin = User(username="root", role=UserRole.ADMIN)
    admin.id = 1  # type: ignore[attr-defined]
    admin.is_active = True

    monkeypatch.setattr(UserFormService, "_user_query", lambda self: _DummyQuery(), raising=False)
    monkeypatch.setattr(
        User,
        "active_admin_count",
        classmethod(lambda cls, *, exclude_user_id=None: 0),
    )

    result = service.validate(
        {
            "username": "root",
            "role": UserRole.USER,
            "is_active": True,
        },
        resource=admin,
    )

    assert result.success is False
    assert result.message_key == UserFormService.MESSAGE_LAST_ADMIN_REQUIRED


@pytest.mark.unit
def test_validate_allows_change_when_other_admin_exists(monkeypatch) -> None:
    service = UserFormService()
    admin = User(username="root", role=UserRole.ADMIN)
    admin.id = 2  # type: ignore[attr-defined]
    admin.is_active = True

    monkeypatch.setattr(UserFormService, "_user_query", lambda self: _DummyQuery(), raising=False)
    monkeypatch.setattr(
        User,
        "active_admin_count",
        classmethod(lambda cls, *, exclude_user_id=None: 1),
    )

    result = service.validate(
        {
            "username": "root",
            "role": UserRole.USER,
            "is_active": True,
        },
        resource=admin,
    )

    assert result.success is True
    assert result.data
