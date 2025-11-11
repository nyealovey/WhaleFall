"""Queue worker responsible for persisting structured logs asynchronously."""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from queue import Empty, Full, Queue
from typing import Any

from app import db
from app.models.unified_log import UnifiedLog
from sqlalchemy import text


class LogQueueWorker:
    """Background worker that flushes log entries to the database."""

    def __init__(
        self,
        app,
        *,
        queue_size: int = 1000,
        batch_size: int = 100,
        flush_interval: float = 3.0,
    ) -> None:
        self.app = app
        self.queue: Queue[dict[str, Any]] = Queue(maxsize=queue_size)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: list[dict[str, Any]] = []
        self._last_flush = time.time()
        self._shutdown = threading.Event()
        self._enum_checked = False
        self._thread = threading.Thread(target=self._run, name="structlog-worker", daemon=True)
        self._thread.start()

    def enqueue(self, log_entry: dict[str, Any]) -> None:
        if self._shutdown.is_set():
            return
        try:
            self.queue.put_nowait(log_entry)
        except Full:
            logging.warning(
                "Structured log dropped because queue is full", extra={"queue_size": self.queue.qsize()}
            )

    def shutdown(self, timeout: float = 5.0) -> None:
        self._shutdown.set()
        self._thread.join(timeout=timeout)
        self._flush_buffer()

    def _run(self) -> None:
        while not self._shutdown.is_set():
            try:
                log_entry = self.queue.get(timeout=0.5)
                self._buffer.append(log_entry)
            except Empty:
                pass

            if self._should_flush():
                self._flush_buffer()

        # Flush remaining logs on shutdown
        self._flush_buffer()

    def _should_flush(self) -> bool:
        if not self._buffer:
            return False
        if len(self._buffer) >= self.batch_size:
            return True
        return time.time() - self._last_flush >= self.flush_interval

    def _flush_buffer(self) -> None:
        if not self._buffer:
            return

        entries = [entry for entry in self._buffer if entry]
        self._buffer.clear()
        if not entries:
            return

        try:
            with self.app.app_context():
                self._ensure_log_level_enum()

                models = [UnifiedLog.create_log_entry(**entry) for entry in entries]
                if models:
                    db.session.add_all(models)
                    db.session.commit()
        except Exception:  # noqa: BLE001
            logging.exception("Error flushing structured logs to database")
            with contextlib.suppress(Exception):
                db.session.rollback()
        finally:
            self._last_flush = time.time()

    def _ensure_log_level_enum(self) -> None:
        if self._enum_checked:
            return

        bind = db.session.get_bind()
        if not bind or bind.dialect.name != "postgresql":
            self._enum_checked = True
            return

        exists = bind.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'log_level'")
        ).scalar()

        if not exists:
            bind.execute(
                text(
                    "CREATE TYPE log_level AS ENUM ('DEBUG','INFO','WARNING','ERROR','CRITICAL')"
                )
            )

        self._enum_checked = True


__all__ = ["LogQueueWorker"]
