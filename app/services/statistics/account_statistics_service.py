"""账户统计服务.

将账户统计页面使用到的统计逻辑拆分为可复用的服务函数.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.errors import SystemError
from app.repositories.account_statistics_repository import AccountStatisticsRepository
from app.utils.structlog_config import log_error


def fetch_summary(*, instance_id: int | None = None, db_type: str | None = None) -> dict[str, int]:
    """获取账户汇总统计信息.

    统计账户总数、活跃数、锁定数、正常数、已删除数,以及关联的实例统计.
    可选择性地只统计指定实例或数据库类型的账户.

    Args:
        instance_id: 可选的实例 ID 筛选.
        db_type: 可选的数据库类型筛选,如 'mysql'、'postgresql'.

    Returns:
        包含账户和实例统计信息的字典,格式如下:
        {
            'total_accounts': 100,       # 账户总数
            'active_accounts': 85,       # 活跃账户数
            'locked_accounts': 10,       # 锁定账户数
            'normal_accounts': 75,       # 正常账户数
            'deleted_accounts': 15,      # 已删除账户数
            'total_instances': 10,       # 实例总数
            'active_instances': 8,       # 活跃实例数
            'disabled_instances': 2,     # 禁用实例数
            'normal_instances': 8,       # 正常实例数
            'deleted_instances': 0       # 已删除实例数
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
        return AccountStatisticsRepository.fetch_summary(instance_id=instance_id, db_type=db_type)
    except Exception as exc:
        log_error("获取账户统计汇总失败", module="account_statistics", exception=exc)
        msg = "获取账户统计汇总失败"
        raise SystemError(msg) from exc


def fetch_db_type_stats() -> dict[str, dict[str, int]]:
    """按数据库类型返回账户统计信息.

    Returns:
        以数据库类型为键的字典,每个值包含该类型的账户统计,格式如下:
        {
            'mysql': {
                'total': 50,
                'active': 45,
                'normal': 40,
                'locked': 5,
                'deleted': 5
            },
            'postgresql': {...},
            ...
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
        return AccountStatisticsRepository.fetch_db_type_stats()
    except Exception as exc:
        log_error("获取数据库类型统计失败", module="account_statistics", exception=exc)
        msg = "获取数据库类型统计失败"
        raise SystemError(msg) from exc


def fetch_classification_stats() -> dict[str, dict[str, Any]]:
    """按账户分类返回统计信息.

    Returns:
        以分类名称为键的字典,每个值包含该分类的统计信息,格式如下:
        {
            'admin': {
                'account_count': 10,
                'color': '#ff0000',
                'display_name': '管理员'
            },
            'readonly': {...},
            ...
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
        return AccountStatisticsRepository.fetch_classification_stats()
    except Exception as exc:
        log_error("获取账户分类统计失败", module="account_statistics", exception=exc)
        msg = "获取账户分类统计失败"
        raise SystemError(msg) from exc


def fetch_classification_overview() -> dict[str, Any]:
    """获取分类账户概览.

    Returns:
        包含分类账户概览的字典,格式如下:
        {
            'total': 100,              # 已分类账户总数
            'auto': 80,                # 自动分类账户数
            'classifications': [...]   # 分类详情列表
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
        return AccountStatisticsRepository.fetch_classification_overview()
    except Exception as exc:
        log_error("获取账户分类概览失败", module="account_statistics", exception=exc)
        msg = "获取账户分类概览失败"
        raise SystemError(msg) from exc


def fetch_rule_match_stats(rule_ids: Sequence[int] | None = None) -> dict[int, int]:
    """统计每条规则所关联的账户数量.

    Args:
        rule_ids: 可选的规则 ID 列表,如果提供则只统计这些规则.

    Returns:
        以规则 ID 为键、账户数量为值的字典,格式如下:
        {
            1: 50,   # 规则 1 关联 50 个账户
            2: 30,   # 规则 2 关联 30 个账户
            ...
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
        return AccountStatisticsRepository.fetch_rule_match_stats(rule_ids)
    except Exception as exc:
        log_error("获取规则匹配统计失败", module="account_statistics", exception=exc)
        msg = "获取规则匹配统计失败"
        raise SystemError(msg) from exc


def build_aggregated_statistics() -> dict[str, Any]:
    """组装账户统计页面的完整数据.

    汇总账户的基本统计、数据库类型分布和分类统计.

    Returns:
        包含完整统计信息的字典,包含 fetch_summary、fetch_db_type_stats
        和 fetch_classification_stats 的所有字段.

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    summary = fetch_summary()
    db_type_stats = fetch_db_type_stats()
    classification_stats = fetch_classification_stats()

    return {
        **summary,
        "database_instances": summary.get("total_instances", 0),
        "db_type_stats": db_type_stats,
        "classification_stats": classification_stats,
    }


def empty_statistics() -> dict[str, Any]:
    """构造空的统计结果.

    Returns:
        所有统计值为 0 或空字典的字典,格式与 build_aggregated_statistics 返回值相同.

    """
    return {
        "total_accounts": 0,
        "active_accounts": 0,
        "locked_accounts": 0,
        "normal_accounts": 0,
        "deleted_accounts": 0,
        "database_instances": 0,
        "total_instances": 0,
        "active_instances": 0,
        "disabled_instances": 0,
        "normal_instances": 0,
        "deleted_instances": 0,
        "db_type_stats": {},
        "classification_stats": {},
    }
