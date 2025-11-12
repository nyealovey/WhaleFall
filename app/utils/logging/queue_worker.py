"""负责异步持久化结构化日志的队列工作线程。"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from queue import Empty, Full, Queue
from typing import Any

from app import db
from app.models.unified_log import UnifiedLog


class LogQueueWorker:
    """后台线程，按批次将日志写入数据库。"""

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
        self._thread = threading.Thread(target=self._run, name="structlog-worker", daemon=True)
        self._thread.start()

    def enqueue(self, log_entry: dict[str, Any]) -> None:
        if self._shutdown.is_set():
            return
        try:
            self.queue.put_nowait(log_entry)
        except Full:
            logging.warning(
                "结构化日志队列已满，丢弃一条日志", extra={"queue_size": self.queue.qsize()}
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

        # 线程退出前确保剩余日志也写入
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
                models = [UnifiedLog.create_log_entry(**entry) for entry in entries]
                if models:
                    db.session.add_all(models)
                    db.session.commit()
        except Exception:  # noqa: BLE001
            logging.exception("写入结构化日志到数据库失败")
            with contextlib.suppress(Exception):
                db.session.rollback()
        finally:
            self._last_flush = time.time()


__all__ = ["LogQueueWorker"]
