"""
泰摸鱼吧 - 本地开发环境启动文件
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
from app import create_app


def main():
    """主函数"""
    # 创建Flask应用
    app = create_app()

    # 获取配置
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"

    print("=" * 50)
    print("🐟 泰摸鱼吧 - 本地开发环境")
    print("=" * 50)
    print(f"🌐 访问地址: http://{host}:{port}")
    print("🔑 默认登录: admin/Admin123!")
    print(f"📊 管理界面: http://{host}:{port}/admin")
    print(f"🔧 调试模式: {'开启' if debug else '关闭'}")
    print("=" * 50)
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)

    # 启动Flask应用
    # 在debug模式下禁用reloader以避免重复启动调度器
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
