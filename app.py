"""
鲸落 - 本地开发环境启动文件
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault("FLASK_APP", "app")
os.environ.setdefault("FLASK_ENV", "development")

# 导入Flask应用
from app import create_app  # noqa: E402


def main() -> None:
    """主函数"""
    # 创建Flask应用
    app = create_app(init_scheduler_on_start=True)

    # 获取配置
    host = os.environ.get("FLASK_HOST", "0.0.0.0")  # 容器内必须使用0.0.0.0
    port = int(os.environ.get("FLASK_PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"

    # 配置日志
    from app.utils.structlog_config import get_system_logger

    logger = get_system_logger()

    # 检查并创建管理员用户
    with app.app_context():
        from app.models.user import User
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User.create_admin()

    logger.info("=" * 50)
    logger.info("🐟 鲸落 - 本地开发环境")
    logger.info("=" * 50)
    logger.info(f"🌐 访问地址: http://{host}:{port}")
    logger.info("🔑 默认登录: admin/[随机密码]")
    logger.info(f"📊 管理界面: http://{host}:{port}/admin")
    logger.info(f"🔧 调试模式: {'开启' if debug else '关闭'}")
    logger.info("=" * 50)
    logger.info("💡 查看管理员密码: python scripts/show_admin_password.py")
    logger.info("💡 重置管理员密码: python scripts/reset_admin_password.py")
    logger.info("=" * 50)
    logger.info("按 Ctrl+C 停止服务器")
    logger.info("=" * 50)

    # 启动Flask应用
    # 在debug模式下禁用reloader以避免重复启动调度器
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
