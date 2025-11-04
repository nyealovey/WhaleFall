from __future__ import annotations

from typing import Any, Dict, Iterable, List

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

PERMISSION_FIELDS = {
    "global_privileges",
    "database_privileges",
    "predefined_roles",
    "role_attributes",
    "database_privileges_pg",
    "tablespace_privileges",
    "server_roles",
    "server_permissions",
    "database_roles",
    "database_permissions",
    "oracle_roles",
    "system_privileges",
    "tablespace_privileges_oracle",
    "type_specific",
}


class PermissionSyncError(RuntimeError):
    """权限同步阶段出现错误时抛出，携带阶段 summary。"""

    def __init__(self, summary: Dict[str, Any], message: str | None = None) -> None:
        super().__init__(message or summary.get("message") or "权限同步失败")
        self.summary = summary


class AccountPermissionManager:
    """处理权限快照的增量更新。"""

    def __init__(self) -> None:
        self.logger = get_sync_logger()

    def synchronize(
        self,
        instance: Instance,
        remote_accounts: Iterable[dict],
        active_accounts: List[InstanceAccount],
        *,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        remote_map = {account["username"]: account for account in remote_accounts}
        created = 0
        updated = 0
        skipped = 0
        errors: List[str] = []

        for account in active_accounts:
            remote = remote_map.get(account.username)
            if not remote:
                skipped += 1
                continue

            permissions = remote.get("permissions", {})
            is_superuser = bool(remote.get("is_superuser", False))

            existing = AccountPermission.query.filter_by(instance_account_id=account.id).first()
            if not existing:
                existing = AccountPermission.query.filter_by(
                    instance_id=instance.id,
                    db_type=instance.db_type,
                    username=account.username,
                ).first()
                if existing and not existing.instance_account_id:
                    existing.instance_account_id = account.id
            if existing:
                diff = self._calculate_diff(existing, permissions, is_superuser)
                if diff["changed"]:
                    self._apply_permissions(existing, permissions, is_superuser)
                    existing.last_change_type = diff["change_type"]
                    existing.last_change_time = time_utils.now()
                    updated += 1
                    try:
                        self._log_change(
                            instance,
                            username=account.username,
                            change_type=diff["change_type"],
                            diff_payload=diff,
                            session_id=session_id,
                        )
                    except Exception as log_exc:  # noqa: BLE001
                        errors.append(f"记录权限变更日志失败: {log_exc}")
                        self.logger.error(
                            "account_permission_change_log_failed",
                            module="account_sync",
                            phase="collection",
                            instance_id=instance.id,
                            instance_name=instance.name,
                            username=account.username,
                            error=str(log_exc),
                        )
                        skipped += 1
                        continue
                else:
                    skipped += 1
                existing.last_sync_time = time_utils.now()
            else:
                existing = AccountPermission(
                    instance_id=instance.id,
                    db_type=instance.db_type,
                    instance_account_id=account.id,
                    username=account.username,
                    is_superuser=is_superuser,
                )
                self._apply_permissions(existing, permissions, is_superuser)
                existing.last_change_type = "add"
                existing.last_change_time = time_utils.now()
                existing.last_sync_time = time_utils.now()
                created += 1
                db.session.add(existing)

                try:
                    self._log_change(
                        instance,
                        username=account.username,
                        change_type="add",
                        diff_payload={"privilege_diff": permissions},
                        session_id=session_id,
                    )
                except Exception as log_exc:  # noqa: BLE001
                    errors.append(f"记录新增权限日志失败: {log_exc}")
                    self.logger.error(
                        "account_permission_change_log_failed",
                        module="account_sync",
                        phase="collection",
                        instance_id=instance.id,
                        instance_name=instance.name,
                        username=account.username,
                        error=str(log_exc),
                    )
                    skipped += 1
                    continue

        try:
            db.session.commit()
        except SQLAlchemyError as exc:  # noqa: BLE001
            db.session.rollback()
            self.logger.error(
                "account_permission_sync_commit_failed",
                instance=instance.name,
                instance_id=instance.id,
                module="account_sync",
                phase="collection",
                error=str(exc),
                exc_info=True,
            )
            raise

        summary: Dict[str, Any] = {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "processed_records": created + updated,
            "errors": errors,
            "status": "completed" if not errors else "failed",
            "message": None if not errors else "权限同步阶段发生错误",
        }

        if errors:
            self.logger.error(
                "account_permission_sync_failed",
                instance=instance.name,
                instance_id=instance.id,
                module="account_sync",
                phase="collection",
                errors=errors,
                session_id=session_id,
            )
            raise PermissionSyncError(summary)

        self.logger.info(
            "account_permission_sync_completed",
            instance=instance.name,
            instance_id=instance.id,
            module="account_sync",
            phase="collection",
            **{k: v for k, v in summary.items() if k not in {"errors"}},
        )

        return summary

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _apply_permissions(
        self,
        record: AccountPermission,
        permissions: Dict,
        is_superuser: bool,
    ) -> None:
        record.is_superuser = is_superuser
        for field in PERMISSION_FIELDS:
            if field in permissions:
                setattr(record, field, permissions[field])
            elif field == "type_specific":
                # 若未提供，保持原值
                continue
            else:
                setattr(record, field, None)

    def _calculate_diff(
        self,
        record: AccountPermission,
        permissions: Dict,
        is_superuser: bool,
    ) -> Dict[str, Any]:
        diff: Dict[str, Any] = {"changed": False}

        if record.is_superuser != is_superuser:
            diff["changed"] = True
            diff.setdefault("other_diff", {})["is_superuser"] = {
                "old": record.is_superuser,
                "new": is_superuser,
            }

        for field in PERMISSION_FIELDS:
            new_value = permissions.get(field)
            old_value = getattr(record, field)
            if new_value is None and old_value is None:
                continue
            if new_value != old_value:
                diff["changed"] = True
                diff.setdefault("privilege_diff", {})[field] = {
                    "old": old_value,
                    "new": new_value,
                }

        if not diff["changed"]:
            diff["change_type"] = "none"
        elif diff.get("privilege_diff"):
            diff["change_type"] = "modify_privilege"
        else:
            diff["change_type"] = "modify_other"

        return diff

    def _log_change(
        self,
        instance: Instance,
        *,
        username: str,
        change_type: str,
        diff_payload: Dict[str, Any],
    ) -> None:
        if change_type == "none":
            return

        log = AccountChangeLog(
            instance_id=instance.id,
            db_type=instance.db_type,
            username=username,
            change_type=change_type,
            change_time=time_utils.now(),
            privilege_diff=diff_payload.get("privilege_diff"),
            other_diff=diff_payload.get("other_diff"),
        )
        db.session.add(log)
