#!/usr/bin/env python3
"""
测试数据库连接
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_db_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    
    try:
        from app import create_app, db
        from app.models.user import User
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            # 测试数据库连接
            print("1. 测试数据库连接...")
            result = db.session.execute(db.text("SELECT 1")).scalar()
            print(f"   数据库连接测试: {result}")
            
            # 测试用户查询
            print("2. 测试用户查询...")
            admin_user = User.query.filter_by(username="admin").first()
            if admin_user:
                print(f"   找到admin用户: {admin_user.username} (ID: {admin_user.id})")
                print(f"   用户是否激活: {admin_user.is_active}")
            else:
                print("   ❌ 未找到admin用户")
            
            # 测试用户加载器
            print("3. 测试用户加载器...")
            from app import login_manager
            
            @login_manager.user_loader
            def load_user(user_id: str) -> "User | None":
                return User.query.get(int(user_id))
            
            user = load_user("1")
            if user:
                print(f"   用户加载器测试: {user.username} (ID: {user.id})")
            else:
                print("   ❌ 用户加载器失败")
                
    except Exception as e:
        print(f"❌ 测试数据库连接时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_db_connection()
