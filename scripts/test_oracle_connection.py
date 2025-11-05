#!/usr/bin/env python3
"""
测试 Oracle 数据库连接
用于验证用户名大小写问题的修复
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Instance, Credential
from app.services.connection_adapters.connection_factory import ConnectionFactory


def test_oracle_connection(instance_id=None):
    """测试 Oracle 连接"""
    app = create_app()
    
    with app.app_context():
        # 查找 Oracle 实例
        if instance_id:
            instance = Instance.query.get(instance_id)
            if not instance:
                print(f"❌ 未找到 ID 为 {instance_id} 的实例")
                return
            instances = [instance]
        else:
            instances = Instance.query.filter_by(db_type='oracle', is_active=True).all()
        
        if not instances:
            print("❌ 未找到任何 Oracle 实例")
            return
        
        print(f"找到 {len(instances)} 个 Oracle 实例\n")
        
        success_count = 0
        fail_count = 0
        
        for instance in instances:
            print(f"{'='*60}")
            print(f"测试实例: {instance.name} (ID: {instance.id})")
            print(f"主机: {instance.host}:{instance.port}")
            print(f"数据库: {instance.database_name or 'ORCL'}")
            
            if instance.credential:
                print(f"凭据: {instance.credential.name}")
                print(f"用户名: {instance.credential.username}")
                print(f"用户名（大写）: {instance.credential.username.upper()}")
            else:
                print("❌ 未配置凭据")
                fail_count += 1
                continue
            
            print("\n开始测试连接...")
            
            try:
                result = ConnectionFactory.test_connection(instance)
                
                if result.get('success'):
                    print(f"✅ 连接成功!")
                    print(f"   消息: {result.get('message')}")
                    if result.get('version'):
                        print(f"   版本: {result.get('version')}")
                    success_count += 1
                else:
                    print(f"❌ 连接失败!")
                    print(f"   错误: {result.get('error')}")
                    fail_count += 1
                    
            except Exception as e:
                print(f"❌ 测试异常: {str(e)}")
                fail_count += 1
            
            print()
        
        print(f"{'='*60}")
        print(f"测试完成: 成功 {success_count} 个, 失败 {fail_count} 个")


def list_oracle_credentials():
    """列出所有 Oracle 凭据"""
    app = create_app()
    
    with app.app_context():
        credentials = Credential.query.filter_by(db_type='oracle', is_active=True).all()
        
        if not credentials:
            print("未找到任何 Oracle 凭据")
            return
        
        print(f"找到 {len(credentials)} 个 Oracle 凭据:\n")
        
        for cred in credentials:
            print(f"ID: {cred.id}")
            print(f"名称: {cred.name}")
            print(f"用户名: {cred.username}")
            print(f"用户名（大写）: {cred.username.upper()}")
            print(f"类型: {cred.credential_type}")
            print(f"数据库类型: {cred.db_type}")
            print(f"状态: {'启用' if cred.is_active else '禁用'}")
            print("-" * 40)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试 Oracle 数据库连接')
    parser.add_argument('--instance-id', type=int, help='指定实例 ID')
    parser.add_argument('--list-credentials', action='store_true', help='列出所有 Oracle 凭据')
    
    args = parser.parse_args()
    
    if args.list_credentials:
        list_oracle_credentials()
    else:
        test_oracle_connection(args.instance_id)


if __name__ == "__main__":
    main()
