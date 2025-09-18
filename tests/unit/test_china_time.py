from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3

"""
测试东八区时间函数
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

import pytz

from app.utils.timezone import get_china_date, get_china_time, get_china_today


def test_china_time():
    """测试东八区时间函数"""
    logger.debug("=== 测试东八区时间函数 ===")

    # 1. 当前UTC时间
    utc_now = datetime.utcnow()
    logger.debug("当前UTC时间: {utc_now}")

    # 2. 当前东八区时间
    china_now = get_china_time()
    logger.debug("当前东八区时间: {china_now}")

    # 3. 东八区日期
    china_date = get_china_date()
    logger.debug("东八区日期: {china_date}")

    # 4. 东八区今天的开始时间（UTC）
    china_today_utc = get_china_today()
    logger.debug("东八区今天的开始时间（UTC）: {china_today_utc}")

    # 5. 手动计算东八区时间
    china_tz = pytz.timezone("Asia/Shanghai")
    manual_china_time = datetime.now(china_tz)
    logger.debug("手动计算的东八区时间: {manual_china_time}")
    logger.debug("手动计算的东八区日期: {manual_china_time.date()}")


if __name__ == "__main__":
    test_china_time()
