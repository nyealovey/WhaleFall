from dataclasses import dataclass
from typing import Any

import pytest

from app.core.constants import UserRole
from app.core.exceptions import ConflictError, ValidationError
from app.models.user import User
from app.services.users.user_write_service import UserWriteService


@dataclass(slots=True)
class _StubUser:
    username: str
    role: str
    id: int
    is_active: bool = True

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


class _StubUsersRepository:
    def __init__(self, user: object | None, *, username_exists: bool = False) -> None:
        self._user = user
        self._username_exists = username_exists

    def get_by_id(self, user_id: int) -> object | None:  # noqa: ARG002
        return self._user

    def get_by_username(self, username: str) -> object | None:  # noqa: ARG002
        if not self._username_exists:
            return None
        return _StubUser(username=username, role=UserRole.USER, id=999)

    def add(self, user: object) -> object:  # noqa: ARG002
        return user


@pytest.mark.unit
def test_update_prevents_disabling_last_admin(monkeypatch) -> None:
    admin = _StubUser(username="root", role=UserRole.ADMIN, id=1, is_active=True)

    service = UserWriteService(repository=_StubUsersRepository(admin))  # type: ignore[arg-type]
    monkeypatch.setattr(
        User,
        "active_admin_count",
        classmethod(lambda cls, *, exclude_user_id=None: 0),
    )

    with pytest.raises(ValidationError) as exc:
        service.update(
            admin.id,
            {
                "username": "root",
                "role": UserRole.USER,
                "is_active": True,
            },
        )

    assert exc.value.message_key == "LAST_ADMIN_REQUIRED"


@pytest.mark.unit
def test_update_allows_change_when_other_admin_exists(monkeypatch) -> None:
    admin = _StubUser(username="root", role=UserRole.ADMIN, id=2, is_active=True)

    service = UserWriteService(repository=_StubUsersRepository(admin))  # type: ignore[arg-type]
    monkeypatch.setattr(
        User,
        "active_admin_count",
        classmethod(lambda cls, *, exclude_user_id=None: 1),
    )

    updated = service.update(
        admin.id,
        {
            "username": "root",
            "role": UserRole.USER,
            "is_active": True,
        },
    )

    assert updated.role == UserRole.USER


@pytest.mark.unit
def test_create_returns_username_exists_message_key() -> None:
    service = UserWriteService(repository=_StubUsersRepository(None, username_exists=True))  # type: ignore[arg-type]

    with pytest.raises(ConflictError) as exc:
        service.create(
            {
                "username": "admin",
                "role": UserRole.ADMIN,
                "password": "TestPass1",
                "is_active": True,
            },
        )

    assert exc.value.message_key == UserWriteService.MESSAGE_USERNAME_EXISTS


@pytest.mark.unit
def test_user_write_service_supports_default_repository() -> None:
    UserWriteService()


@pytest.mark.unit
def test_update_requires_is_active_field() -> None:
    admin = _StubUser(username="root", role=UserRole.ADMIN, id=1, is_active=True)
    service = UserWriteService(repository=_StubUsersRepository(admin))  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        service.update(
            admin.id,
            {
                "username": "root",
                "role": UserRole.ADMIN,
            },
        )


@pytest.mark.unit
def test_is_target_state_admin_treats_missing_is_active_as_false() -> None:
    assert UserWriteService._is_target_state_admin({"role": UserRole.ADMIN}) is False
