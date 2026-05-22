import pytest

from app.schemas.credentials import CredentialCreatePayload
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
@pytest.mark.parametrize("username", ["DOMAIN\\svc_whalefall", "svc_whalefall@example.com", "svc_whalefall"])
def test_ldap_credential_allows_domain_username_formats(username: str) -> None:
    payload = validate_or_raise(
        CredentialCreatePayload,
        {
            "name": "ldap-admin",
            "credential_type": "ldap",
            "username": username,
            "password": "SecurePass1",
        },
    )

    assert payload.username == username
