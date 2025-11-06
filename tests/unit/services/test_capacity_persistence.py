from datetime import datetime, timezone, date

import pytest

from app.models.instance import Instance
from app.services.database_sync.persistence import CapacityPersistence


@pytest.mark.unit
def test_save_database_stats_upsert(db):
    instance = Instance(
        name="test-instance",
        db_type="postgresql",
        host="127.0.0.1",
        port=5432,
    )
    db.session.add(instance)
    db.session.commit()

    persistence = CapacityPersistence()
    collected_date = date(2025, 11, 6)
    collected_at = datetime(2025, 11, 6, 3, 0, tzinfo=timezone.utc)

    # 首次写入
    first_payload = [
        {
            "database_name": "pangus",
            "size_mb": 100,
            "data_size_mb": 90,
            "log_size_mb": 10,
            "collected_date": collected_date,
            "collected_at": collected_at,
        }
    ]

    saved_count = persistence.save_database_stats(instance, first_payload)
    assert saved_count == 1

    from app.models.database_size_stat import DatabaseSizeStat

    stat = DatabaseSizeStat.query.filter_by(instance_id=instance.id).one()
    assert stat.size_mb == 100
    assert stat.collected_date == collected_date

    # 第二次写入同一主键，确保更新而非新增
    updated_payload = [
        {
            "database_name": "pangus",
            "size_mb": 150,
            "data_size_mb": 120,
            "log_size_mb": 30,
            "collected_date": collected_date,
            "collected_at": collected_at,
        }
    ]

    saved_count = persistence.save_database_stats(instance, updated_payload)
    assert saved_count == 1

    stat = DatabaseSizeStat.query.filter_by(instance_id=instance.id).one()
    assert stat.size_mb == 150
    assert stat.data_size_mb == 120
    assert stat.log_size_mb == 30

    # 确认只有一条记录存在
    assert DatabaseSizeStat.query.filter_by(instance_id=instance.id).count() == 1
