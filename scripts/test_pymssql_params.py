#!/usr/bin/env python3
"""
测试pymssql参数处理
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.connection_factory import ConnectionFactory
from app.models.instance import Instance

def test_pymssql_parameters(instance_id: int):
    """测试pymssql参数处理"""
    
    instance = Instance.query.get(instance_id)
    if not instance:
        print(f"❌ 实例 {instance_id} 不存在")
        return
    
    print(f"🔍 测试pymssql参数处理")
    print(f"   实例: {instance.name}")
    print(f"   主机: {instance.host}:{instance.port}")
    print()
    
    conn = ConnectionFactory.create_connection(instance)
    
    try:
        if not conn.connect():
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        print(f"   驱动类型: {conn.driver_type}")
        
        # 测试1: 无参数查询
        print("\n1️⃣ 测试无参数查询...")
        try:
            result = conn.execute_query("SELECT 1 as test")
            print(f"   ✅ 无参数查询成功: {result}")
        except Exception as e:
            print(f"   ❌ 无参数查询失败: {e}")
        
        # 测试2: 单参数查询
        print("\n2️⃣ 测试单参数查询...")
        try:
            result = conn.execute_query("SELECT SUSER_NAME() as [current_user]")
            current_user = result[0][0] if result else None
            print(f"   ✅ 单参数查询成功: {current_user}")
        except Exception as e:
            print(f"   ❌ 单参数查询失败: {e}")
            return
        
        # 测试3: 带参数的查询
        print(f"\n3️⃣ 测试带参数查询 (用户: {current_user})...")
        try:
            # 测试服务器角色查询
            sql = """
                SELECT r.name
                FROM sys.server_role_members rm
                JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
                JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
                WHERE p.name = %s
            """
            result = conn.execute_query(sql, (current_user,))
            print(f"   ✅ 带参数查询成功: {[row[0] for row in result]}")
        except Exception as e:
            print(f"   ❌ 带参数查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试4: 直接使用pymssql
        print(f"\n4️⃣ 测试直接使用pymssql...")
        try:
            cursor = conn.connection.cursor()
            sql = """
                SELECT r.name
                FROM sys.server_role_members rm
                JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
                JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
                WHERE p.name = %s
            """
            cursor.execute(sql, (current_user,))
            result = cursor.fetchall()
            cursor.close()
            print(f"   ✅ 直接pymssql查询成功: {[row[0] for row in result]}")
        except Exception as e:
            print(f"   ❌ 直接pymssql查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试5: 测试数据库查询
        print(f"\n5️⃣ 测试数据库查询...")
        try:
            # 获取数据库列表
            databases_sql = "SELECT name FROM sys.databases WHERE state = 0"
            databases = conn.execute_query(databases_sql)
            print(f"   ✅ 数据库列表: {[row[0] for row in databases]}")
            
            if databases:
                db_name = databases[0][0]
                print(f"   🔍 测试数据库: {db_name}")
                
                # 测试跨数据库查询
                roles_sql = f"""
                    SELECT r.name
                    FROM [{db_name}].sys.database_role_members rm
                    JOIN [{db_name}].sys.database_principals r ON rm.role_principal_id = r.principal_id
                    JOIN [{db_name}].sys.database_principals p ON rm.member_principal_id = p.principal_id
                    WHERE p.name = %s
                """
                result = conn.execute_query(roles_sql, (current_user,))
                print(f"   ✅ 跨数据库查询成功: {[row[0] for row in result]}")
                
        except Exception as e:
            print(f"   ❌ 数据库查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*50)
        print("🎉 pymssql参数测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_pymssql_params.py <instance_id>")
        print("示例: python test_pymssql_params.py 1")
        sys.exit(1)
    
    # 创建Flask应用上下文
    app = create_app()
    with app.app_context():
        instance_id = int(sys.argv[1])
        test_pymssql_parameters(instance_id)
