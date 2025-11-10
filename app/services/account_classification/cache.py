"""Classification cache helpers."""

from __future__ import annotations

from typing import Any, Iterable

from app.services.cache_service import cache_manager
from app.utils.structlog_config import log_error


class ClassificationCache:
    """Wrapper around global cache manager for classification-specific keys."""

    def __init__(self, manager: Any | None = None) -> None:  # noqa: ANN401
        self.manager = manager or cache_manager

    # ---- Rules cache -----------------------------------------------------
    def get_rules(self) -> list[dict[str, Any]] | None:
        """Return cached rules payload if available."""
        if not self.manager:
            return None
        cached = self.manager.get_classification_rules_cache()
        if not cached:
            return None
        if isinstance(cached, dict) and "rules" in cached:
            return cached["rules"]
        if isinstance(cached, list):
            return cached
        log_error("Invalid classification rules cache format", module="account_classification_cache")
        return None

    def set_rules(self, rules_data: Iterable[dict[str, Any]]) -> bool:
        """Persist rules payload to cache."""
        if not self.manager:
            return False
        payload = list(rules_data)
        if not payload:
            return False
        return self.manager.set_classification_rules_cache(payload)

    # ---- Rules cache (per db type) --------------------------------------
    def set_rules_by_db_type(self, db_type: str, rules: Iterable[dict[str, Any]]) -> bool:
        if not self.manager:
            return False
        return self.manager.set_classification_rules_by_db_type_cache(db_type, list(rules))

    # ---- Invalidation helpers -------------------------------------------
    def invalidate_all(self) -> bool:
        if not self.manager:
            return False
        self.manager.invalidate_classification_cache()
        self.manager.invalidate_all_db_type_cache()
        return True

    def invalidate_db_type(self, db_type: str) -> bool:
        if not self.manager:
            return False
        self.manager.invalidate_db_type_cache(db_type)
        return True
