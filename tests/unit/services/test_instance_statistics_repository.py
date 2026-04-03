from __future__ import annotations

import pytest

from app import create_app, db
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
            ],
        )


@pytest.mark.unit
def test_instance_statistics_repository_counts_total_current_active_inactive_and_deleted_instances(app) -> None:
    from app.models.instance import Instance

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
    from app.models.instance import Instance
    from app.models.instance_config_snapshot import InstanceConfigSnapshot
    from app.models.tag import Tag

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
