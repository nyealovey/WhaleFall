#!/usr/bin/env python3
"""
测试登录功能
"""

import requests
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_login():
    """测试登录功能"""
    print("🔍 测试登录功能...")
    
    # 创建会话
    session = requests.Session()
    
    # 1. 获取登录页面和CSRF令牌
    print("1. 获取登录页面...")
    response = session.get("http://localhost:5001/login")
    print(f"   状态码: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ 无法访问登录页面: {response.status_code}")
        return
    
    # 从HTML中提取CSRF令牌
    import re
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    if not csrf_match:
        print("❌ 无法找到CSRF令牌")
        return
    
    csrf_token = csrf_match.group(1)
    print(f"   CSRF令牌: {csrf_token[:20]}...")
    
    # 2. 尝试登录
    print("2. 尝试登录...")
    login_data = {
        "username": "admin",
        "password": "Admin123",
        "csrf_token": csrf_token
    }
    
    response = session.post("http://localhost:5001/login", data=login_data, allow_redirects=False)
    print(f"   状态码: {response.status_code}")
    print(f"   重定向到: {response.headers.get('Location', '无')}")
    
    if response.status_code == 302:
        print("✅ 登录成功，正在重定向")
        
        # 3. 跟随重定向
        redirect_url = response.headers.get('Location')
        if redirect_url:
            print(f"3. 跟随重定向到: {redirect_url}")
            response = session.get(f"http://localhost:5001{redirect_url}")
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ 重定向成功，页面正常加载")
            else:
                print(f"❌ 重定向失败: {response.status_code}")
    else:
        print(f"❌ 登录失败: {response.status_code}")
        print(f"   响应内容: {response.text[:200]}...")

if __name__ == "__main__":
    test_login()
