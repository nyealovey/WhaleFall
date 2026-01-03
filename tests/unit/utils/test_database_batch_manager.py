from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app import create_app, db
from app.models.user import User
from app.settings import Settings
from app.utils.database_batch_manager import DatabaseBatchManager


@pytest.mark.unit
def test_database_batch_manager_allows_partial_success(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )

        manager = DatabaseBatchManager(batch_size=10, instance_name="unit-test")
        manager.add_operation("add", User(username="dup", password="TestPass1", role="admin"), "add user1")
        manager.add_operation("add", User(username="dup", password="TestPass1", role="admin"), "add user2 duplicate")

        success = manager.commit_batch()
        assert success is False

        stats = manager.get_statistics()
        assert stats["successful_operations"] == 1
        assert stats["failed_operations"] == 1

        users = User.query.filter_by(username="dup").all()
        assert len(users) == 1


@pytest.mark.unit
def test_database_batch_manager_returns_true_when_batch_is_fully_successful(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )

        manager = DatabaseBatchManager(batch_size=10, instance_name="unit-test")
        manager.add_operation("add", User(username="u1", password="TestPass1", role="admin"), "add user1")
        manager.add_operation("add", User(username="u2", password="TestPass1", role="admin"), "add user2")

        success = manager.commit_batch()
        assert success is True

        stats = manager.get_statistics()
        assert stats["successful_operations"] == 2
        assert stats["failed_operations"] == 0

        username_attr = cast(InstrumentedAttribute[str], User.username)
        username_condition = cast(ColumnElement[bool], username_attr.in_(["u1", "u2"]))
        users = User.query.filter(username_condition).all()
        assert {user.username for user in users} == {"u1", "u2"}
