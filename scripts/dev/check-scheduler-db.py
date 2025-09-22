#!/usr/bin/env python3
"""
检查调度器SQLite数据库的结构和内容
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_scheduler_database():
    """检查调度器数据库"""
    print("🔍 检查调度器SQLite数据库...")
    
    # 数据库文件路径
    db_path = project_root / "userdata" / "scheduler.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print(f"✅ 数据库文件存在: {db_path}")
    print(f"📁 文件大小: {db_path.stat().st_size} bytes")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n📋 数据库表列表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 检查apscheduler_jobs表
        if ('apscheduler_jobs',) in tables:
            print(f"\n📊 apscheduler_jobs表信息:")
            
            # 获取表结构
            cursor.execute("PRAGMA table_info(apscheduler_jobs);")
            columns = cursor.fetchall()
            print("  列结构:")
            for col in columns:
                print(f"    - {col[1]} ({col[2]})")
            
            # 获取任务数量
            cursor.execute("SELECT COUNT(*) FROM apscheduler_jobs;")
            job_count = cursor.fetchone()[0]
            print(f"  任务数量: {job_count}")
            
            # 获取任务详情
            if job_count > 0:
                cursor.execute("SELECT id, next_run_time, job_state FROM apscheduler_jobs LIMIT 5;")
                jobs = cursor.fetchall()
                print("  任务详情:")
                for job in jobs:
                    print(f"    - ID: {job[0]}, 下次运行: {job[1]}, 状态: {job[2]}")
        
        # 检查其他表
        for table in tables:
            if table[0] != 'apscheduler_jobs':
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                count = cursor.fetchone()[0]
                print(f"\n📊 {table[0]}表: {count} 条记录")
        
        conn.close()
        print("\n✅ 数据库检查完成")
        
    except Exception as e:
        print(f"❌ 检查数据库时出错: {e}")

def create_scheduler_database():
    """手动创建调度器数据库"""
    print("\n🔧 手动创建调度器数据库...")
    
    try:
        from app.scheduler import scheduler, init_scheduler
        
        # 创建模拟的Flask应用
        class MockApp:
            def __init__(self):
                self.config = {}
        
        app = MockApp()
        
        # 初始化调度器
        result = init_scheduler(app)
        
        if result:
            print("✅ 调度器数据库创建成功")
            
            # 停止调度器
            scheduler.stop()
            print("✅ 调度器已停止")
        else:
            print("❌ 调度器数据库创建失败")
            
    except Exception as e:
        print(f"❌ 创建数据库时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_scheduler_database()
    
    # 如果数据库不存在，尝试创建
    db_path = project_root / "userdata" / "scheduler.db"
    if not db_path.exists():
        create_scheduler_database()
        check_scheduler_database()
