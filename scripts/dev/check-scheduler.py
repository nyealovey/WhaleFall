#!/usr/bin/env python3
"""
检查调度器状态
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_scheduler():
    """检查调度器状态"""
    print("🔍 检查调度器状态...")
    
    try:
        from app import create_app
        from app.scheduler import scheduler
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            print("1. 调度器基本信息:")
            print(f"   调度器对象: {scheduler}")
            print(f"   是否已启动: {hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running}")
            
            if hasattr(scheduler, 'scheduler') and scheduler.scheduler:
                print("2. 调度器详情:")
                print(f"   调度器实例: {scheduler.scheduler}")
                print(f"   是否运行: {scheduler.scheduler.running}")
                
                # 获取任务列表
                try:
                    jobs = scheduler.get_jobs()
                    print(f"   任务数量: {len(jobs)}")
                    
                    if jobs:
                        print("   任务列表:")
                        for job in jobs:
                            print(f"     - {job.name} (ID: {job.id})")
                            print(f"       下次运行: {job.next_run_time}")
                            print(f"       触发器: {job.trigger}")
                    else:
                        print("   ❌ 没有找到任务")
                        
                except Exception as e:
                    print(f"   ❌ 获取任务失败: {e}")
            
            # 检查SQLite数据库
            print("3. 检查SQLite数据库:")
            sqlite_path = Path("userdata/scheduler.db")
            if sqlite_path.exists():
                print(f"   ✅ 数据库文件存在: {sqlite_path}")
                print(f"   文件大小: {sqlite_path.stat().st_size} bytes")
                
                # 检查数据库内容
                import sqlite3
                conn = sqlite3.connect(str(sqlite_path))
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"   数据库表: {[table[0] for table in tables]}")
                
                if ('apscheduler_jobs',) in tables:
                    cursor.execute("SELECT COUNT(*) FROM apscheduler_jobs;")
                    job_count = cursor.fetchone()[0]
                    print(f"   任务记录数: {job_count}")
                    
                    if job_count > 0:
                        cursor.execute("SELECT id, next_run_time FROM apscheduler_jobs LIMIT 5;")
                        jobs = cursor.fetchall()
                        print("   任务详情:")
                        for job in jobs:
                            print(f"     - ID: {job[0]}, 下次运行: {job[1]}")
                
                conn.close()
            else:
                print(f"   ❌ 数据库文件不存在: {sqlite_path}")
                
    except Exception as e:
        print(f"❌ 检查调度器时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_scheduler()
