"""鲸落 - 数据库批量操作管理器.

提供高效的批量提交机制,优化大量数据处理性能.
"""

from __future__ import annotations

from types import TracebackType
from typing import TypedDict

import structlog

from app import db
from app.types import LoggerProtocol


class _PendingOperation(TypedDict):
    type: str
    entity: object
    description: str


class DatabaseBatchManager:
    """数据库批量操作管理器.

    负责管理数据库操作的批量提交,提高性能并确保事务一致性.
    支持自动批量提交、手动提交和回滚操作,适用于大量数据处理场景.

    Attributes:
        batch_size: 批次大小,达到此数量时自动提交.
        logger: 结构化日志记录器.
        instance_name: 实例名称,用于日志记录.
        current_batch: 当前批次编号.
        total_operations: 总操作数.
        successful_operations: 成功操作数.
        failed_operations: 失败操作数.
        pending_operations: 待提交的操作队列.

    Example:
        >>> with DatabaseBatchManager(batch_size=100) as manager:
        ...     for entity in entities:
        ...         manager.add_operation('add', entity, 'Add user')
        ...     # 自动提交剩余操作

    """

    def __init__(
        self,
        batch_size: int = 100,
        logger: LoggerProtocol | None = None,
        instance_name: str = "",
    ) -> None:
        """初始化批量管理器.

        Args:
            batch_size: 批次大小,默认 100.达到此数量时自动提交.
            logger: 日志记录器,默认使用 structlog.
            instance_name: 实例名称,用于日志记录和追踪.

        """
        self.batch_size = batch_size
        self.logger: LoggerProtocol = logger if logger is not None else structlog.get_logger()
        self.instance_name = instance_name

        # 批次计数器
        self.current_batch = 0
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0

        # 操作队列
        self.pending_operations: list[_PendingOperation] = []

        self.logger.info(
            "初始化数据库批量管理器",
            module="database_batch_manager",
            instance_name=instance_name,
            batch_size=batch_size,
        )

    def add_operation(self, operation_type: str, entity: object, description: str = "") -> None:
        """添加数据库操作到批次队列.

        将操作添加到待处理队列,当队列达到批次大小时自动提交.

        Args:
            operation_type: 操作类型,可选值:'add'(新增)、'update'(更新)、'delete'(删除).
            entity: 数据库实体对象,必须是 SQLAlchemy 模型实例.
            description: 操作描述,用于日志记录和错误追踪.

        Returns:
            None.

        Example:
            >>> manager.add_operation('add', user, 'Add new user')
            >>> manager.add_operation('update', user, 'Update user status')

        """
        self.pending_operations.append({"type": operation_type, "entity": entity, "description": description})

        self.total_operations += 1

        # 如果达到批次大小,自动提交
        if len(self.pending_operations) >= self.batch_size:
            self.commit_batch()

    def commit_batch(self) -> bool:
        """提交当前批次的所有操作.

        执行队列中的所有操作并提交事务.如果任何操作失败,
        记录错误但继续处理其他操作(允许部分成功).如果提交失败,回滚整个批次.

        Returns:
            当批次内所有操作均成功提交时返回 True.
            若存在任意单条失败(但其它操作仍可能已提交)则返回 False.
            若批次提交失败(整体回滚)则返回 False.

        Example:
            >>> manager.add_operation('add', user1)
            >>> manager.add_operation('add', user2)
            >>> success = manager.commit_batch()

        """
        if not self.pending_operations:
            return True

        self.current_batch += 1
        operations = list(self.pending_operations)
        batch_size = len(operations)
        self.pending_operations.clear()
        batch_successful = 0
        batch_failed = 0

        try:
            self.logger.info(
                "开始提交批次 %s",
                self.current_batch,
                module="database_batch_manager",
                instance_name=self.instance_name,
                batch_size=batch_size,
                total_operations=self.total_operations,
            )

            with db.session.begin():
                for index, operation in enumerate(operations, start=1):
                    operation_type = operation["type"]
                    entity = operation["entity"]
                    description = operation["description"]

                    try:
                        with db.session.begin_nested():
                            if operation_type == "add":
                                db.session.add(entity)
                            elif operation_type == "update":
                                db.session.merge(entity)
                            elif operation_type == "delete":
                                db.session.delete(entity)
                            else:
                                raise ValueError(f"Unsupported operation type: {operation_type!r}")

                            # Flush inside a SAVEPOINT so a single IntegrityError won't poison the batch.
                            db.session.flush()
                    except Exception as op_error:
                        batch_failed += 1
                        self.failed_operations += 1
                        self.logger.exception(
                            "批次操作失败: %s",
                            description,
                            module="database_batch_manager",
                            instance_name=self.instance_name,
                            batch=self.current_batch,
                            operation_index=index,
                            operation_type=operation_type,
                            error=str(op_error),
                        )
                        continue

                    batch_successful += 1
                    self.successful_operations += 1

        except Exception as e:
            self.logger.exception(
                "批次 %s 提交失败",
                self.current_batch,
                module="database_batch_manager",
                instance_name=self.instance_name,
                batch_size=batch_size,
                error=str(e),
            )

            db.session.rollback()

            return False
        else:
            if batch_failed:
                self.logger.warning(
                    "批次 %s 部分成功",
                    self.current_batch,
                    module="database_batch_manager",
                    instance_name=self.instance_name,
                    successful_ops=batch_successful,
                    failed_ops=batch_failed,
                )
                return False

            self.logger.info(
                "批次 %s 提交成功",
                self.current_batch,
                module="database_batch_manager",
                instance_name=self.instance_name,
                successful_ops=batch_successful,
                failed_ops=0,
            )
            return True

    def flush_remaining(self) -> bool:
        """提交剩余的所有操作.

        在批量操作结束时调用,提交队列中剩余的未达到批次大小的操作.

        Returns:
            提交成功返回 True,失败返回 False.如果队列为空返回 True.

        Example:
            >>> manager.add_operation('add', user)  # 只有1个操作
            >>> manager.flush_remaining()  # 提交剩余操作
            True

        """
        if self.pending_operations:
            self.logger.info(
                "提交剩余操作",
                module="database_batch_manager",
                instance_name=self.instance_name,
                remaining_operations=len(self.pending_operations),
            )
            return self.commit_batch()
        return True

    def rollback(self) -> None:
        """回滚所有未提交的操作.

        回滚当前事务并清空待处理队列.通常在异常情况下调用.

        Returns:
            None.

        Example:
            >>> try:
            ...     manager.add_operation('add', user)
            ... except Exception:
            ...     manager.rollback()

        """
        try:
            if self.pending_operations:
                self.logger.warning(
                    "回滚未提交的操作",
                    module="database_batch_manager",
                    instance_name=self.instance_name,
                    pending_operations=len(self.pending_operations),
                )

            db.session.rollback()
            self.pending_operations.clear()

        except Exception as e:
            self.logger.exception(
                "回滚操作失败",
                module="database_batch_manager",
                instance_name=self.instance_name,
                error=str(e),
            )

    def get_statistics(self) -> dict[str, int]:
        """获取批量操作统计信息.

        Returns:
            包含统计信息的字典,格式如下:
            {
                'total_operations': 100,        # 总操作数
                'successful_operations': 95,    # 成功操作数
                'failed_operations': 5,         # 失败操作数
                'batches_processed': 2,         # 已处理批次数
                'pending_operations': 10,       # 待处理操作数
                'batch_size': 50               # 批次大小
            }

        Example:
            >>> stats = manager.get_statistics()
            >>> print(f"成功率: {stats['successful_operations'] / stats['total_operations']}")

        """
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "batches_processed": self.current_batch,
            "pending_operations": len(self.pending_operations),
            "batch_size": self.batch_size,
        }

    def __enter__(self) -> "DatabaseBatchManager":
        """上下文管理器入口.

        Returns:
            返回自身实例,支持 with 语句.

        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """上下文管理器出口.

        正常退出时提交剩余操作,异常退出时回滚操作.

        Args:
            exc_type: 异常类型.
            exc_val: 异常值.
            exc_tb: 异常追踪信息.

        Returns:
            None.

        """
        if exc_type is None:
            # 正常退出,提交剩余操作
            self.flush_remaining()
        else:
            # 异常退出,回滚操作
            self.rollback()

        # 记录最终统计
        stats = self.get_statistics()
        self.logger.info(
            "批量管理器操作完成",
            module="database_batch_manager",
            instance_name=self.instance_name,
            **stats,
        )
        return None
