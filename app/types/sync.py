"""账户/数据库同步相关类型别名."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypedDict, TypeAlias

if TYPE_CHECKING:
    from app.types.accounts import PermissionSnapshot, RemoteAccount
    from app.types.structures import JsonDict, JsonValue
else:
    PermissionSnapshot = Mapping[str, Any]
    RemoteAccount = Mapping[str, Any]
    JsonValue = Any
    JsonDict = dict[str, JsonValue]


class SyncConnection(Protocol):
    """数据库连接对象协议."""

    def connect(self) -> bool:  # pragma: no cover - protocol
        ...

    def disconnect(self) -> None:  # pragma: no cover - protocol
        ...

    def execute_query(
        self, query: str, params: Sequence[JsonValue] | Mapping[str, JsonValue] | None = None
    ) -> Iterable[Sequence[JsonValue]]:
        ...


class SyncSummary(TypedDict, total=False):
    """同步阶段统计信息."""

    created: int
    updated: int
    skipped: int
    errors: list[str]
    processed_records: int
    status: str
    message: str


class PrivilegeDiffEntry(TypedDict):
    """权限差异明细条目."""

    field: str
    label: str
    object: str
    action: Literal["GRANT", "REVOKE", "ALTER"]
    permissions: list[str]


class OtherDiffEntry(TypedDict):
    """非权限字段的差异条目."""

    field: str
    label: str
    before: str
    after: str
    description: str


DiffEntry: TypeAlias = PrivilegeDiffEntry | OtherDiffEntry


class PermissionDiffPayload(TypedDict, total=False):
    """权限差异快照."""

    changed: bool
    change_type: str
    privilege_diff: list[PrivilegeDiffEntry]
    other_diff: list[OtherDiffEntry]


RemoteAccountMap: TypeAlias = dict[str, RemoteAccount]


class InventorySummary(TypedDict, total=False):
    """账户清单阶段统计信息."""

    status: Literal["completed", "skipped"]
    created: int
    refreshed: int
    reactivated: int
    deactivated: int
    processed_records: int
    total_remote: int
    active_accounts: list[str]
    active_count: int


class CollectionSummary(TypedDict, total=False):
    """权限采集阶段统计信息."""

    status: Literal["completed", "skipped", "failed"]
    created: int
    updated: int
    skipped: int
    processed_records: int
    errors: list[str]
    message: str


class SyncStagesSummary(TypedDict):
    """两阶段同步结果."""

    inventory: InventorySummary
    collection: CollectionSummary


class SyncOperationResult(TypedDict, total=False):
    """对外暴露的账户同步结果."""

    success: bool
    message: str
    error: str
    synced_count: int
    added_count: int
    modified_count: int
    removed_count: int
    details: SyncStagesSummary | JsonDict


__all__ = [
    "CollectionSummary",
    "DiffEntry",
    "InventorySummary",
    "OtherDiffEntry",
    "PermissionDiffPayload",
    "PrivilegeDiffEntry",
    "RemoteAccountMap",
    "SyncConnection",
    "SyncOperationResult",
    "SyncStagesSummary",
    "SyncSummary",
]
