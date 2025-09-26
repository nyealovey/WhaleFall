#!/usr/bin/env python3
"""
MySQL 容量采集调试脚本
用于诊断 MySQL 实例的容量采集问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.instance import Instance
from app.services.database_size_collector_service import DatabaseSizeCollectorService

def debug_mysql_capacity(instance_id):
    """调试指定实例的MySQL容量采集"""
    app = create_app()
    
    with app.app_context():
        # 获取实例
        instance = Instance.query.get(instance_id)
        if not instance:
            print(f"❌ 实例 {instance_id} 不存在")
            return
            
        print(f"🔍 调试实例: {instance.name} (ID: {instance_id})")
        print(f"   类型: {instance.db_type}")
        print(f"   主机: {instance.host}:{instance.port}")
        print(f"   状态: {'启用' if instance.is_active else '禁用'}")
        print(f"   凭据: {'有' if instance.credential else '无'}")
        
        if not instance.is_active:
            print("❌ 实例已禁用")
            return
            
        if not instance.credential:
            print("❌ 实例缺少连接凭据")
            return
        
        if instance.db_type != 'mysql':
            print(f"❌ 实例类型不是 MySQL，而是 {instance.db_type}")
            return
        
        # 创建采集服务
        collector = DatabaseSizeCollectorService(instance)
        
        # 测试连接
        print("\n🔌 测试数据库连接...")
        if not collector.connect():
            print("❌ 数据库连接失败")
            return
        print("✅ 数据库连接成功")
        
        # 测试权限
        print("\n🔐 测试MySQL权限...")
        try:
            # 测试 information_schema 访问权限
            test_query = "SELECT COUNT(*) FROM information_schema.SCHEMATA"
            test_result = collector.db_connection.execute_query(test_query)
            if test_result:
                print(f"✅ information_schema.SCHEMATA 访问正常: {test_result[0][0]} 个数据库")
            else:
                print("❌ 无法访问 information_schema.SCHEMATA")
                return
            
            # 测试 tables 表访问权限
            test_query2 = "SELECT COUNT(*) FROM information_schema.tables LIMIT 1"
            test_result2 = collector.db_connection.execute_query(test_query2)
            if test_result2:
                print(f"✅ information_schema.tables 访问正常: {test_result2[0][0]} 个表")
            else:
                print("❌ 无法访问 information_schema.tables")
                return
                
        except Exception as e:
            print(f"❌ 权限测试失败: {e}")
            return
        
        # 测试容量采集查询
        print("\n📊 测试容量采集查询...")
        try:
            data = collector._collect_mysql_sizes()
            print(f"✅ 容量采集成功: {len(data)} 个数据库")
            
            if data:
                print("\n📋 采集到的数据库:")
                for db in data[:5]:  # 只显示前5个
                    print(f"   - {db['database_name']}: {db['size_mb']} MB")
                if len(data) > 5:
                    print(f"   ... 还有 {len(data) - 5} 个数据库")
            else:
                print("⚠️  未采集到任何数据库数据")
                
        except Exception as e:
            print(f"❌ 容量采集失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            collector.disconnect()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python debug_mysql_capacity.py <instance_id>")
        print("示例: python debug_mysql_capacity.py 1")
        sys.exit(1)
    
    try:
        instance_id = int(sys.argv[1])
        debug_mysql_capacity(instance_id)
    except ValueError:
        print("❌ 实例ID必须是数字")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        sys.exit(1)
