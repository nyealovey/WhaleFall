"""
鲸落 - 容量同步适配器模块
提供容量相关采集与发现服务的封装
"""

from .database_size_collector_service import DatabaseSizeCollectorService

__all__ = [
    "DatabaseSizeCollectorService",
]
