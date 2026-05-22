import pytest

from app.core.exceptions import ValidationError
from app.schemas.ad_domain_config import AdDomainConfigPayload
from app.schemas.validation import validate_or_raise


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "user.chint.com",
        "netbios_name": "USER",
        "domain_controllers": ["192.168.0.236"],
        "ldap_port": 389,
        "use_ssl": False,
        "verify_ssl": False,
        "base_dn": "DC=user,DC=chint,DC=com",
        "credential_id": 1,
        "is_enabled": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.unit
def test_ad_domain_config_allows_ou_base_dn_with_split_dc_labels() -> None:
    payload = validate_or_raise(
        AdDomainConfigPayload,
        _payload(base_dn=" OU=Users,DC=user,DC=chint,DC=com "),
    )

    assert payload.base_dn == "OU=Users,DC=user,DC=chint,DC=com"


@pytest.mark.unit
def test_ad_domain_config_rejects_dc_component_with_dot() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(
            AdDomainConfigPayload,
            _payload(base_dn="DC=user,DC=chint.com,DC=com"),
        )

    assert "Base DN 的 DC 片段不能包含点号" in str(excinfo.value)
