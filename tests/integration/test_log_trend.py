#!/usr/bin/env python3

"""
测试日志趋势数据获取
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

from app import create_app
from app.models.log import Log
from app.routes.dashboard import get_log_trend_data


def test_log_trend():
    """测试日志趋势数据获取"""
    app = create_app()

    with app.app_context():
        print("=== 测试日志趋势数据获取 ===")

        # 1. 检查数据库中的日志记录
        total_logs = Log.query.count()
        print(f"数据库总日志数: {total_logs}")

        # 2. 检查最近的日志记录
        recent_logs = Log.query.order_by(Log.created_at.desc()).limit(5).all()
        print("\n最近的5条日志记录:")
        for log in recent_logs:
            print(f"  - ID: {log.id}, 时间: {log.created_at}, 消息: {log.message}")

        # 3. 测试日志趋势数据获取
        print("\n获取日志趋势数据:")
        trend_data = get_log_trend_data()
        for item in trend_data:
            print(f"  - 日期: {item['date']}, 数量: {item['count']}")

        # 4. 检查今天的日志数量
        from app.utils.timezone import CHINA_TZ, china_to_utc, get_china_today

        today = get_china_today().date()
        start_utc = china_to_utc(datetime.combine(today, datetime.min.time()).replace(tzinfo=CHINA_TZ))
        end_utc = china_to_utc(datetime.combine(today, datetime.max.time()).replace(tzinfo=CHINA_TZ))

        today_count = Log.query.filter(Log.created_at >= start_utc, Log.created_at <= end_utc).count()

        print(f"\n今天({today})的日志数量: {today_count}")
        print(f"UTC时间范围: {start_utc} 到 {end_utc}")


if __name__ == "__main__":
    test_log_trend()
