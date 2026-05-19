import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster
from app.services.accounts_sync.inventory_manager import AccountInventoryManager
from app.services.accounts_sync.permission_manager import AccountPermissionManager
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission


@pytest.mark.unit
def test_inventory_sync_scopes_same_username_by_account_owner() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_availability_groups"],
            ],
        )
        instance = Instance(
            name="node-1",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([instance, cluster])
        db.session.flush()
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

        ag_account = InstanceAccount(
            instance_id=instance.id,
            username="shared_login",
            db_type=DatabaseType.SQLSERVER,
            owner_type="sqlserver_ag",
            owner_id=ag.id,
            cluster_id=cluster.id,
            availability_group_id=ag.id,
            is_active=True,
        )
        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="shared_login",
            db_type=DatabaseType.SQLSERVER,
            owner_type="instance",
            owner_id=instance.id,
            is_active=True,
        )
        db.session.add_all([instance_account, ag_account])
        db.session.commit()

        summary, active_accounts = AccountInventoryManager().synchronize(
            instance,
            [
                {
                    "username": "shared_login",
                    "db_type": DatabaseType.SQLSERVER,
                    "is_active": True,
                    "is_superuser": False,
                    "is_locked": False,
                    "permissions": {"type_specific": {}},
                    "owner_type": "sqlserver_ag",
                    "owner_id": ag.id,
                    "cluster_id": cluster.id,
                    "availability_group_id": ag.id,
                }
            ],
        )

        db.session.refresh(instance_account)
        db.session.refresh(ag_account)
        assert summary["deactivated"] == 0
        assert instance_account.is_active is True
        assert ag_account.is_active is True
        assert [account.id for account in active_accounts] == [ag_account.id]


@pytest.mark.unit
def test_inventory_sync_creates_ag_account_with_owner_scope() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_availability_groups"],
            ],
        )
        instance = Instance(
            name="node-1",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([instance, cluster])
        db.session.flush()
        ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="ag-contained",
            listener_host="10.0.0.20",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        db.session.add(ag)
        db.session.commit()

        summary, active_accounts = AccountInventoryManager().synchronize(
            instance,
            [
                {
                    "username": "ag_only_login",
                    "db_type": DatabaseType.SQLSERVER,
                    "is_active": True,
                    "is_superuser": False,
                    "is_locked": False,
                    "permissions": {"type_specific": {}},
                    "owner_type": "sqlserver_ag",
                    "owner_id": ag.id,
                    "cluster_id": cluster.id,
                    "availability_group_id": ag.id,
                }
            ],
        )

        created = InstanceAccount.query.filter_by(username="ag_only_login").one()
        assert summary["created"] == 1
        assert active_accounts == [created]
        assert created.owner_type == "sqlserver_ag"
        assert created.owner_id == ag.id
        assert created.cluster_id == cluster.id
        assert created.availability_group_id == ag.id


@pytest.mark.unit
def test_permission_sync_scopes_same_username_by_account_owner() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_change_log"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_availability_groups"],
            ],
        )
        instance = Instance(
            name="node-1",
            db_type=DatabaseType.SQLSERVER,
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        cluster = SQLServerCluster(name="cluster-a", description="")
        db.session.add_all([instance, cluster])
        db.session.flush()
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

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="shared_login",
            db_type=DatabaseType.SQLSERVER,
            owner_type="instance",
            owner_id=instance.id,
            is_active=True,
        )
        ag_account = InstanceAccount(
            instance_id=instance.id,
            username="shared_login",
            db_type=DatabaseType.SQLSERVER,
            owner_type="sqlserver_ag",
            owner_id=ag.id,
            cluster_id=cluster.id,
            availability_group_id=ag.id,
            is_active=True,
        )
        db.session.add_all([instance_account, ag_account])
        db.session.commit()

        summary = AccountPermissionManager().synchronize(
            instance,
            [
                {
                    "username": "shared_login",
                    "db_type": DatabaseType.SQLSERVER,
                    "is_active": True,
                    "is_superuser": False,
                    "is_locked": False,
                    "owner_type": "instance",
                    "owner_id": instance.id,
                    "permissions": {
                        "sqlserver_server_roles": ["securityadmin"],
                        "type_specific": {"security_scope": "instance"},
                    },
                },
                {
                    "username": "shared_login",
                    "db_type": DatabaseType.SQLSERVER,
                    "is_active": True,
                    "is_superuser": True,
                    "is_locked": False,
                    "owner_type": "sqlserver_ag",
                    "owner_id": ag.id,
                    "cluster_id": cluster.id,
                    "availability_group_id": ag.id,
                    "permissions": {
                        "sqlserver_server_roles": ["sysadmin"],
                        "type_specific": {"security_scope": "contained_availability_group"},
                    },
                },
            ],
            [instance_account, ag_account],
            session_id="sync-1",
        )

        permissions = {
            item.owner_type: item
            for item in AccountPermission.query.order_by(AccountPermission.owner_type.asc()).all()
        }
        logs = AccountChangeLog.query.order_by(AccountChangeLog.owner_type.asc()).all()

        assert summary.get("created") == 2
        assert permissions["instance"].owner_id == instance.id
        assert permissions["instance"].cluster_id is None
        assert permissions["sqlserver_ag"].owner_id == ag.id
        assert permissions["sqlserver_ag"].cluster_id == cluster.id
        assert permissions["sqlserver_ag"].availability_group_id == ag.id
        assert permissions["instance"].permission_snapshot["categories"]["sqlserver_server_roles"] == [
            "securityadmin"
        ]
        assert permissions["sqlserver_ag"].permission_snapshot["categories"]["sqlserver_server_roles"] == ["sysadmin"]
        assert [(log.owner_type, log.owner_id) for log in logs] == [("instance", instance.id), ("sqlserver_ag", ag.id)]
