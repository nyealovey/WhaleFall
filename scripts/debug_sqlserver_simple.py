#!/usr/bin/env python3
"""
简单的SQL Server调试脚本
逐步测试每个查询
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.connection_factory import ConnectionFactory
from app.models.instance import Instance

def debug_sqlserver_step_by_step(instance_id: int):
    """逐步调试SQL Server查询"""
    
    instance = Instance.query.get(instance_id)
    if not instance:
        print(f"❌ 实例 {instance_id} 不存在")
        return
    
    print(f"🔍 SQL Server逐步调试")
    print(f"   实例: {instance.name}")
    print(f"   主机: {instance.host}:{instance.port}")
    print(f"   凭据: {instance.credential.username if instance.credential else 'None'}")
    print("="*50)
    
    conn = ConnectionFactory.create_connection(instance)
    
    try:
        if not conn.connect():
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        print(f"   驱动类型: {conn.driver_type}")
        
        # 步骤1: 获取当前用户
        print("\n步骤1: 获取当前用户")
        try:
            result = conn.execute_query("SELECT SUSER_NAME() as [current_user]")
            current_user = result[0][0] if result else None
            print(f"✅ 当前用户: {current_user}")
        except Exception as e:
            print(f"❌ 获取当前用户失败: {e}")
            return
        
        # 步骤2: 检查sysadmin
        print(f"\n步骤2: 检查sysadmin权限")
        try:
            sql = "SELECT IS_SRVROLEMEMBER('sysadmin', %s) as is_sysadmin"
            result = conn.execute_query(sql, (current_user,))
            is_sysadmin = bool(result[0][0]) if result else False
            print(f"✅ 是否为sysadmin: {is_sysadmin}")
        except Exception as e:
            print(f"❌ 检查sysadmin失败: {e}")
            return
        
        # 步骤3: 获取数据库列表
        print(f"\n步骤3: 获取数据库列表")
        try:
            databases_sql = "SELECT name FROM sys.databases WHERE state = 0"
            databases = conn.execute_query(databases_sql)
            print(f"✅ 找到 {len(databases)} 个数据库: {[row[0] for row in databases]}")
        except Exception as e:
            print(f"❌ 获取数据库列表失败: {e}")
            return
        
        # 步骤4: 测试第一个数据库的查询
        if databases:
            db_name = databases[0][0]
            print(f"\n步骤4: 测试数据库 {db_name} 的查询")
            
            # 4.1: 测试用户是否在数据库中
            print(f"   4.1: 检查用户是否在数据库中")
            try:
                user_check_sql = f"""
                    SELECT name, type_desc
                    FROM [{db_name}].sys.database_principals
                    WHERE name = %s
                """
                result = conn.execute_query(user_check_sql, (current_user,))
                if result:
                    print(f"   ✅ 用户在数据库中: {result[0]}")
                else:
                    print(f"   ⚠️  用户不在数据库中")
            except Exception as e:
                print(f"   ❌ 检查用户失败: {e}")
            
            # 4.2: 测试数据库角色查询
            print(f"   4.2: 测试数据库角色查询")
            try:
                roles_sql = f"""
                    SELECT r.name
                    FROM [{db_name}].sys.database_role_members rm
                    JOIN [{db_name}].sys.database_principals r ON rm.role_principal_id = r.principal_id
                    JOIN [{db_name}].sys.database_principals p ON rm.member_principal_id = p.principal_id
                    WHERE p.name = %s
                """
                result = conn.execute_query(roles_sql, (current_user,))
                print(f"   ✅ 数据库角色: {[row[0] for row in result]}")
            except Exception as e:
                print(f"   ❌ 数据库角色查询失败: {e}")
                print(f"   错误详情: {str(e)}")
            
            # 4.3: 测试数据库权限查询
            print(f"   4.3: 测试数据库权限查询")
            try:
                perms_sql = f"""
                    SELECT permission_name
                    FROM [{db_name}].sys.database_permissions
                    WHERE grantee_principal_id = (
                        SELECT principal_id
                        FROM [{db_name}].sys.database_principals
                        WHERE name = %s
                    )
                    AND state = 'G'
                """
                result = conn.execute_query(perms_sql, (current_user,))
                print(f"   ✅ 数据库权限: {[row[0] for row in result]}")
            except Exception as e:
                print(f"   ❌ 数据库权限查询失败: {e}")
                print(f"   错误详情: {str(e)}")
            
            # 4.4: 如果是sysadmin，测试特殊查询
            if is_sysadmin:
                print(f"   4.4: 测试sysadmin特殊查询")
                
                # 测试固定角色查询
                try:
                    fixed_roles_sql = f"""
                        SELECT r.name
                        FROM [{db_name}].sys.database_principals r
                        WHERE r.type = 'R' AND r.is_fixed_role = 1
                        ORDER BY r.name
                    """
                    result = conn.execute_query(fixed_roles_sql)
                    print(f"   ✅ 固定角色: {[row[0] for row in result]}")
                except Exception as e:
                    print(f"   ❌ 固定角色查询失败: {e}")
                
                # 测试所有权限查询
                try:
                    all_perms_sql = f"""
                        SELECT DISTINCT permission_name
                        FROM [{db_name}].sys.database_permissions
                        WHERE state = 'G'
                        ORDER BY permission_name
                    """
                    result = conn.execute_query(all_perms_sql)
                    print(f"   ✅ 所有权限: {[row[0] for row in result]}")
                except Exception as e:
                    print(f"   ❌ 所有权限查询失败: {e}")
        
        print("\n" + "="*50)
        print("🎉 逐步调试完成！")
        
    except Exception as e:
        print(f"❌ 调试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_sqlserver_simple.py <instance_id>")
        print("示例: python debug_sqlserver_simple.py 1")
        sys.exit(1)
    
    # 创建Flask应用上下文
    app = create_app()
    with app.app_context():
        instance_id = int(sys.argv[1])
        debug_sqlserver_step_by_step(instance_id)
