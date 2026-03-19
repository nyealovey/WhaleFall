"""实例统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app import db
from app.models.instance import Instance
from app.models.instance_config_snapshot import InstanceConfigSnapshot
from app.models.tag import Tag, instance_tags


AUDIT_INFO_CONFIG_KEY = "audit_info"
_STANDALONE_ARCHITECTURE_ALIASES = {"standalone", "single", "单机"}


class InstanceStatisticsRepository:
    """实例统计读模型 Repository."""

    @staticmethod
    def fetch_summary(*, db_type: str | None = None) -> dict[str, int]:
        """获取实例统计摘要."""
        query = Instance.query
        if db_type:
            query = query.filter(Instance.db_type == db_type)

        current_query = query.filter(Instance.deleted_at.is_(None))
        current_instances = current_query.count()
        active_instances = current_query.filter(Instance.is_active.is_(True)).count()
        disabled_instances = max(current_instances - active_instances, 0)
        deleted_instances = query.filter(Instance.deleted_at.isnot(None)).count()
        total_instances = current_instances + deleted_instances
        normal_instances = active_instances
        active_instance_ids = [
            int(instance_id)
            for (instance_id,) in current_query.with_entities(Instance.id).filter(Instance.is_active.is_(True)).all()
        ]
        audit_enabled_instances = InstanceStatisticsRepository._count_audit_enabled_instances(active_instance_ids)
        high_availability_instances = InstanceStatisticsRepository._count_high_availability_instances(active_instance_ids)

        return {
            "total_instances": total_instances,
            "current_instances": current_instances,
            "active_instances": active_instances,
            "normal_instances": normal_instances,
            "disabled_instances": disabled_instances,
            "deleted_instances": deleted_instances,
            "audit_enabled_instances": audit_enabled_instances,
            "high_availability_instances": high_availability_instances,
        }

    @staticmethod
    def _count_audit_enabled_instances(active_instance_ids: list[int]) -> int:
        if not active_instance_ids:
            return 0

        rows = (
            db.session.query(InstanceConfigSnapshot.instance_id, InstanceConfigSnapshot.facts)
            .filter(
                InstanceConfigSnapshot.instance_id.in_(active_instance_ids),
                InstanceConfigSnapshot.config_key == AUDIT_INFO_CONFIG_KEY,
            )
            .all()
        )

        enabled_count = 0
        for _, facts in rows:
            if not isinstance(facts, dict):
                continue
            has_audit = bool(facts.get("has_audit"))
            try:
                enabled_audit_count = int(facts.get("enabled_audit_count") or 0)
            except (TypeError, ValueError):
                enabled_audit_count = 0
            if has_audit and enabled_audit_count > 0:
                enabled_count += 1
        return enabled_count

    @staticmethod
    def _count_high_availability_instances(active_instance_ids: list[int]) -> int:
        if not active_instance_ids:
            return 0

        rows = (
            db.session.query(instance_tags.c.instance_id, Tag.name, Tag.display_name)
            .join(Tag, Tag.id == instance_tags.c.tag_id)
            .filter(
                instance_tags.c.instance_id.in_(active_instance_ids),
                Tag.category == "architecture",
            )
            .all()
        )

        architecture_tokens_by_instance: dict[int, set[str]] = defaultdict(set)
        for instance_id, tag_name, display_name in rows:
            architecture_tokens_by_instance[int(instance_id)].update(
                InstanceStatisticsRepository._normalize_architecture_tokens(tag_name, display_name),
            )

        return sum(
            1
            for instance_id in active_instance_ids
            if InstanceStatisticsRepository._is_high_availability_architecture(
                architecture_tokens_by_instance.get(instance_id, set())
            )
        )

    @staticmethod
    def _normalize_architecture_tokens(*values: object) -> set[str]:
        tokens: set[str] = set()
        for value in values:
            if value is None:
                continue
            normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
            if normalized:
                tokens.add(normalized)
        return tokens

    @staticmethod
    def _is_high_availability_architecture(tokens: set[str]) -> bool:
        if not tokens:
            return False
        return any(token not in _STANDALONE_ARCHITECTURE_ALIASES for token in tokens)

    @staticmethod
    def fetch_db_type_stats() -> list[Any]:
        """获取实例按数据库类型统计."""
        return (
            db.session.query(Instance.db_type, db.func.count(Instance.id).label("count"))
            .filter(Instance.deleted_at.is_(None))
            .group_by(Instance.db_type)
            .all()
        )

    @staticmethod
    def fetch_port_stats(limit: int = 10) -> list[Any]:
        """获取实例按端口统计."""
        return (
            db.session.query(Instance.port, db.func.count(Instance.id).label("count"))
            .filter(Instance.deleted_at.is_(None))
            .group_by(Instance.port)
            .order_by(db.func.count(Instance.id).desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def fetch_version_stats() -> list[Any]:
        """获取实例按版本统计."""
        return (
            db.session.query(
                Instance.db_type,
                Instance.main_version,
                db.func.count(Instance.id).label("count"),
            )
            .filter(Instance.deleted_at.is_(None))
            .group_by(Instance.db_type, Instance.main_version)
            .all()
        )
