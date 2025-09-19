#!/usr/bin/env python3
"""
导出权限配置数据脚本
从现有数据库中导出权限配置数据，用于更新初始化脚本
"""

import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.permission_config import PermissionConfig

def export_permission_configs():
    """导出权限配置数据"""
    app = create_app()
    
    with app.app_context():
        # 查询所有权限配置
        permissions = PermissionConfig.query.order_by(
            PermissionConfig.db_type,
            PermissionConfig.category,
            PermissionConfig.sort_order
        ).all()
        
        if not permissions:
            print("❌ 数据库中没有权限配置数据")
            return
        
        print(f"✅ 找到 {len(permissions)} 条权限配置数据")
        
        # 按数据库类型分组
        grouped_permissions = {}
        for perm in permissions:
            db_type = perm.db_type
            if db_type not in grouped_permissions:
                grouped_permissions[db_type] = {}
            
            category = perm.category
            if category not in grouped_permissions[db_type]:
                grouped_permissions[db_type][category] = []
            
            grouped_permissions[db_type][category].append({
                'permission_name': perm.permission_name,
                'description': perm.description,
                'sort_order': perm.sort_order,
                'is_active': perm.is_active
            })
        
        # 生成SQL插入语句
        sql_statements = []
        sql_statements.append("-- 权限配置数据（从现有数据库导出）")
        sql_statements.append("-- 导出时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        sql_statements.append("")
        
        for db_type, categories in grouped_permissions.items():
            sql_statements.append(f"-- {db_type.upper()}权限配置")
            
            for category, perms in categories.items():
                sql_statements.append(f"-- {category}")
                for perm in perms:
                    sql_statements.append(
                        f"('{db_type}', '{category}', '{perm['permission_name']}', "
                        f"'{perm['description']}', {str(perm['is_active']).upper()}, "
                        f"{perm['sort_order']}, NOW(), NOW()),"
                    )
                sql_statements.append("")
        
        # 保存到文件
        output_file = os.path.join(os.path.dirname(__file__), 'exported_permission_configs.sql')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sql_statements))
        
        print(f"✅ 权限配置数据已导出到: {output_file}")
        
        # 显示统计信息
        print("\n📊 权限配置统计:")
        for db_type, categories in grouped_permissions.items():
            total_perms = sum(len(perms) for perms in categories.values())
            print(f"  {db_type.upper()}: {total_perms} 条权限")
            for category, perms in categories.items():
                print(f"    - {category}: {len(perms)} 条")

if __name__ == '__main__':
    export_permission_configs()

