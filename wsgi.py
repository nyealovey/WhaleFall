"""
鲸落 - WSGI入口文件
生产环境WSGI服务器入口点
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault("FLASK_APP", "app")
os.environ.setdefault("FLASK_ENV", "production")

# 导入Flask应用
from app import create_app

# 创建Flask应用实例
application = app = create_app()

if __name__ == "__main__":
    # 开发环境直接运行
    application.run(host="0.0.0.0", port=5001, debug=False)
