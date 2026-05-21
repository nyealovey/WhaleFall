from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.core.types.account_change_logs import AccountChangeLogsListFilters
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.repositories.account_change_logs_repository import AccountChangeLogsRepository
from app.settings import Settings


@pytest.fixture(scope="function")
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    app = create_app(init_scheduler_on_start=False, settings=Settings.load())
    app.config["TESTING"] = True
    return app


@pytest.mark.unit
def test_account_change_logs_join_current_account_by_owner_scope(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_change_log"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_cluster_instances"],
                db.metadata.tables["sqlserver_availability_groups"],
            ],
        )

        instance = Instance(
            name="sqlserver-1",
            db_type=DatabaseType.SQLSERVER,
            host="127.0.0.1",
            port=1433,
            is_active=True,
        )
        db.session.add(instance)
        db.session.flush()

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="same_name",
            db_type=DatabaseType.SQLSERVER,
            owner_type="instance",
            owner_id=instance.id,
            is_active=True,
        )
        ag_account = InstanceAccount(
            instance_id=instance.id,
            username="same_name",
            db_type=DatabaseType.SQLSERVER,
            owner_type="sqlserver_ag",
            owner_id=7,
            is_active=True,
        )
        db.session.add_all([instance_account, ag_account])
        db.session.flush()

        permission_facts = {
            "version": 2,
            "db_type": "sqlserver",
            "capabilities": [],
            "capability_reasons": {},
            "roles": [],
            "privileges": {},
            "errors": [],
            "meta": {},
        }
        db.session.add_all(
            [
                AccountPermission(
                    instance_id=instance.id,
                    db_type=DatabaseType.SQLSERVER,
                    instance_account_id=instance_account.id,
                    username="same_name",
                    owner_type="instance",
                    owner_id=instance.id,
                    permission_facts=permission_facts,
                ),
                AccountPermission(
                    instance_id=instance.id,
                    db_type=DatabaseType.SQLSERVER,
                    instance_account_id=ag_account.id,
                    username="same_name",
                    owner_type="sqlserver_ag",
                    owner_id=7,
                    permission_facts=permission_facts,
                ),
                AccountChangeLog(
                    instance_id=instance.id,
                    db_type=DatabaseType.SQLSERVER,
                    username="same_name",
                    owner_type="instance",
                    owner_id=instance.id,
                    change_type="modify_other",
                    change_time=datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
                    status="success",
                    message="instance log",
                ),
                AccountChangeLog(
                    instance_id=instance.id,
                    db_type=DatabaseType.SQLSERVER,
                    username="same_name",
                    owner_type="sqlserver_ag",
                    owner_id=7,
                    change_type="modify_other",
                    change_time=datetime(2026, 5, 20, 9, 1, tzinfo=UTC),
                    status="success",
                    message="ag log",
                ),
            ],
        )
        db.session.commit()

        result = AccountChangeLogsRepository().list_logs(
            AccountChangeLogsListFilters(
                page=1,
                limit=20,
                sort_field="change_time",
                sort_order="asc",
                search_term="",
                instance_id=instance.id,
                db_type=None,
                change_type=None,
                status=None,
                hours=None,
            ),
        )

        assert result.total == 2
        assert {
            log_entry.owner_type: account_id
            for log_entry, _instance_name, _instance_host, account_id in result.items
        } == {
            "instance": instance_account.id,
            "sqlserver_ag": ag_account.id,
        }


@pytest.mark.unit
def test_account_change_logs_render_ag_listener_as_virtual_instance(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_change_log"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_cluster_instances"],
                db.metadata.tables["sqlserver_availability_groups"],
            ],
        )

        instance = Instance(
            name="gf-mssqlag-04",
            db_type=DatabaseType.SQLSERVER,
            host="10.10.1.4",
            port=1433,
            is_active=True,
        )
        db.session.add(instance)
        db.session.flush()

        cluster = SQLServerCluster(name="cluster-gf", is_enabled=True)
        db.session.add(cluster)
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="AGDB08",
            listener_name="AGDB08-LSN",
            listener_host="192.168.0.73",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        db.session.add(ag)
        db.session.flush()

        ag_account = InstanceAccount(
            instance_id=instance.id,
            username="jt_mssqlinfo_srv",
            db_type=DatabaseType.SQLSERVER,
            owner_type="sqlserver_ag",
            owner_id=ag.id,
            cluster_id=cluster.id,
            availability_group_id=ag.id,
            is_active=True,
        )
        db.session.add(ag_account)
        db.session.flush()
        db.session.add_all(
            [
                AccountPermission(
                    instance_id=instance.id,
                    db_type=DatabaseType.SQLSERVER,
                    instance_account_id=ag_account.id,
                    username="jt_mssqlinfo_srv",
                    owner_type="sqlserver_ag",
                    owner_id=ag.id,
                    cluster_id=cluster.id,
                    availability_group_id=ag.id,
                    permission_facts={"capabilities": []},
                ),
                AccountChangeLog(
                    instance_id=instance.id,
                    db_type=DatabaseType.SQLSERVER,
                    username="jt_mssqlinfo_srv",
                    owner_type="sqlserver_ag",
                    owner_id=ag.id,
                    cluster_id=cluster.id,
                    availability_group_id=ag.id,
                    change_type="add",
                    change_time=datetime(2026, 5, 21, 9, 5, tzinfo=UTC),
                    status="success",
                    message="新增账户",
                ),
            ],
        )
        db.session.commit()

        result = AccountChangeLogsRepository().list_logs(
            AccountChangeLogsListFilters(
                page=1,
                limit=20,
                sort_field="change_time",
                sort_order="asc",
                search_term="",
                instance_id=None,
                db_type=None,
                change_type=None,
                status=None,
                hours=None,
            ),
        )

        assert result.total == 1
        _log_entry, instance_name, instance_host, account_id = result.items[0]
        assert instance_name == "AGDB08-LSN"
        assert instance_host == "192.168.0.73"
        assert account_id == ag_account.id
