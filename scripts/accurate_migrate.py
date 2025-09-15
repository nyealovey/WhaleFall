#!/usr/bin/env python3
"""
准确的数据库迁移脚本
从SQLite迁移到PostgreSQL
基于实际的表结构
"""

import os
import sys
import sqlite3
import psycopg
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 数据库配置
SQLITE_DB_PATH = "userdata/taifish_dev.db"
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "taifish_dev",
    "user": "taifish_user",
    "password": "Taifish2024!"
}

def get_sqlite_tables():
    """获取SQLite中的所有表"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return tables

def get_table_schema(sqlite_cursor, table_name):
    """获取表的列信息"""
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = sqlite_cursor.fetchall()
    
    # 转换为字典格式
    schema = []
    for col in columns:
        schema.append({
            'cid': col[0],
            'name': col[1],
            'type': col[2],
            'notnull': bool(col[3]),
            'default_value': col[4],
            'pk': bool(col[5])
        })
    
    return schema

def migrate_table(sqlite_cursor, postgres_cursor, table_name):
    """迁移单个表的数据"""
    print(f"迁移表: {table_name}")
    
    # 获取表结构
    schema = get_table_schema(sqlite_cursor, table_name)
    if not schema:
        print(f"  跳过表 {table_name} (无列信息)")
        return 0
    
    # 获取SQLite数据
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"  表 {table_name} 没有数据，跳过")
        return 0
    
    # 构建INSERT语句
    column_names = [col['name'] for col in schema]
    placeholders = ", ".join(["%s"] * len(column_names))
    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    
    # 插入数据
    inserted_count = 0
    for row in rows:
        try:
            # 处理特殊数据类型
            processed_row = []
            for i, value in enumerate(row):
                if value is None:
                    processed_row.append(None)
                elif isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                    # JSON数据
                    try:
                        processed_row.append(json.loads(value))
                    except:
                        processed_row.append(value)
                else:
                    processed_row.append(value)
            
            postgres_cursor.execute(insert_sql, processed_row)
            inserted_count += 1
        except Exception as e:
            print(f"  插入数据失败 (行 {inserted_count + 1}): {e}")
            print(f"  数据: {row}")
            continue
    
    postgres_cursor.connection.commit()
    print(f"  成功迁移 {inserted_count} 条记录")
    return inserted_count

def migrate_sequences(sqlite_cursor, postgres_cursor):
    """迁移序列值"""
    print("迁移序列值...")
    
    # 获取所有表的主键最大值
    tables = get_sqlite_tables()
    
    for table_name in tables:
        try:
            # 检查表是否存在且有id列
            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = sqlite_cursor.fetchall()
            has_id = any(col[1] == 'id' and col[5] for col in columns)  # col[5]是pk标志
            
            if not has_id:
                continue
            
            # 获取最大ID
            sqlite_cursor.execute(f"SELECT MAX(id) FROM {table_name}")
            max_id = sqlite_cursor.fetchone()[0]
            
            if max_id:
                # 重置PostgreSQL序列
                postgres_cursor.execute(f"SELECT setval('{table_name}_id_seq', {max_id}, true)")
                print(f"  重置序列 {table_name}_id_seq 到 {max_id}")
        except Exception as e:
            print(f"  重置序列 {table_name}_id_seq 失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("准确的数据库迁移工具 - SQLite to PostgreSQL")
    print("=" * 60)
    
    # 检查SQLite数据库
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"错误: SQLite数据库文件不存在: {SQLITE_DB_PATH}")
        return False
    
    try:
        # 连接数据库
        print("1. 连接数据库...")
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_cursor = sqlite_conn.cursor()
        
        postgres_conn = psycopg.connect(**POSTGRES_CONFIG)
        postgres_cursor = postgres_conn.cursor()
        
        print("   ✓ SQLite连接成功")
        print("   ✓ PostgreSQL连接成功")
        
        # 获取所有表
        print("\n2. 获取表信息...")
        tables = get_sqlite_tables()
        print(f"   发现 {len(tables)} 个表: {', '.join(tables)}")
        
        # 迁移数据
        print("\n3. 开始迁移数据...")
        total_migrated = 0
        
        for table_name in tables:
            try:
                migrated_count = migrate_table(sqlite_cursor, postgres_cursor, table_name)
                total_migrated += migrated_count
            except Exception as e:
                print(f"  迁移表 {table_name} 失败: {e}")
                continue
        
        # 迁移序列值
        print("\n4. 迁移序列值...")
        migrate_sequences(sqlite_cursor, postgres_cursor)
        
        # 验证迁移结果
        print("\n5. 验证迁移结果...")
        for table_name in tables:
            try:
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                postgres_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                postgres_count = postgres_cursor.fetchone()[0]
                
                status = "✓" if sqlite_count == postgres_count else "✗"
                print(f"   {status} {table_name}: SQLite({sqlite_count}) -> PostgreSQL({postgres_count})")
                
            except Exception as e:
                print(f"   ✗ {table_name}: 验证失败 - {e}")
        
        print(f"\n6. 迁移完成!")
        print(f"   总共迁移了 {total_migrated} 条记录")
        
        # 关闭连接
        sqlite_conn.close()
        postgres_conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
