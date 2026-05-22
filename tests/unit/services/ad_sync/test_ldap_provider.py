from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from app.core.exceptions import ValidationError
from app.models.ad_domain_config import AdDomainConfig
from app.services.ad_sync import ldap_provider
from app.services.ad_sync.ldap_provider import LdapProvider


class _Credential:
    username = "CORP\\svc"

    @staticmethod
    def get_plain_password() -> str:
        return "secret"


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        domain_controllers=["dc01.corp.example.com", "dc02.corp.example.com"],
        ldap_port=636,
        use_ssl=True,
        verify_ssl=False,
        base_dn="DC=corp,DC=example,DC=com",
        credential=_Credential(),
    )


class _Entry:
    def __init__(self, data: dict[str, object]) -> None:
        self.entry_attributes_as_dict = data


class _Server:
    def __init__(self, host: str, **_: object) -> None:
        self.host = host


class _Connection:
    def __init__(self, server: _Server, **kwargs: object) -> None:
        assert kwargs["user"] == "CORP\\svc"
        assert kwargs["password"] == "secret"
        assert kwargs["auto_referrals"] is False
        if "dc01" in server.host:
            raise RuntimeError("bind failed")
        self.entries: list[_Entry] = []

    def search(self, _base_dn: str, search_filter: str, *, attributes: list[str]) -> None:
        assert "sAMAccountName" in attributes
        if "objectClass=user" in search_filter:
            self.entries = [
                _Entry({"sAMAccountName": ["disabled"], "userAccountControl": [514], "displayName": ["Disabled User"]}),
            ]
            return
        self.entries = [
            _Entry({"sAMAccountName": ["Domain Admins"], "objectClass": ["group"]}),
        ]

    def unbind(self) -> None:
        return None


@pytest.mark.unit
def test_ldap_provider_falls_back_to_next_controller_and_logs_warning(monkeypatch) -> None:
    warnings: list[dict[str, object]] = []
    server_hosts: list[str] = []

    def _log_warning(message: str, **kwargs: object) -> None:
        warnings.append({"message": message, **kwargs})

    class _RecordingServer(_Server):
        def __init__(self, host: str, **kwargs: object) -> None:
            server_hosts.append(host)
            super().__init__(host, **kwargs)

    monkeypatch.setattr(ldap_provider, "Server", _RecordingServer)
    monkeypatch.setattr(ldap_provider, "Connection", _Connection)
    monkeypatch.setattr(ldap_provider, "log_warning", _log_warning, raising=False)

    principals = LdapProvider().fetch_principals(cast(AdDomainConfig, _config()))

    assert principals["disabled"].object_kind == "user"
    assert principals["disabled"].is_disabled is True
    assert principals["domain admins"].object_kind == "group"
    assert principals["domain admins"].is_disabled is None
    assert server_hosts == ["dc01.corp.example.com", "dc02.corp.example.com"]
    assert warnings == [
        {
            "message": "AD 域控连接失败,尝试下一个域控",
            "module": "ad_sync",
            "controller": "dc01.corp.example.com",
            "ldap_host": "dc01.corp.example.com",
            "port": 636,
            "use_ssl": True,
            "verify_ssl": False,
            "error": "bind failed",
        },
    ]


@pytest.mark.unit
def test_ldap_provider_raises_when_search_returns_referral_without_entries() -> None:
    class _ReferralConnection:
        entries: list[_Entry] = []
        result = {
            "description": "referral",
            "message": "0000202B: RefErr",
            "referrals": ["ldap://corp.example.com/DC=corp,DC=example,DC=com"],
        }

        def search(self, _base_dn: str, _search_filter: str, *, attributes: list[str]) -> bool:
            assert "sAMAccountName" in attributes
            return False

    with pytest.raises(RuntimeError, match="LDAP 查询失败"):
        LdapProvider._search_principals(
            _ReferralConnection(),
            "DC=corp,DC=example,DC=com",
            "(&(objectClass=user)(objectCategory=person))",
            object_kind="user",
            target={},
        )


@pytest.mark.unit
def test_ldap_provider_rejects_base_dn_with_dotted_dc_before_connecting(monkeypatch) -> None:
    def _server_should_not_be_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("invalid Base DN should be rejected before LDAP connect")

    config = _config()
    config.base_dn = "DC=user,DC=chint.com,DC=com"
    monkeypatch.setattr(ldap_provider, "Server", _server_should_not_be_called)

    with pytest.raises(ValidationError, match="Base DN 的 DC 片段不能包含点号"):
        LdapProvider().fetch_principals(cast(AdDomainConfig, config))
