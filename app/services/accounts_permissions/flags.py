"""Feature flags for account permission snapshot rollout."""

from __future__ import annotations

from os import environ

from flask import current_app, has_app_context


def snapshot_read_enabled() -> bool:
    if has_app_context():
        return bool(current_app.config.get("ACCOUNT_PERMISSION_SNAPSHOT_READ", False))
    raw = (environ.get("ACCOUNT_PERMISSION_SNAPSHOT_READ") or "").strip().lower()
    return raw in {"true", "1", "yes", "y", "on"}

