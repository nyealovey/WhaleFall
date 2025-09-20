#!/usr/bin/env python3
"""
检查密码哈希
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_password():
    """检查密码哈希"""
    print("🔍 检查密码哈希...")
    
    try:
        from app import create_app, bcrypt
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            # 数据库中的密码哈希
            db_hash = "$2b$12$DKFZJIArZQ0ASgxpcGyrHeAXYTBS0ThJjewzso1BnQQm7UWdomcAu"
            
            # 测试不同的密码
            test_passwords = [
                "admin123",
                "admin",
                "password",
                "123456",
                "admin123!",
                "Admin123",
                "whalefall",
                "WhaleFall2024!",
                "Dev2024!"
            ]
            
            print(f"数据库中的密码哈希: {db_hash}")
            print("\n测试密码:")
            
            for password in test_passwords:
                if bcrypt.check_password_hash(db_hash, password):
                    print(f"✅ 找到正确密码: {password}")
                    return password
                else:
                    print(f"❌ 密码不匹配: {password}")
            
            print("\n❌ 没有找到匹配的密码")
            
    except Exception as e:
        print(f"❌ 检查密码时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_password()
