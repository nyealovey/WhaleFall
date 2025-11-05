import pytest

from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.services.account_sync.inventory_manager import AccountInventoryManager


@pytest.mark.unit
def test_account_inventory_manager_lifecycle(db):
    instance = Instance(
        name="test-instance",
        db_type="mysql",
        host="localhost",
        port=3306,
    )
    db.session.add(instance)
    db.session.commit()

    manager = AccountInventoryManager()

    stage_one_remote = [
        {"username": "user_a", "db_type": "mysql", "is_active": True},
        {"username": "user_b", "db_type": "mysql", "is_active": True},
    ]

    summary, active_accounts = manager.synchronize(instance, stage_one_remote)
    assert summary["created"] == 2
    assert len(active_accounts) == 2

    records = InstanceAccount.query.filter_by(instance_id=instance.id).all()
    assert len(records) == 2
    for record in records:
        assert record.is_active is True
        assert record.first_seen_at is not None

    stage_two_remote = [
        {"username": "user_b", "db_type": "mysql", "is_active": True},
        {"username": "user_c", "db_type": "mysql", "is_active": True},
    ]

    summary, active_accounts = manager.synchronize(instance, stage_two_remote)
    assert summary["created"] == 1
    assert summary["deactivated"] == 1
    assert len(active_accounts) == 2

    user_a = InstanceAccount.query.filter_by(instance_id=instance.id, username="user_a").first()
    assert user_a is not None
    assert user_a.is_active is False

    stage_three_remote = [
        {"username": "user_a", "db_type": "mysql", "is_active": True},
        {"username": "user_c", "db_type": "mysql", "is_active": True},
    ]

    summary, active_accounts = manager.synchronize(instance, stage_three_remote)
    assert summary["reactivated"] == 1
    assert summary["deactivated"] == 1
    assert len(active_accounts) == 2

    user_a = InstanceAccount.query.filter_by(instance_id=instance.id, username="user_a").first()
    assert user_a.is_active is True
