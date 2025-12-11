"""负责异步持久化结构化日志的队列工作线程."""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from functools import lru_cache
from importlib import import_module
from queue import Empty, Full, Queue
from typing import TYPE_CHECKING

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.types import JsonValue

if TYPE_CHECKING:
    from app.models.unified_log import UnifiedLog

queue_logger = logging.getLogger(__name__)


LogEntry = dict[str, JsonValue]
LogBuffer = list[LogEntry]


@lru_cache(maxsize=1)
def _get_logging_dependencies() -> tuple[SQLAlchemy, type[UnifiedLog]]:
    """惰性加载数据库句柄与日志模型以避免循环导入.

    Returns:
        包含 SQLAlchemy db 实例与 UnifiedLog 模型的元组.

    """
    app_module = import_module("app")
    models_module = import_module("app.models.unified_log")
    db: SQLAlchemy = app_module.db
    unified_log: type[UnifiedLog] = models_module.UnifiedLog
    return db, unified_log


class LogQueueWorker:
    """后台线程,按批次将日志写入数据库.

    Attributes:
        app: Flask 应用实例.
        queue: 日志条目队列.
        batch_size: 批次大小.
        flush_interval: 刷新间隔(秒).

    """

    def __init__(
        self,
        app: Flask,
        *,
        queue_size: int = 1000,
        batch_size: int = 100,
        flush_interval: float = 3.0,
    ) -> None:
        """初始化日志队列工作线程.

        Args:
            app: Flask 应用实例.
            queue_size: 队列最大容量,默认 1000.
            batch_size: 批次大小,默认 100.
            flush_interval: 刷新间隔(秒),默认 3.0.

        """
        self.app = app
        self.queue: Queue[LogEntry] = Queue(maxsize=queue_size)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: LogBuffer = []
        self._last_flush = time.time()
        self._shutdown = threading.Event()
        self._thread = threading.Thread(target=self._run, name="structlog-worker", daemon=True)
        self._thread.start()
        self._closed = False

    def enqueue(self, log_entry: LogEntry) -> None:
        """将日志条目加入队列.

        Args:
            log_entry: 日志条目字典.

        Returns:
            None.

        """
        if self._shutdown.is_set():
            return
        try:
            self.queue.put_nowait(log_entry)
        except Full:
            queue_logger.warning(
                "结构化日志队列已满,丢弃一条日志",
                extra={"queue_size": self.queue.qsize()},
            )

    def close(self, timeout: float = 5.0) -> None:
        """显式关闭工作线程并刷新剩余日志.

        Args:
            timeout: 等待线程结束的超时时间(秒),默认 5.0.

        Returns:
            None.

        """
        if self._closed:
            return
        self._shutdown.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._flush_buffer()
        self._closed = True

    def shutdown(self, timeout: float = 5.0) -> None:
        """兼容旧关闭接口.

        Args:
            timeout: 等待线程结束的超时时间(秒),默认 5.0.

        Returns:
            None.

        """
        self.close(timeout=timeout)

    def _run(self) -> None:
        """工作线程主循环,从队列中取出日志并批量写入数据库.

        Returns:
            None.

        """
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
        """判断是否应该刷新缓冲区.

        Returns:
            如果缓冲区达到批次大小或超过刷新间隔,返回 True.

        """
        if not self._buffer:
            return False
        if len(self._buffer) >= self.batch_size:
            return True
        return time.time() - self._last_flush >= self.flush_interval

    def _flush_buffer(self) -> None:
        """将缓冲区中的日志批量写入数据库.

        Returns:
            None.

        """
        if not self._buffer:
            return

        entries = [entry for entry in self._buffer if entry]
        self._buffer.clear()
        if not entries:
            return

        db: SQLAlchemy | None = None
        try:
            db, UnifiedLog = _get_logging_dependencies()
            with self.app.app_context():
                models = [UnifiedLog.create_log_entry(**entry) for entry in entries]
                if models:
                    db.session.add_all(models)
                    db.session.commit()
        except Exception:
            queue_logger.exception("写入结构化日志到数据库失败")
            if db is not None:
                with contextlib.suppress(Exception):
                    db.session.rollback()
        finally:
            self._last_flush = time.time()

    def __del__(self) -> None:
        """对象回收时仅标记关闭,避免在 GC 期间执行日志 IO."""
        shutdown = getattr(self, "_shutdown", None)
        if shutdown is not None and not shutdown.is_set():
            shutdown.set()


__all__ = ["LogQueueWorker"]
