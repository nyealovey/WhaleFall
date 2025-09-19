#!/usr/bin/env python3
"""
Oracle连接测试脚本
用于测试Oracle数据库连接是否正常
"""

import os
import sys
import oracledb
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_oracle_import():
    """测试Oracle驱动导入"""
    try:
        import oracledb
        print("✅ Oracle驱动导入成功")
        print(f"   版本: {oracledb.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Oracle驱动导入失败: {e}")
        return False

def test_oracle_client_libs():
    """测试Oracle客户端库文件"""
    try:
        # 检查Oracle客户端库
        client_lib_path = oracledb.init_oracle_client()
        print(f"✅ Oracle客户端库加载成功")
        print(f"   路径: {client_lib_path}")
        return True
    except Exception as e:
        print(f"❌ Oracle客户端库加载失败: {e}")
        print("   请确保已安装Oracle Instant Client")
        return False

def test_oracle_connection():
    """测试Oracle数据库连接"""
    # 从环境变量或配置文件读取连接信息
    host = os.getenv('ORACLE_HOST', 'localhost')
    port = os.getenv('ORACLE_PORT', '1521')
    service_name = os.getenv('ORACLE_SERVICE', 'XE')
    username = os.getenv('ORACLE_USER', 'system')
    password = os.getenv('ORACLE_PASSWORD', 'oracle')
    
    try:
        # 构建连接字符串
        dsn = f"{host}:{port}/{service_name}"
        print(f"🔗 尝试连接Oracle数据库: {dsn}")
        
        # 建立连接
        with oracledb.connect(
            user=username,
            password=password,
            dsn=dsn
        ) as connection:
            print("✅ Oracle数据库连接成功")
            
            # 执行简单查询
            with connection.cursor() as cursor:
                cursor.execute("SELECT SYSDATE FROM DUAL")
                result = cursor.fetchone()
                print(f"   服务器时间: {result[0]}")
                
                # 查询版本信息
                cursor.execute("SELECT * FROM V$VERSION WHERE ROWNUM = 1")
                version = cursor.fetchone()
                print(f"   数据库版本: {version[0]}")
            
            return True
            
    except Exception as e:
        print(f"❌ Oracle数据库连接失败: {e}")
        print("   请检查连接参数和网络连接")
        return False

def test_oracle_connection_pool():
    """测试Oracle连接池"""
    try:
        # 创建连接池
        pool = oracledb.create_pool(
            user=os.getenv('ORACLE_USER', 'system'),
            password=os.getenv('ORACLE_PASSWORD', 'oracle'),
            dsn=f"{os.getenv('ORACLE_HOST', 'localhost')}:{os.getenv('ORACLE_PORT', '1521')}/{os.getenv('ORACLE_SERVICE', 'XE')}",
            min=1,
            max=5,
            increment=1
        )
        
        print("✅ Oracle连接池创建成功")
        
        # 测试从连接池获取连接
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'Connection Pool Test' FROM DUAL")
                result = cursor.fetchone()
                print(f"   连接池测试: {result[0]}")
        
        pool.close()
        return True
        
    except Exception as e:
        print(f"❌ Oracle连接池测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 Oracle连接测试开始...")
    print("=" * 50)
    
    # 测试步骤
    tests = [
        ("Oracle驱动导入", test_oracle_import),
        ("Oracle客户端库", test_oracle_client_libs),
        ("Oracle数据库连接", test_oracle_connection),
        ("Oracle连接池", test_oracle_connection_pool),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 测试: {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print("-" * 30)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！Oracle连接配置正常。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查Oracle配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
