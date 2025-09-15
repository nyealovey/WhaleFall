#!/usr/bin/env python3
"""
修复的SQLite到PostgreSQL数据迁移脚本
处理JSON字段和数据类型兼容性问题
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

def convert_json_field(value: Any) -> Optional[str]:
    """将Python对象转换为JSON字符串"""
    if value is None:
        return None
    if isinstance(value, str):
        # 如果已经是字符串，尝试解析为JSON验证格式
        try:
            json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            # 如果不是有效JSON，包装为JSON字符串
            return json.dumps(value)
    else:
        return json.dumps(value)

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

def convert_datetime(value: Any) -> Optional[str]:
    """转换日期时间"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)

def migrate_table_data(table_name: str, columns: List[str], data: List[Tuple]) -> int:
    """迁移单个表的数据"""
    if not data:
        print(f"  表 {table_name} 没有数据，跳过")
        return 0
    
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # 构建INSERT语句
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        migrated_count = 0
        
        for row in data:
            try:
                # 处理每一行数据
                processed_row = []
                for i, value in enumerate(row):
                    if value is None:
                        processed_row.append(None)
                    elif columns[i] in ['global_privileges', 'database_privileges', 'predefined_roles', 
                                      'role_attributes', 'database_privileges_pg', 'tablespace_privileges',
                                      'server_roles', 'server_permissions', 'database_roles', 'database_permissions',
                                      'oracle_roles', 'system_privileges', 'tablespace_privileges_oracle',
                                      'type_specific', 'metadata', 'extra_data']:
                        # JSON字段
                        processed_row.append(convert_json_field(value))
                    elif 'is_' in columns[i] or columns[i] in ['is_active', 'is_system', 'is_superuser', 'is_deleted']:
                        # 布尔字段
                        processed_row.append(convert_boolean(value))
                    elif 'time' in columns[i] or 'created_at' in columns[i] or 'updated_at' in columns[i]:
                        # 时间字段
                        processed_row.append(convert_datetime(value))
                    else:
                        # 其他字段直接使用
                        processed_row.append(value)
                
                cursor.execute(insert_sql, processed_row)
                migrated_count += 1
                
            except Exception as e:
                print(f"  插入数据失败 (行 {migrated_count + 1}): {e}")
                print(f"  数据: {row}")
                continue
        
        conn.commit()
        print(f"  成功迁移 {migrated_count} 条记录")
        return migrated_count
        
    except Exception as e:
        print(f"  迁移表 {table_name} 失败: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> List[str]:
    """获取表的列名"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return columns

def main():
    print("开始修复的SQLite到PostgreSQL数据迁移...")
    
    # 连接SQLite数据库
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    
    # 需要迁移的表（按依赖顺序）
    tables_to_migrate = [
        'users',
        'instances', 
        'credentials',
        'database_type_configs',
        'account_classifications',
        'classification_rules',
        'permission_configs',
        'account_classification_assignments',
        'classification_batches',
        'global_params',
        'current_account_sync_data',
        'account_change_log',
        'sync_sessions',
        'sync_instance_records',
        'unified_logs',
        'tasks'
    ]
    
    total_migrated = 0
    
    for table_name in tables_to_migrate:
        print(f"\n迁移表: {table_name}")
        
        try:
            # 获取表结构
            columns = get_table_columns(sqlite_cursor, table_name)
            
            # 获取数据
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            data = sqlite_cursor.fetchall()
            
            # 迁移数据
            migrated = migrate_table_data(table_name, columns, data)
            total_migrated += migrated
            
        except Exception as e:
            print(f"  处理表 {table_name} 时出错: {e}")
            continue
    
    # 迁移序列值
    print(f"\n迁移序列值...")
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # 获取SQLite序列值
        sqlite_cursor.execute("SELECT name, seq FROM sqlite_sequence")
        sequences = sqlite_cursor.fetchall()
        
        for seq_name, seq_value in sequences:
            table_name = seq_name.replace('_id_seq', '')
            try:
                cursor.execute(f"SELECT setval('{seq_name}', {seq_value})")
                print(f"  重置序列 {seq_name} 到 {seq_value}")
            except Exception as e:
                print(f"  重置序列 {seq_name} 失败: {e}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"  迁移序列值失败: {e}")
    
    # 验证迁移结果
    print(f"\n验证迁移结果...")
    try:
        conn = psycopg.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        for table_name in tables_to_migrate:
            try:
                # 检查SQLite记录数
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # 检查PostgreSQL记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                pg_count = cursor.fetchone()[0]
                
                if sqlite_count == pg_count:
                    print(f"  ✓ {table_name}: SQLite({sqlite_count}) -> PostgreSQL({pg_count})")
                else:
                    print(f"  ✗ {table_name}: SQLite({sqlite_count}) -> PostgreSQL({pg_count})")
                    
            except Exception as e:
                print(f"  ✗ {table_name}: 验证失败 - {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"  验证迁移结果失败: {e}")
    
    sqlite_conn.close()
    
    print(f"\n迁移完成!")
    print(f"总共迁移了 {total_migrated} 条记录")

if __name__ == "__main__":
    main()
