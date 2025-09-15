#!/usr/bin/env python3
"""
测试PostgreSQL连接和数据迁移
"""

import os
import sys
import psycopg
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 数据库配置
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "taifish_dev",
    "user": "taifish_user",
    "password": "Taifish2024!"
}

def test_connection():
    """测试PostgreSQL连接"""
    print("测试PostgreSQL连接...")
    
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # 测试基本连接
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"  ✓ 连接成功: {version}")
        
        # 测试数据库大小
        cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        size = cursor.fetchone()[0]
        print(f"  ✓ 数据库大小: {size}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ✗ 连接失败: {e}")
        return False

def test_tables():
    """测试表是否存在"""
    print("\n测试表结构...")
    
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"  发现 {len(tables)} 个表:")
        for table in tables:
            print(f"    - {table}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ✗ 获取表信息失败: {e}")
        return False

def test_data():
    """测试数据迁移"""
    print("\n测试数据迁移...")
    
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # 测试主要表的数据
        test_tables = ['users', 'instances', 'credentials', 'unified_logs']
        
        for table in test_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✓ {table}: {count} 条记录")
            except Exception as e:
                print(f"  ✗ {table}: 查询失败 - {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ✗ 测试数据失败: {e}")
        return False

def test_app_connection():
    """测试应用连接"""
    print("\n测试应用连接...")
    
    try:
        from app import create_app, db
        
        app = create_app()
        with app.app_context():
            # 测试数据库连接
            db.session.execute("SELECT 1")
            print("  ✓ 应用数据库连接正常")
            
            # 测试模型查询
            from app.models.user import User
            user_count = User.query.count()
            print(f"  ✓ 用户模型查询正常: {user_count} 个用户")
            
            from app.models.instance import Instance
            instance_count = Instance.query.count()
            print(f"  ✓ 实例模型查询正常: {instance_count} 个实例")
        
        return True
        
    except Exception as e:
        print(f"  ✗ 应用连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("PostgreSQL连接和数据测试")
    print("=" * 50)
    
    success = True
    
    # 测试连接
    if not test_connection():
        success = False
    
    # 测试表结构
    if not test_tables():
        success = False
    
    # 测试数据
    if not test_data():
        success = False
    
    # 测试应用连接
    if not test_app_connection():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ 所有测试通过!")
        print("PostgreSQL迁移成功，可以启动应用了")
    else:
        print("✗ 部分测试失败!")
        print("请检查错误信息并修复")
    
    print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
