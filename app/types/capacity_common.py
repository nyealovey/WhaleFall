"""容量统计通用类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CapacityInstanceRef:
    """容量统计项中的实例元信息."""

    id: int
    name: str
    db_type: str

