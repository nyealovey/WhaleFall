"""账户权限同步管理器，实现权限增量及变更日志。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from collections.abc import Iterable

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

PRIVILEGE_FIELD_LABELS: dict[str, str] = {
    "global_privileges": "全局权限",
    "database_privileges": "数据库权限",
    "database_privileges_pg": "数据库权限",
    "predefined_roles": "预设角色",
    "role_attributes": "角色属性",
    "tablespace_privileges": "表空间权限",
    "server_roles": "服务器角色",
    "server_permissions": "服务器权限",
    "database_roles": "数据库角色",
    "database_permissions": "数据库权限",
    "oracle_roles": "Oracle 角色",
    "system_privileges": "系统权限",
    "tablespace_privileges_oracle": "表空间权限",
}

OTHER_FIELD_LABELS: dict[str, str] = {
    "is_superuser": "超级用户",
    "is_locked": "锁定状态",
    "type_specific": "数据库特性",
}


class PermissionSyncError(RuntimeError):
    """权限同步阶段出现错误时抛出，携带阶段 summary。

    Attributes:
        summary: 同步阶段的统计信息字典。

    """

    def __init__(self, summary: dict[str, Any], message: str | None = None) -> None:
        """初始化权限同步错误。

        Args:
            summary: 同步阶段的统计信息。
            message: 错误消息，可选。

        """
        super().__init__(message or summary.get("message") or "权限同步失败")
        self.summary = summary


class AccountPermissionManager:
    """处理权限快照的增量更新。

    负责将远程账户权限与本地 AccountPermission 表进行同步，
    包括创建新权限记录、更新已变更的权限、记录权限变更日志。

    Attributes:
        logger: 同步日志记录器。

    """

    def __init__(self) -> None:
        """初始化账户权限管理器。"""
        self.logger = get_sync_logger()

    def synchronize(
        self,
        instance: Instance,
        remote_accounts: Iterable[dict],
        active_accounts: list[InstanceAccount],
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """同步账户权限数据。

        将远程账户权限与本地数据库进行对比，执行以下操作：
        - 创建新账户的权限记录
        - 更新已变更的权限
        - 记录权限变更日志

        Args:
            instance: 数据库实例对象。
            remote_accounts: 远程账户数据列表，每项包含 username、permissions、
                is_superuser、is_locked 等字段。
            active_accounts: 活跃的 InstanceAccount 对象列表。
            session_id: 同步会话 ID，可选。

        Returns:
            同步统计信息字典，包含以下字段：
            {
                'created': 新创建的权限记录数,
                'updated': 更新的权限记录数,
                'skipped': 跳过的记录数,
                'processed_records': 处理的记录总数,
                'errors': 错误信息列表,
                'status': 同步状态（'completed' 或 'failed'）,
                'message': 同步结果消息
            }

        Raises:
            SQLAlchemyError: 当数据库提交失败时抛出。
            PermissionSyncError: 当权限同步过程中发生错误时抛出。

        """
        remote_map = {account["username"]: account for account in remote_accounts}
        created = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        for account in active_accounts:
            remote = remote_map.get(account.username)
            if not remote:
                skipped += 1
                continue

            permissions = remote.get("permissions", {})
            is_superuser = bool(remote.get("is_superuser", False))
            is_locked = bool(remote.get("is_locked", False))

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
                diff = self._calculate_diff(existing, permissions, is_superuser, is_locked)
                if diff["changed"]:
                    self._apply_permissions(existing, permissions, is_superuser, is_locked)
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
                            module="accounts_sync",
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
                self._apply_permissions(existing, permissions, is_superuser, is_locked)
                existing.last_change_type = "add"
                existing.last_change_time = time_utils.now()
                existing.last_sync_time = time_utils.now()
                created += 1
                db.session.add(existing)

                try:
                    initial_diff = self._build_initial_diff_payload(permissions, is_superuser, is_locked)
                    self._log_change(
                        instance,
                        username=account.username,
                        change_type="add",
                        diff_payload=initial_diff,
                        session_id=session_id,
                    )
                except Exception as log_exc:  # noqa: BLE001
                    errors.append(f"记录新增权限日志失败: {log_exc}")
                    self.logger.error(
                        "account_permission_change_log_failed",
                        module="accounts_sync",
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
                module="accounts_sync",
                phase="collection",
                error=str(exc),
                exc_info=True,
            )
            raise

        summary: dict[str, Any] = {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "processed_records": created + updated,
            "errors": errors,
            "status": "completed" if not errors else "failed",
            "message": (
                f"权限同步完成：新增 {created} 个账户，更新 {updated} 个账户"
                if not errors
                else "权限同步阶段发生错误"
            ),
        }

        if errors:
            self.logger.error(
                "account_permission_sync_failed",
                instance=instance.name,
                instance_id=instance.id,
                module="accounts_sync",
                phase="collection",
                errors=errors,
                session_id=session_id,
            )
            raise PermissionSyncError(summary)

        self.logger.info(
            "account_permission_sync_completed",
            instance=instance.name,
            instance_id=instance.id,
            module="accounts_sync",
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
        permissions: dict,
        is_superuser: bool,
        is_locked: bool,
    ) -> None:
        """将权限快照写入账户记录。

        Args:
            record: 需要更新的账户权限记录。
            permissions: 标准化后的权限字典。
            is_superuser: 是否具有超级权限。
            is_locked: 账户是否被锁定。

        Returns:
            None: 属性赋值完成后返回。

        """
        record.is_superuser = is_superuser
        record.is_locked = bool(is_locked)
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
        permissions: dict,
        is_superuser: bool,
        is_locked: bool,
    ) -> dict[str, Any]:
        """计算新旧权限之间的差异。

        Args:
            record: 当前持久化的权限记录。
            permissions: 新的权限字典。
            is_superuser: 最新的超级权限状态。
            is_locked: 最新的锁定状态。

        Returns:
            dict[str, Any]: 包含 privilege_diff 与 other_diff 的结构。

        """
        privilege_changes: list[dict[str, Any]] = []
        other_changes: list[dict[str, Any]] = []

        if record.is_superuser != is_superuser:
            other_entry = self._build_other_diff_entry(
                field="is_superuser",
                old_value=record.is_superuser,
                new_value=is_superuser,
            )
            if other_entry:
                other_changes.append(other_entry)

        if bool(record.is_locked) != bool(is_locked):
            locked_entry = self._build_other_diff_entry(
                field="is_locked",
                old_value=bool(record.is_locked),
                new_value=bool(is_locked),
            )
            if locked_entry:
                other_changes.append(locked_entry)

        for field in PERMISSION_FIELDS:
            new_value = permissions.get(field)
            old_value = getattr(record, field)
            if new_value is None and old_value is None:
                continue

            if field in PRIVILEGE_FIELD_LABELS:
                entries = self._build_privilege_diff_entries(field, old_value, new_value)
                privilege_changes.extend(entries)
            else:
                entry = self._build_other_diff_entry(field, old_value, new_value)
                if entry:
                    other_changes.append(entry)

        changed = bool(privilege_changes or other_changes)
        if not changed:
            change_type = "none"
        elif privilege_changes:
            change_type = "modify_privilege"
        else:
            change_type = "modify_other"

        return {
            "changed": changed,
            "change_type": change_type,
            "privilege_diff": privilege_changes,
            "other_diff": other_changes,
        }

    def _log_change(
        self,
        instance: Instance,
        *,
        username: str,
        change_type: str,
        diff_payload: dict[str, Any],
        session_id: str | None = None,
    ) -> None:
        """将权限变更写入变更日志表。

        Args:
            instance: 数据库实例。
            username: 变更的账户名。
            change_type: 变更类型。
            diff_payload: 差异结果。
            session_id: 同步会话 ID，可选。

        Returns:
            None: 日志添加到会话后返回。

        """
        if change_type == "none":
            return

        privilege_diff = diff_payload.get("privilege_diff") or []
        other_diff = diff_payload.get("other_diff") or []
        summary = self._build_change_summary(username, change_type, privilege_diff, other_diff)

        log = AccountChangeLog(
            instance_id=instance.id,
            db_type=instance.db_type,
            username=username,
            change_type=change_type,
            change_time=time_utils.now(),
            privilege_diff=privilege_diff,
            other_diff=other_diff,
            message=summary,
            session_id=session_id,
        )
        db.session.add(log)

    # ------------------------------------------------------------------
    # Diff 构建辅助
    # ------------------------------------------------------------------
    def _build_initial_diff_payload(
        self,
        permissions: dict[str, Any],
        is_superuser: bool,
        is_locked: bool,
    ) -> dict[str, Any]:
        """构建新账户的权限差异初始结构。

        Args:
            permissions: 标准化权限字典。
            is_superuser: 是否超级用户。
            is_locked: 是否锁定。

        Returns:
            dict[str, Any]: 含 privilege_diff/other_diff 的初始字典。

        """
        privilege_diff: list[dict[str, Any]] = []
        for field in PERMISSION_FIELDS:
            if field in PRIVILEGE_FIELD_LABELS:
                privilege_diff.extend(
                    self._build_privilege_diff_entries(field, None, permissions.get(field))
                )
        other_diff: list[dict[str, Any]] = []
        if is_superuser:
            other_entry = self._build_other_diff_entry("is_superuser", False, True)
            if other_entry:
                other_diff.append(other_entry)
        if is_locked:
            locked_entry = self._build_other_diff_entry("is_locked", False, True)
            if locked_entry:
                other_diff.append(locked_entry)

        type_specific_entry = self._build_other_diff_entry(
            "type_specific", None, permissions.get("type_specific")
        )
        if type_specific_entry:
            other_diff.append(type_specific_entry)
        return {
            "privilege_diff": privilege_diff,
            "other_diff": other_diff,
        }

    def _build_privilege_diff_entries(
        self,
        field: str,
        old_value: Any,
        new_value: Any,
    ) -> list[dict[str, Any]]:
        """比较权限字段并返回差异条目。

        Args:
            field: 权限字段名称。
            old_value: 原权限值，可为映射或序列。
            new_value: 新权限值。

        Returns:
            list[dict[str, Any]]: 包含 GRANT/REVOKE/ALTER 等动作的条目。

        """
        label = PRIVILEGE_FIELD_LABELS.get(field, field)
        entries: list[dict[str, Any]] = []

        if self._is_mapping(old_value) or self._is_mapping(new_value):
            old_map = self._normalize_mapping(old_value)
            new_map = self._normalize_mapping(new_value)
            all_keys = sorted(set(old_map.keys()) | set(new_map.keys()))

            for key in all_keys:
                old_set = old_map.get(key, set())
                new_set = new_map.get(key, set())
                grants = sorted(new_set - old_set)
                revokes = sorted(old_set - new_set)

                object_label = f"{label}:{key}" if key else label
                if grants:
                    entries.append(
                        {
                            "field": field,
                            "label": label,
                            "object": object_label,
                            "action": "GRANT",
                            "permissions": grants,
                        }
                    )
                if revokes:
                    entries.append(
                        {
                            "field": field,
                            "label": label,
                            "object": object_label,
                            "action": "REVOKE",
                            "permissions": revokes,
                        }
                    )
                if not grants and not revokes and new_set != old_set:
                    entries.append(
                        {
                            "field": field,
                            "label": label,
                            "object": object_label,
                            "action": "ALTER",
                            "permissions": sorted(new_set),
                        }
                    )
            return entries

        old_set = self._normalize_sequence(old_value)
        new_set = self._normalize_sequence(new_value)
        if not old_set and not new_set:
            return entries

        grants = sorted(new_set - old_set)
        revokes = sorted(old_set - new_set)
        object_label = label

        if grants:
            entries.append(
                {
                    "field": field,
                    "label": label,
                    "object": object_label,
                    "action": "GRANT",
                    "permissions": grants,
                }
            )
        if revokes:
            entries.append(
                {
                    "field": field,
                    "label": label,
                    "object": object_label,
                    "action": "REVOKE",
                    "permissions": revokes,
                }
            )
        if not grants and not revokes and new_set != old_set:
            entries.append(
                {
                    "field": field,
                    "label": label,
                    "object": object_label,
                    "action": "ALTER",
                    "permissions": sorted(new_set),
                }
            )
        return entries

    def _build_other_diff_entry(
        self,
        field: str,
        old_value: Any,
        new_value: Any,
    ) -> dict[str, Any] | None:
        """构建非权限字段的差异条目。

        Args:
            field: 字段名称。
            old_value: 原值。
            new_value: 新值。

        Returns:
            dict | None: 若发生变化则返回记录，否则返回 None。

        """
        if old_value == new_value:
            return None

        label = OTHER_FIELD_LABELS.get(field, field)
        description = self._build_other_description(label, old_value, new_value)
        return {
            "field": field,
            "label": label,
            "before": self._repr_value(old_value),
            "after": self._repr_value(new_value),
            "description": description,
        }

    def _build_other_description(self, label: str, old_value: Any, new_value: Any) -> str:
        """生成非权限字段差异的自然语言描述。

        Args:
            label: 字段展示名。
            old_value: 旧值。
            new_value: 新值。

        Returns:
            str: 适合日志的描述文本。

        """
        before = self._repr_value(old_value)
        after = self._repr_value(new_value)
        if before and after:
            return f"{label} 从 {before} 调整为 {after}"
        if after and not before:
            return f"{label} 设置为 {after}"
        if before and not after:
            return f"{label} 已清空"
        return f"{label} 已更新"

    def _build_change_summary(
        self,
        username: str,
        change_type: str,
        privilege_diff: list[dict[str, Any]],
        other_diff: list[dict[str, Any]],
    ) -> str:
        """根据差异构建日志摘要。

        Args:
            username: 账户名。
            change_type: 变更类型。
            privilege_diff: 权限差异列表。
            other_diff: 其他字段差异列表。

        Returns:
            str: 汇总字符串。

        """
        segments: list[str] = []

        if change_type == "add":
            grant_count = self._count_permissions_by_action(privilege_diff, "GRANT")
            if grant_count:
                segments.append(f"新增账户，赋予 {grant_count} 项权限")
            else:
                segments.append("新增账户")
        else:
            if privilege_diff:
                grant_count = self._count_permissions_by_action(privilege_diff, "GRANT")
                revoke_count = self._count_permissions_by_action(privilege_diff, "REVOKE")
                alter_count = self._count_permissions_by_action(privilege_diff, "ALTER")
                parts: list[str] = []
                if grant_count:
                    parts.append(f"新增 {grant_count} 项授权")
                if revoke_count:
                    parts.append(f"撤销 {revoke_count} 项授权")
                if alter_count and not grant_count and not revoke_count:
                    parts.append(f"更新 {alter_count} 项权限")
                if parts:
                    segments.append("权限更新：" + "，".join(parts))

            if other_diff:
                descriptions = [entry.get("description") for entry in other_diff if entry.get("description")]
                if descriptions:
                    segments.append("其他变更：" + "，".join(descriptions))

        base = f"账户 {username}"
        if segments:
            return f"{base} " + "；".join(segments)
        return f"{base} 未发生变更"

    @staticmethod
    def _is_mapping(value: Any) -> bool:
        """判断值是否为映射类型。

        Args:
            value: 待检查的值。

        Returns:
            bool: 是映射类型返回 True，否则 False。

        """
        return isinstance(value, dict)

    @staticmethod
    def _normalize_mapping(value: Any) -> dict[str, set]:
        """将权限映射标准化为 {str: set} 结构。

        Args:
            value: 可能为 dict/None 的权限结构。

        Returns:
            dict[str, set]: 键为字符串，值为去重集合。

        """
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, set] = {}
        for key, permissions in value.items():
            normalized[str(key)] = AccountPermissionManager._normalize_sequence(permissions)
        return normalized

    @staticmethod
    def _normalize_sequence(value: Any) -> set:
        """将单值或序列转换为集合形式。

        Args:
            value: 序列、集合或单个值。

        Returns:
            set: 去重后的值集合。

        """
        if value is None:
            return set()
        if isinstance(value, (list, tuple, set)):
            return {AccountPermissionManager._repr_value(item) for item in value if item is not None}
        return {AccountPermissionManager._repr_value(value)}

    @staticmethod
    def _repr_value(value: Any) -> str:
        """将值转换为日志友好的文本。

        Args:
            value: 任意类型的值。

        Returns:
            str: 适合日志输出的字符串。

        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return "是" if value else "否"
        if isinstance(value, (list, tuple, set)):
            return "、".join(str(item) for item in value)
        if isinstance(value, dict):
            ordered_items = sorted(value.items(), key=lambda item: str(item[0]))
            return "; ".join(
                f"{key}:{AccountPermissionManager._repr_value(val)}" for key, val in ordered_items
            )
        return str(value)

    @staticmethod
    def _count_permissions_by_action(privilege_diff: list[dict[str, Any]], action: str) -> int:
        """统计差异中指定动作的权限数量。

        Args:
            privilege_diff: 权限差异列表。
            action: 待统计的动作关键字。

        Returns:
            int: 权限条目的数量。

        """
        total = 0
        for entry in privilege_diff:
            if entry.get("action") == action:
                total += len(entry.get("permissions", []))
        return total
