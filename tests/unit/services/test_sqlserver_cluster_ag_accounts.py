import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.services.accounts_sync.sqlserver_ag_accounts_sync_service import SQLServerAgAccountsSyncService
from app.services.instances.instance_ag_accounts_service import InstanceAgAccountsService


@pytest.fixture(scope="function")
def app():
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    return app


def _create_tables() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["instances"],
            db.metadata.tables["instance_accounts"],
            db.metadata.tables["account_permission"],
            db.metadata.tables["sqlserver_clusters"],
            db.metadata.tables["sqlserver_cluster_instances"],
            db.metadata.tables["sqlserver_availability_groups"],
        ],
    )


def _add_account(
    *,
    instance: Instance,
    ag: SQLServerAvailabilityGroup | None,
    username: str,
    is_superuser: bool = False,
    is_active: bool = True,
    is_locked: bool = False,
) -> InstanceAccount:
    account = InstanceAccount(
        instance_id=instance.id,
        username=username,
        db_type=DatabaseType.SQLSERVER,
        owner_type="sqlserver_ag" if ag else "instance",
        owner_id=ag.id if ag else instance.id,
        cluster_id=ag.cluster_id if ag else None,
        availability_group_id=ag.id if ag else None,
        is_active=is_active,
    )
    db.session.add(account)
    db.session.flush()
    db.session.add(
        AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.SQLSERVER,
            instance_account_id=account.id,
            username=username,
            owner_type=account.owner_type,
            owner_id=account.owner_id,
            cluster_id=account.cluster_id,
            availability_group_id=account.availability_group_id,
            permission_facts={
                "version": 2,
                "db_type": "sqlserver",
                "capabilities": [capability for capability, enabled in (("SUPERUSER", is_superuser), ("LOCKED", is_locked)) if enabled],
                "capability_reasons": {
                    **({"SUPERUSER": ["test"]} if is_superuser else {}),
                    **({"LOCKED": ["type_specific.is_disabled=True"]} if is_locked else {}),
                },
                "roles": ["sysadmin"] if is_superuser else [],
                "privileges": {},
                "errors": [],
                "meta": {},
            },
            type_specific={
                "version": 1,
                "security_scope": "contained_availability_group" if ag else "instance",
            },
        )
    )
    return account


@pytest.mark.unit
def test_instance_ag_accounts_lists_contained_ag_accounts_for_same_cluster(app) -> None:
    with app.app_context():
        _create_tables()
        instance = Instance(
            name="node-1",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        other_instance = Instance(
            name="node-other",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.99",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-a", description="")
        other_cluster = SQLServerCluster(name="cluster-b", description="")
        db.session.add_all([instance, other_instance, cluster, other_cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        included_ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="ag-contained",
            listener_name="ag-contained-lsn",
            listener_host="10.0.0.20",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        disabled_contained_ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="ag-legacy",
            listener_name="ag-legacy-lsn",
            listener_host="10.0.0.21",
            listener_port=1433,
            contained_enabled=False,
            is_enabled=True,
        )
        outside_ag = SQLServerAvailabilityGroup(
            cluster_id=other_cluster.id,
            name="ag-outside",
            listener_name="ag-outside-lsn",
            listener_host="10.0.0.30",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        db.session.add_all([included_ag, disabled_contained_ag, outside_ag])
        db.session.flush()
        _add_account(instance=instance, ag=None, username="same_name")
        ag_account = _add_account(instance=instance, ag=included_ag, username="same_name", is_superuser=True)
        _add_account(instance=instance, ag=disabled_contained_ag, username="legacy_user")
        _add_account(instance=other_instance, ag=outside_ag, username="outside_user")
        db.session.commit()

        result = InstanceAgAccountsService().list_for_instance(instance.id)

        assert result["cluster"]["name"] == "cluster-a"
        assert result["total"] == 1
        assert result["items"][0]["id"] == ag_account.id
        assert result["items"][0]["username"] == "same_name"
        assert result["items"][0]["availability_group_name"] == "ag-contained"
        assert result["items"][0]["listener_name"] == "ag-contained-lsn"
        assert result["items"][0]["listener_host"] == "10.0.0.20"
        assert result["items"][0]["is_deleted"] is False
        assert result["items"][0]["last_change_time"] is not None
        assert result["items"][0]["availability_reasons"] == []
        assert result["items"][0]["is_superuser"] is True


@pytest.mark.unit
def test_instance_ag_accounts_filters_search_and_deleted_accounts(app) -> None:
    with app.app_context():
        _create_tables()
        instance = Instance(
            name="node-filter",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-filter", description="")
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="ag-contained",
            listener_name="ag-lsn",
            listener_host="10.0.0.20",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        db.session.add(ag)
        db.session.flush()
        _add_account(instance=instance, ag=ag, username="active_login", is_locked=True)
        deleted_account = _add_account(instance=instance, ag=ag, username="deleted_login", is_active=False)
        db.session.commit()

        default_result = InstanceAgAccountsService().list_for_instance(instance.id)
        search_result = InstanceAgAccountsService().list_for_instance(instance.id, search="deleted", include_deleted=True)

        assert [item["username"] for item in default_result["items"]] == ["active_login"]
        assert default_result["items"][0]["availability_reasons"] == ["账户已禁用"]
        assert search_result["total"] == 1
        assert search_result["items"][0]["id"] == deleted_account.id
        assert search_result["items"][0]["username"] == "deleted_login"
        assert search_result["items"][0]["is_deleted"] is True


@pytest.mark.unit
def test_instance_ag_accounts_returns_empty_when_instance_has_no_cluster(app) -> None:
    with app.app_context():
        _create_tables()
        instance = Instance(
            name="standalone",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.12",
            port=1433,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        result = InstanceAgAccountsService().list_for_instance(instance.id)

        assert result == {"cluster": None, "items": [], "total": 0}


@pytest.mark.unit
def test_instance_ag_accounts_returns_empty_when_cluster_is_disabled(app) -> None:
    with app.app_context():
        _create_tables()
        instance = Instance(
            name="node-disabled-cluster",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.13",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-disabled", description="", is_enabled=False)
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="ag-contained",
            listener_host="10.0.0.20",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        db.session.add(ag)
        db.session.flush()
        _add_account(instance=instance, ag=ag, username="ag_user")
        db.session.commit()

        result = InstanceAgAccountsService().list_for_instance(instance.id)

        assert result == {"cluster": None, "items": [], "total": 0}


@pytest.mark.unit
def test_sqlserver_ag_sync_skips_disabled_cluster(app, monkeypatch) -> None:
    with app.app_context():
        _create_tables()
        instance = Instance(
            name="node-sync-disabled",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.14",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-disabled-sync", description="", is_enabled=False)
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        db.session.add(
            SQLServerAvailabilityGroup(
                cluster_id=cluster.id,
                name="ag-contained",
                listener_host="10.0.0.20",
                listener_port=1433,
                contained_enabled=True,
                is_enabled=True,
            )
        )
        db.session.commit()

        called = {"value": False}

        def _fake_sync_one_ag(*args, **kwargs):
            called["value"] = True
            return {"status": "completed", "processed_records": 1}

        monkeypatch.setattr(SQLServerAgAccountsSyncService, "_sync_one_ag", _fake_sync_one_ag)

        result = SQLServerAgAccountsSyncService().sync_for_instance(instance, session_id="test")

        assert result == {"status": "skipped", "processed_records": 0, "items": []}
        assert called["value"] is False
