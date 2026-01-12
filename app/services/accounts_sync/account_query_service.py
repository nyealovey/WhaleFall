"""账户查询辅助服务."""

from __future__ import annotations

from app.models.account_permission import AccountPermission
from app.repositories.accounts_sync_repository import AccountsSyncRepository


def get_accounts_by_instance(
    instance_id: int,
    *,
    include_inactive: bool = False,
    include_permission_details: bool = False,
) -> list[AccountPermission]:
    """按实例获取账户列表.

    查询指定实例的所有账户权限记录,按用户名升序排列.

    Args:
        instance_id: 实例 ID.
        include_inactive: 是否包含已失活账户,默认为 False.
        include_permission_details: 是否包含权限明细字段,默认为 False(列表场景只取摘要字段).

    Returns:
        账户权限对象列表,按用户名升序排列.

    """
    return AccountsSyncRepository.list_account_permissions_by_instance(
        instance_id,
        include_inactive=include_inactive,
        include_permission_details=include_permission_details,
    )
