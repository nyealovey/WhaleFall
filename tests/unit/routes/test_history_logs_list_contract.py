import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CACHE_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-key")

from app import create_app, db
from app.constants.system_constants import LogLevel
from app.models.unified_log import UnifiedLog
from app.models.user import User
from app.utils.time_utils import time_utils


@pytest.mark.unit
def test_history_logs_list_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["unified_logs"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        log = UnifiedLog(
            timestamp=time_utils.now(),
            level=LogLevel.INFO,
            module="unit-test",
            message="hello",
            traceback=None,
            context={"event": "contract"},
        )
        db.session.add(log)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/history/logs/api/list")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False
        assert "message" in payload
        assert "timestamp" in payload

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())

        items = data.get("items")
        assert isinstance(items, list)
        assert len(items) == 1

        item = items[0]
        assert isinstance(item, dict)
        expected_keys = {
            "id",
            "timestamp",
            "timestamp_display",
            "level",
            "module",
            "message",
            "traceback",
            "context",
        }
        assert expected_keys.issubset(item.keys())
