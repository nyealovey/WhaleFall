from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import text

from app import create_app, db
from app.core.constants.status_types import TaskRunStatus
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.instance_config_snapshot import InstanceConfigSnapshot
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.models.jumpserver_asset_snapshot import JumpServerAssetSnapshot
from app.models.risk_center_rule_setting import RiskCenterRuleSetting
from app.models.mysql_cluster import MySQLCluster, MySQLClusterInstance
from app.models.sqlserver_ag_sync_state import SQLServerAgDatabaseSyncState, SQLServerAgReplicaSyncState
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.settings import Settings
from app.services.risk_center.risk_center_read_service import RiskCenterReadService
from app.services.risk_center.risk_center_rule_settings_service import RiskCenterRuleSettingsService


def _card_items(result: dict[str, object]) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], result["items"])


@pytest.fixture(scope="function")
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True
    return app


def _create_tables() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["instances"],
            db.metadata.tables["instance_accounts"],
            db.metadata.tables["account_permission"],
            db.metadata.tables["account_change_log"],
            db.metadata.tables["task_runs"],
            db.metadata.tables["task_run_items"],
            db.metadata.tables["credentials"],
            db.metadata.tables["instance_config_snapshots"],
            db.metadata.tables["jumpserver_asset_snapshots"],
            db.metadata.tables["risk_center_rule_settings"],
            db.metadata.tables["veeam_source_bindings"],
            db.metadata.tables["veeam_machine_backup_snapshots"],
            db.metadata.tables["mysql_clusters"],
            db.metadata.tables["mysql_cluster_instances"],
            db.metadata.tables["sqlserver_clusters"],
            db.metadata.tables["sqlserver_cluster_instances"],
            db.metadata.tables["sqlserver_availability_groups"],
            db.metadata.tables["sqlserver_ag_database_sync_states"],
            db.metadata.tables["sqlserver_ag_replica_sync_states"],
        ],
    )
    db.session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS instance_size_stats (
                id INTEGER NOT NULL,
                instance_id INTEGER NOT NULL,
                total_size_mb INTEGER NOT NULL,
                database_count INTEGER NOT NULL,
                collected_date DATE NOT NULL,
                collected_at DATETIME NOT NULL,
                is_deleted BOOLEAN NOT NULL,
                deleted_at DATETIME,
                created_at DATETIME,
                updated_at DATETIME,
                PRIMARY KEY (id, collected_date),
                FOREIGN KEY(instance_id) REFERENCES instances(id)
            );
            """,
        ),
    )
    db.session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS instance_size_aggregations (
                id INTEGER NOT NULL,
                instance_id INTEGER NOT NULL,
                period_type VARCHAR(20) NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                total_size_mb INTEGER NOT NULL,
                avg_size_mb INTEGER NOT NULL,
                max_size_mb INTEGER NOT NULL,
                min_size_mb INTEGER NOT NULL,
                data_count INTEGER NOT NULL,
                database_count INTEGER NOT NULL,
                avg_database_count NUMERIC(10,2),
                max_database_count INTEGER,
                min_database_count INTEGER,
                total_size_change_mb INTEGER,
                total_size_change_percent NUMERIC(10,2),
                database_count_change INTEGER,
                database_count_change_percent NUMERIC(10,2),
                growth_rate NUMERIC(10,2),
                trend_direction VARCHAR(20),
                calculated_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL,
                PRIMARY KEY (id, period_start),
                FOREIGN KEY(instance_id) REFERENCES instances(id)
            );
            """,
        ),
    )
    db.session.commit()


def _create_veeam_source() -> VeeamSourceBinding:
    credential = Credential(
        name="veeam-admin",
        credential_type="veeam",
        username="backup-admin",
        password="VeeamPass123",
        is_active=True,
    )
    db.session.add(credential)
    db.session.flush()
    source = VeeamSourceBinding(
        credential_id=credential.id,
        server_host="10.0.0.10",
        server_port=9419,
        api_version="1.3-rev1",
        is_enabled=True,
        verify_ssl=True,
        match_domains=[],
    )
    db.session.add(source)
    db.session.flush()
    return source


def _add_recent_backup(source: VeeamSourceBinding, instance: Instance, now: datetime) -> None:
    db.session.add(
        VeeamMachineBackupSnapshot(
            source_binding_id=source.id,
            machine_name=str(instance.name),
            normalized_machine_name=str(instance.name),
            latest_backup_at=now - timedelta(hours=2),
            raw_payload={},
        )
    )


def _add_capacity(instance: Instance, now: datetime, row_id: int) -> None:
    db.session.add(
        InstanceSizeStat(
            id=row_id,
            instance_id=instance.id,
            total_size_mb=1024,
            database_count=1,
            collected_at=now - timedelta(hours=3),
            collected_date=now.date(),
            is_deleted=False,
        )
    )


def _add_audit_snapshot(instance: Instance, now: datetime, *, has_audit: bool, enabled_count: int) -> None:
    db.session.add(
        InstanceConfigSnapshot(
            instance_id=instance.id,
            db_type=instance.db_type,
            config_key="audit_info",
            snapshot={},
            facts={
                "has_audit": has_audit,
                "audit_count": 1 if has_audit else 0,
                "enabled_audit_count": enabled_count,
            },
            last_sync_time=now - timedelta(hours=2),
        )
    )


@pytest.mark.unit
def test_risk_center_marks_missing_backup_as_critical(app) -> None:
    with app.app_context():
        _create_tables()
        instance = Instance(name="db-critical", db_type="mysql", host="10.0.0.1", port=3306, is_active=True)
        db.session.add(instance)
        db.session.commit()

        result = RiskCenterReadService().list_cards()

        card = _card_items(result)[0]
        assert card["overall_severity"] == "high"
        assert card["backup"]["label"] == "未备份"
        assert card["status_band"]["tone"] == "danger"
        assert card["status_band"]["label"] == "High · 备份缺失"
        assert all(item["label"] != "未备份" for item in card["risk_flags"])
        assert any(item["rule_key"] == "backup_missing" and item["severity"] == "high" for item in card["risk_items"])


@pytest.mark.unit
def test_risk_center_uses_configured_rule_severity_for_missing_backup(app) -> None:
    with app.app_context():
        _create_tables()
        rule_setting = RiskCenterRuleSetting()
        rule_setting.rule_key = "backup_missing"
        rule_setting.enabled = True
        rule_setting.severity = "medium"
        db.session.add(rule_setting)
        db.session.add(Instance(name="db-medium-backup", db_type="mysql", host="10.0.0.1", port=3306, is_active=True))
        db.session.commit()

        result = RiskCenterReadService().list_cards()

        card = _card_items(result)[0]
        assert card["overall_severity"] == "medium"
        assert card["backup"]["tone"] == "warning"
        assert card["risk_items"][0]["rule_key"] == "backup_missing"
        assert card["risk_items"][0]["severity"] == "medium"


@pytest.mark.unit
def test_risk_center_omits_disabled_rule_from_cards_and_summary(app) -> None:
    now = datetime.now(UTC)
    with app.app_context():
        _create_tables()
        rule_setting = RiskCenterRuleSetting()
        rule_setting.rule_key = "backup_missing"
        rule_setting.enabled = False
        rule_setting.severity = "high"
        db.session.add(rule_setting)
        instance = Instance(name="db-muted-backup", db_type="mysql", host="10.0.0.1", port=3306, is_active=True)
        db.session.add(instance)
        db.session.flush()
        _add_capacity(instance, now, 1)
        _add_audit_snapshot(instance, now, has_audit=True, enabled_count=1)
        db.session.commit()

        service = RiskCenterReadService()
        result = service.list_cards()
        summary = service.build_summary()

        card = _card_items(result)[0]
        assert card["overall_severity"] == "ok"
        assert card["risk_items"] == []
        assert summary["severity_counts"] == {"high": 0, "medium": 0, "low": 0, "ok": 1}
        assert summary["top_risks"] == []


@pytest.mark.unit
def test_risk_center_builds_audit_and_managed_metrics_without_unmanaged_risk(app) -> None:
    now = datetime.now(UTC)
    with app.app_context():
        _create_tables()
        source = _create_veeam_source()
        enabled = Instance(name="a-audit-enabled", db_type="sqlserver", host="10.0.0.11", port=1433, is_active=True)
        disabled = Instance(name="b-audit-disabled", db_type="mysql", host="10.0.0.12", port=3306, is_active=True)
        missing = Instance(name="c-audit-missing", db_type="postgresql", host="10.0.0.13", port=5432, is_active=True)
        db.session.add_all([enabled, disabled, missing])
        db.session.flush()
        for index, instance in enumerate([enabled, disabled, missing], start=1):
            _add_recent_backup(source, instance, now)
            _add_capacity(instance, now, index)
        _add_audit_snapshot(enabled, now, has_audit=True, enabled_count=1)
        _add_audit_snapshot(disabled, now, has_audit=True, enabled_count=0)
        db.session.add(
            JumpServerAssetSnapshot(
                external_id="managed-audit-enabled",
                name="a-audit-enabled",
                db_type="sqlserver",
                host="10.0.0.11",
                port=1433,
                raw_payload={},
                synced_at=now,
            )
        )
        db.session.commit()

        cards = {card["name"]: card for card in _card_items(RiskCenterReadService().list_cards())}

        assert cards["a-audit-enabled"]["audit"]["label"] == "已启用"
        assert cards["a-audit-enabled"]["managed"]["label"] == "已托管"
        assert cards["a-audit-enabled"]["overall_severity"] == "ok"
        assert cards["b-audit-disabled"]["audit"]["label"] == "未启用"
        assert cards["b-audit-disabled"]["managed"]["label"] == "未托管"
        assert cards["b-audit-disabled"]["overall_severity"] == "medium"
        assert cards["c-audit-missing"]["audit"]["label"] == "未配置"
        assert cards["c-audit-missing"]["managed"]["label"] == "未托管"
        assert cards["c-audit-missing"]["overall_severity"] == "medium"
        assert not any(item["category"] == "managed" for item in cards["b-audit-disabled"]["risk_items"])


@pytest.mark.unit
def test_risk_center_orders_high_medium_low_ok(app) -> None:
    now = datetime.now(UTC)
    with app.app_context():
        _create_tables()
        critical = Instance(name="a-critical", db_type="mysql", host="10.0.0.1", port=3306, is_active=True)
        warning = Instance(name="b-warning", db_type="postgresql", host="10.0.0.2", port=5432, is_active=True)
        unknown = Instance(name="c-unknown", db_type="oracle", host="10.0.0.3", port=1521, is_active=True)
        ok = Instance(name="d-ok", db_type="sqlserver", host="10.0.0.4", port=1433, is_active=True)
        db.session.add_all([critical, warning, unknown, ok])
        db.session.flush()
        source = _create_veeam_source()
        _add_audit_snapshot(unknown, now, has_audit=True, enabled_count=1)
        _add_audit_snapshot(ok, now, has_audit=True, enabled_count=1)

        db.session.add(
            VeeamMachineBackupSnapshot(
                source_binding_id=source.id,
                machine_name="b-warning",
                normalized_machine_name="b-warning",
                latest_backup_at=now - timedelta(hours=30),
                raw_payload={},
            )
        )
        db.session.add(
            VeeamMachineBackupSnapshot(
                source_binding_id=source.id,
                machine_name="c-unknown",
                normalized_machine_name="c-unknown",
                latest_backup_at=now - timedelta(hours=2),
                raw_payload={},
            )
        )
        account = InstanceAccount(instance_id=unknown.id, username="root", db_type="oracle", is_active=True)
        db.session.add(account)
        db.session.flush()
        db.session.add(
            AccountPermission(
                instance_id=unknown.id,
                instance_account_id=account.id,
                db_type="oracle",
                username="root",
                permission_facts={"capabilities": ["SUPERUSER"]},
                last_sync_time=now,
            )
        )
        db.session.add(
            VeeamMachineBackupSnapshot(
                source_binding_id=source.id,
                machine_name="d-ok",
                normalized_machine_name="d-ok",
                latest_backup_at=now - timedelta(hours=2),
                raw_payload={},
            )
        )
        db.session.add(
            InstanceSizeStat(
                id=1,
                instance_id=warning.id,
                total_size_mb=2048,
                database_count=3,
                collected_at=now - timedelta(hours=3),
                collected_date=now.date(),
                is_deleted=False,
            )
        )
        db.session.add(
            InstanceSizeAggregation(
                id=1,
                instance_id=warning.id,
                period_type="day",
                period_start=now.date(),
                period_end=now.date(),
                total_size_mb=2048,
                avg_size_mb=2048,
                max_size_mb=2048,
                min_size_mb=2048,
                data_count=1,
                database_count=3,
                growth_rate=35,
                calculated_at=now,
            )
        )
        db.session.add(
            InstanceSizeStat(
                id=2,
                instance_id=ok.id,
                total_size_mb=1024,
                database_count=2,
                collected_at=now - timedelta(hours=3),
                collected_date=now.date(),
                is_deleted=False,
            )
        )
        db.session.commit()

        result = RiskCenterReadService().list_cards()

        cards = _card_items(result)
        assert [item["name"] for item in cards] == ["a-critical", "b-warning", "c-unknown", "d-ok"]
        assert [item["overall_severity"] for item in cards] == ["high", "medium", "low", "ok"]


@pytest.mark.unit
def test_risk_center_summary_counts_each_instance_in_three_visible_buckets() -> None:
    cards: list[dict[str, object]] = [
        {"overall_severity": "high", "risk_items": [{"severity": "high"}, {"severity": "medium"}]},
        {"overall_severity": "medium", "risk_items": [{"severity": "medium"}, {"severity": "medium"}]},
        {"overall_severity": "low", "risk_items": [{"severity": "low"}]},
        {"overall_severity": "ok", "risk_items": []},
    ]

    counts = RiskCenterReadService._build_severity_counts(cards)

    assert counts == {"high": 1, "medium": 1, "low": 1, "ok": 1}
    assert sum(counts.values()) == len(cards)


@pytest.mark.unit
def test_risk_center_ok_filter_includes_non_warning_non_critical_cards() -> None:
    cards = [
        {"overall_severity": "high", "db_type": "mysql", "status": "active", "tags": [], "name": "a", "host": "1"},
        {"overall_severity": "medium", "db_type": "mysql", "status": "active", "tags": [], "name": "b", "host": "2"},
        {"overall_severity": "low", "db_type": "mysql", "status": "active", "tags": [], "name": "c", "host": "3"},
        {"overall_severity": "ok", "db_type": "mysql", "status": "active", "tags": [], "name": "e", "host": "5"},
    ]

    filtered = [
        card
        for card in cards
        if RiskCenterReadService._matches_filters(card, severity="ok", db_type="", status="", tag="", search="")
    ]

    assert [card["overall_severity"] for card in filtered] == ["ok"]


@pytest.mark.unit
def test_risk_center_filters_match_search_db_type_status_and_tag() -> None:
    cards = [
        {
            "overall_severity": "medium",
            "db_type": "mysql",
            "status": "active",
            "tags": [{"name": "prod"}],
            "name": "billing-main",
            "host": "10.2.0.10",
        },
        {
            "overall_severity": "high",
            "db_type": "sqlserver",
            "status": "inactive",
            "tags": [{"name": "finance"}],
            "name": "finance-ledger",
            "host": "10.8.0.20",
        },
    ]

    def matched_names(**filters: str) -> list[str]:
        defaults = {"severity": "", "db_type": "", "status": "", "tag": "", "search": ""}
        defaults.update(filters)
        return [
            str(card["name"])
            for card in cards
            if RiskCenterReadService._matches_filters(
                card,
                severity=defaults["severity"],
                db_type=defaults["db_type"],
                status=defaults["status"],
                tag=defaults["tag"],
                search=defaults["search"],
            )
        ]

    assert matched_names(search="ledger") == ["finance-ledger"]
    assert matched_names(search="10.2.0") == ["billing-main"]
    assert matched_names(search="sqlserver") == ["finance-ledger"]
    assert matched_names(db_type="mysql") == ["billing-main"]
    assert matched_names(status="inactive") == ["finance-ledger"]
    assert matched_names(tag="finance") == ["finance-ledger"]


@pytest.mark.unit
def test_risk_center_builds_access_and_task_risks(app) -> None:
    now = datetime.now(UTC)
    with app.app_context():
        _create_tables()
        instance = Instance(name="db-access", db_type="postgresql", host="10.0.0.8", port=5432, is_active=True)
        db.session.add(instance)
        db.session.flush()
        source = _create_veeam_source()
        account = InstanceAccount(instance_id=instance.id, username="root", db_type="postgresql", is_active=True)
        db.session.add(account)
        db.session.flush()
        db.session.add(
            AccountPermission(
                instance_id=instance.id,
                instance_account_id=account.id,
                db_type="postgresql",
                username="root",
                permission_facts={"capabilities": ["SUPERUSER"]},
                last_sync_time=now,
            )
        )
        db.session.add(
            AccountChangeLog(
                instance_id=instance.id,
                username="root",
                db_type="postgresql",
                change_type="permission_changed",
                change_time=now - timedelta(hours=2),
                status="success",
            )
        )
        run = TaskRun()
        run.run_id = "run-risk-1"
        run.task_key = "accounts_sync"
        run.task_name = "账户同步"
        run.task_category = "account"
        run.trigger_source = "manual"
        run.status = TaskRunStatus.FAILED
        run.started_at = now - timedelta(hours=1)
        db.session.add(run)
        db.session.flush()
        item = TaskRunItem()
        item.run_id = run.run_id
        item.item_type = "instance"
        item.item_key = str(instance.id)
        item.item_name = instance.name
        item.instance_id = instance.id
        item.status = TaskRunStatus.FAILED
        item.started_at = now - timedelta(hours=1)
        item.error_message = "同步失败"
        db.session.add(item)
        db.session.add(
            VeeamMachineBackupSnapshot(
                source_binding_id=source.id,
                machine_name="db-access",
                normalized_machine_name="db-access",
                latest_backup_at=now - timedelta(hours=2),
                raw_payload={},
            )
        )
        db.session.add(
            InstanceSizeStat(
                id=1,
                instance_id=instance.id,
                total_size_mb=512,
                database_count=1,
                collected_at=now - timedelta(hours=3),
                collected_date=now.date(),
                is_deleted=False,
            )
        )
        db.session.commit()

        result = RiskCenterReadService().list_cards()

        card = _card_items(result)[0]
        assert card["access"]["label"] == "1 高权"
        assert card["tasks"]["label"] == "账户同步失败"
        assert any(item["category"] == "task" for item in card["risk_flags"])
        assert any(item["category"] == "access" for item in card["risk_flags"])


@pytest.mark.unit
def test_risk_center_task_metric_names_failed_sync_task() -> None:
    instance = Instance(id=44, name="db-task", db_type="mysql", host="10.0.0.44", port=3306, is_active=True)
    run = TaskRun()
    run.run_id = "run-db-sync"
    run.task_key = "database_sync"
    run.task_name = "数据库同步"
    run.task_category = "database"
    run.trigger_source = "scheduler"
    run.status = TaskRunStatus.FAILED
    run.started_at = datetime(2026, 5, 14, 8, tzinfo=UTC)
    item = TaskRunItem()
    item.run_id = run.run_id
    item.item_type = "instance"
    item.item_key = str(instance.id)
    item.item_name = instance.name
    item.instance_id = instance.id
    item.status = TaskRunStatus.FAILED
    item.started_at = run.started_at
    item.error_message = "数据库同步超时"
    item.run = run

    task_metric, task_risks = RiskCenterReadService._build_task_metric(instance, item)

    assert task_metric["label"] == "数据库同步失败"
    assert task_metric["detail"] == "定时任务"
    assert task_metric["tone"] == "warning"
    assert task_risks[0]["label"] == "数据库同步失败"


@pytest.mark.unit
def test_risk_center_does_not_treat_locked_accounts_as_access_risk() -> None:
    instance = Instance(id=42, name="db-locked", db_type="mysql", host="10.0.0.42", port=3306, is_active=True)

    access_metric, access_risks = RiskCenterReadService._build_access_metric(
        instance,
        {"locked_count": 2, "superuser_count": 0, "recent_change_count": 0},
    )

    assert access_metric["label"] == "正常"
    assert access_metric["tone"] == "success"
    assert access_metric["locked_count"] == 2
    assert access_risks == []


@pytest.mark.unit
def test_risk_center_locked_accounts_do_not_hide_superuser_access_risk() -> None:
    instance = Instance(id=43, name="db-super", db_type="mysql", host="10.0.0.43", port=3306, is_active=True)

    access_metric, access_risks = RiskCenterReadService._build_access_metric(
        instance,
        {"locked_count": 2, "superuser_count": 1, "recent_change_count": 0},
    )

    assert access_metric["label"] == "1 高权"
    assert access_metric["tone"] == "info"
    assert [risk["label"] for risk in access_risks] == ["存在高权账号"]


@pytest.mark.unit
def test_risk_center_rule_defaults_exclude_capacity_stale_capacity_missing_and_inactive() -> None:
    rules = RiskCenterRuleSettingsService.build_default_map()

    assert "capacity_stale" not in rules
    assert "capacity_missing" not in rules
    assert "instance_inactive" not in rules


@pytest.mark.unit
def test_risk_center_rule_defaults_include_cluster_abnormal() -> None:
    rules = RiskCenterRuleSettingsService.build_default_map()

    assert rules["cluster_abnormal"]["label"] == "群集异常"
    assert rules["cluster_abnormal"]["severity"] == "medium"


@pytest.mark.unit
def test_risk_center_marks_sqlserver_cluster_abnormal_on_secondary_instance(app) -> None:
    now = datetime.now(UTC)
    with app.app_context():
        _create_tables()
        source = _create_veeam_source()
        primary = Instance(name="sql-primary", db_type="sqlserver", host="10.0.0.51", port=1433, is_active=True)
        secondary = Instance(name="sql-secondary", db_type="sqlserver", host="10.0.0.52", port=1433, is_active=True)
        cluster = SQLServerCluster(name="sql-cluster")
        db.session.add_all([primary, secondary, cluster])
        db.session.flush()
        ag = SQLServerAvailabilityGroup(cluster_id=cluster.id, name="ag-main", is_enabled=True)
        db.session.add(ag)
        db.session.flush()
        db.session.add_all(
            [
                SQLServerClusterInstance(cluster_id=cluster.id, instance_id=primary.id),
                SQLServerClusterInstance(cluster_id=cluster.id, instance_id=secondary.id),
            ]
        )
        for index, instance in enumerate([primary, secondary], start=1):
            _add_recent_backup(source, instance, now)
            _add_capacity(instance, now, index)
            _add_audit_snapshot(instance, now, has_audit=True, enabled_count=1)
        db.session.add(
            SQLServerAgReplicaSyncState(
                cluster_id=cluster.id,
                availability_group_id=ag.id,
                ag_name=ag.name,
                replica_server_name=primary.name,
                role_desc="PRIMARY",
                synchronization_health_desc="HEALTHY",
                connected_state_desc="CONNECTED",
                operational_state_desc="ONLINE",
                recovery_health_desc="ONLINE",
                is_primary=True,
                is_abnormal=False,
                last_checked_at=now,
            )
        )
        db.session.add(
            SQLServerAgReplicaSyncState(
                cluster_id=cluster.id,
                availability_group_id=ag.id,
                ag_name=ag.name,
                replica_server_name=secondary.name,
                role_desc="SECONDARY",
                synchronization_health_desc="NOT_HEALTHY",
                connected_state_desc="DISCONNECTED",
                operational_state_desc="ONLINE",
                recovery_health_desc="ONLINE",
                is_primary=False,
                is_abnormal=True,
                error_summary="health=NOT_HEALTHY; connected=DISCONNECTED",
                last_checked_at=now,
            )
        )
        db.session.commit()

        cards = {card["name"]: card for card in _card_items(RiskCenterReadService().list_cards())}

        primary_risks = {item["rule_key"] for item in cards["sql-primary"]["risk_items"]}
        secondary_risks = {item["rule_key"] for item in cards["sql-secondary"]["risk_items"]}
        assert "cluster_abnormal" not in primary_risks
        assert "cluster_abnormal" in secondary_risks
        cluster_risk = next(item for item in cards["sql-secondary"]["risk_items"] if item["rule_key"] == "cluster_abnormal")
        assert cluster_risk["severity"] == "medium"
        assert cluster_risk["label"] == "群集异常"
        assert "ag-main" in str(cluster_risk["detail"])
        assert cards["sql-secondary"]["cluster"]["label"] == "群集异常"
        assert cards["sql-secondary"]["cluster"]["tone"] == "warning"


@pytest.mark.unit
def test_risk_center_marks_sqlserver_database_sync_abnormal_on_secondary_instance(app) -> None:
    now = datetime.now(UTC)
    with app.app_context():
        _create_tables()
        source = _create_veeam_source()
        primary = Instance(name="sql-primary-db", db_type="sqlserver", host="10.0.0.61", port=1433, is_active=True)
        secondary = Instance(name="sql-secondary-db", db_type="sqlserver", host="10.0.0.62", port=1433, is_active=True)
        cluster = SQLServerCluster(name="sql-cluster-db")
        db.session.add_all([primary, secondary, cluster])
        db.session.flush()
        ag = SQLServerAvailabilityGroup(cluster_id=cluster.id, name="ag-db", is_enabled=True)
        db.session.add(ag)
        db.session.flush()
        db.session.add_all(
            [
                SQLServerClusterInstance(cluster_id=cluster.id, instance_id=primary.id),
                SQLServerClusterInstance(cluster_id=cluster.id, instance_id=secondary.id),
            ]
        )
        for index, instance in enumerate([primary, secondary], start=1):
            _add_recent_backup(source, instance, now)
            _add_capacity(instance, now, index)
            _add_audit_snapshot(instance, now, has_audit=True, enabled_count=1)
        db.session.add(
            SQLServerAgReplicaSyncState(
                cluster_id=cluster.id,
                availability_group_id=ag.id,
                ag_name=ag.name,
                replica_server_name=secondary.name,
                role_desc="SECONDARY",
                synchronization_health_desc="HEALTHY",
                connected_state_desc="CONNECTED",
                operational_state_desc="ONLINE",
                recovery_health_desc="ONLINE",
                is_primary=False,
                is_abnormal=False,
                last_checked_at=now,
            )
        )
        db.session.add(
            SQLServerAgDatabaseSyncState(
                cluster_id=cluster.id,
                availability_group_id=ag.id,
                ag_name=ag.name,
                database_name="billing",
                replica_server_name=secondary.name,
                synchronization_state_desc="NOT_SYNCHRONIZING",
                synchronization_health_desc="NOT_HEALTHY",
                database_state_desc="ONLINE",
                is_suspended=False,
                is_abnormal=True,
                error_summary="sync_state=NOT_SYNCHRONIZING; health=NOT_HEALTHY",
                last_checked_at=now,
            )
        )
        db.session.commit()

        cards = {card["name"]: card for card in _card_items(RiskCenterReadService().list_cards())}

        primary_risks = {item["rule_key"] for item in cards["sql-primary-db"]["risk_items"]}
        secondary_risks = {item["rule_key"] for item in cards["sql-secondary-db"]["risk_items"]}
        assert "cluster_abnormal" not in primary_risks
        assert "cluster_abnormal" in secondary_risks
        cluster_risk = next(item for item in cards["sql-secondary-db"]["risk_items"] if item["rule_key"] == "cluster_abnormal")
        assert "billing" in str(cluster_risk["detail"])


@pytest.mark.unit
def test_risk_center_marks_mysql_replica_abnormal_on_replica_instance(app) -> None:
    now = datetime.now(UTC)
    with app.app_context():
        _create_tables()
        source = _create_veeam_source()
        primary = Instance(name="mysql-primary", db_type="mysql", host="10.0.0.71", port=3306, is_active=True)
        replica = Instance(name="mysql-replica", db_type="mysql", host="10.0.0.72", port=3306, is_active=True)
        cluster = MySQLCluster(name="mysql-cluster", is_enabled=True)
        db.session.add_all([primary, replica, cluster])
        db.session.flush()
        db.session.add_all(
            [
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=primary.id,
                    replication_role="primary",
                    replication_status="healthy",
                    last_checked_at=now,
                ),
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=replica.id,
                    replication_role="replica",
                    replication_status="unhealthy",
                    last_io_error="Got fatal error 1236 from source",
                    last_checked_at=now,
                ),
            ]
        )
        for index, instance in enumerate([primary, replica], start=1):
            _add_recent_backup(source, instance, now)
            _add_capacity(instance, now, index)
            _add_audit_snapshot(instance, now, has_audit=True, enabled_count=1)
        db.session.commit()

        cards = {card["name"]: card for card in _card_items(RiskCenterReadService().list_cards())}

        primary_risks = {item["rule_key"] for item in cards["mysql-primary"]["risk_items"]}
        replica_risks = {item["rule_key"] for item in cards["mysql-replica"]["risk_items"]}
        assert "cluster_abnormal" not in primary_risks
        assert "cluster_abnormal" in replica_risks


@pytest.mark.unit
def test_risk_center_omits_capacity_missing_capacity_stale_and_inactive_risks() -> None:
    now = datetime.now(UTC)
    instance = SimpleNamespace(id=46, name="db-muted", db_type="mysql", host="10.0.0.46", port=3306, is_active=False)

    card = RiskCenterReadService()._build_card(
        instance=instance,
        now=now,
        backup={"latest_backup_at": (now - timedelta(hours=2)).isoformat()},
        capacity=SimpleNamespace(total_size_mb=1024, collected_at=now - timedelta(hours=72)),
        growth=None,
        audit=SimpleNamespace(
            facts={"has_audit": True, "enabled_audit_count": 1},
            last_sync_time=now - timedelta(hours=1),
        ),
        managed=False,
        access={},
        failed_task=None,
        cluster_issues=[],
        tags=[],
        rule_map={},
    )

    rule_keys = {str(item["rule_key"]) for item in card["risk_items"]}
    assert "capacity_stale" not in rule_keys
    assert "capacity_missing" not in rule_keys
    assert "instance_inactive" not in rule_keys
    assert card["overall_severity"] == "ok"


@pytest.mark.unit
def test_risk_center_group_ignores_instance_tags() -> None:
    now = datetime.now(UTC)
    instance = SimpleNamespace(id=45, name="db-prod", db_type="mysql", host="10.0.0.45", port=3306, is_active=True)

    card = RiskCenterReadService()._build_card(
        instance=instance,
        now=now,
        backup={},
        capacity=None,
        growth=None,
        audit=None,
        managed=False,
        access={},
        failed_task=None,
        cluster_issues=[],
        tags=[SimpleNamespace(name="prod", display_name="生产"), SimpleNamespace(name="replica", display_name="主从")],
        rule_map={},
    )

    assert card["group"] == "MYSQL"


@pytest.mark.unit
def test_risk_center_top_risks_include_only_high_and_medium_without_twelve_item_cap() -> None:
    cards = [
        {
            "instance_id": index,
            "name": f"db-{index:02d}",
            "db_type": "mysql",
            "host": f"10.0.0.{index}",
            "group": "MYSQL",
            "risk_items": [
                {
                    "rule_key": "backup_stale",
                    "category": "backup",
                    "severity": "medium",
                    "label": "备份滞后",
                    "detail": "最近备份过期",
                    "occurred_at": f"2026-05-27T00:{index:02d}:00+00:00",
                }
            ],
        }
        for index in range(13)
    ]
    cards.append(
        {
            "instance_id": 99,
            "name": "db-low",
            "db_type": "mysql",
            "host": "10.0.0.99",
            "group": "MYSQL",
            "risk_items": [
                {
                    "rule_key": "access_superuser",
                    "category": "access",
                    "severity": "low",
                    "label": "存在高权账号",
                    "detail": "1 个账号具备超级权限",
                    "occurred_at": "2026-05-27T01:00:00+00:00",
                }
            ],
        }
    )

    top_risks = RiskCenterReadService._build_top_risks(cards)

    assert len(top_risks) == 13
    assert {risk["severity"] for risk in top_risks} == {"medium"}
