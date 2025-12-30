"""Feature flags for account classification rollout."""

from __future__ import annotations

from os import environ

from flask import current_app, has_app_context


def dsl_v4_enabled() -> bool:
    """Whether to enable DSL v4 evaluation for account classification rules."""
    if has_app_context():
        return bool(current_app.config.get("ACCOUNT_CLASSIFICATION_DSL_V4", False))
    raw = (environ.get("ACCOUNT_CLASSIFICATION_DSL_V4") or "").strip().lower()
    return raw in {"true", "1", "yes", "y", "on"}
