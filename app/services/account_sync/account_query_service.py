"""账户查询辅助服务。"""

from __future__ import annotations

from typing import List

from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance_account import InstanceAccount


def get_accounts_by_instance(instance_id: int, include_inactive: bool = False) -> List[CurrentAccountSyncData]:
    """按实例获取账户列表。

    Args:
        instance_id: 实例ID
        include_inactive: 是否包含已失活账户（默认为 False）
    """
    query = (
        CurrentAccountSyncData.query.join(InstanceAccount, CurrentAccountSyncData.instance_account)
        .filter(CurrentAccountSyncData.instance_id == instance_id)
    )
    if not include_inactive:
        query = query.filter(InstanceAccount.is_active.is_(True))
    return query.order_by(CurrentAccountSyncData.username.asc()).all()
