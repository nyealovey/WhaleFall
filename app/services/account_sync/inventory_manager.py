from __future__ import annotations

from typing import Iterable, List, Tuple

from app import db
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


class AccountInventoryManager:
    """维护 InstanceAccount 清单同步的管理器。"""

    def __init__(self) -> None:
        self.logger = get_sync_logger()

    def synchronize(self, instance: Instance, remote_accounts: Iterable[dict]) -> Tuple[dict, List[InstanceAccount]]:
        """根据远端账户列表同步 InstanceAccount 表。

        Args:
            instance: 数据库实例
            remote_accounts: 远程账户数据列表，每项至少包含 username、db_type、attributes（可选）、is_active

        Returns:
            Tuple[dict, List[InstanceAccount]]: 同步统计信息与活跃账户对象列表
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

        active_accounts: List[InstanceAccount] = []

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
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            self.logger.error(
                "account_inventory_sync_commit_failed",
                instance=instance.name,
                instance_id=instance.id,
                module="account_sync",
                phase="inventory",
                error=str(exc),
                exc_info=True,
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
            module="account_sync",
            phase="inventory",
            **summary,
        )

        return summary, active_accounts
