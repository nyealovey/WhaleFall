"""统一搜索筛选器配置.

将所有纯枚举/常量型筛选项集中到此处,避免分散定义造成维护困难.
动态数据请使用 ``app.services.common.filter_options_service.FilterOptionsService``.
"""

from __future__ import annotations

from typing import Final

from app.core.constants.database_types import DatabaseType
from app.core.constants.sync_constants import SyncCategory, SyncConstants, SyncOperationType

DATABASE_TYPES: Final[list[dict[str, str]]] = [
    {
        "name": db_type,
        "display_name": DatabaseType.DISPLAY_NAMES.get(db_type, db_type),
        "icon": DatabaseType.ICONS.get(db_type, "fa-database"),
        "color": DatabaseType.COLORS.get(db_type, "primary"),
    }
    for db_type in DatabaseType.RELATIONAL
]

# 凭据类型
CREDENTIAL_TYPES: Final[list[dict[str, str]]] = [
    {"value": "database", "label": "数据库凭据"},
    {"value": "api", "label": "API 凭据"},
    {"value": "ssh", "label": "SSH 凭据"},
]

SYNC_TYPES: Final[list[dict[str, str]]] = [
    {
        "value": op_type.value,
        "label": SyncConstants.OPERATION_TYPE_DISPLAY.get(op_type, op_type.value),
    }
    for op_type in SyncOperationType
]

# 同步分类
SYNC_CATEGORIES: Final[list[dict[str, str]]] = [
    {
        "value": category.value,
        "label": SyncConstants.CATEGORY_DISPLAY.get(category, category.value),
    }
    for category in SyncCategory
]

# 日志级别
LOG_LEVELS: Final[list[dict[str, str]]] = [
    {"value": level, "label": level} for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
]

# 时间范围
TIME_RANGES: Final[list[dict[str, str]]] = [
    {"value": "1h", "label": "最近1小时"},
    {"value": "1d", "label": "最近1天"},
    {"value": "1w", "label": "最近1周"},
    {"value": "1m", "label": "最近1月"},
]

# 统计周期
PERIOD_TYPES: Final[list[dict[str, str]]] = [
    {"value": "daily", "label": "日统计"},
    {"value": "weekly", "label": "周统计"},
    {"value": "monthly", "label": "月统计"},
    {"value": "quarterly", "label": "季统计"},
]

# 通用激活状态筛选
STATUS_ACTIVE_OPTIONS: Final[list[dict[str, str]]] = [
    {"value": "all", "label": "全部状态"},
    {"value": "active", "label": "启用"},
    {"value": "inactive", "label": "停用"},
]

# 同步任务状态筛选
STATUS_SYNC_OPTIONS: Final[list[dict[str, str]]] = [
    {"value": "", "label": "全部状态"},
    {"value": "pending", "label": "等待中"},
    {"value": "running", "label": "运行中"},
    {"value": "paused", "label": "已暂停"},
    {"value": "completed", "label": "已完成"},
    {"value": "failed", "label": "失败"},
    {"value": "cancelled", "label": "已取消"},
]

# TaskRun(运行中心)状态筛选
STATUS_TASK_RUN_OPTIONS: Final[list[dict[str, str]]] = [
    {"value": "", "label": "全部状态"},
    {"value": "running", "label": "运行中"},
    {"value": "completed", "label": "已完成"},
    {"value": "failed", "label": "失败"},
    {"value": "cancelled", "label": "已取消"},
]

# TaskRun(运行中心)触发来源筛选
TASK_RUN_TRIGGER_SOURCES: Final[list[dict[str, str]]] = [
    {"value": "", "label": "全部来源"},
    {"value": "scheduled", "label": "定时任务"},
    {"value": "manual", "label": "手动触发"},
    {"value": "api", "label": "API"},
]

# TaskRun(运行中心)任务分类筛选
TASK_RUN_CATEGORIES: Final[list[dict[str, str]]] = [
    {"value": "", "label": "全部分类"},
    {"value": "account", "label": "账户"},
    {"value": "capacity", "label": "容量"},
    {"value": "aggregation", "label": "聚合"},
    {"value": "classification", "label": "分类"},
    {"value": "other", "label": "其他"},
]

PAGINATION_SIZES: Final[list[int]] = [10, 20, 50, 100]
