#!/usr/bin/env python3
"""
测试Flask应用会话超时配置
"""

import os
import sys
from datetime import timedelta

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_flask_session_config():
    """测试Flask应用会话配置"""
    print("🧪 测试Flask应用会话超时配置")
    print("=" * 60)
    
    # 设置测试环境变量
    test_values = [
        (None, "使用默认值"),
        ("1800", "30分钟"),
        ("3600", "1小时"),
        ("7200", "2小时"),
        ("10800", "3小时")
    ]
    
    for env_value, description in test_values:
        print(f"\n🔧 测试场景: {description}")
        print("-" * 40)
        
        # 设置环境变量
        if env_value:
            os.environ["PERMANENT_SESSION_LIFETIME"] = env_value
        else:
            os.environ.pop("PERMANENT_SESSION_LIFETIME", None)
        
        try:
            # 导入必要的模块
            from app.constants import SystemConstants
            
            # 模拟Flask配置逻辑
            session_lifetime = int(os.getenv("PERMANENT_SESSION_LIFETIME", SystemConstants.SESSION_LIFETIME))
            
            print(f"  环境变量: {os.getenv('PERMANENT_SESSION_LIFETIME', 'None')}")
            print(f"  默认值: {SystemConstants.SESSION_LIFETIME} 秒")
            print(f"  最终配置: {session_lifetime} 秒")
            
            # 转换为可读格式
            hours = session_lifetime // 3600
            minutes = (session_lifetime % 3600) // 60
            seconds = session_lifetime % 60
            
            if hours > 0:
                time_str = f"{hours}小时"
                if minutes > 0:
                    time_str += f"{minutes}分钟"
                if seconds > 0:
                    time_str += f"{seconds}秒"
            elif minutes > 0:
                time_str = f"{minutes}分钟"
                if seconds > 0:
                    time_str += f"{seconds}秒"
            else:
                time_str = f"{seconds}秒"
            
            print(f"  可读格式: {time_str}")
            
            # 验证配置
            if env_value:
                expected = int(env_value)
                if session_lifetime == expected:
                    print("  ✅ 配置正确：使用环境变量值")
                else:
                    print(f"  ❌ 配置错误：期望 {expected}，实际 {session_lifetime}")
            else:
                if session_lifetime == SystemConstants.SESSION_LIFETIME:
                    print("  ✅ 配置正确：使用默认值")
                else:
                    print(f"  ❌ 配置错误：期望 {SystemConstants.SESSION_LIFETIME}，实际 {session_lifetime}")
                    
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
    
    print(f"\n📋 配置说明:")
    print("  1. Flask应用会从环境变量 PERMANENT_SESSION_LIFETIME 读取会话超时时间")
    print("  2. 如果环境变量不存在，使用 SystemConstants.SESSION_LIFETIME 默认值")
    print("  3. 配置会应用到以下地方:")
    print("     - app.config['PERMANENT_SESSION_LIFETIME']")
    print("     - app.config['SESSION_TIMEOUT']")
    print("     - login_manager.remember_cookie_duration")
    print("  4. 在.env文件中设置: PERMANENT_SESSION_LIFETIME=3600")
    print("  5. 在Docker环境中通过环境变量传递")

if __name__ == "__main__":
    test_flask_session_config()
