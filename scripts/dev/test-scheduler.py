#!/usr/bin/env python3
"""
测试调度器功能的简单脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'
os.environ['DATABASE_URL'] = 'postgresql+psycopg://whalefall_user:Dev2024!@localhost:5432/whalefall_dev'
os.environ['CACHE_REDIS_URL'] = 'redis://:RedisDev2024!@localhost:6379/0'

def test_scheduler():
    """测试调度器初始化"""
    print("🧪 测试调度器初始化...")
    
    try:
        # 导入调度器
        from app.scheduler import scheduler, init_scheduler
        
        print("✅ 调度器模块导入成功")
        
        # 创建模拟的Flask应用
        class MockApp:
            def __init__(self):
                self.config = {}
        
        app = MockApp()
        
        # 初始化调度器
        print("🚀 初始化调度器...")
        result = init_scheduler(app)
        
        if result:
            print("✅ 调度器初始化成功")
            
            # 测试获取任务
            print("📋 获取现有任务...")
            jobs = scheduler.get_jobs()
            print(f"✅ 找到 {len(jobs)} 个任务")
            
            # 停止调度器
            print("⏹️  停止调度器...")
            scheduler.stop()
            print("✅ 调度器已停止")
            
        else:
            print("❌ 调度器初始化失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scheduler()
