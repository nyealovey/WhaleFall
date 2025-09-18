from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3

"""
测试日志记录功能
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from app import create_app, db
from app.models.log import Log
from app.utils.logger import log_operation


def test_logging():
    """测试日志记录功能"""
    app = create_app()

    with app.app_context():
        logger.debug("=== 测试日志记录功能 ===")

        # 1. 检查数据库连接
        try:
            db.session.execute(db.text("SELECT 1"))
            logger.debug("✅ 数据库连接正常")
        except Exception:
            logger.debug("❌ 数据库连接失败: {e}")
            return

        # 2. 检查Log表结构
        try:
            logs_count = Log.query.count()
            logger.debug("✅ 当前日志记录数: {logs_count}")
        except Exception:
            logger.debug("❌ 查询日志表失败: {e}")
            return

        # 3. 测试直接创建日志记录
        try:
            test_log = Log(
                level="INFO",
                log_type="test",
                message="测试日志记录",
                module="test",
                details="这是一个测试日志",
                user_id=1,
            )
            db.session.add(test_log)
            db.session.commit()
            logger.debug("✅ 直接创建日志记录成功")
        except Exception:
            logger.debug("❌ 直接创建日志记录失败: {e}")
            db.session.rollback()

        # 4. 测试log_operation函数
        try:
            log_operation("TEST_OPERATION", 1, {"test": "data"})
            logger.debug("✅ log_operation函数调用成功")
        except Exception:
            logger.debug("❌ log_operation函数调用失败: {e}")

        # 5. 检查新增的日志记录
        try:
            new_logs = Log.query.filter(Log.message.like("%测试%")).all()
            logger.debug("✅ 找到 {len(new_logs)} 条测试日志记录")
            for log in new_logs:
                logger.debug("   - ID: {log.id}, 消息: {log.message}, 时间: {log.created_at}")
        except Exception:
            logger.debug("❌ 查询测试日志失败: {e}")


if __name__ == "__main__":
    test_logging()
