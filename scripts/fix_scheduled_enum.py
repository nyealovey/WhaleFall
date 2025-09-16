#!/usr/bin/env python3
"""
修复PostgreSQL中sync_type_enum枚举的scheduled值问题
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config

def fix_scheduled_enum():
    """修复scheduled枚举值问题"""
    app = create_app()
    
    # 从配置获取数据库连接信息
    db_url = Config.SQLALCHEMY_DATABASE_URI
    print(f"数据库URL: {db_url}")
    
    # 解析数据库连接信息
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql://', 1)
    
    try:
        # 连接数据库
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ 数据库连接成功")
        
        # 1. 检查当前枚举值
        cursor.execute("SELECT unnest(enum_range(NULL::sync_type_enum))")
        current_values = [row[0] for row in cursor.fetchall()]
        print(f"当前枚举值: {current_values}")
        
        # 2. 先添加scheduled值到枚举（如果不存在）
        if 'scheduled' not in current_values:
            print("添加scheduled值到枚举...")
            cursor.execute("ALTER TYPE sync_type_enum ADD VALUE 'scheduled'")
            print("✅ 已添加scheduled值到枚举")
        
        # 3. 检查是否有scheduled值的数据
        cursor.execute("SELECT COUNT(*) FROM sync_sessions WHERE sync_type = 'scheduled'")
        scheduled_count = cursor.fetchone()[0]
        print(f"包含scheduled值的记录数: {scheduled_count}")
        
        if scheduled_count > 0:
            
            # 4. 更新数据：scheduled -> scheduled_task
            print("更新scheduled为scheduled_task...")
            cursor.execute("UPDATE sync_sessions SET sync_type = 'scheduled_task' WHERE sync_type = 'scheduled'")
            updated_count = cursor.rowcount
            print(f"✅ 已更新 {updated_count} 条记录")
            
            # 5. 验证更新结果
            cursor.execute("SELECT COUNT(*) FROM sync_sessions WHERE sync_type = 'scheduled'")
            remaining_scheduled = cursor.fetchone()[0]
            print(f"剩余的scheduled记录数: {remaining_scheduled}")
            
            # 6. 检查所有sync_type值
            cursor.execute("SELECT DISTINCT sync_type FROM sync_sessions ORDER BY sync_type")
            all_types = [row[0] for row in cursor.fetchall()]
            print(f"数据库中的所有sync_type值: {all_types}")
            
        else:
            print("✅ 没有发现scheduled值的记录")
        
        cursor.close()
        conn.close()
        print("✅ 修复完成")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_scheduled_enum()
    sys.exit(0 if success else 1)
