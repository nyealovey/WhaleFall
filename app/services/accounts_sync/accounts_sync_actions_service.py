"""Accounts sync actions service.

将路由层的“动作编排”逻辑下沉到 service 层:
- 全量同步: 校验活跃实例 + 启动后台线程 + 返回 session_id
- 单实例同步: 获取实例 + 执行同步 + 标准化 result 结构
"""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from sqlalchemy.exc import SQLAlchemyError

from app.constants.sync_constants import SyncOperationType
from app.errors import NotFoundError, SystemError, ValidationError
from app.models.instance import Instance
from app.services.sync_session_service import sync_session_service
from app.infra.route_safety import log_with_context


class SupportsAccountSync(Protocol):
    """Account sync service protocol (for DI & tests)."""

    def sync_accounts(
        self,
        instance: Instance,
        sync_type: str = SyncOperationType.MANUAL_SINGLE.value,
        session_id: str | None = None,
        created_by: int | None = None,
    ) -> Mapping[str, Any] | None:
        """同步指定实例的账户数据.

        Args:
            instance: 实例对象.
            sync_type: 同步类型.
            session_id: 可选的同步会话 ID.
            created_by: 可选的操作者用户 ID.

        Returns:
            Mapping[str, Any] | None: 同步结果(dict)或 None.

        """
        ...


BACKGROUND_SYNC_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ValidationError,
    SystemError,
    SQLAlchemyError,
    RuntimeError,
)


@dataclass(frozen=True, slots=True)
class AccountsSyncBackgroundLaunchResult:
    """后台全量同步启动结果."""

    session_id: str
    active_instance_count: int
    thread_name: str


@dataclass(frozen=True, slots=True)
class AccountsSyncBackgroundPreparedSession:
    """后台全量同步准备结果(已创建会话,尚未启动线程)."""

    session_id: str
    active_instance_count: int


@dataclass(frozen=True, slots=True)
class AccountsSyncActionResult:
    """同步动作结果(供路由层决定 200/400)."""

    success: bool
    message: str
    result: dict[str, Any]


def _launch_background_sync(
    *,
    created_by: int | None,
    session_id: str,
    sync_task: Callable[..., None],
) -> threading.Thread:
    def _run_sync_task(captured_created_by: int | None, captured_session_id: str) -> None:
        try:
            sync_task(manual_run=True, created_by=captured_created_by, session_id=captured_session_id)
        except BACKGROUND_SYNC_EXCEPTIONS as exc:  # pragma: no cover
            log_with_context(
                "error",
                "后台批量账户同步失败",
                module="accounts_sync",
                action="sync_all_accounts_background",
                context={
                    "created_by": captured_created_by,
                    "session_id": captured_session_id,
                },
                extra={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
                include_actor=False,
            )

    thread = threading.Thread(
        target=_run_sync_task,
        args=(created_by, session_id),
        name="sync_accounts_manual_batch",
        daemon=True,
    )
    thread.start()
    return thread


def _resolve_default_sync_task() -> Callable[..., None]:
    """惰性加载默认的批量同步任务,避免导入期循环依赖."""
    module = importlib.import_module("app.tasks.accounts_sync_tasks")
    return cast("Callable[..., None]", module.sync_accounts)


class AccountsSyncActionsService:
    """账户同步动作编排服务."""

    def __init__(
        self,
        *,
        sync_service: SupportsAccountSync,
        sync_task: Callable[..., None] | None = None,
    ) -> None:
        """初始化动作服务.

        Args:
            sync_service: 单实例同步 service(可用于 DI/测试).
            sync_task: 批量同步任务函数(用于后台线程).

        """
        self._sync_service = sync_service
        self._sync_task = sync_task or _resolve_default_sync_task()

    @staticmethod
    def _ensure_active_instances() -> int:
        active_count = Instance.query.filter_by(is_active=True).count()
        if active_count == 0:
            raise ValidationError("没有找到活跃的数据库实例")
        return int(active_count)

    @staticmethod
    def _get_instance(instance_id: int) -> Instance:
        instance = Instance.query.filter_by(id=instance_id).first()
        if instance is None:
            raise NotFoundError("实例不存在")
        return instance

    @staticmethod
    def _normalize_sync_result(result: Mapping[str, Any] | None, *, context: str) -> tuple[bool, dict[str, Any]]:
        if not result:
            return False, {"status": "failed", "message": f"{context}返回为空"}

        normalized = dict(result)
        is_success = bool(normalized.pop("success", True))
        message = normalized.get("message")
        if not message:
            message = f"{context}{'成功' if is_success else '失败'}"

        normalized["status"] = "completed" if is_success else "failed"
        normalized["message"] = message
        normalized["success"] = is_success
        return is_success, normalized

    def prepare_background_full_sync(self, *, created_by: int | None) -> AccountsSyncBackgroundPreparedSession:
        """创建同步会话并返回 session_id(不启动线程).

        该方法只做会话创建,由调用方决定何时启动后台线程(通常需在事务提交后).

        Args:
            created_by: 可选的操作者用户 ID.

        Returns:
            AccountsSyncBackgroundPreparedSession: 准备结果.

        """
        active_instance_count = self._ensure_active_instances()
        session = sync_session_service.create_session(
            sync_type=SyncOperationType.MANUAL_TASK.value,
            sync_category="account",
            created_by=created_by,
        )
        return AccountsSyncBackgroundPreparedSession(
            session_id=session.session_id,
            active_instance_count=active_instance_count,
        )

    def launch_background_full_sync(
        self,
        *,
        created_by: int | None,
        prepared: AccountsSyncBackgroundPreparedSession,
    ) -> AccountsSyncBackgroundLaunchResult:
        """启动后台线程执行全量账户同步.

        Args:
            created_by: 可选的操作者用户 ID.
            prepared: 已准备的会话信息(包含 session_id).

        Returns:
            AccountsSyncBackgroundLaunchResult: 后台同步启动结果.

        """
        thread = _launch_background_sync(
            created_by=created_by,
            session_id=prepared.session_id,
            sync_task=self._sync_task,
        )
        return AccountsSyncBackgroundLaunchResult(
            session_id=prepared.session_id,
            active_instance_count=prepared.active_instance_count,
            thread_name=thread.name,
        )

    def sync_instance_accounts(
        self,
        *,
        instance_id: int,
        actor_id: int | None = None,
        sync_type: str = SyncOperationType.MANUAL_SINGLE.value,
    ) -> AccountsSyncActionResult:
        """同步指定实例的账户并标准化结果结构.

        Args:
            instance_id: 实例 ID.
            actor_id: 可选的操作者用户 ID(仅用于日志上下文).
            sync_type: 同步类型.

        Returns:
            AccountsSyncActionResult: 动作结果(供路由层封套/状态码使用).

        """
        instance = self._get_instance(instance_id)

        log_with_context(
            "info",
            "开始同步实例账户",
            module="accounts_sync",
            action="sync_instance_accounts",
            context={
                "actor_id": actor_id,
                "instance_id": instance.id,
                "instance_name": instance.name,
                "db_type": instance.db_type,
                "host": instance.host,
            },
            include_actor=False,
        )

        raw_result = self._sync_service.sync_accounts(instance, sync_type=sync_type)
        is_success, normalized = self._normalize_sync_result(raw_result, context=f"实例 {instance.name} 账户同步")

        if is_success:
            instance.sync_count = (cast("int | None", instance.sync_count) or 0) + 1
            log_with_context(
                "info",
                "实例账户同步成功",
                module="accounts_sync",
                action="sync_instance_accounts",
                context={
                    "actor_id": actor_id,
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "synced_count": normalized.get("synced_count", 0),
                },
                include_actor=False,
            )
        else:
            log_with_context(
                "error",
                "实例账户同步失败",
                module="accounts_sync",
                action="sync_instance_accounts",
                context={
                    "actor_id": actor_id,
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "db_type": instance.db_type,
                    "host": instance.host,
                },
                extra={"error_message": cast(str, normalized.get("message") or "账户同步失败")},
                include_actor=False,
            )

        return AccountsSyncActionResult(
            success=is_success,
            message=cast(str, normalized["message"]),
            result=normalized,
        )
