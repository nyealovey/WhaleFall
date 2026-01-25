"""账户权限同步管理器,实现权限增量及变更日志."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.core.exceptions import ConflictError
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.repositories.accounts_sync_repository import AccountsSyncRepository
from app.schemas.internal_contracts.account_change_log_diff_v1 import wrap_entries_v1
from app.schemas.internal_contracts.type_specific_v1 import normalize_type_specific_v1
from app.services.accounts_permissions.facts_builder import build_permission_facts
from app.services.accounts_permissions.snapshot_view import build_permission_snapshot_view
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from app.core.types import (
        JsonDict,
        JsonValue,
        OtherDiffEntry,
        PermissionDiffPayload,
        PrivilegeDiffEntry,
        RemoteAccount,
        RemoteAccountMap,
        SyncSummary,
    )
    from app.models.instance import Instance
    from app.models.instance_account import InstanceAccount

PERMISSION_LOG_EXCEPTIONS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    ValueError,
    TypeError,
)

PRIVILEGE_FIELD_LABELS: dict[str, str] = {
    # MySQL
    "mysql_global_privileges": "全局权限",
    "mysql_database_privileges": "数据库权限",
    "mysql_granted_roles": "角色",
    "mysql_role_members": "角色成员",
    # PostgreSQL
    "postgresql_predefined_roles": "预设角色",
    "postgresql_role_attributes": "角色属性",
    "postgresql_database_privileges": "数据库权限",
    # SQL Server
    "sqlserver_server_roles": "服务器角色",
    "sqlserver_server_permissions": "服务器权限",
    "sqlserver_database_roles": "数据库角色",
    "sqlserver_database_permissions": "数据库权限",
    # Oracle
    "oracle_roles": "Oracle 角色",
    "oracle_system_privileges": "系统权限",
}

OTHER_FIELD_LABELS: dict[str, str] = {
    "is_superuser": "超级用户",
    "is_locked": "锁定状态",
    "type_specific": "数据库特性",
}

_PERMISSION_TO_SNAPSHOT_CATEGORY_KEY: dict[str, str] = {
    "mysql_global_privileges": "mysql_global_privileges",
    "mysql_database_privileges": "mysql_database_privileges",
    "mysql_granted_roles": "mysql_granted_roles",
    "mysql_role_members": "mysql_role_members",
    "postgresql_predefined_roles": "postgresql_predefined_roles",
    "postgresql_role_attributes": "postgresql_role_attributes",
    "postgresql_database_privileges": "postgresql_database_privileges",
    "sqlserver_server_roles": "sqlserver_server_roles",
    "sqlserver_server_permissions": "sqlserver_server_permissions",
    "sqlserver_database_roles": "sqlserver_database_roles",
    "sqlserver_database_permissions": "sqlserver_database_permissions",
    "oracle_roles": "oracle_roles",
    "oracle_system_privileges": "oracle_system_privileges",
}

_TYPE_SPECIFIC_FORBIDDEN_KEYS: set[str] = {
    "is_superuser",
    "is_locked",
    "roles",
    "privileges",
}


@dataclass(slots=True)
class SyncOutcome:
    """单个账户同步操作的统计结果."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    error: str | None = None


@dataclass(slots=True)
class RemoteAccountSnapshot:
    """远程账户权限快照."""

    permissions: JsonDict


@dataclass(slots=True)
class SyncContext:
    """单个账户同步过程上下文."""

    instance: Instance
    username: str
    session_id: str | None


class PermissionSyncError(RuntimeError):
    """权限同步阶段出现错误时抛出,携带阶段 summary.

    Attributes:
        summary: 同步阶段的统计信息字典.

    """

    def __init__(self, summary: SyncSummary, message: str | None = None) -> None:
        """初始化权限同步错误.

        Args:
            summary: 同步阶段的统计信息.
            message: 错误消息,可选.

        """
        super().__init__(message or summary.get("message") or "权限同步失败")
        self.summary = summary


class AccountPermissionManager:
    """处理权限快照的增量更新.

    负责将远程账户权限与本地 AccountPermission 表进行同步,
    包括创建新权限记录、更新已变更的权限、记录权限变更日志.

    Attributes:
        logger: 同步日志记录器.

    """

    def __init__(self, repository: AccountsSyncRepository | None = None) -> None:
        """初始化账户权限管理器."""
        self.logger = get_sync_logger()
        self._repository = repository or AccountsSyncRepository()

    def synchronize(
        self,
        instance: Instance,
        remote_accounts: Iterable[RemoteAccount],
        active_accounts: list[InstanceAccount],
        *,
        session_id: str | None = None,
    ) -> SyncSummary:
        """同步账户权限数据.

        将远程账户权限与本地数据库进行对比,执行以下操作:
        - 创建新账户的权限记录
        - 更新已变更的权限
        - 记录权限变更日志

        Args:
            instance: 数据库实例对象.
            remote_accounts: 远程账户数据列表,每项包含 username、permissions、
                is_superuser、is_locked 等字段.
            active_accounts: 活跃的 InstanceAccount 对象列表.
            session_id: 同步会话 ID,可选.

        Returns:
            同步统计信息字典,包含以下字段:
            {
                'created': 新创建的权限记录数,
                'updated': 更新的权限记录数,
                'skipped': 跳过的记录数,
                'processed_records': 处理的记录总数,
                'errors': 错误信息列表,
                'status': 同步状态('completed' 或 'failed'),
                'message': 同步结果消息
            }

        Raises:
            SQLAlchemyError: 当数据库提交失败时抛出.
            PermissionSyncError: 当权限同步过程中发生错误时抛出.

        """
        remote_map: RemoteAccountMap = {account["username"]: account for account in remote_accounts}
        counts = {"created": 0, "updated": 0, "skipped": 0}
        errors: list[str] = []

        try:
            with db.session.begin_nested():
                for account in active_accounts:
                    remote = remote_map.get(account.username)
                    if not remote:
                        counts["skipped"] += 1
                        continue

                    context = SyncContext(instance=instance, username=account.username, session_id=session_id)
                    outcome = self._sync_single_account(account, remote, context)
                    counts["created"] += outcome.created
                    counts["updated"] += outcome.updated
                    counts["skipped"] += outcome.skipped
                    if outcome.error:
                        errors.append(outcome.error)

                db.session.flush()
        except SQLAlchemyError as exc:
            self.logger.exception(
                "account_permission_sync_flush_failed",
                instance=instance.name,
                instance_id=instance.id,
                module="accounts_sync",
                phase="collection",
                error=str(exc),
            )
            raise

        return self._finalize_summary(instance, session_id, counts, errors)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _sync_single_account(
        self,
        account: InstanceAccount,
        remote: RemoteAccount,
        context: SyncContext,
    ) -> SyncOutcome:
        snapshot = self._extract_remote_context(remote)
        record = self._find_permission_record(context.instance, account)
        if record:
            return self._process_existing_permission(record, snapshot, context)
        return self._process_new_permission(account, snapshot, context)

    @staticmethod
    def _extract_remote_context(remote: RemoteAccount) -> RemoteAccountSnapshot:
        """提取远程权限与标志."""
        permissions = cast("JsonDict", remote.get("permissions", {}))
        return RemoteAccountSnapshot(
            permissions=permissions,
        )

    def _find_permission_record(self, instance: Instance, account: InstanceAccount) -> AccountPermission | None:
        """查找或回填账户权限记录."""
        existing = self._repository.get_permission_by_instance_account_id(account.id)
        if existing:
            return existing
        existing = self._repository.get_permission_by_instance_username(
            instance_id=instance.id,
            db_type=instance.db_type,
            username=account.username,
        )
        if existing and not existing.instance_account_id:
            raise ConflictError(
                message="权限记录缺少 instance_account_id, 请先完成数据回填",
                message_key="SYNC_DATA_ERROR",
            )
        return existing

    def _process_existing_permission(
        self,
        record: AccountPermission,
        snapshot: RemoteAccountSnapshot,
        context: SyncContext,
    ) -> SyncOutcome:
        diff = self._calculate_diff(
            record,
            snapshot.permissions,
        )
        if not bool(diff.get("changed")):
            self._mark_synced(record)
            return SyncOutcome(skipped=1)

        change_type = cast(str, diff.get("change_type", "none"))
        self._apply_permissions(
            record,
            snapshot.permissions,
        )
        record.last_change_type = change_type
        record.last_change_time = time_utils.now()
        self._mark_synced(record)

        try:
            self._log_change(
                context.instance,
                username=context.username,
                change_type=change_type,
                diff_payload=diff,
                session_id=context.session_id,
            )
        except PERMISSION_LOG_EXCEPTIONS as log_exc:
            self._handle_log_failure(log_exc, context)
            return SyncOutcome(updated=1, skipped=1, error=f"记录权限变更日志失败: {log_exc}")

        return SyncOutcome(updated=1)

    def _process_new_permission(
        self,
        account: InstanceAccount,
        snapshot: RemoteAccountSnapshot,
        context: SyncContext,
    ) -> SyncOutcome:
        record = AccountPermission()
        record.instance_id = context.instance.id
        record.db_type = context.instance.db_type
        record.instance_account_id = account.id
        record.username = account.username
        self._apply_permissions(
            record,
            snapshot.permissions,
        )
        record.last_change_type = "add"
        record.last_change_time = time_utils.now()
        record.last_sync_time = time_utils.now()
        db.session.add(record)

        try:
            initial_diff = self._build_initial_diff_payload(
                record,
                snapshot.permissions,
            )
            self._log_change(
                context.instance,
                username=account.username,
                change_type="add",
                diff_payload=initial_diff,
                session_id=context.session_id,
            )
        except PERMISSION_LOG_EXCEPTIONS as log_exc:
            self._handle_log_failure(log_exc, context)
            return SyncOutcome(created=1, skipped=1, error=f"记录新增权限日志失败: {log_exc}")

        return SyncOutcome(created=1)

    @staticmethod
    def _mark_synced(record: AccountPermission) -> None:
        """更新同步时间戳."""
        record.last_sync_time = time_utils.now()

    def _handle_log_failure(
        self,
        exc: BaseException,
        context: SyncContext,
    ) -> None:
        """统一处理日志记录异常."""
        self.logger.exception(
            "account_permission_change_log_failed",
            module="accounts_sync",
            phase="collection",
            instance_id=context.instance.id,
            instance_name=context.instance.name,
            username=context.username,
            error=str(exc),
        )

    def _finalize_summary(
        self,
        instance: Instance,
        session_id: str | None,
        counts: dict[str, int],
        errors: list[str],
    ) -> SyncSummary:
        """组装同步摘要并输出日志."""
        summary: SyncSummary = {
            "created": counts["created"],
            "updated": counts["updated"],
            "skipped": counts["skipped"],
            "processed_records": counts["created"] + counts["updated"],
            "errors": errors,
            "status": "completed" if not errors else "failed",
            "message": (
                f"权限同步完成:新增 {counts['created']} 个账户,更新 {counts['updated']} 个账户"
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

    def _apply_permissions(
        self,
        record: AccountPermission,
        permissions: JsonDict,
    ) -> None:
        """将权限快照写入账户记录.

        Args:
            record: 需要更新的账户权限记录.
            permissions: 标准化后的权限字典.

        Returns:
            None: 属性赋值完成后返回.

        """
        if "type_specific" in permissions:
            raw_type_specific = permissions.get("type_specific")
            sanitized_type_specific, removed_keys = self._sanitize_type_specific(raw_type_specific)
            if removed_keys:
                db_type_value = record.db_type
                db_type_label = "" if db_type_value is None else str(db_type_value).lower()
                self.logger.warning(
                    "account_permission_type_specific_forbidden_keys_removed",
                    module="accounts_sync",
                    db_type=db_type_label,
                    removed_keys=removed_keys,
                )
            if sanitized_type_specific is not None:
                record.type_specific = normalize_type_specific_v1(sanitized_type_specific)
                permissions = {**permissions, "type_specific": dict(sanitized_type_specific)}

        record.permission_snapshot = self._build_permission_snapshot(
            record,
            permissions,
        )

        try:
            record.permission_facts = build_permission_facts(
                record=record,
                snapshot=getattr(record, "permission_snapshot", None),
            )
        except Exception as exc:  # pragma: no cover - 防御性
            self.logger.exception(
                "account_permission_facts_build_failed",
                module="accounts_sync",
                phase="collection",
                fallback=True,
                fallback_reason="FACTS_BUILD_FAILED",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            record.permission_facts = {
                "version": 2,
                "db_type": ("" if record.db_type is None else str(record.db_type).lower()),
                "capabilities": [],
                "capability_reasons": {},
                "roles": [],
                "privileges": {},
                "errors": ["FACTS_BUILD_FAILED"],
                "meta": {"source": "error", "error_type": type(exc).__name__},
            }

    @staticmethod
    def _sanitize_type_specific(type_specific: object) -> tuple[JsonDict | None, list[str]]:
        if not isinstance(type_specific, dict):
            return None, []
        removed_keys = sorted(key for key in type_specific if key in _TYPE_SPECIFIC_FORBIDDEN_KEYS)
        sanitized = {key: value for key, value in type_specific.items() if key not in _TYPE_SPECIFIC_FORBIDDEN_KEYS}
        return dict(sanitized), removed_keys

    @staticmethod
    def _facts_has_capability(facts: object, name: str) -> bool:
        if not isinstance(facts, dict):
            return False
        capabilities = facts.get("capabilities")
        if not isinstance(capabilities, list):
            return False
        return any(item == name for item in capabilities if isinstance(item, str))

    @staticmethod
    def _build_permission_snapshot(
        record: AccountPermission,
        permissions: JsonDict,
    ) -> JsonDict:
        db_type_value = getattr(record, "db_type", None)
        db_type = "" if db_type_value is None else str(db_type_value).lower()

        categories: JsonDict = {}
        extra: JsonDict = {}
        type_specific: JsonDict = {}
        errors: list[str] = []

        for key, value in permissions.items():
            if key == "type_specific":
                if isinstance(value, dict):
                    sanitized, removed_keys = AccountPermissionManager._sanitize_type_specific(value)
                    if removed_keys:
                        errors.extend([f"TYPE_SPECIFIC_FORBIDDEN_FIELD:{item}" for item in removed_keys])
                    if sanitized is not None:
                        type_specific[db_type] = dict(sanitized)
                continue

            target_key = _PERMISSION_TO_SNAPSHOT_CATEGORY_KEY.get(key)
            if target_key:
                categories[target_key] = value
                continue

            extra[key] = value

        return {
            "version": 4,
            "categories": categories,
            "type_specific": type_specific,
            "extra": extra,
            "errors": errors,
            "meta": {},
        }

    def _calculate_diff(
        self,
        record: AccountPermission,
        permissions: JsonDict,
    ) -> PermissionDiffPayload:
        """计算新旧权限之间的差异.

        Args:
            record: 当前持久化的权限记录.
            permissions: 新的权限字典.

        Returns:
            PermissionDiffPayload: 包含 privilege_diff 与 other_diff 的结构.

        """
        old_snapshot = build_permission_snapshot_view(record)
        new_snapshot = self._build_permission_snapshot(
            record,
            permissions,
        )

        old_facts = build_permission_facts(record=record, snapshot=old_snapshot)
        new_facts = build_permission_facts(record=record, snapshot=new_snapshot)
        old_is_superuser = self._facts_has_capability(old_facts, "SUPERUSER")
        new_is_superuser = self._facts_has_capability(new_facts, "SUPERUSER")
        old_is_locked = self._facts_has_capability(old_facts, "LOCKED")
        new_is_locked = self._facts_has_capability(new_facts, "LOCKED")

        privilege_changes = self._collect_privilege_changes(old_snapshot, new_snapshot)
        other_changes = self._collect_other_changes(
            record,
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            old_is_superuser=old_is_superuser,
            new_is_superuser=new_is_superuser,
            old_is_locked=old_is_locked,
            new_is_locked=new_is_locked,
        )
        change_type = self._determine_change_type(privilege_changes, other_changes)
        changed = change_type != "none"
        return {
            "changed": changed,
            "change_type": change_type,
            "privilege_diff": privilege_changes,
            "other_diff": other_changes,
        }

    def _collect_privilege_changes(
        self,
        old_snapshot: JsonDict,
        new_snapshot: JsonDict,
    ) -> list[PrivilegeDiffEntry]:
        """收集权限字段的差异(基于 v4 snapshot/view)."""
        entries: list[PrivilegeDiffEntry] = []
        old_categories_value = old_snapshot.get("categories")
        new_categories_value = new_snapshot.get("categories")
        old_categories: Mapping[str, JsonValue] = (
            cast("Mapping[str, JsonValue]", old_categories_value) if isinstance(old_categories_value, Mapping) else {}
        )
        new_categories: Mapping[str, JsonValue] = (
            cast("Mapping[str, JsonValue]", new_categories_value) if isinstance(new_categories_value, Mapping) else {}
        )

        for field in sorted(set(old_categories.keys()) | set(new_categories.keys())):
            entries.extend(
                self._build_privilege_diff_entries(
                    field,
                    old_categories.get(field),
                    new_categories.get(field),
                ),
            )
        return entries

    def _collect_other_changes(
        self,
        record: AccountPermission,
        *,
        old_snapshot: JsonDict,
        new_snapshot: JsonDict,
        old_is_superuser: bool,
        new_is_superuser: bool,
        old_is_locked: bool,
        new_is_locked: bool,
    ) -> list[OtherDiffEntry]:
        """收集非权限字段差异(基于 v4 snapshot/view)."""
        changes: list[OtherDiffEntry] = []
        for field, old_value, new_value in (
            ("is_superuser", old_is_superuser, new_is_superuser),
            ("is_locked", old_is_locked, new_is_locked),
        ):
            entry = self._build_other_diff_entry(field, old_value, new_value)
            if entry:
                changes.append(entry)
        db_type_value = getattr(record, "db_type", None)
        db_type = "" if db_type_value is None else str(db_type_value).lower()
        old_type_specific_value = old_snapshot.get("type_specific")
        new_type_specific_value = new_snapshot.get("type_specific")
        old_type_specific: Mapping[str, JsonValue] = (
            cast("Mapping[str, JsonValue]", old_type_specific_value)
            if isinstance(old_type_specific_value, Mapping)
            else {}
        )
        new_type_specific: Mapping[str, JsonValue] = (
            cast("Mapping[str, JsonValue]", new_type_specific_value)
            if isinstance(new_type_specific_value, Mapping)
            else {}
        )
        changes.extend(
            self._build_type_specific_diff_entries(
                old_type_specific.get(db_type),
                new_type_specific.get(db_type),
            ),
        )
        return changes

    def _build_type_specific_diff_entries(
        self,
        old_value: JsonValue | None,
        new_value: JsonValue | None,
    ) -> list[OtherDiffEntry]:
        """构建 type_specific 的差异条目.

        说明:
        - 当旧/新值均为 dict(或 Mapping) 时,按 key 拆分为多条条目(便于 UI 可读性与摘要收敛)。
        - 其它情况沿用单条 `type_specific` 的展示。
        """
        if isinstance(old_value, Mapping) and isinstance(new_value, Mapping):
            label_prefix = OTHER_FIELD_LABELS.get("type_specific", "type_specific")
            entries: list[OtherDiffEntry] = []
            keys = sorted(set(old_value.keys()) | set(new_value.keys()), key=lambda value: str(value))
            for key in keys:
                old_item = old_value.get(key)
                new_item = new_value.get(key)
                if old_item == new_item:
                    continue
                key_text = str(key)
                label = f"{label_prefix} · {key_text}"
                entries.append(
                    {
                        "field": f"type_specific.{key_text}",
                        "label": label,
                        "before": self._repr_value(old_item),
                        "after": self._repr_value(new_item),
                        "description": self._build_other_description(label, old_item, new_item),
                    },
                )
            return entries

        entry = self._build_other_diff_entry("type_specific", old_value, new_value)
        return [entry] if entry else []

    @staticmethod
    def _determine_change_type(
        privilege_changes: list[PrivilegeDiffEntry],
        other_changes: list[OtherDiffEntry],
    ) -> str:
        """根据差异条目判断变更类型."""
        if not privilege_changes and not other_changes:
            return "none"
        if privilege_changes:
            return "modify_privilege"
        return "modify_other"

    def _log_change(
        self,
        instance: Instance,
        *,
        username: str,
        change_type: str,
        diff_payload: PermissionDiffPayload,
        session_id: str | None = None,
    ) -> None:
        """将权限变更写入变更日志表.

        Args:
            instance: 数据库实例.
            username: 变更的账户名.
            change_type: 变更类型.
            diff_payload: 差异结果.
            session_id: 同步会话 ID,可选.

        Returns:
            None: 日志添加到会话后返回.

        """
        if change_type == "none":
            return

        privilege_diff = cast("list[PrivilegeDiffEntry]", diff_payload.get("privilege_diff", []))
        other_diff = cast("list[OtherDiffEntry]", diff_payload.get("other_diff", []))
        summary = self._build_change_summary(username, change_type, privilege_diff, other_diff)

        log = AccountChangeLog()
        log.instance_id = instance.id
        log.db_type = instance.db_type
        log.username = username
        log.change_type = change_type
        log.change_time = time_utils.now()
        log.privilege_diff = wrap_entries_v1(privilege_diff)
        log.other_diff = wrap_entries_v1(other_diff)
        log.message = summary
        log.session_id = session_id
        db.session.add(log)

    # ------------------------------------------------------------------
    # Diff 构建辅助
    # ------------------------------------------------------------------
    def _build_initial_diff_payload(
        self,
        record: AccountPermission,
        permissions: JsonDict,
    ) -> PermissionDiffPayload:
        """构建新账户的权限差异初始结构(基于 v4 snapshot/view).

        Args:
            record: 目标权限记录(用于确定 db_type).
            permissions: 标准化权限字典.

        Returns:
            PermissionDiffPayload: 含 privilege_diff/other_diff 的初始字典.

        """
        snapshot = self._build_permission_snapshot(
            record,
            permissions,
        )
        facts = build_permission_facts(record=record, snapshot=snapshot)
        is_superuser = self._facts_has_capability(facts, "SUPERUSER")
        is_locked = self._facts_has_capability(facts, "LOCKED")

        categories_value = snapshot.get("categories")
        categories: Mapping[str, JsonValue] = (
            cast("Mapping[str, JsonValue]", categories_value) if isinstance(categories_value, Mapping) else {}
        )
        privilege_diff: list[PrivilegeDiffEntry] = []
        for field in sorted(categories.keys()):
            privilege_diff.extend(
                self._build_privilege_diff_entries(field, None, categories.get(field)),
            )
        other_diff: list[OtherDiffEntry] = []
        if is_superuser:
            other_entry = self._build_other_diff_entry(
                "is_superuser",
                old_value=False,
                new_value=True,
            )
            if other_entry:
                other_diff.append(other_entry)
        if is_locked:
            locked_entry = self._build_other_diff_entry(
                "is_locked",
                old_value=False,
                new_value=True,
            )
            if locked_entry:
                other_diff.append(locked_entry)

        db_type_value = getattr(record, "db_type", None)
        db_type = "" if db_type_value is None else str(db_type_value).lower()
        type_specific_value = snapshot.get("type_specific")
        type_specific: Mapping[str, JsonValue] = (
            cast("Mapping[str, JsonValue]", type_specific_value) if isinstance(type_specific_value, Mapping) else {}
        )
        type_specific_entry = self._build_other_diff_entry("type_specific", None, type_specific.get(db_type))
        if type_specific_entry:
            other_diff.append(type_specific_entry)
        return {
            "privilege_diff": privilege_diff,
            "other_diff": other_diff,
        }

    def _build_privilege_diff_entries(
        self,
        field: str,
        old_value: JsonValue | None,
        new_value: JsonValue | None,
    ) -> list[PrivilegeDiffEntry]:
        """比较权限字段并返回差异条目.

        Args:
            field: 权限字段名称.
            old_value: 原权限值,可为映射或序列.
            new_value: 新权限值.

        Returns:
            list[PrivilegeDiffEntry]: 包含 GRANT/REVOKE/ALTER 等动作的条目.

        """
        label = PRIVILEGE_FIELD_LABELS.get(field, field)
        entries: list[PrivilegeDiffEntry] = []

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
                        },
                    )
                if revokes:
                    entries.append(
                        {
                            "field": field,
                            "label": label,
                            "object": object_label,
                            "action": "REVOKE",
                            "permissions": revokes,
                        },
                    )
                if not grants and not revokes and new_set != old_set:
                    entries.append(
                        {
                            "field": field,
                            "label": label,
                            "object": object_label,
                            "action": "ALTER",
                            "permissions": sorted(new_set),
                        },
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
                },
            )
        if revokes:
            entries.append(
                {
                    "field": field,
                    "label": label,
                    "object": object_label,
                    "action": "REVOKE",
                    "permissions": revokes,
                },
            )
        if not grants and not revokes and new_set != old_set:
            entries.append(
                {
                    "field": field,
                    "label": label,
                    "object": object_label,
                    "action": "ALTER",
                    "permissions": sorted(new_set),
                },
            )
        return entries

    def _build_other_diff_entry(
        self,
        field: str,
        old_value: JsonValue | None,
        new_value: JsonValue | None,
    ) -> OtherDiffEntry | None:
        """构建非权限字段的差异条目.

        Args:
            field: 字段名称.
            old_value: 原值.
            new_value: 新值.

        Returns:
            OtherDiffEntry | None: 若发生变化则返回记录,否则返回 None.

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

    def _build_other_description(
        self,
        label: str,
        old_value: JsonValue | None,
        new_value: JsonValue | None,
    ) -> str:
        """生成非权限字段差异的自然语言描述.

        Args:
            label: 字段展示名.
            old_value: 旧值.
            new_value: 新值.

        Returns:
            str: 适合日志的描述文本.

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
        privilege_diff: list[PrivilegeDiffEntry],
        other_diff: list[OtherDiffEntry],
    ) -> str:
        """根据差异构建日志摘要."""
        segments: list[str] = []
        privilege_summary = self._summarize_privilege_changes(change_type, privilege_diff)
        if privilege_summary:
            segments.append(privilege_summary)
        other_summary = self._summarize_other_changes(other_diff)
        if other_summary:
            segments.append(other_summary)

        base = f"账户 {username}"
        if not segments:
            return f"{base} 未发生变更"
        return f"{base} " + ";".join(segments)

    def _summarize_privilege_changes(
        self,
        change_type: str,
        privilege_diff: list[PrivilegeDiffEntry],
    ) -> str:
        """构建权限差异的文本."""
        if change_type == "add":
            grant_count = self._count_permissions_by_action(privilege_diff, "GRANT")
            return f"新增账户,赋予 {grant_count} 项权限" if grant_count else "新增账户"

        if not privilege_diff:
            return ""

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
        return "权限更新:" + ",".join(parts) if parts else ""

    @staticmethod
    def _summarize_other_changes(other_diff: list[OtherDiffEntry]) -> str:
        """构建非权限变更说明."""
        descriptions = [entry.get("description") for entry in other_diff if entry.get("description")]
        if not descriptions:
            return ""
        return "其他变更:" + ",".join(descriptions)

    @staticmethod
    def _is_mapping(value: JsonValue | None) -> bool:
        """判断值是否为映射类型.

        Args:
            value: 待检查的值.

        Returns:
            bool: 是映射类型返回 True,否则 False.

        """
        return isinstance(value, dict)

    @staticmethod
    def _normalize_mapping(value: JsonValue | None) -> dict[str, set[str]]:
        """将权限映射标准化为 {str: set} 结构.

        Args:
            value: 可能为 dict/None 的权限结构.

        Returns:
            dict[str, set[str]]: 键为字符串,值为去重集合.

        """
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, set[str]] = {}
        for key, permissions in value.items():
            normalized[str(key)] = AccountPermissionManager._normalize_sequence(permissions)
        return normalized

    @staticmethod
    def _normalize_sequence(value: JsonValue | Sequence[JsonValue] | set[str] | None) -> set[str]:
        """将单值或序列转换为集合形式.

        Args:
            value: 序列、集合或单个值.

        Returns:
            set[str]: 去重后的值集合.

        """
        if value is None:
            return set()
        if isinstance(value, (list, tuple, set)):
            return {AccountPermissionManager._repr_value(item) for item in value if item is not None}
        return {AccountPermissionManager._repr_value(value)}

    @staticmethod
    def _repr_value(value: JsonValue | Sequence[str] | set[str] | None) -> str:
        """将值转换为日志友好的文本.

        Args:
            value: JSON 值或标准化序列.

        Returns:
            str: 适合日志输出的字符串.

        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return "是" if value else "否"
        if isinstance(value, (list, tuple, set)):
            return "、".join(str(item) for item in value)
        if isinstance(value, dict):
            ordered_items = sorted(value.items(), key=lambda item: str(item[0]))
            return "; ".join(f"{key}:{AccountPermissionManager._repr_value(val)}" for key, val in ordered_items)
        return str(value)

    @staticmethod
    def _count_permissions_by_action(privilege_diff: list[PrivilegeDiffEntry], action: str) -> int:
        """统计差异中指定动作的权限数量.

        Args:
            privilege_diff: 权限差异列表.
            action: 待统计的动作关键字.

        Returns:
            int: 权限条目的数量.

        """
        total = 0
        for entry in privilege_diff:
            if entry.get("action") == action:
                total += len(entry.get("permissions", []))
        return total
