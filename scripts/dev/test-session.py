#!/usr/bin/env python3
"""
测试会话状态
"""

import requests
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_session():
    """测试会话状态"""
    print("🔍 测试会话状态...")
    
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
        
        # 2. 测试需要登录的页面
        print("2. 测试需要登录的页面...")
        
        # 测试dashboard
        response = session.get("http://localhost:5001/dashboard/")
        print(f"   dashboard状态码: {response.status_code}")
        
        # 测试instances
        response = session.get("http://localhost:5001/instances/")
        print(f"   instances状态码: {response.status_code}")
        
        # 测试credentials
        response = session.get("http://localhost:5001/credentials/")
        print(f"   credentials状态码: {response.status_code}")
        
        # 3. 检查会话cookie
        print("3. 检查会话cookie...")
        for cookie in session.cookies:
            print(f"   {cookie.name}: {cookie.value[:20]}...")
            
    else:
        print(f"❌ 登录失败: {response.status_code}")

if __name__ == "__main__":
    import re
    test_session()
