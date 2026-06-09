"""告警事件候选 DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, cast

MB_PER_GB = 1024


@dataclass(frozen=True, slots=True)
class DatabaseCapacityGrowthCandidate:
    """数据库容量增长告警候选."""

    instance_id: int
    instance_name: object
    database_name: str
    current_size_mb: int
    baseline_size_mb: int
    size_change_mb: int
    size_change_percent: float
    baseline_collected_date: date
    baseline_age_days: int
    current_collected_date: date

    @classmethod
    def from_row(
        cls,
        *,
        row: dict[str, object],
        baseline: object | None,
        percent_threshold: int,
        absolute_gb_threshold: int,
        lookback_days: int,
    ) -> DatabaseCapacityGrowthCandidate | None:
        raw_database_name = row.get("database_name")
        current_collected_date = row.get("collected_date")
        raw_instance_id = row.get("instance_id")
        raw_size_mb = row.get("size_mb")
        if (
            not isinstance(raw_database_name, str)
            or not raw_database_name.strip()
            or current_collected_date is None
            or raw_instance_id is None
            or raw_size_mb is None
            or baseline is None
        ):
            return None

        instance_id = int(cast("int | str", raw_instance_id))
        database_name = raw_database_name.strip()
        current_date = cast(date, current_collected_date)
        baseline_row = cast(Any, baseline)
        baseline_size_mb = int(cast("int | str", baseline_row.size_mb))
        baseline_collected_date = cast(date, baseline_row.collected_date)
        if baseline_size_mb <= 0:
            return None

        current_size_mb = int(cast("int | str", raw_size_mb))
        size_change_mb = current_size_mb - baseline_size_mb
        if size_change_mb <= 0:
            return None

        size_change_percent = round((size_change_mb / baseline_size_mb) * 100, 2)
        size_change_gb = size_change_mb / MB_PER_GB
        if size_change_percent < int(percent_threshold) or size_change_gb < int(absolute_gb_threshold):
            return None

        baseline_age_days = (current_date - baseline_collected_date).days
        if baseline_age_days < 1 or baseline_age_days > lookback_days:
            return None

        return cls(
            instance_id=instance_id,
            instance_name=row.get("instance_name"),
            database_name=database_name,
            current_size_mb=current_size_mb,
            baseline_size_mb=baseline_size_mb,
            size_change_mb=size_change_mb,
            size_change_percent=size_change_percent,
            baseline_collected_date=baseline_collected_date,
            baseline_age_days=baseline_age_days,
            current_collected_date=current_date,
        )

    @property
    def dedupe_key(self) -> str:
        return f"{self.instance_id}:{self.database_name}"

    def payload_json(self) -> dict[str, object]:
        return {
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "database_name": self.database_name,
            "current_size_mb": self.current_size_mb,
            "baseline_size_mb": self.baseline_size_mb,
            "size_change_mb": self.size_change_mb,
            "size_change_percent": self.size_change_percent,
            "baseline_collected_date": self.baseline_collected_date.isoformat(),
            "baseline_age_days": self.baseline_age_days,
            "current_collected_date": self.current_collected_date.isoformat(),
        }
