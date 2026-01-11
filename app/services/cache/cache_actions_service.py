"""Cache actions service.

将 cache namespace 的核心逻辑下沉到 service 层：
- cache stats
- clear-user / clear-instance / clear-all
- clear-classification
- classification stats

路由层仅保留鉴权/CSRF、参数读取、封套与 safe_call。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

import app.services.cache_service as cache_service_module
from app.errors import ConflictError, NotFoundError, SystemError, ValidationError
from app.models.instance import Instance
from app.services.account_classification.orchestrator import AccountClassificationService
from app.infra.route_safety import log_with_context
from app.utils.structlog_config import log_info

_CLASSIFICATION_DB_TYPES: list[str] = ["mysql", "postgresql", "sqlserver", "oracle"]
_VALID_CLASSIFICATION_DB_TYPES: set[str] = set(_CLASSIFICATION_DB_TYPES)


@dataclass(frozen=True, slots=True)
class CacheStatsResult:
    """缓存统计结果."""

    stats: dict[str, object]


@dataclass(frozen=True, slots=True)
class CacheClearAllResult:
    """批量清除缓存结果."""

    cleared_count: int


@dataclass(frozen=True, slots=True)
class CacheClassificationStatsResult:
    """分类缓存统计结果."""

    cache_stats: dict[str, object]
    db_type_stats: dict[str, dict[str, object]]
    cache_enabled: bool


class SupportsCacheService(Protocol):
    """cache service protocol (for tests & type checking)."""

    def get_cache_stats(self) -> dict[str, object]:
        """获取缓存统计信息."""
        ...

    def invalidate_user_cache(self, instance_id: int, username: str) -> bool:
        """清除指定用户在指定实例上的缓存."""
        ...

    def invalidate_instance_cache(self, instance_id: int) -> bool:
        """清除指定实例的缓存."""
        ...

    def get_classification_rules_by_db_type_cache(self, db_type: str) -> list[object] | None:
        """获取指定 db_type 的分类规则缓存(不存在返回 None)."""
        ...


class CacheActionsService:
    """缓存动作编排服务."""

    @staticmethod
    def _require_cache_service() -> SupportsCacheService:
        manager = cache_service_module.cache_service
        if manager is None:
            raise SystemError("缓存服务未初始化")
        return cast(SupportsCacheService, manager)

    def get_cache_stats(self) -> CacheStatsResult:
        """获取缓存统计信息."""
        manager = self._require_cache_service()
        stats = manager.get_cache_stats()
        return CacheStatsResult(stats=stats)

    def clear_user_cache(self, *, instance_id: int | None, username: str | None, operator_id: int | None) -> str:
        """清除指定用户在指定实例上的缓存."""
        manager = self._require_cache_service()
        if not instance_id or not username:
            raise ValidationError("缺少必要参数: instance_id 和 username")

        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError("实例不存在")

        success = manager.invalidate_user_cache(instance_id, username)
        if not success:
            raise ConflictError("用户缓存清除失败")

        log_info(
            "用户缓存清除成功",
            module="cache",
            instance_id=instance_id,
            username=username,
            operator_id=operator_id,
        )
        return "用户缓存清除成功"

    def clear_instance_cache(self, *, instance_id: int | None, operator_id: int | None) -> str:
        """清除指定实例的缓存."""
        manager = self._require_cache_service()
        if not instance_id:
            raise ValidationError("缺少必要参数: instance_id")

        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError("实例不存在")

        success = manager.invalidate_instance_cache(instance_id)
        if not success:
            raise ConflictError("实例缓存清除失败")

        log_info(
            "实例缓存清除成功",
            module="cache",
            instance_id=instance_id,
            operator_id=operator_id,
        )
        return "实例缓存清除成功"

    def clear_all_cache(self, *, operator_id: int | None) -> CacheClearAllResult:
        """清除所有活跃实例的缓存."""
        manager = self._require_cache_service()
        instances = Instance.query.filter_by(is_active=True).all()

        cleared_count = 0
        for instance in instances:
            try:
                if manager.invalidate_instance_cache(instance.id):
                    cleared_count += 1
            except cache_service_module.CACHE_EXCEPTIONS as exc:
                log_with_context(
                    "error",
                    "清除实例缓存失败",
                    module="cache",
                    action="clear_all_cache",
                    context={"instance_id": instance.id},
                    extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
                )

        log_info(
            "批量清除缓存完成",
            module="cache",
            cleared_count=cleared_count,
            operator_id=operator_id,
        )
        return CacheClearAllResult(cleared_count=cleared_count)

    def clear_classification_cache(self, *, db_type: str | None, operator_id: int | None) -> str:
        """清除分类规则缓存(可按 db_type 定向清除)."""
        db_type_raw = (db_type or "").strip()
        if db_type_raw:
            normalized_type = db_type_raw.lower()
            if normalized_type not in _VALID_CLASSIFICATION_DB_TYPES:
                raise ValidationError(f"不支持的数据库类型: {db_type_raw}")

            result = AccountClassificationService().invalidate_db_type_cache(normalized_type)
            if not result:
                raise ConflictError(f"数据库类型 {db_type_raw} 缓存清除失败")

            log_info(
                f"数据库类型 {db_type_raw} 缓存清除成功",
                module="cache",
                operator_id=operator_id,
                db_type=normalized_type,
            )
            return f"数据库类型 {db_type_raw} 缓存已清除"

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
        manager = self._require_cache_service()

        stats = manager.get_cache_stats()
        db_type_stats: dict[str, dict[str, object]] = {}

        for db_type in _CLASSIFICATION_DB_TYPES:
            try:
                rules_cache = manager.get_classification_rules_by_db_type_cache(db_type)
                db_type_stats[db_type] = {
                    "rules_cached": rules_cache is not None,
                    "rules_count": len(rules_cache) if rules_cache else 0,
                }
            except cache_service_module.CACHE_EXCEPTIONS as exc:
                log_with_context(
                    "error",
                    "获取数据库类型缓存统计失败",
                    module="cache",
                    action="get_classification_cache_stats",
                    context={"db_type": db_type},
                    extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
                )
                db_type_stats[db_type] = {
                    "rules_cached": False,
                    "rules_count": 0,
                    "error": str(exc),
                }

        return CacheClassificationStatsResult(
            cache_stats=stats,
            db_type_stats=db_type_stats,
            cache_enabled=True,
        )
