#!/usr/bin/env python3
"""
最终的数据迁移脚本
处理所有表的数据迁移，确保列顺序和数据类型正确
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
        
        # 按PostgreSQL列顺序插入数据
        insert_sql = """
            INSERT INTO current_account_sync_data (
                id, db_type, session_id, sync_time, status, message, error_message,
                username, is_superuser, global_privileges, database_privileges,
                predefined_roles, role_attributes, database_privileges_pg,
                tablespace_privileges, server_roles, server_permissions,
                database_roles, database_permissions, oracle_roles,
                system_privileges, tablespace_privileges_oracle, type_specific,
                last_sync_time, last_change_type, last_change_time,
                is_deleted, deleted_time, instance_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        converted_data = []
        for row in sqlite_data:
            # 按PostgreSQL列顺序重新排列数据
            converted_row = (
                row[0],  # id
                row[2],  # db_type
                row[3],  # session_id
                row[4],  # sync_time
                row[5],  # status
                row[6],  # message
                row[7],  # error_message
                row[8],  # username
                convert_boolean(row[9]),  # is_superuser
                convert_json_field(row[10]),  # global_privileges
                convert_json_field(row[11]),  # database_privileges
                convert_json_field(row[12]),  # predefined_roles
                convert_json_field(row[13]),  # role_attributes
                convert_json_field(row[14]),  # database_privileges_pg
                convert_json_field(row[15]),  # tablespace_privileges
                convert_json_field(row[16]),  # server_roles
                convert_json_field(row[17]),  # server_permissions
                convert_json_field(row[18]),  # database_roles
                convert_json_field(row[19]),  # database_permissions
                convert_json_field(row[20]),  # oracle_roles
                convert_json_field(row[21]),  # system_privileges
                convert_json_field(row[22]),  # tablespace_privileges_oracle
                convert_json_field(row[23]),  # type_specific
                row[24],  # last_sync_time
                row[25],  # last_change_type
                row[26],  # last_change_time
                convert_boolean(row[27]),  # is_deleted
                row[28],  # deleted_time
                row[1]   # instance_id (移到最后)
            )
            converted_data.append(converted_row)
        
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

def migrate_remaining_tables():
    """迁移剩余的表"""
    print("📋 迁移剩余表...")
    
    # 需要迁移的表
    tables = [
        'account_change_log',
        'account_classification_assignments',
        'sync_instance_records'
    ]
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    
    pg_conn = psycopg.connect(**POSTGRES_CONFIG)
    pg_cursor = pg_conn.cursor()
    
    total_migrated = 0
    
    for table_name in tables:
        try:
            print(f"  📋 迁移 {table_name}...")
            
            # 清空目标表
            pg_cursor.execute(f"DELETE FROM {table_name}")
            
            # 获取PostgreSQL列名
            pg_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """, (table_name,))
            pg_columns = [col[0] for col in pg_cursor.fetchall()]
            
            # 获取SQLite数据
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            sqlite_data = sqlite_cursor.fetchall()
            
            if not sqlite_data:
                print(f"    ⚠️  {table_name}表无数据")
                continue
            
            # 准备插入语句
            placeholders = ", ".join(["%s"] * len(pg_columns))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(pg_columns)}) VALUES ({placeholders})"
            
            converted_data = []
            for row in sqlite_data:
                converted_row = []
                for i, value in enumerate(row):
                    if value is None:
                        converted_row.append(None)
                    elif pg_columns[i] in ['is_active', 'is_system', 'is_deleted']:
                        converted_row.append(convert_boolean(value))
                    elif 'json' in pg_columns[i].lower() or pg_columns[i] in ['config', 'metadata', 'permissions', 'rules', 'tags']:
                        converted_row.append(convert_json_field(value))
                    else:
                        converted_row.append(value)
                converted_data.append(tuple(converted_row))
            
            pg_cursor.executemany(insert_sql, converted_data)
            pg_conn.commit()
            
            print(f"    ✅ {table_name}: {len(converted_data)}条记录")
            total_migrated += len(converted_data)
            
        except Exception as e:
            print(f"    ❌ {table_name}迁移失败: {e}")
            pg_conn.rollback()
    
    sqlite_conn.close()
    pg_conn.close()
    
    return total_migrated

def main():
    print("🚀 开始最终数据迁移...\n")
    
    total_migrated = 0
    
    # 迁移current_account_sync_data
    total_migrated += migrate_current_account_sync_data()
    
    # 迁移剩余表
    total_migrated += migrate_remaining_tables()
    
    print(f"\n🎉 迁移完成! 总共迁移了 {total_migrated} 条记录")
    
    # 验证迁移结果
    print("\n📊 验证迁移结果...")
    conn = psycopg.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    tables_to_check = [
        'instances', 'current_account_sync_data', 'account_change_log',
        'account_classification_assignments', 'sync_instance_records'
    ]
    
    for table_name in tables_to_check:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name}: {count}条记录")
        except Exception as e:
            print(f"  {table_name}: 查询失败 - {e}")
    
    conn.close()

if __name__ == "__main__":
    main()
