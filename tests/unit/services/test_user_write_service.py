import pytest

from app.constants import UserRole
from app.errors import ConflictError, ValidationError
from app.models.user import User
from app.repositories.users_repository import UsersRepository
from app.services.users.user_write_service import UserWriteService


class _StubUsersRepository(UsersRepository):
    def __init__(self, user: User | None, *, username_exists: bool = False) -> None:
        self._user = user
        self._username_exists = username_exists

    def get_by_id(self, user_id: int) -> User | None:  # noqa: ARG002
        return self._user

    def get_by_username(self, username: str) -> User | None:  # noqa: ARG002
        if not self._username_exists:
            return None
        existing = User(username=username, role=UserRole.USER)
        existing.id = 999  # type: ignore[attr-defined]
        return existing

    def add(self, user: User) -> User:  # noqa: ARG002
        return user


@pytest.mark.unit
def test_update_prevents_disabling_last_admin(monkeypatch) -> None:
    admin = User(username="root", role=UserRole.ADMIN)
    admin.id = 1  # type: ignore[attr-defined]
    admin.is_active = True

    service = UserWriteService(repository=_StubUsersRepository(admin))
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
    admin = User(username="root", role=UserRole.ADMIN)
    admin.id = 2  # type: ignore[attr-defined]
    admin.is_active = True

    service = UserWriteService(repository=_StubUsersRepository(admin))
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
    service = UserWriteService(repository=_StubUsersRepository(None, username_exists=True))

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
