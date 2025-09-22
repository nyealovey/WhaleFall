#!/usr/bin/env python3
"""
检查Flask路由
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_routes():
    """检查Flask路由"""
    print("🔍 检查Flask路由...")
    
    try:
        from app import create_app
        
        # 创建应用上下文
        app = create_app()
        
        print("注册的路由:")
        for rule in app.url_map.iter_rules():
            print(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
            
    except Exception as e:
        print(f"❌ 检查路由时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_routes()
