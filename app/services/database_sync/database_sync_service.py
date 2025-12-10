"""数据库容量同步服务.

该模块提供与历史版本兼容的 `DatabaseSizeCollectorService`,内部委托
`app.services.database_sync` 中的协调器与适配器完成工作.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self
from types import TracebackType

from app.utils.structlog_config import get_system_logger

from .coordinator import CapacitySyncCoordinator

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from app.models.instance import Instance


class DatabaseSizeCollectorService:
    """数据库容量采集服务(兼容包装器).

    提供与历史版本兼容的接口,内部委托给 CapacitySyncCoordinator 实现.
    支持上下文管理器协议,自动管理数据库连接.

    Attributes:
        instance: 数据库实例对象.
        logger: 系统日志记录器.

    Example:
        >>> with DatabaseSizeCollectorService(instance) as collector:
        ...     count = collector.collect_and_save()

    """

    def __init__(self, instance: Instance) -> None:
        """初始化数据库容量采集服务.

        Args:
            instance: 数据库实例对象.

        """
        self.instance = instance
        self.logger = get_system_logger()
        self._coordinator = CapacitySyncCoordinator(instance)

    def __enter__(self) -> Self:
        """进入上下文管理器,建立数据库连接.

        Returns:
            服务实例自身.

        """
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """退出上下文管理器,断开数据库连接.

        Args:
            exc_type: 异常类型.
            exc_val: 异常值.
            exc_tb: 异常追踪信息.

        Returns:
            None: 断开连接后返回 False-equivalent 以继续传播异常.

        """
        self.disconnect()

    # --------------------------------------------------------------------- #
    # 连接管理
    # --------------------------------------------------------------------- #
    def connect(self) -> bool:
        """建立数据库连接.

        Returns:
            连接成功返回 True,失败返回 False.

        """
        return self._coordinator.connect()

    def disconnect(self) -> None:
        """断开数据库连接.

        Returns:
            None: 委托协调器断开连接后返回.

        """
        self._coordinator.disconnect()

    # --------------------------------------------------------------------- #
    # 库存同步
    # --------------------------------------------------------------------- #
    def fetch_databases_metadata(self) -> list[dict]:
        """获取远程数据库清单.

        Returns:
            数据库元数据列表.

        """
        return self._coordinator.fetch_inventory()

    def sync_instance_databases(self, metadata: Iterable[dict]) -> dict:
        """同步数据库清单到本地.

        Args:
            metadata: 数据库元数据列表.

        Returns:
            同步统计信息字典.

        """
        return self._coordinator.sync_instance_databases(metadata)

    def synchronize_database_inventory(self) -> dict:
        """执行完整的库存同步流程.

        Returns:
            同步统计信息字典.

        """
        return self._coordinator.synchronize_inventory()

    # --------------------------------------------------------------------- #
    # 容量采集
    # --------------------------------------------------------------------- #
    def collect_database_sizes(
        self,
        target_databases: Sequence[str] | None = None,
    ) -> list[dict]:
        """采集数据库容量数据.

        Args:
            target_databases: 目标数据库名称列表,为 None 时采集所有数据库.

        Returns:
            容量数据列表.

        """
        return self._coordinator.collect_capacity(target_databases)

    # --------------------------------------------------------------------- #
    # 数据持久化
    # --------------------------------------------------------------------- #
    def save_collected_data(self, data: Iterable[dict]) -> int:
        """保存数据库容量统计数据.

        Args:
            data: 容量数据列表.

        Returns:
            保存的记录数.

        """
        return self._coordinator.save_database_stats(data)

    def save_instance_size_stat(self, data: Iterable[dict]) -> bool:
        """保存实例容量统计数据.

        Args:
            data: 容量数据列表.

        Returns:
            保存成功返回 True,失败返回 False.

        """
        return self._coordinator.save_instance_stats(data)

    def update_instance_total_size(self) -> bool:
        """更新实例总容量.

        Returns:
            更新成功返回 True,失败返回 False.

        """
        return self._coordinator.update_instance_total_size()

    # --------------------------------------------------------------------- #
    # 综合流程
    # --------------------------------------------------------------------- #
    def collect_and_save(self) -> int:
        """执行完整的容量采集和保存流程.

        Returns:
            保存的记录数.

        """
        return self._coordinator.collect_and_save()


def collect_all_instances_database_sizes() -> dict[str, Any]:
    """采集所有活跃实例的数据库容量数据.

    遍历所有活跃实例,依次执行容量采集和保存操作.

    Returns:
        采集结果统计字典,包含以下字段:
        {
            'status': 'success' 或 'partial_success',
            'total_instances': 总实例数,
            'processed_instances': 成功处理的实例数,
            'total_records': 保存的记录总数,
            'errors': 错误信息列表
        }

    """
    from app.models.instance import Instance

    logger = get_system_logger()
    logger.info("开始采集所有实例的数据库容量数据...")

    instances = Instance.query.filter_by(is_active=True).all()
    if not instances:
        logger.warning("没有找到活跃的数据库实例")
        return {
            "status": "success",
            "total_instances": 0,
            "processed_instances": 0,
            "total_records": 0,
            "errors": [],
        }

    results: dict[str, Any] = {
        "status": "success",
        "total_instances": len(instances),
        "processed_instances": 0,
        "total_records": 0,
        "errors": [],
    }

    for instance in instances:
        try:
            logger.info(
                "开始采集实例数据库容量",
                instance=instance.name,
                db_type=instance.db_type,
            )
            with DatabaseSizeCollectorService(instance) as collector:
                saved_count = collector.collect_and_save()
                results["processed_instances"] += 1
                results["total_records"] += saved_count
                logger.info(
                    "实例容量采集完成",
                    instance=instance.name,
                    saved_count=saved_count,
                )
        except Exception as exc:
            error_msg = f"实例 {instance.name} 采集失败: {exc}"
            logger.error(
                "capacity_collection_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            results["errors"].append(error_msg)

    if results["errors"]:
        results["status"] = "partial_success"

    logger.info(
        "数据库容量采集完成",
        processed_instances=results["processed_instances"],
        total_instances=results["total_instances"],
        total_records=results["total_records"],
    )
    return results
