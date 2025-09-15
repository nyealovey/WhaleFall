#!/usr/bin/env python3
"""
精确的SQLite到PostgreSQL数据迁移脚本
处理列顺序和数据类型匹配问题
"""

import sqlite3
import psycopg
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

# 数据库配置
SQLITE_DB = "userdata/taifish_dev.db"
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "taifish_dev",
    "user": "taifish_user",
    "password": "Taifish2024!"
}

def convert_boolean(value: Any) -> Optional[bool]:
    """转换布尔值"""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return False

def convert_json_field(value: Any) -> Optional[str]:
    """将Python对象转换为JSON字符串"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            return json.dumps(value)
    else:
        return json.dumps(value)

def migrate_instances():
    """迁移instances表"""
    print("📋 迁移 instances...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    
    pg_conn = psycopg.connect(**POSTGRES_CONFIG)
    pg_cursor = pg_conn.cursor()
    
    try:
        # 清空目标表
        pg_cursor.execute("DELETE FROM instances")
        
        # 获取SQLite数据
        sqlite_cursor.execute("SELECT * FROM instances")
        sqlite_data = sqlite_cursor.fetchall()
        
        if not sqlite_data:
            print("  ⚠️  instances表无数据")
            return 0
        
        # 插入数据，按PostgreSQL列顺序
        insert_sql = """
            INSERT INTO instances (
                id, name, db_type, host, port, database_name, database_version,
                environment, sync_count, credential_id, description, tags,
                status, is_active, last_connected, created_at, updated_at, deleted_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        converted_data = []
        for row in sqlite_data:
            # 按PostgreSQL列顺序重新排列数据
            converted_row = (
                row[0],  # id
                row[1],  # name
                row[2],  # db_type
                row[3],  # host
                row[4],  # port
                row[5],  # database_name
                row[6],  # database_version
                row[7],  # environment
                row[8],  # sync_count
                row[9],  # credential_id
                row[10], # description
                convert_json_field(row[11]), # tags
                row[12], # status
                convert_boolean(row[13]), # is_active
                row[14], # last_connected
                row[15], # created_at
                row[16], # updated_at
                row[17]  # deleted_at
            )
            converted_data.append(converted_row)
        
        pg_cursor.executemany(insert_sql, converted_data)
        pg_conn.commit()
        
        print(f"  ✅ instances: {len(converted_data)}条记录")
        return len(converted_data)
        
    except Exception as e:
        print(f"  ❌ instances迁移失败: {e}")
        pg_conn.rollback()
        return 0
    finally:
        sqlite_conn.close()
        pg_conn.close()

def migrate_current_account_sync_data():
    """迁移current_account_sync_data表"""
    print("📋 迁移 current_account_sync_data...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    
    pg_conn = psycopg.connect(**POSTGRES_CONFIG)
    pg_cursor = pg_conn.cursor()
    
    try:
        # 清空目标表
        pg_cursor.execute("DELETE FROM current_account_sync_data")
        
        # 获取SQLite数据
        sqlite_cursor.execute("SELECT * FROM current_account_sync_data")
        sqlite_data = sqlite_cursor.fetchall()
        
        if not sqlite_data:
            print("  ⚠️  current_account_sync_data表无数据")
            return 0
        
        # 获取PostgreSQL列名
        pg_cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'current_account_sync_data' 
            ORDER BY ordinal_position
        """)
        pg_columns = [col[0] for col in pg_cursor.fetchall()]
        
        # 准备插入语句
        placeholders = ", ".join(["%s"] * len(pg_columns))
        insert_sql = f"INSERT INTO current_account_sync_data ({', '.join(pg_columns)}) VALUES ({placeholders})"
        
        converted_data = []
        for row in sqlite_data:
            converted_row = []
            for i, value in enumerate(row):
                if value is None:
                    converted_row.append(None)
                elif pg_columns[i] in ['is_active', 'is_system', 'is_deleted']:
                    converted_row.append(convert_boolean(value))
                elif 'json' in pg_columns[i].lower() or pg_columns[i] in ['global_privileges', 'database_privileges', 'table_privileges', 'column_privileges', 'metadata']:
                    converted_row.append(convert_json_field(value))
                else:
                    converted_row.append(value)
            converted_data.append(tuple(converted_row))
        
        pg_cursor.executemany(insert_sql, converted_data)
        pg_conn.commit()
        
        print(f"  ✅ current_account_sync_data: {len(converted_data)}条记录")
        return len(converted_data)
        
    except Exception as e:
        print(f"  ❌ current_account_sync_data迁移失败: {e}")
        pg_conn.rollback()
        return 0
    finally:
        sqlite_conn.close()
        pg_conn.close()

def main():
    print("🚀 开始精确数据迁移...\n")
    
    total_migrated = 0
    
    # 按依赖关系迁移
    total_migrated += migrate_instances()
    total_migrated += migrate_current_account_sync_data()
    
    print(f"\n🎉 迁移完成! 总共迁移了 {total_migrated} 条记录")

if __name__ == "__main__":
    main()
