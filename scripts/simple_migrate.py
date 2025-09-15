#!/usr/bin/env python3
"""
简化的数据库迁移脚本
从SQLite迁移到PostgreSQL
"""

import os
import sys
import sqlite3
import psycopg
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 数据库配置
SQLITE_DB_PATH = "userdata/taifish_dev.db"
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "taifish_dev",
    "user": "taifish_user",
    "password": "Taifish2024!"
}

def migrate_users():
    """迁移用户数据"""
    print("迁移用户数据...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()
    
    postgres_conn = psycopg.connect(**POSTGRES_CONFIG)
    postgres_cursor = postgres_conn.cursor()
    
    try:
        # 获取SQLite用户数据
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        
        if not users:
            print("  没有用户数据需要迁移")
            return
        
        # 插入到PostgreSQL
        for user in users:
            try:
                postgres_cursor.execute("""
                    INSERT INTO users (id, username, email, password_hash, role, is_active, 
                                     created_at, updated_at, last_login)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, user)
            except Exception as e:
                print(f"  插入用户失败: {e}")
        
        postgres_conn.commit()
        print(f"  成功迁移 {len(users)} 个用户")
        
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_instances():
    """迁移实例数据"""
    print("迁移实例数据...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()
    
    postgres_conn = psycopg.connect(**POSTGRES_CONFIG)
    postgres_cursor = postgres_conn.cursor()
    
    try:
        # 获取SQLite实例数据
        sqlite_cursor.execute("SELECT * FROM instances")
        instances = sqlite_cursor.fetchall()
        
        if not instances:
            print("  没有实例数据需要迁移")
            return
        
        # 插入到PostgreSQL
        for instance in instances:
            try:
                postgres_cursor.execute("""
                    INSERT INTO instances (id, name, host, port, database_type, 
                                         is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, instance)
            except Exception as e:
                print(f"  插入实例失败: {e}")
        
        postgres_conn.commit()
        print(f"  成功迁移 {len(instances)} 个实例")
        
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_logs():
    """迁移日志数据"""
    print("迁移日志数据...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()
    
    postgres_conn = psycopg.connect(**POSTGRES_CONFIG)
    postgres_cursor = postgres_conn.cursor()
    
    try:
        # 获取SQLite日志数据
        sqlite_cursor.execute("SELECT * FROM logs")
        logs = sqlite_cursor.fetchall()
        
        if not logs:
            print("  没有日志数据需要迁移")
            return
        
        # 插入到PostgreSQL
        for log in logs:
            try:
                postgres_cursor.execute("""
                    INSERT INTO logs (id, level, module, message, details, source, 
                                    user_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, log)
            except Exception as e:
                print(f"  插入日志失败: {e}")
        
        postgres_conn.commit()
        print(f"  成功迁移 {len(logs)} 条日志")
        
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def main():
    """主函数"""
    print("=" * 50)
    print("简化数据库迁移工具")
    print("=" * 50)
    
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"错误: SQLite数据库文件不存在: {SQLITE_DB_PATH}")
        return False
    
    try:
        # 测试PostgreSQL连接
        print("测试PostgreSQL连接...")
        postgres_conn = psycopg.connect(**POSTGRES_CONFIG)
        postgres_conn.close()
        print("  ✓ PostgreSQL连接成功")
        
        # 迁移数据
        migrate_users()
        migrate_instances()
        migrate_logs()
        
        print("\n迁移完成!")
        return True
        
    except Exception as e:
        print(f"迁移失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
