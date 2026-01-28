"""Cache actions service.

将 cache namespace 的核心逻辑下沉到 service 层：
- cache stats
- clear-classification
- classification stats

路由层仅保留鉴权/CSRF、参数读取、封套与 safe_call。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from app.core.exceptions import ConflictError, SystemError
from app.schemas.cache_actions import (
    CLASSIFICATION_DB_TYPES,
    ClearClassificationCachePayload,
)
from app.schemas.validation import validate_or_raise
from app.services.account_classification.orchestrator import AccountClassificationService
from app.utils.cache_utils import CacheManagerRegistry
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info

_CLASSIFICATION_RULES_PREFIX = "classification_rules"


@dataclass(frozen=True, slots=True)
class CacheStatsResult:
    """缓存统计结果."""

    stats: dict[str, object]


@dataclass(frozen=True, slots=True)
class CacheClassificationStatsResult:
    """分类缓存统计结果."""

    cache_stats: dict[str, object]
    db_type_stats: dict[str, dict[str, object]]
    cache_enabled: bool


class SupportsCacheManager(Protocol):
    """cache manager protocol (for tests & type checking)."""

    def get_stats(self) -> dict[str, object]:
        """获取缓存统计信息."""
        ...

    def get(self, key: str) -> object | None:
        """读取缓存."""
        ...


def _extract_rules_from_cache(value: object | None) -> list[object] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        rules = value.get("rules")
        if isinstance(rules, list):
            return rules
        return None
    return None


class CacheActionsService:
    """缓存动作编排服务."""

    @staticmethod
    def _get_cache_manager() -> SupportsCacheManager:
        try:
            manager = CacheManagerRegistry.get()
        except RuntimeError as exc:
            raise SystemError("缓存管理器未初始化") from exc
        return cast(SupportsCacheManager, manager)

    def get_cache_stats(self) -> CacheStatsResult:
        """获取缓存统计信息."""
        manager = self._get_cache_manager()
        stats = manager.get_stats()
        return CacheStatsResult(stats=stats)

    def clear_classification_cache(self, payload: object | None, *, operator_id: int | None) -> str:
        """清除分类规则缓存(可按 db_type 定向清除)."""
        sanitized = parse_payload(payload)
        params = validate_or_raise(ClearClassificationCachePayload, sanitized)

        if params.db_type:
            result = AccountClassificationService().invalidate_db_type_cache(params.db_type)
            if not result:
                raise ConflictError(f"数据库类型 {params.db_type} 缓存清除失败")

            log_info(
                f"数据库类型 {params.db_type} 缓存清除成功",
                module="cache",
                operator_id=operator_id,
                db_type=params.db_type,
            )
            return f"数据库类型 {params.db_type} 缓存已清除"

        result = AccountClassificationService().invalidate_cache()
        if not result:
            raise ConflictError("分类缓存清除失败")

        log_info(
            "分类缓存清除成功",
            module="cache",
            operator_id=operator_id,
        )
        return "分类缓存已清除"

    def get_classification_cache_stats(self) -> CacheClassificationStatsResult:
        """获取分类缓存统计信息(总览 + 按 db_type 细分)."""
        manager = self._get_cache_manager()

        stats = manager.get_stats()
        db_type_stats: dict[str, dict[str, object]] = {}

        all_key = f"{_CLASSIFICATION_RULES_PREFIX}:all"
        all_rules = _extract_rules_from_cache(manager.get(all_key))

        grouped_counts: dict[str, int] = dict.fromkeys(CLASSIFICATION_DB_TYPES, 0)
        if all_rules is not None:
            for rule in all_rules:
                if not isinstance(rule, dict):
                    continue
                db_type_raw = rule.get("db_type")
                if not isinstance(db_type_raw, str):
                    continue
                normalized = db_type_raw.strip().lower()
                if normalized in grouped_counts:
                    grouped_counts[normalized] += 1

        rules_cached = all_rules is not None
        for db_type in CLASSIFICATION_DB_TYPES:
            db_type_stats[db_type] = {
                "rules_cached": rules_cached,
                "rules_count": grouped_counts.get(db_type, 0),
            }

        return CacheClassificationStatsResult(
            cache_stats=stats,
            db_type_stats=db_type_stats,
            cache_enabled=True,
        )
