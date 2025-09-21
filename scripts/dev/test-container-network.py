#!/usr/bin/env python3
"""
测试Docker容器网络连接
验证服务名解析和容器间通信
"""

import subprocess
import sys
import time

def run_command(cmd):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_network_connectivity():
    """测试网络连接性"""
    print("🔍 测试Docker容器网络连接...")
    
    # 1. 检查Docker Compose服务状态
    print("\n1. 检查服务状态:")
    success, stdout, stderr = run_command("docker compose -f docker-compose.prod.yml ps")
    if success:
        print("✅ 服务状态:")
        print(stdout)
    else:
        print("❌ 无法获取服务状态:")
        print(stderr)
        return False
    
    # 2. 检查网络配置
    print("\n2. 检查网络配置:")
    success, stdout, stderr = run_command("docker network ls | grep whalefall")
    if success:
        print("✅ 网络列表:")
        print(stdout)
    else:
        print("❌ 无法获取网络信息:")
        print(stderr)
    
    # 3. 检查容器IP地址
    print("\n3. 检查容器IP地址:")
    containers = ["whalefall_postgres_prod", "whalefall_redis_prod", "whalefall_app_prod"]
    for container in containers:
        success, stdout, stderr = run_command(f"docker inspect {container} --format='{{{{.NetworkSettings.IPAddress}}}}'")
        if success and stdout.strip():
            print(f"✅ {container}: {stdout.strip()}")
        else:
            print(f"❌ {container}: 无法获取IP")
    
    # 4. 测试服务名解析
    print("\n4. 测试服务名解析:")
    success, stdout, stderr = run_command("docker exec whalefall_app_prod nslookup postgres")
    if success:
        print("✅ postgres 服务名解析:")
        print(stdout)
    else:
        print("❌ postgres 服务名解析失败:")
        print(stderr)
    
    # 5. 测试数据库连接
    print("\n5. 测试数据库连接:")
    success, stdout, stderr = run_command("docker exec whalefall_app_prod python -c \"import psycopg2; conn = psycopg2.connect('postgresql://whalefall_user:whalefall_password@postgres:5432/whalefall_prod'); print('✅ 数据库连接成功'); conn.close()\"")
    if success:
        print("✅ 数据库连接测试通过")
    else:
        print("❌ 数据库连接测试失败:")
        print(stderr)
    
    # 6. 测试Redis连接
    print("\n6. 测试Redis连接:")
    success, stdout, stderr = run_command("docker exec whalefall_app_prod python -c \"import redis; r = redis.Redis(host='redis', port=6379, password='whalefall_redis_password'); r.ping(); print('✅ Redis连接成功')\"")
    if success:
        print("✅ Redis连接测试通过")
    else:
        print("❌ Redis连接测试失败:")
        print(stderr)
    
    return True

def main():
    """主函数"""
    print("🐟 Docker容器网络连接测试")
    print("=" * 50)
    
    # 检查Docker是否运行
    success, _, _ = run_command("docker --version")
    if not success:
        print("❌ Docker未运行或未安装")
        sys.exit(1)
    
    # 检查Docker Compose是否运行
    success, _, _ = run_command("docker compose --version")
    if not success:
        print("❌ Docker Compose未运行或未安装")
        sys.exit(1)
    
    # 运行网络测试
    test_network_connectivity()
    
    print("\n" + "=" * 50)
    print("🎉 网络连接测试完成")

if __name__ == "__main__":
    main()
