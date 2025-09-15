#!/usr/bin/env python3
"""
修复PostgreSQL表结构，使其与SQLite完全一致
"""

import sqlite3
import psycopg
import json
from typing import Dict, List, Tuple

# 数据库配置
SQLITE_DB = "userdata/taifish_dev.db"
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "taifish_dev",
    "user": "taifish_user",
    "password": "Taifish2024!"
}

def get_sqlite_schema(table_name: str) -> List[Tuple]:
    """获取SQLite表结构"""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    schema = cursor.fetchall()
    conn.close()
    return schema

def get_postgresql_schema(table_name: str) -> List[Tuple]:
    """获取PostgreSQL表结构"""
    conn = psycopg.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table_name,))
    schema = cursor.fetchall()
    conn.close()
    return schema

def fix_global_params_table():
    """修复global_params表结构"""
    conn = psycopg.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 删除现有表
        cursor.execute("DROP TABLE IF EXISTS global_params CASCADE")
        
        # 重新创建表，与SQLite结构一致
        cursor.execute("""
            CREATE TABLE global_params (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                value TEXT,
                description TEXT,
                param_type VARCHAR(50) DEFAULT 'string',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("✅ global_params表结构已修复")
        
    except Exception as e:
        print(f"❌ 修复global_params表失败: {e}")
        conn.rollback()
    finally:
        conn.close()

def check_all_tables():
    """检查所有表的结构差异"""
    sqlite_tables = [
        'account_change_log', 'account_changes', 'account_classification_assignments',
        'account_classifications', 'alembic_version', 'classification_batches',
        'classification_rules', 'credentials', 'current_account_sync_data',
        'database_type_configs', 'expired_sync_locks', 'global_params',
        'instances', 'logs', 'permission_configs', 'sync_instance_records',
        'sync_locks_stats', 'sync_performance_view', 'sync_sessions',
        'tasks', 'unified_logs', 'users'
    ]
    
    print("=== 表结构差异检查 ===\n")
    
    for table in sqlite_tables:
        try:
            sqlite_schema = get_sqlite_schema(table)
            postgres_schema = get_postgresql_schema(table)
            
            print(f"📋 {table}:")
            print(f"  SQLite列数: {len(sqlite_schema)}")
            print(f"  PostgreSQL列数: {len(postgres_schema)}")
            
            if len(sqlite_schema) != len(postgres_schema):
                print(f"  ⚠️  列数不匹配!")
                
                print("  SQLite列:")
                for col in sqlite_schema:
                    print(f"    - {col[1]} ({col[2]})")
                    
                print("  PostgreSQL列:")
                for col in postgres_schema:
                    print(f"    - {col[0]} ({col[1]})")
            else:
                print(f"  ✅ 列数匹配")
                
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
        
        print()

def main():
    print("🔧 开始修复PostgreSQL表结构...\n")
    
    # 检查所有表
    check_all_tables()
    
    # 修复global_params表
    fix_global_params_table()
    
    print("\n🎉 表结构修复完成!")

if __name__ == "__main__":
    main()
