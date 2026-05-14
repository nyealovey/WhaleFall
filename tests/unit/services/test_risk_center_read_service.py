from datetime import UTC, datetime, timedelta
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
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.settings import Settings
from app.services.risk_center.risk_center_read_service import RiskCenterReadService


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
            db.metadata.tables["veeam_source_bindings"],
            db.metadata.tables["veeam_machine_backup_snapshots"],
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


@pytest.mark.unit
def test_risk_center_marks_missing_backup_as_critical(app) -> None:
    with app.app_context():
        _create_tables()
        instance = Instance(name="db-critical", db_type="mysql", host="10.0.0.1", port=3306, is_active=True)
        db.session.add(instance)
        db.session.commit()

        result = RiskCenterReadService().list_cards()

        card = _card_items(result)[0]
        assert card["overall_severity"] == "critical"
        assert card["backup"]["label"] == "未备份"
        assert card["status_band"]["tone"] == "danger"
        assert any(item["category"] == "backup" and item["severity"] == "critical" for item in card["risk_flags"])


@pytest.mark.unit
def test_risk_center_orders_critical_warning_unknown_ok(app) -> None:
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
        assert [item["overall_severity"] for item in cards] == ["critical", "warning", "unknown", "ok"]


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
        assert card["tasks"]["label"] == "任务失败"
        assert any(item["category"] == "task" for item in card["risk_flags"])
        assert any(item["category"] == "access" for item in card["risk_flags"])
