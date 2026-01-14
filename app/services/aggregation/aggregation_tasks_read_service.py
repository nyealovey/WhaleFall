"""统计聚合 tasks 读能力 Service.

职责:
- 为 `app/tasks/capacity_aggregation_tasks.py` 提供最小读能力,避免 tasks 直接查库/ORM 查询
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.models.instance import Instance
from app.repositories.aggregation_repository import AggregationRepository
from app.repositories.filter_options_repository import FilterOptionsRepository
from app.repositories.instances_repository import InstancesRepository


@dataclass(frozen=True, slots=True)
class AggregationStatus:
    """聚合状态数据."""

    latest_aggregation: datetime | None
    aggregation_counts: dict[str, int]
    total_instances: int


class AggregationTasksReadService:
    """统计聚合任务读取服务."""

    def __init__(
        self,
        instances_repository: FilterOptionsRepository | None = None,
        aggregation_repository: AggregationRepository | None = None,
        instances_core_repository: InstancesRepository | None = None,
    ) -> None:
        """初始化统计聚合任务读取服务."""
        self._instances_repository = instances_repository or FilterOptionsRepository()
        self._aggregation_repository = aggregation_repository or AggregationRepository()
        self._instances_core_repository = instances_core_repository or InstancesRepository()

    def list_active_instances(self) -> list[Instance]:
        """获取启用的实例列表."""
        return self._instances_repository.list_active_instances()

    def get_instance_by_id(self, instance_id: int) -> Instance | None:
        """按 ID 获取实例(可为空)."""
        return self._instances_core_repository.get_instance(instance_id)

    def count_active_instances(self) -> int:
        """统计启用实例数量."""
        return self._instances_core_repository.count_active_instances()

    def has_aggregation_for_period(self, *, period_type: str, period_start: date) -> bool:
        """判断某周期聚合是否已完成(覆盖全部活跃实例)."""
        expected_instances = self.count_active_instances()
        if expected_instances <= 0:
            return False

        database_aggregated_instances = self._aggregation_repository.count_active_instances_with_database_size_aggregation(
            period_type=period_type,
            period_start=period_start,
        )
        instance_aggregated_instances = self._aggregation_repository.count_active_instances_with_instance_size_aggregation(
            period_type=period_type,
            period_start=period_start,
        )
        return (
            database_aggregated_instances >= expected_instances
            and instance_aggregated_instances >= expected_instances
        )

    def get_status(self) -> AggregationStatus:
        """获取聚合状态."""
        latest_time = self._aggregation_repository.fetch_latest_aggregation_time()
        counts = self._aggregation_repository.fetch_aggregation_counts()
        return AggregationStatus(
            latest_aggregation=latest_time,
            aggregation_counts=counts,
            total_instances=self._instances_core_repository.count_active_instances(),
        )
