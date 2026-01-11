"""账户同步 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.orm import contains_eager, load_only

from app.models.account_permission import AccountPermission
from app.models.instance_account import InstanceAccount


class AccountsSyncRepository:
    """账户同步读模型 Repository."""

    @staticmethod
    def list_account_permissions_by_instance(
        instance_id: int,
        *,
        include_inactive: bool = False,
        include_permission_details: bool = False,
    ) -> list[AccountPermission]:
        """按实例获取账户权限列表."""
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
                    AccountPermission.type_specific,
                    AccountPermission.permission_facts,
                    AccountPermission.last_sync_time,
                    AccountPermission.last_change_type,
                    AccountPermission.last_change_time,
                ),
            )

        if not include_inactive:
            query = query.filter(InstanceAccount.is_active.is_(True))

        return query.order_by(AccountPermission.username.asc()).all()

    @staticmethod
    def list_instance_accounts(*, instance_id: int) -> list[InstanceAccount]:
        """按实例获取 InstanceAccount 列表."""
        return InstanceAccount.query.filter_by(instance_id=instance_id).all()

    @staticmethod
    def get_permission_by_instance_account_id(instance_account_id: int) -> AccountPermission | None:
        """按 instance_account_id 获取账户权限记录(可为空)."""
        return cast(
            "AccountPermission | None",
            AccountPermission.query.filter_by(instance_account_id=instance_account_id).first(),
        )

    @staticmethod
    def get_permission_by_instance_username(
        *,
        instance_id: int,
        db_type: str,
        username: str,
    ) -> AccountPermission | None:
        """按 (instance_id, db_type, username) 获取账户权限记录(可为空)."""
        return cast(
            "AccountPermission | None",
            AccountPermission.query.filter_by(
                instance_id=instance_id,
                db_type=db_type,
                username=username,
            ).first(),
        )

