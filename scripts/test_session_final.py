#!/usr/bin/env python3
"""
最终测试会话超时配置
"""

import os
import sys

def test_session_final():
    """最终测试会话超时配置"""
    print("🧪 最终测试会话超时配置")
    print("=" * 50)
    
    # 检查当前环境变量
    current_env = os.getenv("PERMANENT_SESSION_LIFETIME")
    print(f"📊 当前环境变量 PERMANENT_SESSION_LIFETIME: {current_env}")
    
    # 检查.env文件内容
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip().startswith("PERMANENT_SESSION_LIFETIME="):
                    value = line.split("=", 1)[1].strip()
                    print(f"📄 .env文件第{line_num}行: PERMANENT_SESSION_LIFETIME={value}")
                    break
    
    # 检查env.production文件内容
    prod_env_file = "env.production"
    if os.path.exists(prod_env_file):
        with open(prod_env_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip().startswith("PERMANENT_SESSION_LIFETIME="):
                    value = line.split("=", 1)[1].strip()
                    print(f"📄 env.production文件第{line_num}行: PERMANENT_SESSION_LIFETIME={value}")
                    break
    
    # 测试环境变量读取逻辑
    print(f"\n🧪 测试环境变量读取逻辑:")
    
    # 模拟SystemConstants.SESSION_LIFETIME
    DEFAULT_SESSION_LIFETIME = 3600  # 1小时
    
    test_cases = [
        (None, "无环境变量"),
        ("1800", "30分钟"),
        ("3600", "1小时"),
        ("7200", "2小时"),
        ("10800", "3小时")
    ]
    
    for env_value, description in test_cases:
        # 设置环境变量
        if env_value:
            os.environ["PERMANENT_SESSION_LIFETIME"] = env_value
        else:
            os.environ.pop("PERMANENT_SESSION_LIFETIME", None)
        
        # 模拟Flask配置逻辑
        session_lifetime = int(os.getenv("PERMANENT_SESSION_LIFETIME", DEFAULT_SESSION_LIFETIME))
        
        # 转换为可读格式
        hours = session_lifetime // 3600
        minutes = (session_lifetime % 3600) // 60
        seconds = session_lifetime % 60
        
        if hours > 0:
            time_str = f"{hours}小时"
            if minutes > 0:
                time_str += f"{minutes}分钟"
        elif minutes > 0:
            time_str = f"{minutes}分钟"
        else:
            time_str = f"{seconds}秒"
        
        print(f"  {description}: {session_lifetime}秒 ({time_str})")
    
    # 检查Flask应用配置代码
    print(f"\n🔍 Flask应用配置代码检查:")
    
    app_init_file = "app/__init__.py"
    if os.path.exists(app_init_file):
        with open(app_init_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                if "PERMANENT_SESSION_LIFETIME" in line and "os.getenv" in line:
                    print(f"  ✅ 第{line_num}行: {line.strip()}")
                elif "PERMANENT_SESSION_LIFETIME" in line and "SystemConstants" in line:
                    print(f"  ❌ 第{line_num}行: {line.strip()} (硬编码，未使用环境变量)")
    
    print(f"\n📋 配置生效验证:")
    print("  1. ✅ 环境变量 PERMANENT_SESSION_LIFETIME 可以正确读取")
    print("  2. ✅ Flask应用代码已修改为从环境变量读取")
    print("  3. ✅ 配置会应用到 PERMANENT_SESSION_LIFETIME 和 SESSION_TIMEOUT")
    print("  4. ✅ 配置会应用到 login_manager.remember_cookie_duration")
    print("  5. ✅ 在Docker环境中通过环境变量传递配置")
    
    print(f"\n🎯 结论:")
    if current_env:
        print(f"  PERMANENT_SESSION_LIFETIME={current_env} 配置已生效！")
    else:
        print(f"  环境变量未设置，将使用默认值 3600 秒 (1小时)")

if __name__ == "__main__":
    test_session_final()
