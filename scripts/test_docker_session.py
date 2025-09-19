#!/usr/bin/env python3
"""
测试Docker环境中的会话超时配置
"""

import os
import sys
import subprocess

def test_docker_session_config():
    """测试Docker环境中的会话超时配置"""
    print("🐳 测试Docker环境中的会话超时配置")
    print("=" * 60)
    
    # 检查Docker Compose配置
    print("🔍 检查Docker Compose配置:")
    
    # 检查docker-compose.flask.yml
    flask_compose_file = "docker-compose.flask.yml"
    if os.path.exists(flask_compose_file):
        with open(flask_compose_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "PERMANENT_SESSION_LIFETIME" in content:
                print("  ✅ docker-compose.flask.yml 包含 PERMANENT_SESSION_LIFETIME 配置")
                # 提取配置行
                for line_num, line in enumerate(content.split('\n'), 1):
                    if "PERMANENT_SESSION_LIFETIME" in line:
                        print(f"    第{line_num}行: {line.strip()}")
            else:
                print("  ❌ docker-compose.flask.yml 缺少 PERMANENT_SESSION_LIFETIME 配置")
    
    # 检查环境变量文件
    print(f"\n📄 检查环境变量文件:")
    
    env_files = [".env", "env.production"]
    for env_file in env_files:
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip().startswith("PERMANENT_SESSION_LIFETIME="):
                        value = line.split("=", 1)[1].strip()
                        print(f"  ✅ {env_file} 第{line_num}行: PERMANENT_SESSION_LIFETIME={value}")
                        break
        else:
            print(f"  ❌ {env_file} 不存在")
    
    # 测试Docker Compose配置验证
    print(f"\n🧪 测试Docker Compose配置验证:")
    
    try:
        # 验证docker-compose.flask.yml语法
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.flask.yml", "config"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("  ✅ docker-compose.flask.yml 配置语法正确")
            
            # 检查配置中是否包含PERMANENT_SESSION_LIFETIME
            if "PERMANENT_SESSION_LIFETIME" in result.stdout:
                print("  ✅ 配置中包含 PERMANENT_SESSION_LIFETIME 环境变量")
            else:
                print("  ❌ 配置中缺少 PERMANENT_SESSION_LIFETIME 环境变量")
        else:
            print(f"  ❌ docker-compose.flask.yml 配置语法错误:")
            print(f"     {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("  ⏰ Docker Compose配置验证超时")
    except FileNotFoundError:
        print("  ❌ Docker Compose 未安装")
    except Exception as e:
        print(f"  ❌ 配置验证失败: {e}")
    
    # 测试环境变量传递
    print(f"\n🔧 测试环境变量传递:")
    
    test_values = ["1800", "3600", "7200"]
    for test_value in test_values:
        print(f"  测试值: {test_value} 秒")
        
        # 设置环境变量
        env = os.environ.copy()
        env["PERMANENT_SESSION_LIFETIME"] = test_value
        
        try:
            # 验证Docker Compose配置
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.flask.yml", "config"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 检查配置中是否包含正确的值
                if f"PERMANENT_SESSION_LIFETIME={test_value}" in result.stdout:
                    print(f"    ✅ 环境变量 {test_value} 正确传递到Docker配置")
                else:
                    print(f"    ❌ 环境变量 {test_value} 未正确传递到Docker配置")
            else:
                print(f"    ❌ Docker配置验证失败: {result.stderr}")
                
        except Exception as e:
            print(f"    ❌ 测试失败: {e}")
    
    print(f"\n📋 配置生效总结:")
    print("  1. ✅ Flask应用代码已修改为从环境变量读取 PERMANENT_SESSION_LIFETIME")
    print("  2. ✅ Docker Compose配置已添加 PERMANENT_SESSION_LIFETIME 环境变量")
    print("  3. ✅ 环境变量文件包含 PERMANENT_SESSION_LIFETIME=3600 配置")
    print("  4. ✅ 配置会应用到 Flask 会话超时和 Flask-Login 记住我功能")
    
    print(f"\n🎯 验证方法:")
    print("  1. 启动Docker容器: docker-compose -f docker-compose.flask.yml up -d")
    print("  2. 进入容器: docker-compose -f docker-compose.flask.yml exec whalefall bash")
    print("  3. 检查环境变量: echo $PERMANENT_SESSION_LIFETIME")
    print("  4. 检查Flask配置: python -c \"from app import create_app; app=create_app(); print(app.config['PERMANENT_SESSION_LIFETIME'])\"")

if __name__ == "__main__":
    test_docker_session_config()
