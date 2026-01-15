from typing import Any, cast

import pytest

from app import create_app, db
from app.core.constants import DatabaseType, SyncSessionStatus
from app.core.exceptions import NotFoundError, ValidationError
from app.models.instance import Instance
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.services.sync_session_service import SyncItemStats, SyncSessionService


@pytest.mark.unit
def test_clean_sync_details_injects_version_for_empty_dict() -> None:
    service = SyncSessionService()
    assert service._clean_sync_details({}) == {"version": 1}


@pytest.mark.unit
def test_create_session_disallows_custom_session_id() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[db.metadata.tables["sync_sessions"]])
        service = SyncSessionService()

        with pytest.raises(TypeError):
            cast(Any, service).create_session(
                sync_type="manual_task",
                sync_category="account",
                created_by=None,
                session_id="fixed-session-id",
            )


@pytest.mark.unit
def test_add_instance_records_rejects_missing_instance_ids() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        service = SyncSessionService()
        session = service.create_session(sync_type="manual_task", sync_category="account", created_by=None)

        with pytest.raises(ValidationError) as exc:
            service.add_instance_records(session.session_id, [instance.id, 99999])

        assert exc.value.extra.get("missing_instance_ids") == [99999]


@pytest.mark.unit
def test_complete_instance_sync_raises_on_write_error(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        service = SyncSessionService()
        session = service.create_session(sync_type="manual_task", sync_category="account", created_by=None)
        records = service.add_instance_records(session.session_id, [instance.id])
        record = records[0]

        def _boom_complete_sync(self, **_kwargs):  # noqa: ANN001
            raise RuntimeError("boom")

        monkeypatch.setattr(SyncInstanceRecord, "complete_sync", _boom_complete_sync)

        with pytest.raises(RuntimeError, match="boom"):
            service.complete_instance_sync(record.id, stats=SyncItemStats(), sync_details={})


@pytest.mark.unit
def test_fail_instance_sync_raises_on_write_error(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        service = SyncSessionService()
        session = service.create_session(sync_type="manual_task", sync_category="account", created_by=None)
        records = service.add_instance_records(session.session_id, [instance.id])
        record = records[0]

        def _boom_fail_sync(self, **_kwargs):  # noqa: ANN001
            raise RuntimeError("boom")

        monkeypatch.setattr(SyncInstanceRecord, "fail_sync", _boom_fail_sync)

        with pytest.raises(RuntimeError, match="boom"):
            service.fail_instance_sync(record.id, error_message="x", sync_details={})


@pytest.mark.unit
def test_get_session_records_raises_on_query_error(monkeypatch) -> None:
    service = SyncSessionService()

    def _boom_get_records_by_session(session_id: str):  # noqa: ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(SyncInstanceRecord, "get_records_by_session", staticmethod(_boom_get_records_by_session))

    with pytest.raises(RuntimeError, match="boom"):
        service.get_session_records("s-1")


@pytest.mark.unit
def test_get_session_by_id_raises_on_query_error(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        service = SyncSessionService()

        class _BoomQuery:
            def filter_by(self, **_kwargs):  # noqa: ANN001
                raise RuntimeError("boom")

        monkeypatch.setattr(SyncSession, "query", _BoomQuery())

        with pytest.raises(RuntimeError, match="boom"):
            service.get_session_by_id("s-1")


@pytest.mark.unit
def test_cancel_session_returns_false_when_session_not_running() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[db.metadata.tables["sync_sessions"]])

        service = SyncSessionService()
        session = service.create_session(sync_type="manual_task", sync_category="account", created_by=None)

        with db.session.begin_nested():
            session.status = SyncSessionStatus.COMPLETED
            db.session.flush()

        assert service.cancel_session(session.session_id) is False


@pytest.mark.unit
def test_start_instance_sync_raises_when_record_missing() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
            ],
        )
        service = SyncSessionService()

        with pytest.raises(NotFoundError):
            service.start_instance_sync(99999)


@pytest.mark.unit
def test_start_instance_sync_raises_on_write_error(monkeypatch) -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        service = SyncSessionService()
        session = service.create_session(sync_type="manual_task", sync_category="account", created_by=None)
        record = service.add_instance_records(session.session_id, [instance.id])[0]

        def _boom_start_sync(self):  # noqa: ANN001
            raise RuntimeError("boom")

        monkeypatch.setattr(SyncInstanceRecord, "start_sync", _boom_start_sync)

        with pytest.raises(RuntimeError, match="boom"):
            service.start_instance_sync(record.id)


@pytest.mark.unit
def test_complete_instance_sync_raises_when_record_missing() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
            ],
        )
        service = SyncSessionService()

        with pytest.raises(NotFoundError):
            service.complete_instance_sync(99999, stats=SyncItemStats(), sync_details={})


@pytest.mark.unit
def test_fail_instance_sync_raises_when_record_missing() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
            ],
        )
        service = SyncSessionService()

        with pytest.raises(NotFoundError):
            service.fail_instance_sync(99999, error_message="x", sync_details={})
