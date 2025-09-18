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
            print("❌ 未找到管理员用户")
            return
        
        print(f"\n{'='*60}")
        print(f"🔐 管理员账户信息")
        print(f"{'='*60}")
        print(f"用户名: {admin.username}")
        print(f"角色: {admin.role}")
        print(f"创建时间: {admin.created_at}")
        print(f"最后登录: {admin.last_login or '从未登录'}")
        print(f"账户状态: {'活跃' if admin.is_active else '禁用'}")
        print(f"{'='*60}")
        
        # 检查是否使用环境变量密码
        env_password = os.getenv('DEFAULT_ADMIN_PASSWORD')
        if env_password:
            print(f"🔑 当前使用环境变量密码")
            print(f"密码长度: {len(env_password)} 位")
            print(f"密码: {env_password}")
        else:
            print(f"🔑 当前使用随机生成密码")
            print(f"密码长度: 12 位")
            print(f"⚠️  密码已加密存储，无法直接显示")
            print(f"💡 如需重置密码，请设置环境变量 DEFAULT_ADMIN_PASSWORD")
        
        print(f"{'='*60}")
        print(f"💡 提示:")
        print(f"   - 生产环境请立即修改默认密码")
        print(f"   - 可通过环境变量 DEFAULT_ADMIN_PASSWORD 设置密码")
        print(f"   - 或通过Web界面修改密码")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    show_admin_password()
