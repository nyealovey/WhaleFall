"""账户分类每日统计定时任务."""

from __future__ import annotations

import time
from typing import Any

from app import create_app, db
from app.services.account_classification.daily_stats_service import AccountClassificationDailyStatsService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def calculate_account_classification_daily_stats() -> dict[str, Any]:
    """计算并写入账户分类每日统计(规则命中数 + 分类去重账号数)."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        started_at = time.perf_counter()

        sync_logger.info(
            "开始计算账户分类每日统计",
            module="account_classification_daily_stats",
        )

        try:
            result = AccountClassificationDailyStatsService().compute_and_persist()
            db.session.commit()
        except Exception as exc:  # noqa: BLE001 - scheduler task boundary
            db.session.rollback()
            sync_logger.exception(
                "账户分类每日统计计算失败",
                module="account_classification_daily_stats",
                error=str(exc),
            )
            return {
                "success": False,
                "message": f"账户分类每日统计计算失败: {exc!s}",
                "error": str(exc),
            }

        sync_logger.info(
            "账户分类每日统计计算完成",
            module="account_classification_daily_stats",
            stat_date=result.stat_date.isoformat(),
            computed_at=time_utils.format_china_time(result.computed_at),
            rules_count=result.rules_count,
            accounts_count=result.accounts_count,
            rule_match_rows=result.rule_match_rows,
            classification_match_rows=result.classification_match_rows,
            duration_seconds=round(time.perf_counter() - started_at, 2),
        )

        return {
            "success": True,
            "message": "账户分类每日统计计算完成",
            "stat_date": result.stat_date.isoformat(),
            "computed_at": result.computed_at.isoformat(),
            "rules_count": result.rules_count,
            "accounts_count": result.accounts_count,
            "rule_match_rows": result.rule_match_rows,
            "classification_match_rows": result.classification_match_rows,
        }

