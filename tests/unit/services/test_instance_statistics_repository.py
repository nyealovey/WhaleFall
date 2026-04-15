from __future__ import annotations

from datetime import timedelta

import pytest

from app import create_app, db
from app.models.instance import Instance
from app.models.instance_config_snapshot import InstanceConfigSnapshot
from app.models.jumpserver_asset_snapshot import JumpServerAssetSnapshot
from app.models.tag import Tag
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.repositories.instance_statistics_repository import InstanceStatisticsRepository
from app.settings import Settings
from app.utils.time_utils import time_utils


@pytest.fixture(scope="function")
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True
    return app


def _ensure_instance_statistics_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
                db.metadata.tables["instance_config_snapshots"],
                db.metadata.tables["credentials"],
                db.metadata.tables["jumpserver_asset_snapshots"],
                db.metadata.tables["veeam_source_bindings"],
                db.metadata.tables["veeam_machine_backup_snapshots"],
            ],
        )


@pytest.mark.unit
def test_instance_statistics_repository_counts_total_current_active_inactive_and_deleted_instances(app) -> None:
    _ensure_instance_statistics_tables(app)

    with app.app_context():
        db.session.add_all(
            [
                Instance(name="mysql-active", db_type="mysql", host="127.0.0.1", port=3306, is_active=True),
                Instance(name="mysql-disabled", db_type="mysql", host="127.0.0.2", port=3307, is_active=False),
                Instance(
                    name="mysql-deleted",
                    db_type="mysql",
                    host="127.0.0.3",
                    port=3308,
                    is_active=True,
                    deleted_at=time_utils.now(),
                ),
            ],
        )
        db.session.commit()

        summary = InstanceStatisticsRepository.fetch_summary()

        assert summary["total_instances"] == 3
        assert summary["current_instances"] == 2
        assert summary["active_instances"] == 1
        assert summary["disabled_instances"] == 1
        assert summary["deleted_instances"] == 1
        assert summary["normal_instances"] == 1
        assert summary["audit_enabled_instances"] == 0
        assert summary["high_availability_instances"] == 0


@pytest.mark.unit
def test_instance_statistics_repository_counts_enabled_audit_and_non_standalone_architecture_as_ha(app) -> None:
    _ensure_instance_statistics_tables(app)

    with app.app_context():
        audit_enabled_ha = Instance(
            name="sqlserver-ha-audit", db_type="sqlserver", host="127.0.0.1", port=1433, is_active=True
        )
        active_standalone = Instance(
            name="sqlserver-standalone", db_type="sqlserver", host="127.0.0.2", port=1434, is_active=True
        )
        disabled_with_arch = Instance(
            name="sqlserver-disabled", db_type="sqlserver", host="127.0.0.3", port=1435, is_active=False
        )
        db.session.add_all([audit_enabled_ha, active_standalone, disabled_with_arch])
        db.session.flush()

        geo_redundant = Tag(name="geo_redundant", display_name="两地三中心", category="architecture")
        standalone = Tag(name="standalone", display_name="单机", category="architecture")
        db.session.add_all([geo_redundant, standalone])
        db.session.flush()

        audit_enabled_ha.tags.append(geo_redundant)
        active_standalone.tags.append(standalone)
        disabled_with_arch.tags.append(geo_redundant)
        db.session.flush()

        db.session.add_all(
            [
                InstanceConfigSnapshot(
                    instance_id=audit_enabled_ha.id,
                    db_type="sqlserver",
                    config_key="audit_info",
                    facts={"has_audit": True, "enabled_audit_count": 1},
                ),
                InstanceConfigSnapshot(
                    instance_id=active_standalone.id,
                    db_type="sqlserver",
                    config_key="audit_info",
                    facts={"has_audit": True, "enabled_audit_count": 0},
                ),
                InstanceConfigSnapshot(
                    instance_id=disabled_with_arch.id,
                    db_type="sqlserver",
                    config_key="audit_info",
                    facts={"has_audit": True, "enabled_audit_count": 1},
                ),
            ],
        )
        db.session.commit()

        summary = InstanceStatisticsRepository.fetch_summary()

        assert summary["total_instances"] == 3
        assert summary["current_instances"] == 3
        assert summary["active_instances"] == 2
        assert summary["disabled_instances"] == 1
        assert summary["audit_enabled_instances"] == 1
        assert summary["high_availability_instances"] == 1


@pytest.mark.unit
def test_instance_statistics_repository_counts_managed_and_backup_status_for_current_instances(app) -> None:
    _ensure_instance_statistics_tables(app)

    with app.app_context():
        now = time_utils.now()
        managed_backed_up = Instance(
            name="managed-backed-up", db_type="mysql", host="10.0.0.1", port=3306, is_active=True
        )
        unmanaged_stale = Instance(
            name="unmanaged-stale", db_type="mysql", host="10.0.0.2", port=3306, is_active=True
        )
        unmanaged_not_backed_up = Instance(
            name="unmanaged-not-backed-up", db_type="mysql", host="10.0.0.3", port=3306, is_active=True
        )
        disabled_managed_not_backed_up = Instance(
            name="disabled-managed-not-backed-up", db_type="mysql", host="10.0.0.4", port=3306, is_active=False
        )
        deleted_shadow = Instance(
            name="deleted-shadow",
            db_type="mysql",
            host="10.0.0.5",
            port=3306,
            is_active=True,
            deleted_at=now,
        )
        db.session.add_all(
            [
                managed_backed_up,
                unmanaged_stale,
                unmanaged_not_backed_up,
                disabled_managed_not_backed_up,
                deleted_shadow,
            ]
        )
        db.session.flush()

        db.session.add_all(
            [
                JumpServerAssetSnapshot(
                    external_id="asset-managed",
                    name="managed-backed-up",
                    db_type="mysql",
                    host="10.0.0.1",
                    port=3306,
                    raw_payload={},
                ),
                JumpServerAssetSnapshot(
                    external_id="asset-disabled",
                    name="disabled-managed-not-backed-up",
                    db_type="mysql",
                    host="10.0.0.4",
                    port=3306,
                    raw_payload={},
                ),
                JumpServerAssetSnapshot(
                    external_id="asset-deleted",
                    name="deleted-shadow",
                    db_type="mysql",
                    host="10.0.0.5",
                    port=3306,
                    raw_payload={},
                ),
                VeeamMachineBackupSnapshot(
                    machine_name="managed-backed-up",
                    normalized_machine_name="managed-backed-up",
                    machine_ip="10.0.0.1",
                    normalized_machine_ip="10.0.0.1",
                    latest_backup_at=now - timedelta(hours=2),
                    raw_payload={},
                ),
                VeeamMachineBackupSnapshot(
                    machine_name="unmanaged-stale",
                    normalized_machine_name="unmanaged-stale",
                    machine_ip="10.0.0.2",
                    normalized_machine_ip="10.0.0.2",
                    latest_backup_at=now - timedelta(days=2),
                    raw_payload={},
                ),
                VeeamMachineBackupSnapshot(
                    machine_name="deleted-shadow",
                    normalized_machine_name="deleted-shadow",
                    machine_ip="10.0.0.5",
                    normalized_machine_ip="10.0.0.5",
                    latest_backup_at=now - timedelta(hours=2),
                    raw_payload={},
                ),
            ]
        )
        db.session.commit()

        summary = InstanceStatisticsRepository.fetch_summary()

        assert summary["current_instances"] == 4
        assert summary["managed_instances"] == 2
        assert summary["unmanaged_instances"] == 2
        assert summary["backed_up_instances"] == 1
        assert summary["backup_stale_instances"] == 1
        assert summary["not_backed_up_instances"] == 2
