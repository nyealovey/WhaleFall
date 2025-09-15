#!/usr/bin/env python3
"""
泰摸鱼吧数据库迁移脚本
从SQLite迁移到PostgreSQL
"""

import os
import sys
import sqlite3
import psycopg
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.models import db
from app.models.user import User
from app.models.instance import Instance
from app.models.account import Account
from app.models.credential import Credential
from app.models.account_classification import AccountClassification, ClassificationRule, AccountClassificationAssignment
from app.models.log import Log
from app.models.task import Task
from app.models.database_type_config import DatabaseTypeConfig
from app.models.permission_config import PermissionConfig
from app.models.sync_data import SyncData
from app.models.account_change_log import AccountChangeLog
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.classification_batch import ClassificationBatch

# 数据库配置
SQLITE_DB_PATH = "userdata/taifish_dev.db"
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "taifish_dev",
    "user": "taifish_user",
    "password": "Taifish2024!"
}

def connect_sqlite():
    """连接SQLite数据库"""
    if not os.path.exists(SQLITE_DB_PATH):
        raise FileNotFoundError(f"SQLite数据库文件不存在: {SQLITE_DB_PATH}")
    
    return sqlite3.connect(SQLITE_DB_PATH)

def connect_postgresql():
    """连接PostgreSQL数据库"""
    try:
        conn = psycopg.connect(
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            dbname=POSTGRES_CONFIG["database"],
            user=POSTGRES_CONFIG["user"],
            password=POSTGRES_CONFIG["password"]
        )
        return conn
    except Exception as e:
        print(f"连接PostgreSQL失败: {e}")
        raise

def get_table_columns(cursor, table_name):
    """获取表的列信息"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()

def migrate_table_data(sqlite_cursor, postgres_cursor, table_name, columns):
    """迁移表数据"""
    print(f"正在迁移表: {table_name}")
    
    # 获取SQLite数据
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"  表 {table_name} 没有数据，跳过")
        return 0
    
    # 构建INSERT语句
    column_names = [col[1] for col in columns]  # col[1]是列名
    placeholders = ", ".join(["%s"] * len(column_names))
    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
    
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

def migrate_sequence_values(sqlite_cursor, postgres_cursor):
    """迁移序列值"""
    print("正在迁移序列值...")
    
    # 获取所有表的主键最大值
    tables = [
        'users', 'instances', 'accounts', 'credentials', 'logs', 'tasks',
        'account_classifications', 'classification_rules', 'account_classification_assignments',
        'database_type_configs', 'permission_configs', 'sync_data', 'account_change_logs',
        'current_account_sync_data', 'sync_instance_records', 'classification_batches'
    ]
    
    for table in tables:
        try:
            # 检查表是否存在
            sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not sqlite_cursor.fetchone():
                continue
            
            # 获取最大ID
            sqlite_cursor.execute(f"SELECT MAX(id) FROM {table}")
            max_id = sqlite_cursor.fetchone()[0]
            
            if max_id:
                # 重置PostgreSQL序列
                postgres_cursor.execute(f"SELECT setval('{table}_id_seq', {max_id}, true)")
                print(f"  重置序列 {table}_id_seq 到 {max_id}")
        except Exception as e:
            print(f"  重置序列 {table}_id_seq 失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("泰摸鱼吧数据库迁移工具 - SQLite to PostgreSQL")
    print("=" * 60)
    
    # 检查SQLite数据库
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"错误: SQLite数据库文件不存在: {SQLITE_DB_PATH}")
        return False
    
    # 创建Flask应用上下文
    app = create_app()
    
    try:
        with app.app_context():
            # 连接数据库
            print("1. 连接数据库...")
            sqlite_conn = connect_sqlite()
            sqlite_cursor = sqlite_conn.cursor()
            
            postgres_conn = connect_postgresql()
            postgres_cursor = postgres_conn.cursor()
            
            print("   ✓ SQLite连接成功")
            print("   ✓ PostgreSQL连接成功")
            
            # 创建PostgreSQL表结构
            print("\n2. 创建PostgreSQL表结构...")
            db.create_all()
            print("   ✓ 表结构创建完成")
            
            # 获取所有表
            print("\n3. 获取表信息...")
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in sqlite_cursor.fetchall()]
            print(f"   发现 {len(tables)} 个表: {', '.join(tables)}")
            
            # 迁移数据
            print("\n4. 开始迁移数据...")
            total_migrated = 0
            
            for table_name in tables:
                try:
                    # 获取表结构
                    columns = get_table_columns(sqlite_cursor, table_name)
                    if not columns:
                        print(f"  跳过表 {table_name} (无列信息)")
                        continue
                    
                    # 迁移数据
                    migrated_count = migrate_table_data(sqlite_cursor, postgres_cursor, table_name, columns)
                    total_migrated += migrated_count
                    
                except Exception as e:
                    print(f"  迁移表 {table_name} 失败: {e}")
                    continue
            
            # 迁移序列值
            print("\n5. 迁移序列值...")
            migrate_sequence_values(sqlite_cursor, postgres_cursor)
            
            # 验证迁移结果
            print("\n6. 验证迁移结果...")
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
            
            print(f"\n7. 迁移完成!")
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
