#!/usr/bin/env python3
"""
迁移APScheduler任务从SQLite到PostgreSQL
"""

import sqlite3
import pickle
from datetime import datetime
from app import create_app, db

def migrate_scheduler_data():
    """迁移调度器数据"""
    app = create_app()
    
    with app.app_context():
        print("开始迁移APScheduler任务数据...")
        
        # 1. 从SQLite读取任务数据
        sqlite_conn = sqlite3.connect('userdata/scheduler.db')
        sqlite_cursor = sqlite_conn.cursor()
        
        # 获取所有任务
        sqlite_cursor.execute('SELECT id, next_run_time, job_state FROM apscheduler_jobs')
        jobs = sqlite_cursor.fetchall()
        
        print(f"发现 {len(jobs)} 个任务需要迁移")
        
        # 2. 清理PostgreSQL中的旧任务数据
        print("清理PostgreSQL中的旧任务数据...")
        db.session.execute("DELETE FROM apscheduler_jobs")
        db.session.commit()
        
        # 3. 迁移任务到PostgreSQL
        migrated_count = 0
        for job_id, next_run_time, job_state in jobs:
            try:
                # 反序列化任务状态
                job_data = pickle.loads(job_state)
                
                # 保持原始时间戳格式（double precision）
                # APScheduler使用Unix时间戳存储next_run_time
                next_run_timestamp = next_run_time
                
                # 插入到PostgreSQL
                db.session.execute("""
                    INSERT INTO apscheduler_jobs (id, next_run_time, job_state)
                    VALUES (:id, :next_run_time, :job_state)
                """, {
                    'id': job_id,
                    'next_run_time': next_run_timestamp,
                    'job_state': job_state
                })
                
                print(f"  ✅ 迁移任务: {job_id}")
                if next_run_timestamp:
                    next_run_dt = datetime.fromtimestamp(next_run_timestamp)
                    print(f"     下次执行: {next_run_dt}")
                else:
                    print(f"     下次执行: 无")
                
                migrated_count += 1
                
            except Exception as e:
                print(f"  ❌ 迁移任务 {job_id} 失败: {e}")
                continue
        
        # 4. 提交更改
        db.session.commit()
        
        # 5. 关闭SQLite连接
        sqlite_conn.close()
        
        print(f"\n✅ 迁移完成！成功迁移 {migrated_count} 个任务")
        
        # 6. 验证迁移结果
        print("\n验证迁移结果:")
        result = db.session.execute("SELECT id, next_run_time FROM apscheduler_jobs")
        for row in result.fetchall():
            job_id, next_run_time = row
            if next_run_time:
                next_run_dt = datetime.fromtimestamp(next_run_time)
                print(f"  {job_id}: {next_run_dt}")
            else:
                print(f"  {job_id}: 无计划执行")

if __name__ == "__main__":
    migrate_scheduler_data()