#!/usr/bin/env python3
"""
显示默认管理员密码的脚本
用于在忘记密码时查看当前管理员账户信息
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.models.user import User
from app.utils.structlog_config import get_system_logger

def show_admin_password():
    """显示管理员密码信息"""
    app = create_app()
    
    with app.app_context():
        system_logger = get_system_logger()
        
        # 查找管理员用户
        admin = User.query.filter_by(username="admin").first()
        
        if not admin:
            return
        
        
        # 检查是否使用环境变量密码
        env_password = os.getenv('DEFAULT_ADMIN_PASSWORD')
        if env_password:
        else:
        

if __name__ == "__main__":
    show_admin_password()
