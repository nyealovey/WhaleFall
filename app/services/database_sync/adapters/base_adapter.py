from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from app.models.instance import Instance
from app.utils.structlog_config import get_system_logger


class BaseCapacityAdapter:
    """容量同步适配器基类，定义库存与容量采集接口。"""

    def __init__(self) -> None:
        self.logger = get_system_logger()

    def fetch_inventory(self, instance: Instance, connection) -> List[dict]:
        """列出实例当前的数据库/表空间。"""
        raise NotImplementedError

    def fetch_capacity(
        self,
        instance: Instance,
        connection,
        target_databases: Optional[Sequence[str]] = None,
    ) -> List[dict]:
        """采集指定数据库的容量数据。"""
        raise NotImplementedError

    @staticmethod
    def _normalize_targets(target_databases: Optional[Iterable[str]]) -> Optional[set[str]]:
        if target_databases is None:
            return None
        normalized = {str(name).strip() for name in target_databases if str(name).strip()}
        return normalized or set()
