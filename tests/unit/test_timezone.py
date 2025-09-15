#!/usr/bin/env python3

"""
测试时区转换功能
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

import pytz

from app import create_app
from app.models.log import Log
from app.utils.timezone import format_china_time


def test_timezone():
    """测试时区转换功能"""
    app = create_app()

    with app.app_context():
        print("=== 测试时区转换功能 ===")

        # 1. 测试数据库中的时间
        latest_log = Log.query.order_by(Log.created_at.desc()).first()
        if latest_log:
            print(f"数据库中的时间: {latest_log.created_at}")
            print(f"时区信息: {latest_log.created_at.tzinfo}")

            # 测试时区转换
            china_time = format_china_time(latest_log.created_at)
            print(f"转换为东八区时间: {china_time}")

        # 2. 测试UTC时间转换
        utc_time = datetime.utcnow()
        print(f"\n当前UTC时间: {utc_time}")
        print(f"时区信息: {utc_time.tzinfo}")

        china_time = format_china_time(utc_time)
        print(f"转换为东八区时间: {china_time}")

        # 3. 测试带时区的UTC时间
        from zoneinfo import ZoneInfo
        utc_time_with_tz = utc_time.replace(tzinfo=ZoneInfo("UTC"))
        print(f"\n带时区的UTC时间: {utc_time_with_tz}")
        print(f"时区信息: {utc_time_with_tz.tzinfo}")

        china_time = format_china_time(utc_time_with_tz)
        print(f"转换为东八区时间: {china_time}")


if __name__ == "__main__":
    test_timezone()
