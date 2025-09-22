#!/usr/bin/env python3
"""
测试简单路由
"""

import requests
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_simple_route():
    """测试简单路由"""
    print("🔍 测试简单路由...")
    
    # 创建会话
    session = requests.Session()
    
    # 1. 登录
    print("1. 登录...")
    response = session.get("http://localhost:5001/login")
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    csrf_token = csrf_match.group(1)
    
    login_data = {
        "username": "admin",
        "password": "Admin123",
        "csrf_token": csrf_token
    }
    
    response = session.post("http://localhost:5001/login", data=login_data, allow_redirects=False)
    print(f"   登录状态码: {response.status_code}")
    
    if response.status_code == 302:
        print("✅ 登录成功")
        
        # 2. 测试各种路由
        print("2. 测试各种路由...")
        
        routes = [
            ("/", "首页"),
            ("/profile", "用户资料"),
            ("/logout", "登出"),
            ("/dashboard/", "仪表板"),
            ("/instances/", "实例管理"),
            ("/credentials/", "凭据管理"),
            ("/accounts/", "账户管理"),
            ("/logs/", "日志管理"),
        ]
        
        for route, name in routes:
            response = session.get(f"http://localhost:5001{route}")
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {name} ({route}): {response.status_code}")
            
    else:
        print(f"❌ 登录失败: {response.status_code}")

if __name__ == "__main__":
    import re
    test_simple_route()
