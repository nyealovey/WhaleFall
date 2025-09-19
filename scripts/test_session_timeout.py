#!/usr/bin/env python3
"""
测试会话超时配置是否生效
"""

import os
import sys
from datetime import timedelta

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.constants import SystemConstants

def test_session_timeout_config():
    """测试会话超时配置"""
    print("🧪 测试会话超时配置")
    print("=" * 50)
    
    # 创建Flask应用
    app = create_app()
    
    with app.app_context():
        # 获取配置的会话超时时间
        permanent_session_lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
        session_timeout = app.config.get("SESSION_TIMEOUT")
        
        print(f"📊 配置信息:")
        print(f"  PERMANENT_SESSION_LIFETIME: {permanent_session_lifetime} 秒")
        print(f"  SESSION_TIMEOUT: {session_timeout} 秒")
        print(f"  SystemConstants.SESSION_LIFETIME: {SystemConstants.SESSION_LIFETIME} 秒")
        
        # 检查环境变量
        env_session_lifetime = os.getenv("PERMANENT_SESSION_LIFETIME")
        print(f"  环境变量 PERMANENT_SESSION_LIFETIME: {env_session_lifetime}")
        
        # 转换为可读格式
        if permanent_session_lifetime:
            hours = permanent_session_lifetime // 3600
            minutes = (permanent_session_lifetime % 3600) // 60
            seconds = permanent_session_lifetime % 60
            print(f"  📅 会话超时时间: {hours}小时 {minutes}分钟 {seconds}秒")
        
        # 验证配置是否正确
        if env_session_lifetime:
            expected_lifetime = int(env_session_lifetime)
            if permanent_session_lifetime == expected_lifetime:
                print("✅ 会话超时配置正确：从环境变量读取")
            else:
                print(f"❌ 会话超时配置错误：期望 {expected_lifetime}，实际 {permanent_session_lifetime}")
        else:
            if permanent_session_lifetime == SystemConstants.SESSION_LIFETIME:
                print("✅ 会话超时配置正确：使用默认值")
            else:
                print(f"❌ 会话超时配置错误：期望 {SystemConstants.SESSION_LIFETIME}，实际 {permanent_session_lifetime}")
        
        # 检查Flask-Login配置
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        print(f"\n🔐 Flask-Login配置:")
        print(f"  remember_cookie_duration: {login_manager.remember_cookie_duration} 秒")
        
        if login_manager.remember_cookie_duration == permanent_session_lifetime:
            print("✅ Flask-Login配置正确：与PERMANENT_SESSION_LIFETIME一致")
        else:
            print(f"❌ Flask-Login配置错误：期望 {permanent_session_lifetime}，实际 {login_manager.remember_cookie_duration}")
        
        # 测试不同的环境变量值
        print(f"\n🧪 测试不同环境变量值:")
        test_values = [1800, 7200, 10800]  # 30分钟, 2小时, 3小时
        
        for test_value in test_values:
            os.environ["PERMANENT_SESSION_LIFETIME"] = str(test_value)
            # 重新创建应用以测试新配置
            test_app = create_app()
            with test_app.app_context():
                test_lifetime = test_app.config.get("PERMANENT_SESSION_LIFETIME")
                hours = test_lifetime // 3600
                minutes = (test_lifetime % 3600) // 60
                print(f"  设置 {test_value} 秒 -> 实际配置 {test_lifetime} 秒 ({hours}小时{minutes}分钟)")

if __name__ == "__main__":
    test_session_timeout_config()
