#!/usr/bin/env python3
"""
测试用户会话状态
"""

import requests
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_user_session():
    """测试用户会话状态"""
    print("🔍 测试用户会话状态...")
    
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
        
        # 3. 测试需要登录的API
        print("3. 测试需要登录的API...")
        
        # 测试auth.me接口
        response = session.get("http://localhost:5001/api/me")
        print(f"   /api/me 状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应: {response.text}")
        else:
            print(f"   错误: {response.text[:100]}")
        
        # 测试dashboard API
        response = session.get("http://localhost:5001/dashboard/api/overview")
        print(f"   /dashboard/api/overview 状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应: {response.text[:100]}")
        else:
            print(f"   错误: {response.text[:100]}")
            
    else:
        print(f"❌ 登录失败: {response.status_code}")
        print(f"   响应内容: {response.text[:200]}...")

if __name__ == "__main__":
    import re
    test_user_session()
