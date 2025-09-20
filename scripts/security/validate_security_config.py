#!/usr/bin/env python3
"""
安全配置验证脚本
检查是否存在硬编码密码和密钥，确保所有敏感信息都通过环境变量配置
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_hardcoded_credentials():
    """检查硬编码凭据"""
    print("🔍 检查硬编码凭据...")
    
    # 检查constants.py中的硬编码密码
    constants_file = project_root / "app" / "constants.py"
    if constants_file.exists():
        with open(constants_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否还有硬编码的密码
        hardcoded_patterns = [
            'postgresql://',
            'redis://:',
            'Taifish2024!',
            'localhost:5432',
            'localhost:6379'
        ]
        
        issues = []
        for pattern in hardcoded_patterns:
            if pattern in content:
                issues.append(f"发现硬编码模式: {pattern}")
        
        if issues:
            print("❌ 发现硬编码凭据:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("✅ 未发现硬编码凭据")
            return True
    else:
        print("⚠️  constants.py文件不存在")
        return False

def check_environment_variables():
    """检查必需的环境变量"""
    print("\n🔍 检查必需的环境变量...")
    
    required_vars = [
        'DATABASE_URL',
        'CACHE_REDIS_URL',
        'SECRET_KEY',
        'JWT_SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 缺少必需的环境变量:")
        for var in missing_vars:
            print(f"  - {var}")
        return False
    else:
        print("✅ 所有必需的环境变量都已设置")
        return True

def check_config_security():
    """检查配置安全性"""
    print("\n🔍 检查配置安全性...")
    
    # 检查config.py是否正确处理环境变量
    config_file = project_root / "app" / "config.py"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有正确的环境变量验证
        if "raise ValueError" in content and "DATABASE_URL" in content:
            print("✅ config.py正确验证环境变量")
            return True
        else:
            print("❌ config.py缺少环境变量验证")
            return False
    else:
        print("⚠️  config.py文件不存在")
        return False

def main():
    """主函数"""
    print("🔒 安全配置验证")
    print("=" * 50)
    
    # 执行所有检查
    checks = [
        check_hardcoded_credentials(),
        check_environment_variables(),
        check_config_security()
    ]
    
    # 汇总结果
    print("\n" + "=" * 50)
    if all(checks):
        print("✅ 所有安全检查通过")
        return 0
    else:
        print("❌ 发现安全问题，请修复后重试")
        return 1

if __name__ == "__main__":
    sys.exit(main())
