import pytest

from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.services.database_sync import DatabaseSizeCollectorService
from app.utils.time_utils import time_utils


@pytest.mark.unit
def test_sync_instance_databases_lifecycle(db):
    instance = Instance(
        name="test-instance",
        db_type="mysql",
        host="localhost",
        port=3306,
    )
    db.session.add(instance)
    db.session.commit()

    service = DatabaseSizeCollectorService(instance)
    today = time_utils.now_china().date()

    # 首次同步：创建所有数据库记录
    initial_metadata = [
        {"database_name": "db_one"},
        {"database_name": "db_two"},
    ]
    summary_initial = service.sync_instance_databases(initial_metadata)

    assert summary_initial["created"] == 2
    assert summary_initial["refreshed"] == 0
    assert summary_initial["reactivated"] == 0
    assert summary_initial["deactivated"] == 0
    assert summary_initial["active_databases"] == ["db_one", "db_two"]

    db_records = InstanceDatabase.query.filter_by(instance_id=instance.id).all()
    assert len(db_records) == 2
    for record in db_records:
        assert record.is_active
        assert record.first_seen_date == today
        assert record.last_seen_date == today
        assert record.deleted_at is None

    # 第二次同步：新增 db_three，db_one 被标记为删除
    second_metadata = [
        {"database_name": "db_two"},
        {"database_name": "db_three"},
    ]
    summary_second = service.sync_instance_databases(second_metadata)

    assert summary_second["created"] == 1
    assert summary_second["refreshed"] == 1  # db_two
    assert summary_second["reactivated"] == 0
    assert summary_second["deactivated"] == 1  # db_one
    assert summary_second["active_databases"] == ["db_three", "db_two"]

    db_one = InstanceDatabase.query.filter_by(
        instance_id=instance.id, database_name="db_one"
    ).first()
    assert db_one is not None
    assert not db_one.is_active
    assert db_one.deleted_at is not None

    db_three = InstanceDatabase.query.filter_by(
        instance_id=instance.id, database_name="db_three"
    ).first()
    assert db_three is not None
    assert db_three.is_active
    assert db_three.first_seen_date == today
    assert db_three.last_seen_date == today

    # 第三次同步：db_one 重新出现，应被恢复成活跃状态
    third_metadata = [
        {"database_name": "db_one"},
        {"database_name": "db_three"},
    ]
    summary_third = service.sync_instance_databases(third_metadata)

    assert summary_third["created"] == 0
    assert summary_third["refreshed"] == 1  # db_three 保持活跃
    assert summary_third["reactivated"] == 1  # db_one 被恢复
    assert summary_third["deactivated"] == 1  # db_two 被标记删除
    assert summary_third["active_databases"] == ["db_one", "db_three"]

    db_one = InstanceDatabase.query.filter_by(
        instance_id=instance.id, database_name="db_one"
    ).first()
    assert db_one.is_active
    assert db_one.deleted_at is None
    assert db_one.last_seen_date == today

    db_two = InstanceDatabase.query.filter_by(
        instance_id=instance.id, database_name="db_two"
    ).first()
    assert db_two is not None
    assert not db_two.is_active
