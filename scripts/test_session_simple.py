#!/usr/bin/env python3
"""
简单测试会话超时配置
"""

import os
import sys

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_session_timeout_simple():
    """简单测试会话超时配置"""
    print("🧪 简单测试会话超时配置")
    print("=" * 50)
    
    # 检查环境变量
    env_session_lifetime = os.getenv("PERMANENT_SESSION_LIFETIME")
    print(f"📊 环境变量 PERMANENT_SESSION_LIFETIME: {env_session_lifetime}")
    
    # 检查.env文件
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip().startswith("PERMANENT_SESSION_LIFETIME="):
                    value = line.split("=", 1)[1].strip()
                    print(f"📄 .env文件第{line_num}行: PERMANENT_SESSION_LIFETIME={value}")
                    break
    else:
        print("❌ .env文件不存在")
    
    # 检查env.production文件
    prod_env_file_path = "env.production"
    if os.path.exists(prod_env_file_path):
        with open(prod_env_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip().startswith("PERMANENT_SESSION_LIFETIME="):
                    value = line.split("=", 1)[1].strip()
                    print(f"📄 env.production文件第{line_num}行: PERMANENT_SESSION_LIFETIME={value}")
                    break
    else:
        print("❌ env.production文件不存在")
    
    # 检查SystemConstants
    try:
        from app.constants import SystemConstants
        print(f"📊 SystemConstants.SESSION_LIFETIME: {SystemConstants.SESSION_LIFETIME} 秒")
        
        # 转换为可读格式
        hours = SystemConstants.SESSION_LIFETIME // 3600
        minutes = (SystemConstants.SESSION_LIFETIME % 3600) // 60
        seconds = SystemConstants.SESSION_LIFETIME % 60
        print(f"📅 默认会话超时时间: {hours}小时 {minutes}分钟 {seconds}秒")
        
    except ImportError as e:
        print(f"❌ 无法导入SystemConstants: {e}")
    
    # 测试环境变量读取
    print(f"\n🧪 测试环境变量读取:")
    test_values = [1800, 3600, 7200]  # 30分钟, 1小时, 2小时
    
    for test_value in test_values:
        os.environ["PERMANENT_SESSION_LIFETIME"] = str(test_value)
        read_value = os.getenv("PERMANENT_SESSION_LIFETIME")
        hours = int(read_value) // 3600
        minutes = (int(read_value) % 3600) // 60
        print(f"  设置 {test_value} 秒 -> 读取 {read_value} 秒 ({hours}小时{minutes}分钟)")
    
    # 检查Flask配置逻辑
    print(f"\n🔍 Flask配置逻辑检查:")
    print("  1. 环境变量 PERMANENT_SESSION_LIFETIME 存在时，使用环境变量值")
    print("  2. 环境变量不存在时，使用 SystemConstants.SESSION_LIFETIME 默认值")
    print("  3. 配置应用到:")
    print("     - app.config['PERMANENT_SESSION_LIFETIME']")
    print("     - app.config['SESSION_TIMEOUT']")
    print("     - login_manager.remember_cookie_duration")

if __name__ == "__main__":
    test_session_timeout_simple()
