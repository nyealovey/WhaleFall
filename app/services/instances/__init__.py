"""实例批量操作服务包."""

from .batch_service import (
    InstanceBatchCreationService,
    InstanceBatchDeletionService,
)

__all__ = [
    "InstanceBatchCreationService",
    "InstanceBatchDeletionService",
]
