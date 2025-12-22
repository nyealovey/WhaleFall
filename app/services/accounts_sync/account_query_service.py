"""账户查询辅助服务."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.orm import contains_eager, load_only

from app.models.account_permission import AccountPermission
from app.models.instance_account import InstanceAccount


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
    instance_account_rel = cast("Any", AccountPermission.instance_account)
    query = (
        AccountPermission.query.join(instance_account_rel)
        .options(
            contains_eager(instance_account_rel).load_only(
                InstanceAccount.is_active,
                InstanceAccount.deleted_at,
            ),
        )
        .filter(AccountPermission.instance_id == instance_id)
    )
    if not include_permission_details:
        query = query.options(
            load_only(
                AccountPermission.id,
                AccountPermission.instance_id,
                AccountPermission.db_type,
                AccountPermission.instance_account_id,
                AccountPermission.username,
                AccountPermission.is_superuser,
                AccountPermission.is_locked,
                AccountPermission.type_specific,
                AccountPermission.last_sync_time,
                AccountPermission.last_change_type,
                AccountPermission.last_change_time,
            ),
        )
    if not include_inactive:
        query = query.filter(InstanceAccount.is_active.is_(True))
    return query.order_by(AccountPermission.username.asc()).all()
