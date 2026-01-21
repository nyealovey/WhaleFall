"""账户台账相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.types.tags import TagSummary


@dataclass(frozen=True)
class AccountFilters:
    """账户筛选条件集合."""

    page: int
    limit: int
    search: str
    instance_id: int | None
    include_deleted: bool
    include_roles: bool
    is_locked: str | None
    is_superuser: str | None
    plugin: str
    tags: list[str]
    classification: str
    classification_filter: str
    db_type: str | None


@dataclass(slots=True)
class AccountClassificationSummary:
    """账户分类展示结构."""

    name: str


@dataclass(slots=True)
class AccountLedgerItem:
    """账户台账列表单行结构."""

    id: int
    username: str
    instance_name: str
    instance_host: str
    db_type: str
    is_locked: bool
    is_superuser: bool
    is_active: bool
    is_deleted: bool
    type_specific: dict[str, object]
    tags: list[TagSummary]
    classifications: list[AccountClassificationSummary]


@dataclass(slots=True)
class AccountLedgerMetrics:
    """账户台账列表聚合信息."""

    tags_map: dict[int, list[TagSummary]]
    classifications_map: dict[int, list[AccountClassificationSummary]]
