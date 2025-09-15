#!/usr/bin/env python3
"""
完整的SQLite到PostgreSQL数据迁移脚本
确保表结构一致，正确处理所有数据类型
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
            # 尝试解析为JSON验证格式
            json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            # 如果不是有效JSON，包装为JSON字符串
            return json.dumps(value)
    else:
        return json.dumps(value)

def migrate_table(table_name: str, columns: List[str], data: List[Tuple]) -> int:
    """迁移单个表的数据"""
    if not data:
        print(f"  ⚠️  {table_name}表无数据")
        return 0
    
    conn = psycopg.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 清空目标表
        cursor.execute(f"DELETE FROM {table_name}")
        
        # 准备插入语句
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # 转换数据
        converted_data = []
        for row in data:
            converted_row = []
            for i, value in enumerate(row):
                if value is None:
                    converted_row.append(None)
                elif columns[i] in ['is_active', 'is_system', 'is_deleted']:
                    converted_row.append(convert_boolean(value))
                elif 'json' in columns[i].lower() or columns[i] in ['config', 'metadata', 'permissions', 'rules']:
                    converted_row.append(convert_json_field(value))
                else:
                    converted_row.append(value)
            converted_data.append(tuple(converted_row))
        
        # 批量插入
        cursor.executemany(insert_sql, converted_data)
        conn.commit()
        
        print(f"  ✅ {table_name}: {len(converted_data)}条记录")
        return len(converted_data)
        
    except Exception as e:
        print(f"  ❌ {table_name}迁移失败: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def get_table_columns(table_name: str) -> List[str]:
    """获取表的所有列名"""
    conn = psycopg.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table_name,))
    
    columns = [row[0] for row in cursor.fetchall()]
    conn.close()
    return columns

def main():
    print("🚀 开始完整数据迁移...\n")
    
    # 需要迁移的表（按依赖关系排序）
    tables_to_migrate = [
        'users',
        'instances', 
        'credentials',
        'database_type_configs',
        'permission_configs',
        'account_classifications',
        'classification_rules',
        'account_classification_assignments',
        'classification_batches',
        'current_account_sync_data',
        'account_change_log',
        'logs',
        'unified_logs',
        'sync_sessions',
        'sync_instance_records',
        'tasks',
        'global_params'
    ]
    
    # 连接SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    
    total_migrated = 0
    
    for table_name in tables_to_migrate:
        print(f"📋 迁移 {table_name}...")
        
        try:
            # 获取PostgreSQL表列
            columns = get_table_columns(table_name)
            
            # 获取SQLite数据
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            data = sqlite_cursor.fetchall()
            
            # 迁移数据
            migrated_count = migrate_table(table_name, columns, data)
            total_migrated += migrated_count
            
        except Exception as e:
            print(f"  ❌ {table_name}处理失败: {e}")
    
    sqlite_conn.close()
    
    print(f"\n🎉 迁移完成! 总共迁移了 {total_migrated} 条记录")
    
    # 验证迁移结果
    print("\n📊 验证迁移结果...")
    conn = psycopg.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor()
    
    for table_name in tables_to_migrate:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name}: {count}条记录")
        except Exception as e:
            print(f"  {table_name}: 查询失败 - {e}")
    
    conn.close()

if __name__ == "__main__":
    main()
