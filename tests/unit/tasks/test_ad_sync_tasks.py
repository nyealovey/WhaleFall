from __future__ import annotations

import pytest

from app import create_app, db
from app.core.constants.status_types import TaskRunStatus
from app.models.ad_domain_config import AdDomainConfig
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.tasks import ad_sync_tasks
from app.services.ad_sync.ldap_provider import AdPrincipal, AdPrincipalsFetchResult


def _create_tables() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["credentials"],
            db.metadata.tables["instances"],
            db.metadata.tables["ad_domain_configs"],
            db.metadata.tables["instance_accounts"],
            db.metadata.tables["task_runs"],
            db.metadata.tables["task_run_items"],
        ],
    )


def _create_domain(*, name: str, netbios_name: str) -> AdDomainConfig:
    credential = Credential(
        name=f"{netbios_name}-ldap",
        credential_type="ldap",
        username=f"{netbios_name}\\svc",
        password="secret",
        is_active=True,
    )
    db.session.add(credential)
    db.session.flush()
    domain = AdDomainConfig(
        name=name,
        netbios_name=netbios_name,
        domain_controllers=[f"dc01.{name}"],
        ldap_port=636,
        use_ssl=True,
        verify_ssl=True,
        base_dn="DC=example,DC=com",
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
def test_sync_ad_accounts_marks_partial_success_and_preserves_failed_domain_accounts(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)

    class _FakeProvider:
        def fetch_principals(self, config: AdDomainConfig):
            return self.fetch_principals_with_stats(config).principals

        def fetch_principals_with_stats(self, config: AdDomainConfig):
            if config.netbios_name == "FAIL":
                raise RuntimeError("dc failed")
            return AdPrincipalsFetchResult(
                principals={"disabled": AdPrincipal("disabled", "user", True, {})},
                users_total=1,
                groups_total=0,
            )

    monkeypatch.setattr(ad_sync_tasks, "create_app", lambda **_: app)
    monkeypatch.setattr(ad_sync_tasks, "LdapProvider", _FakeProvider)

    with app.app_context():
        _create_tables()
        ok_domain = _create_domain(name="corp.example.com", netbios_name="CORP")
        failed_domain = _create_domain(name="fail.example.com", netbios_name="FAIL")
        instance = _create_instance()
        ok_account = InstanceAccount(
            instance_id=instance.id,
            db_type="sqlserver",
            username="CORP\\disabled",
            owner_type="instance",
            owner_id=instance.id,
        )
        failed_account = InstanceAccount(
            instance_id=instance.id,
            db_type="sqlserver",
            username="FAIL\\disabled",
            owner_type="instance",
            owner_id=instance.id,
        )
        db.session.add_all([ok_account, failed_account])
        db.session.commit()

        ad_sync_tasks.sync_ad_accounts(manual_run=True, created_by=1)

        run = TaskRun.query.filter_by(task_key="sync_ad_accounts").one()
        assert run.status == TaskRunStatus.COMPLETED_WITH_ERRORS
        assert run.summary_json["ext"]["domains_successful"] == 1
        assert run.summary_json["ext"]["domains_failed"] == 1
        assert ok_domain.last_sync_status == "success"
        assert failed_domain.last_sync_status == "failed"
        assert ok_account.ad_disabled_at is not None
        assert failed_account.ad_disabled_at is None
        assert failed_account.ad_orphaned_at is None


@pytest.mark.unit
def test_sync_ad_accounts_records_ad_fetch_counts_in_summary_and_item_metrics(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)

    class _FakeProvider:
        def fetch_principals(self, config: AdDomainConfig):
            return self.fetch_principals_with_stats(config).principals

        def fetch_principals_with_stats(self, _config: AdDomainConfig) -> AdPrincipalsFetchResult:
            return AdPrincipalsFetchResult(
                principals={
                    "enabled": AdPrincipal("enabled", "user", False, {}),
                    "disabled": AdPrincipal("disabled", "user", True, {}),
                    "domain admins": AdPrincipal("Domain Admins", "group", None, {}),
                },
                users_total=2,
                groups_total=1,
            )

    monkeypatch.setattr(ad_sync_tasks, "create_app", lambda **_: app)
    monkeypatch.setattr(ad_sync_tasks, "LdapProvider", _FakeProvider)

    with app.app_context():
        _create_tables()
        _create_domain(name="corp.example.com", netbios_name="CORP")
        instance = _create_instance()
        db.session.add(
            InstanceAccount(
                instance_id=instance.id,
                db_type="sqlserver",
                username="CORP\\enabled",
                owner_type="instance",
                owner_id=instance.id,
            )
        )
        db.session.commit()

        ad_sync_tasks.sync_ad_accounts(manual_run=True, created_by=1)

        run = TaskRun.query.filter_by(task_key="sync_ad_accounts").one()
        item = TaskRunItem.query.filter_by(run_id=run.run_id, item_type="ad_domain").one()
        assert run.summary_json["ext"]["ad_users_total"] == 2
        assert run.summary_json["ext"]["ad_groups_total"] == 1
        assert run.summary_json["ext"]["ad_principals_total"] == 3
        assert item.metrics_json["ad_users_total"] == 2
        assert item.metrics_json["ad_groups_total"] == 1
        assert item.metrics_json["ad_principals_total"] == 3
