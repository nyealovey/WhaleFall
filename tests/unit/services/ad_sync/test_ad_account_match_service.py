from __future__ import annotations

import pytest

from app import create_app, db
from app.models.ad_domain_config import AdDomainConfig
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.services.ad_sync.ad_account_match_service import AdAccountMatchService
from app.services.ad_sync.ldap_provider import AdPrincipal


def _create_tables() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["credentials"],
            db.metadata.tables["instances"],
            db.metadata.tables["ad_domain_configs"],
            db.metadata.tables["instance_accounts"],
        ],
    )


def _create_domain() -> AdDomainConfig:
    credential = Credential(
        name="ldap-admin",
        credential_type="ldap",
        username="CORP\\svc",
        password="secret",
        is_active=True,
    )
    db.session.add(credential)
    db.session.flush()
    domain = AdDomainConfig(
        name="corp.example.com",
        netbios_name="CORP",
        domain_controllers=["dc01.corp.example.com"],
        ldap_port=636,
        use_ssl=True,
        verify_ssl=True,
        base_dn="DC=corp,DC=example,DC=com",
        credential_id=credential.id,
        is_enabled=True,
    )
    db.session.add(domain)
    db.session.flush()
    return domain


def _create_instance() -> Instance:
    credential = Credential(
        name="sql-admin",
        credential_type="database",
        db_type="sqlserver",
        username="sa",
        password="secret",
        is_active=True,
    )
    instance = Instance(
        name="sql-prod",
        db_type="sqlserver",
        host="127.0.0.1",
        port=1433,
        credential_id=credential.id,
    )
    db.session.add_all([credential, instance])
    db.session.flush()
    return instance


@pytest.mark.unit
def test_ad_account_match_service_updates_instance_and_ag_domain_accounts() -> None:
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        _create_tables()
        domain = _create_domain()
        instance = _create_instance()
        accounts = [
            InstanceAccount(instance_id=instance.id, db_type="sqlserver", username="CORP\\enabled", owner_type="instance", owner_id=instance.id),
            InstanceAccount(instance_id=instance.id, db_type="sqlserver", username="CORP\\disabled", owner_type="sqlserver_ag", owner_id=42),
            InstanceAccount(instance_id=instance.id, db_type="sqlserver", username="CORP\\domain-group", owner_type="instance", owner_id=instance.id),
            InstanceAccount(instance_id=instance.id, db_type="sqlserver", username="CORP\\missing", owner_type="instance", owner_id=instance.id),
            InstanceAccount(instance_id=instance.id, db_type="mysql", username="CORP\\mysql-user", owner_type="instance", owner_id=instance.id),
        ]
        db.session.add_all(accounts)
        db.session.commit()

        result = AdAccountMatchService().match_and_update(
            domain_config=domain,
            principals={
                "enabled": AdPrincipal("enabled", "user", False, {}),
                "disabled": AdPrincipal("disabled", "user", True, {}),
                "domain-group": AdPrincipal("domain-group", "group", None, {}),
            },
        )
        db.session.commit()

        assert result.total == 4
        assert result.normal == 2
        assert result.disabled == 1
        assert result.orphaned == 1
        assert result.updated == 4
        assert accounts[0].ad_disabled_at is None
        assert accounts[0].ad_orphaned_at is None
        assert accounts[1].ad_disabled_at is not None
        assert accounts[1].ad_orphaned_at is None
        assert accounts[2].ad_disabled_at is None
        assert accounts[2].ad_orphaned_at is None
        assert accounts[3].ad_disabled_at is None
        assert accounts[3].ad_orphaned_at is not None
        assert accounts[4].ad_domain_config_id is None


@pytest.mark.unit
def test_ad_account_match_service_preserves_existing_state_timestamp() -> None:
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        _create_tables()
        domain = _create_domain()
        instance = _create_instance()
        account = InstanceAccount(
            instance_id=instance.id,
            db_type="sqlserver",
            username="CORP\\disabled",
            owner_type="instance",
            owner_id=instance.id,
        )
        db.session.add(account)
        db.session.commit()

        AdAccountMatchService().match_and_update(
            domain_config=domain,
            principals={"disabled": AdPrincipal("disabled", "user", True, {})},
        )
        first_disabled_at = account.ad_disabled_at

        AdAccountMatchService().match_and_update(
            domain_config=domain,
            principals={"disabled": AdPrincipal("disabled", "user", True, {})},
        )

        assert account.ad_disabled_at == first_disabled_at
