"""账户清单同步管理器,负责维护 InstanceAccount 状态."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app import db
from app.models.instance_account import InstanceAccount
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.models.instance import Instance


class AccountInventoryManager:
    """维护 InstanceAccount 清单同步的管理器.

    负责将远程数据库账户与本地 InstanceAccount 表进行同步,
    包括创建新账户、重新激活已删除账户、停用不存在的账户.

    Attributes:
        logger: 同步日志记录器.

    """

    def __init__(self) -> None:
        """初始化账户清单管理器."""
        self.logger = get_sync_logger()

    def synchronize(self, instance: Instance, remote_accounts: Iterable[dict]) -> tuple[dict, list[InstanceAccount]]:
        """根据远端账户列表同步 InstanceAccount 表.

        将远程账户数据与本地数据库进行对比,执行以下操作:
        - 创建新发现的账户
        - 重新激活之前被删除的账户
        - 停用远程不存在的账户
        - 更新所有账户的最后可见时间

        Args:
            instance: 数据库实例对象.
            remote_accounts: 远程账户数据列表,每项至少包含以下字段:
                - username: 账户用户名
                - db_type: 数据库类型(可选,默认使用实例类型)
                - is_active: 是否活跃(可选,默认为 True)

        Returns:
            包含两个元素的元组:
            - 同步统计信息字典,包含以下字段:
                {
                    'created': 新创建的账户数,
                    'refreshed': 刷新的账户数,
                    'reactivated': 重新激活的账户数,
                    'deactivated': 停用的账户数,
                    'active_count': 活跃账户总数,
                    'total_remote': 远程账户总数,
                    'processed_records': 处理的记录数
                }
            - 活跃账户对象列表

        Raises:
            Exception: 当数据库提交失败时抛出.

        """
        remote_accounts = list(remote_accounts or [])
        now_ts = time_utils.now()

        existing_accounts = InstanceAccount.query.filter_by(instance_id=instance.id).all()
        existing_map = {account.username: account for account in existing_accounts}

        seen_usernames: set[str] = set()
        created = 0
        reactivated = 0
        refreshed = 0
        deactivated = 0

        active_accounts: list[InstanceAccount] = []

        for item in remote_accounts:
            username = str(item.get("username", "")).strip()
            if not username:
                continue

            seen_usernames.add(username)
            is_active = bool(item.get("is_active", True))
            db_type = (item.get("db_type") or instance.db_type).lower()

            record = existing_map.get(username)
            if record:
                record.last_seen_at = now_ts
                record.updated_at = now_ts
                record.db_type = db_type
                if not record.is_active and is_active:
                    record.is_active = True
                    record.deleted_at = None
                    reactivated += 1
                else:
                    refreshed += 1
            else:
                record = InstanceAccount(
                    instance_id=instance.id,
                    username=username,
                    db_type=db_type,
                    is_active=is_active,
                    first_seen_at=now_ts,
                    last_seen_at=now_ts,
                )
                db.session.add(record)
                existing_map[username] = record
                created += 1

            if is_active:
                active_accounts.append(record)

        for record in existing_accounts:
            if record.username not in seen_usernames and record.is_active:
                record.is_active = False
                record.deleted_at = now_ts
                record.updated_at = now_ts
                deactivated += 1

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            self.logger.exception(
                "account_inventory_sync_commit_failed",
                instance=instance.name,
                instance_id=instance.id,
                module="accounts_sync",
                phase="inventory",
                error=str(exc),
            )
            raise

        summary = {
            "created": created,
            "refreshed": refreshed,
            "reactivated": reactivated,
            "deactivated": deactivated,
            "active_count": len(active_accounts),
            "total_remote": len(remote_accounts),
            "processed_records": created + refreshed + reactivated,
        }

        self.logger.info(
            "account_inventory_sync_completed",
            instance=instance.name,
            instance_id=instance.id,
            module="accounts_sync",
            phase="inventory",
            **summary,
        )

        return summary, active_accounts
