"""统一搜索筛选器配置.

将所有纯枚举/常量型筛选项集中到此处,避免分散定义造成维护困难.
动态数据请使用 ``app.utils.query_filter_utils`` 中的查询方法.
"""

from __future__ import annotations

from typing import Final

from app.constants.sync_constants import SyncConstants

# 数据库类型(默认配置,用作兜底或静态展示)
DATABASE_TYPES: Final[list[dict[str, str]]] = [
    {"name": "mysql", "display_name": "MySQL", "icon": "fa-database", "color": "primary"},
    {"name": "postgresql", "display_name": "PostgreSQL", "icon": "fa-database", "color": "info"},
    {"name": "sqlserver", "display_name": "SQL Server", "icon": "fa-server", "color": "warning"},
    {"name": "oracle", "display_name": "Oracle", "icon": "fa-database", "color": "danger"},
]

# 凭据类型
CREDENTIAL_TYPES: Final[list[dict[str, str]]] = [
    {"value": "database", "label": "数据库凭据"},
    {"value": "api", "label": "API 凭据"},
    {"value": "ssh", "label": "SSH 凭据"},
]

# 同步操作方式(使用已有常量生成,避免重复维护)
SYNC_TYPES: Final[list[dict[str, str]]] = [
    {"value": item["value"], "label": item["label"]}
    for item in SyncConstants.get_all_operation_types()
]

# 同步分类
SYNC_CATEGORIES: Final[list[dict[str, str]]] = [
    {"value": item["value"], "label": item["label"]}
    for item in SyncConstants.get_all_categories()
]

# 日志级别
LOG_LEVELS: Final[list[dict[str, str]]] = [
    {"value": level, "label": level}
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
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
    {"value": "active", "label": "激活"},
    {"value": "inactive", "label": "禁用"},
]

# 同步任务状态筛选
STATUS_SYNC_OPTIONS: Final[list[dict[str, str]]] = [
    {"value": "", "label": "全部状态"},
    {"value": "running", "label": "运行中"},
    {"value": "completed", "label": "已完成"},
    {"value": "failed", "label": "失败"},
    {"value": "cancelled", "label": "已取消"},
]

# 默认分页大小(供表单/路由使用)
PAGINATION_SIZES: Final[list[int]] = [10, 20, 50, 100]
