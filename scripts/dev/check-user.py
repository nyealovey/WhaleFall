#!/usr/bin/env python3
"""
检查用户数据
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_user():
    """检查用户数据"""
    print("🔍 检查用户数据...")
    
    try:
        from app import create_app, db
        from app.models.user import User
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            # 查找admin用户
            admin_user = User.query.filter_by(username="admin").first()
            
            if admin_user:
                print(f"✅ 找到admin用户:")
                print(f"   ID: {admin_user.id}")
                print(f"   用户名: {admin_user.username}")
                print(f"   角色: {admin_user.role}")
                print(f"   是否激活: {admin_user.is_active}")
                print(f"   创建时间: {admin_user.created_at}")
                
                # 测试密码
                password = "admin123"
                if admin_user.check_password(password):
                    print(f"✅ 密码验证成功")
                else:
                    print(f"❌ 密码验证失败")
                    
                # 显示密码哈希
                print(f"   密码哈希: {admin_user.password[:20]}...")
            else:
                print("❌ 未找到admin用户")
                
                # 列出所有用户
                users = User.query.all()
                print(f"   数据库中共有 {len(users)} 个用户:")
                for user in users:
                    print(f"     - {user.username} (ID: {user.id}, 激活: {user.is_active})")
                    
    except Exception as e:
        print(f"❌ 检查用户数据时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_user()
