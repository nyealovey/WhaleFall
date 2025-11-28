"""账户查询辅助服务。"""

from __future__ import annotations

from typing import List

from app.models.account_permission import AccountPermission
from app.models.instance_account import InstanceAccount


def get_accounts_by_instance(instance_id: int, include_inactive: bool = False) -> List[AccountPermission]:
    """按实例获取账户列表。

    查询指定实例的所有账户权限记录，按用户名升序排列。

    Args:
        instance_id: 实例 ID。
        include_inactive: 是否包含已失活账户，默认为 False。

    Returns:
        账户权限对象列表，按用户名升序排列。
    """
    query = (
        AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)
        .filter(AccountPermission.instance_id == instance_id)
    )
    if not include_inactive:
        query = query.filter(InstanceAccount.is_active.is_(True))
    return query.order_by(AccountPermission.username.asc()).all()
