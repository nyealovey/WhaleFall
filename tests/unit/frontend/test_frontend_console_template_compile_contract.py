"""控制台页面模板编译契约测试."""

from __future__ import annotations

import pytest

from app import create_app
from app.settings import Settings


@pytest.mark.unit
def test_console_templates_compile_under_app_context(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    app = create_app(init_scheduler_on_start=False, settings=Settings.load())

    templates = (
        "about.html",
        "instances/detail.html",
        "credentials/list.html",
        "instances/list.html",
        "accounts/ledgers.html",
        "databases/ledgers.html",
        "auth/list.html",
        "history/logs/logs.html",
        "history/account_change_logs/account-change-logs.html",
        "history/sessions/sync-sessions.html",
        "capacity/instances.html",
        "capacity/databases.html",
        "instances/statistics.html",
        "accounts/statistics.html",
        "accounts/classification_statistics.html",
        "admin/partitions/index.html",
        "admin/system-settings/index.html",
        "tags/bulk/assign.html",
    )

    with app.app_context():
        for name in templates:
            app.jinja_env.get_template(name)
