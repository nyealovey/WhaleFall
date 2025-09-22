#!/usr/bin/env python3
"""
重置管理员密码的脚本
可以生成新的随机密码或设置指定密码
"""

import os
import sys
import secrets
import string
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.models.user import User
from app.utils.structlog_config import get_system_logger

def generate_random_password(length=12):
    """生成随机密码"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def reset_admin_password(new_password=None):
    """重置管理员密码"""
    app = create_app()
    
    with app.app_context():
        system_logger = get_system_logger()
        
        # 查找管理员用户
        admin = User.query.filter_by(username="admin").first()
        
        if not admin:
            return
        
        # 生成新密码
        if not new_password:
            new_password = generate_random_password()
        
        # 更新密码
        admin.set_password(new_password)
        
        try:
            from app import db
            db.session.commit()
            
            
            system_logger.info(
                "管理员密码已重置",
                module="reset_admin_password",
                username=admin.username,
                password_length=len(new_password)
            )
            
        except Exception as e:
            system_logger.error(
                "管理员密码重置失败",
                module="reset_admin_password",
                error=str(e)
            )

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='重置管理员密码')
    parser.add_argument('--password', '-p', help='指定新密码（不指定则生成随机密码）')
    parser.add_argument('--length', '-l', type=int, default=12, help='随机密码长度（默认12位）')
    
    args = parser.parse_args()
    
    if args.password:
        reset_admin_password(args.password)
    else:
        # 生成指定长度的随机密码
        new_password = generate_random_password(args.length)
        reset_admin_password(new_password)

if __name__ == "__main__":
    main()
