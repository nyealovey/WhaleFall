#!/usr/bin/env python3
"""
修复聚合同步分类约束问题
这个脚本用于更新现有数据库的约束，添加 'aggregation' 支持
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()

def get_database_connection():
    """获取数据库连接"""
    try:
        # 从环境变量获取数据库连接信息
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'taifish')
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', 'postgres')
        
        print(f"连接到数据库: {host}:{port}/{database}")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def fix_constraints():
    """修复数据库约束"""
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("开始修复数据库约束...")
        
        # 1. 检查现有约束内容
        print("1. 检查现有约束内容...")
        cursor.execute("""
            SELECT 
                conname as constraint_name,
                pg_get_constraintdef(oid) as constraint_definition
            FROM pg_constraint 
            WHERE conrelid = 'sync_sessions'::regclass 
            AND conname LIKE '%sync_category%';
        """)
        
        existing_constraints = cursor.fetchall()
        print("现有 sync_sessions 约束:")
        for constraint in existing_constraints:
            print(f"  - {constraint[0]}: {constraint[1]}")
        
        # 2. 更新 sync_sessions 表的约束
        print("2. 更新 sync_sessions 表的约束...")
        try:
            cursor.execute("""
                ALTER TABLE sync_sessions
                DROP CONSTRAINT sync_sessions_sync_category_check;
            """)
            print("  ✅ 成功删除现有约束")
        except Exception as e:
            print(f"  ⚠️ 删除约束时出错: {e}")
        
        cursor.execute("""
            ALTER TABLE sync_sessions
            ADD CONSTRAINT sync_sessions_sync_category_check
            CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));
        """)
        print("  ✅ 成功添加新约束")
        
        # 2. 更新 sync_instance_records 表的约束
        print("2. 更新 sync_instance_records 表的约束...")
        cursor.execute("""
            ALTER TABLE sync_instance_records
            DROP CONSTRAINT IF EXISTS sync_instance_records_sync_category_check;
        """)
        
        cursor.execute("""
            ALTER TABLE sync_instance_records
            ADD CONSTRAINT sync_instance_records_sync_category_check
            CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));
        """)
        
        # 3. 添加列注释
        print("3. 添加列注释...")
        cursor.execute("""
            COMMENT ON COLUMN sync_sessions.sync_category IS 
            '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
        """)
        
        cursor.execute("""
            COMMENT ON COLUMN sync_instance_records.sync_category IS 
            '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
        """)
        
        # 提交事务
        conn.commit()
        print("✅ 数据库约束修复成功！")
        
        # 4. 验证约束是否正确应用
        print("4. 验证约束...")
        cursor.execute("""
            SELECT 
                conname as constraint_name,
                pg_get_constraintdef(oid) as constraint_definition
            FROM pg_constraint 
            WHERE conrelid = 'sync_sessions'::regclass 
            AND conname LIKE '%sync_category%';
        """)
        
        sync_sessions_constraints = cursor.fetchall()
        print("sync_sessions 约束:")
        for constraint in sync_sessions_constraints:
            print(f"  - {constraint[0]}: {constraint[1]}")
        
        cursor.execute("""
            SELECT 
                conname as constraint_name,
                pg_get_constraintdef(oid) as constraint_definition
            FROM pg_constraint 
            WHERE conrelid = 'sync_instance_records'::regclass 
            AND conname LIKE '%sync_category%';
        """)
        
        sync_instance_records_constraints = cursor.fetchall()
        print("sync_instance_records 约束:")
        for constraint in sync_instance_records_constraints:
            print(f"  - {constraint[0]}: {constraint[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def test_aggregation_insert():
    """测试是否可以插入aggregation分类的会话"""
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("测试插入aggregation分类的会话...")
        
        # 尝试插入一个测试会话
        cursor.execute("""
            INSERT INTO sync_sessions (
                session_id, sync_type, sync_category, status, 
                started_at, total_instances, successful_instances, failed_instances,
                created_at, updated_at
            ) VALUES (
                'test-aggregation-session', 'scheduled_task', 'aggregation', 'running',
                NOW(), 0, 0, 0, NOW(), NOW()
            );
        """)
        
        conn.commit()
        print("✅ 测试插入成功！")
        
        # 清理测试数据
        cursor.execute("DELETE FROM sync_sessions WHERE session_id = 'test-aggregation-session';")
        conn.commit()
        print("✅ 测试数据已清理")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🔧 修复聚合同步分类约束问题")
    print("=" * 50)
    
    # 修复约束
    if fix_constraints():
        print("\n🧪 测试修复结果...")
        if test_aggregation_insert():
            print("\n🎉 所有修复和测试都成功完成！")
            print("现在可以重新测试聚合任务的执行了。")
        else:
            print("\n⚠️ 修复成功但测试失败，请检查数据库连接。")
    else:
        print("\n❌ 修复失败，请检查数据库连接和权限。")
