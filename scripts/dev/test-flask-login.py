#!/usr/bin/env python3
"""
测试Flask-Login会话
"""

import requests
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_flask_login():
    """测试Flask-Login会话"""
    print("🔍 测试Flask-Login会话...")
    
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
    print(f"   重定向到: {response.headers.get('Location', '无')}")
    
    if response.status_code == 302:
        print("✅ 登录成功")
        
        # 2. 检查会话cookie
        print("2. 检查会话cookie...")
        for cookie in session.cookies:
            print(f"   {cookie.name}: {cookie.value[:30]}...")
        
        # 3. 测试Flask-Login会话
        print("3. 测试Flask-Login会话...")
        
        # 测试profile页面（需要登录）
        response = session.get("http://localhost:5001/profile")
        print(f"   /profile 状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Flask-Login会话正常")
        else:
            print(f"   ❌ Flask-Login会话失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
        
        # 测试logout页面（需要登录）
        response = session.get("http://localhost:5001/logout")
        print(f"   /logout 状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ logout页面可访问")
        else:
            print(f"   ❌ logout页面失败: {response.status_code}")
            
    else:
        print(f"❌ 登录失败: {response.status_code}")
        print(f"   响应内容: {response.text[:200]}...")

if __name__ == "__main__":
    import re
    test_flask_login()
