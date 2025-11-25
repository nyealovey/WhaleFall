"""
鲸落 - 数据库批量操作管理器
提供高效的批量提交机制，优化大量数据处理性能
"""

from typing import Any

import structlog

from app import db


class DatabaseBatchManager:
    """数据库批量操作管理器。

    负责管理数据库操作的批量提交，提高性能并确保事务一致性。
    支持自动批量提交、手动提交和回滚操作，适用于大量数据处理场景。

    Attributes:
        batch_size: 批次大小，达到此数量时自动提交。
        logger: 结构化日志记录器。
        instance_name: 实例名称，用于日志记录。
        current_batch: 当前批次编号。
        total_operations: 总操作数。
        successful_operations: 成功操作数。
        failed_operations: 失败操作数。
        pending_operations: 待提交的操作队列。

    Example:
        >>> with DatabaseBatchManager(batch_size=100) as manager:
        ...     for entity in entities:
        ...         manager.add_operation('add', entity, 'Add user')
        ...     # 自动提交剩余操作
    """

    def __init__(self, batch_size: int = 100, logger: Any | None = None, instance_name: str = ""):
        """初始化批量管理器。

        Args:
            batch_size: 批次大小，默认 100。达到此数量时自动提交。
            logger: 日志记录器，默认使用 structlog。
            instance_name: 实例名称，用于日志记录和追踪。
        """
        self.batch_size = batch_size
        self.logger = logger or structlog.get_logger()
        self.instance_name = instance_name

        # 批次计数器
        self.current_batch = 0
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0

        # 操作队列
        self.pending_operations = []

        self.logger.info(
            "初始化数据库批量管理器",
            module="database_batch_manager",
            instance_name=instance_name,
            batch_size=batch_size,
        )

    def add_operation(self, operation_type: str, entity: Any, description: str = "") -> None:
        """添加数据库操作到批次队列。

        将操作添加到待处理队列，当队列达到批次大小时自动提交。

        Args:
            operation_type: 操作类型，可选值：'add'（新增）、'update'（更新）、'delete'（删除）。
            entity: 数据库实体对象，必须是 SQLAlchemy 模型实例。
            description: 操作描述，用于日志记录和错误追踪。

        Example:
            >>> manager.add_operation('add', user, 'Add new user')
            >>> manager.add_operation('update', user, 'Update user status')
        """
        self.pending_operations.append({"type": operation_type, "entity": entity, "description": description})

        self.total_operations += 1

        # 如果达到批次大小，自动提交
        if len(self.pending_operations) >= self.batch_size:
            self.commit_batch()

    def commit_batch(self) -> bool:
        """提交当前批次的所有操作。

        执行队列中的所有操作并提交事务。如果任何操作失败，
        记录错误但继续处理其他操作。如果提交失败，回滚整个批次。

        Returns:
            提交成功返回 True，失败返回 False。

        Example:
            >>> manager.add_operation('add', user1)
            >>> manager.add_operation('add', user2)
            >>> success = manager.commit_batch()
        """
        if not self.pending_operations:
            return True

        self.current_batch += 1
        batch_size = len(self.pending_operations)

        try:
            self.logger.info(
                "开始提交批次 %s",
                self.current_batch,
                module="database_batch_manager",
                instance_name=self.instance_name,
                batch_size=batch_size,
                total_operations=self.total_operations,
            )

            # 执行所有操作
            for operation in self.pending_operations:
                try:
                    if operation["type"] == "add":
                        db.session.add(operation["entity"])
                    elif operation["type"] == "update":
                        # 对于更新操作，实体已经在session中，只需要确保修改被追踪
                        db.session.merge(operation["entity"])
                    elif operation["type"] == "delete":
                        db.session.delete(operation["entity"])

                    self.successful_operations += 1

                except Exception as op_error:
                    self.failed_operations += 1
                    self.logger.error(
                        "批次操作失败: %s",
                        operation["description"],
                        module="database_batch_manager",
                        instance_name=self.instance_name,
                        error=str(op_error),
                    )
                    # 继续处理其他操作，不因单个失败而停止

            # 提交事务
            db.session.commit()

            self.logger.info(
                "批次 %s 提交成功",
                self.current_batch,
                module="database_batch_manager",
                instance_name=self.instance_name,
                successful_ops=batch_size - (self.failed_operations - (self.successful_operations - batch_size)),
                failed_ops=self.failed_operations - (self.successful_operations - batch_size),
            )

            # 清空当前批次
            self.pending_operations.clear()
            return True

        except Exception as e:
            self.logger.error(
                "批次 %s 提交失败",
                self.current_batch,
                module="database_batch_manager",
                instance_name=self.instance_name,
                batch_size=batch_size,
                error=str(e),
            )

            # 回滚当前事务
            db.session.rollback()

            # 清空失败的批次
            self.pending_operations.clear()
            return False

    def flush_remaining(self) -> bool:
        """提交剩余的所有操作。

        在批量操作结束时调用，提交队列中剩余的未达到批次大小的操作。

        Returns:
            提交成功返回 True，失败返回 False。如果队列为空返回 True。

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
        """回滚所有未提交的操作。

        回滚当前事务并清空待处理队列。通常在异常情况下调用。

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
            self.logger.error(
                "回滚操作失败", module="database_batch_manager", instance_name=self.instance_name, error=str(e)
            )

    def get_statistics(self) -> dict:
        """获取批量操作统计信息。

        Returns:
            包含统计信息的字典，格式如下：
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

    def __enter__(self):
        """上下文管理器入口。

        Returns:
            返回自身实例，支持 with 语句。
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:  # noqa: ANN401
        """上下文管理器出口。

        正常退出时提交剩余操作，异常退出时回滚操作。

        Args:
            exc_type: 异常类型。
            exc_val: 异常值。
            exc_tb: 异常追踪信息。
        """
        if exc_type is None:
            # 正常退出，提交剩余操作
            self.flush_remaining()
        else:
            # 异常退出，回滚操作
            self.rollback()

        # 记录最终统计
        stats = self.get_statistics()
        self.logger.info(
            "批量管理器操作完成", module="database_batch_manager", instance_name=self.instance_name, **stats
        )
