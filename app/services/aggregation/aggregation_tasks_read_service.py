"""统计聚合 tasks 读能力 Service.

职责:
- 为 `app/tasks/capacity_aggregation_tasks.py` 提供最小读能力,避免 tasks 直接 `.query/db.session.query`
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import desc, func

from app import db
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.repositories.filter_options_repository import FilterOptionsRepository


@dataclass(frozen=True, slots=True)
class AggregationStatus:
    """聚合状态数据."""

    latest_aggregation: datetime | None
    aggregation_counts: dict[str, int]
    total_instances: int


class AggregationTasksReadService:
    """统计聚合任务读取服务."""

    def __init__(self, instances_repository: FilterOptionsRepository | None = None) -> None:
        self._instances_repository = instances_repository or FilterOptionsRepository()

    def list_active_instances(self) -> list[Instance]:
        """获取启用的实例列表."""
        return self._instances_repository.list_active_instances()

    @staticmethod
    def get_instance_by_id(instance_id: int) -> Instance | None:
        """按 ID 获取实例(可为空)."""
        return Instance.query.get(instance_id)

    @staticmethod
    def count_active_instances() -> int:
        """统计启用实例数量."""
        return int(Instance.query.filter_by(is_active=True).count() or 0)

    @staticmethod
    def has_aggregation_for_period(*, period_type: str, period_start: date) -> bool:
        """判断某周期聚合是否已存在(实例级 + 数据库级均已落库)."""
        db_exists = (
            db.session.query(DatabaseSizeAggregation.id)
            .filter(
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start == period_start,
            )
            .limit(1)
            .first()
            is not None
        )
        if not db_exists:
            return False
        return (
            db.session.query(InstanceSizeAggregation.id)
            .filter(
                InstanceSizeAggregation.period_type == period_type,
                InstanceSizeAggregation.period_start == period_start,
            )
            .limit(1)
            .first()
            is not None
        )

    def get_status(self) -> AggregationStatus:
        """获取聚合状态."""
        latest = DatabaseSizeAggregation.query.order_by(desc(DatabaseSizeAggregation.calculated_at)).first()
        latest_time = latest.calculated_at if latest else None

        rows = (
            db.session.query(
                DatabaseSizeAggregation.period_type,
                func.count(DatabaseSizeAggregation.id).label("count"),
            )
            .group_by(DatabaseSizeAggregation.period_type)
            .all()
        )
        counts: dict[str, int] = {str(row.period_type): int(row.count) for row in rows}
        return AggregationStatus(
            latest_aggregation=latest_time,
            aggregation_counts=counts,
            total_instances=self.count_active_instances(),
        )

