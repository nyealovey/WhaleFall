from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3

"""
测试数据库连接和迁移
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault("FLASK_APP", "app")
os.environ.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{project_root}/userdata/whalefall_dev.db")

from app import create_app, db


def main():
    logger.debug("🔧 测试数据库连接...")

    # 创建Flask应用
    app = create_app()

    with app.app_context():
        try:
            # 创建数据库文件
            db.create_all()
            logger.debug("✅ 数据库创建成功")

            # 检查数据库文件
            db_path = project_root / "userdata" / "whalefall_dev.db"
            if db_path.exists():
                logger.debug("✅ 数据库文件存在: {db_path}")
                logger.debug("📊 文件大小: {db_path.stat().st_size} bytes")
            else:
                logger.debug("❌ 数据库文件不存在")

        except Exception:
            logger.debug("❌ 数据库创建失败: {e}")
            return False

    return True


if __name__ == "__main__":
    main()
