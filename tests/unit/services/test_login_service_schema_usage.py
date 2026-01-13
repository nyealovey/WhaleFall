from __future__ import annotations

import pytest

import app.services.auth.login_service as login_service_module
from app.core.exceptions import ValidationError
from app.services.auth.login_service import LoginService


@pytest.mark.unit
def test_login_service_login_from_payload_uses_parse_payload(monkeypatch) -> None:
    service = LoginService()

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("parse_payload_called")

    monkeypatch.setattr(login_service_module, "parse_payload", _raise, raising=False)

    with pytest.raises(RuntimeError, match="parse_payload_called"):
        service.login_from_payload({"username": "alice", "password": "pw"})


@pytest.mark.unit
def test_login_service_login_from_payload_uses_validate_or_raise(monkeypatch) -> None:
    service = LoginService()

    def _passthrough(payload: object, **_kwargs: object) -> object:
        return payload

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("validate_or_raise_called")

    monkeypatch.setattr(login_service_module, "parse_payload", _passthrough, raising=False)
    monkeypatch.setattr(login_service_module, "validate_or_raise", _raise, raising=False)

    with pytest.raises(RuntimeError, match="validate_or_raise_called"):
        service.login_from_payload({"username": "alice", "password": "pw"})


@pytest.mark.unit
def test_login_service_login_from_payload_rejects_missing_username_or_password() -> None:
    service = LoginService()

    with pytest.raises(ValidationError, match="用户名和密码不能为空"):
        service.login_from_payload({"username": "alice", "password": ""})

