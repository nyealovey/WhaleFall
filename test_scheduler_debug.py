#!/usr/bin/env python3
"""
调度器调试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.scheduler import get_scheduler

def test_scheduler():
    """测试调度器状态"""
    app = create_app()
    
    with app.app_context():
        try:
            scheduler = get_scheduler()
            print(f"调度器对象: {scheduler}")
            print(f"调度器类型: {type(scheduler)}")
            
            if scheduler is None:
                print("❌ 调度器未初始化")
                return
                
            print(f"调度器是否运行: {scheduler.running}")
            
            if not scheduler.running:
                print("❌ 调度器未启动")
                return
                
            jobs = scheduler.get_jobs()
            print(f"任务数量: {len(jobs)}")
            
            for job in jobs:
                print(f"  - 任务ID: {job.id}")
                print(f"    任务名称: {job.name}")
                print(f"    下次运行: {job.next_run_time}")
                print(f"    触发器: {job.trigger}")
                print()
                
        except Exception as e:
            print(f"❌ 调度器测试失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_scheduler()