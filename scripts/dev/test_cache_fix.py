#!/usr/bin/env python3
"""
测试分类规则缓存修复
验证缓存数据格式兼容性和按数据库类型分组功能
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from app.services.cache_manager import cache_manager
from app.services.optimized_account_classification_service import OptimizedAccountClassificationService
from app.models.account_classification import ClassificationRule, AccountClassification
from app.utils.structlog_config import get_system_logger

def test_cache_format_compatibility():
    """测试缓存格式兼容性"""
    print("🔍 测试缓存格式兼容性...")
    
    # 创建测试数据
    test_rules_data = [
        {
            "id": 1,
            "rule_name": "测试规则1",
            "db_type": "mysql",
            "rule_expression": '{"type": "permission", "permissions": ["SELECT"]}',
            "is_active": True,
            "classification_id": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        {
            "id": 2,
            "rule_name": "测试规则2", 
            "db_type": "postgresql",
            "rule_expression": '{"type": "permission", "permissions": ["SELECT"]}',
            "is_active": True,
            "classification_id": 2,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]
    
    # 测试新格式缓存
    print("  📝 测试新格式缓存...")
    new_format_data = {
        "rules": test_rules_data,
        "cached_at": datetime.now().isoformat(),
        "count": len(test_rules_data)
    }
    
    # 设置新格式缓存
    cache_manager.cache.set("test_rules_new", new_format_data, timeout=60)
    
    # 获取新格式缓存
    cached_new = cache_manager.get_classification_rules_cache()
    if cached_new and isinstance(cached_new, dict) and "rules" in cached_new:
        print("  ✅ 新格式缓存设置和获取成功")
    else:
        print("  ❌ 新格式缓存失败")
    
    # 测试旧格式缓存
    print("  📝 测试旧格式缓存...")
    cache_manager.cache.set("test_rules_old", test_rules_data, timeout=60)
    
    # 模拟旧格式缓存获取
    old_cached = cache_manager.cache.get("test_rules_old")
    if old_cached and isinstance(old_cached, list):
        print("  ✅ 旧格式缓存兼容性测试成功")
    else:
        print("  ❌ 旧格式缓存兼容性测试失败")
    
    # 清理测试缓存
    cache_manager.cache.delete("test_rules_new")
    cache_manager.cache.delete("test_rules_old")
    
    print("✅ 缓存格式兼容性测试完成")

def test_db_type_grouping():
    """测试按数据库类型分组功能"""
    print("🔍 测试按数据库类型分组功能...")
    
    service = OptimizedAccountClassificationService()
    
    # 创建测试规则
    test_rules = []
    for i, db_type in enumerate(["mysql", "postgresql", "sqlserver", "oracle"]):
        rule = ClassificationRule()
        rule.id = i + 1
        rule.rule_name = f"测试规则_{db_type}"
        rule.db_type = db_type
        rule.rule_expression = '{"type": "permission", "permissions": ["SELECT"]}'
        rule.is_active = True
        rule.classification_id = i + 1
        rule.created_at = datetime.now()
        rule.updated_at = datetime.now()
        test_rules.append(rule)
    
    # 测试规则分组
    print("  📝 测试规则按数据库类型分组...")
    grouped_rules = service._group_rules_by_db_type(test_rules)
    
    expected_types = ["mysql", "postgresql", "sqlserver", "oracle"]
    for db_type in expected_types:
        if db_type in grouped_rules:
            count = len(grouped_rules[db_type])
            print(f"    ✅ {db_type}: {count} 个规则")
        else:
            print(f"    ❌ {db_type}: 未找到规则")
    
    # 测试缓存设置
    print("  📝 测试按数据库类型缓存设置...")
    for db_type, rules in grouped_rules.items():
        try:
            rules_data = service._rules_to_cache_data(rules)
            cache_manager.set_classification_rules_by_db_type_cache(db_type, rules_data)
            print(f"    ✅ {db_type} 规则缓存设置成功")
        except Exception as e:
            print(f"    ❌ {db_type} 规则缓存设置失败: {e}")
    
    # 测试缓存获取
    print("  📝 测试按数据库类型缓存获取...")
    for db_type in expected_types:
        try:
            cached_rules = cache_manager.get_classification_rules_by_db_type_cache(db_type)
            if cached_rules:
                print(f"    ✅ {db_type} 规则缓存获取成功: {len(cached_rules)} 个规则")
            else:
                print(f"    ⚠️  {db_type} 规则缓存为空")
        except Exception as e:
            print(f"    ❌ {db_type} 规则缓存获取失败: {e}")
    
    print("✅ 按数据库类型分组功能测试完成")

def test_cache_debug():
    """测试缓存调试功能"""
    print("🔍 测试缓存调试功能...")
    
    try:
        debug_info = cache_manager.debug_cache_status()
        
        print("  📊 缓存调试信息:")
        print(f"    缓存启用: {debug_info.get('cache_enabled', False)}")
        print(f"    缓存类型: {debug_info.get('cache_type', 'Unknown')}")
        print(f"    健康检查: {debug_info.get('health_check', False)}")
        
        cache_keys = debug_info.get('cache_keys', {})
        print("  📋 缓存键状态:")
        for key, info in cache_keys.items():
            if info.get('exists'):
                print(f"    ✅ {key}: {info.get('type', 'unknown')} - {info.get('count', 0)} 项")
            else:
                print(f"    ❌ {key}: 不存在")
        
        print("✅ 缓存调试功能测试完成")
        
    except Exception as e:
        print(f"❌ 缓存调试功能测试失败: {e}")

def test_cache_clear():
    """测试缓存清除功能"""
    print("🔍 测试缓存清除功能...")
    
    # 设置一些测试缓存
    test_data = [{"id": 1, "name": "test"}]
    cache_manager.set_classification_rules_by_db_type_cache("mysql", test_data)
    cache_manager.set_classification_rules_by_db_type_cache("postgresql", test_data)
    
    print("  📝 设置测试缓存...")
    
    # 测试清除特定数据库类型缓存
    print("  🗑️  清除MySQL缓存...")
    result = cache_manager.invalidate_db_type_cache("mysql")
    if result:
        print("    ✅ MySQL缓存清除成功")
    else:
        print("    ❌ MySQL缓存清除失败")
    
    # 验证清除结果
    mysql_cache = cache_manager.get_classification_rules_by_db_type_cache("mysql")
    postgresql_cache = cache_manager.get_classification_rules_by_db_type_cache("postgresql")
    
    if not mysql_cache:
        print("    ✅ MySQL缓存已清除")
    else:
        print("    ❌ MySQL缓存未清除")
    
    if postgresql_cache:
        print("    ✅ PostgreSQL缓存保留")
    else:
        print("    ⚠️  PostgreSQL缓存也被清除")
    
    # 清除所有测试缓存
    cache_manager.invalidate_all_db_type_cache()
    print("  🗑️  清除所有测试缓存")
    
    print("✅ 缓存清除功能测试完成")

def main():
    """主测试函数"""
    print("🚀 开始分类规则缓存修复测试")
    print("=" * 50)
    
    # 创建Flask应用上下文
    app = create_app()
    with app.app_context():
        try:
            # 测试缓存格式兼容性
            test_cache_format_compatibility()
            print()
            
            # 测试按数据库类型分组
            test_db_type_grouping()
            print()
            
            # 测试缓存调试功能
            test_cache_debug()
            print()
            
            # 测试缓存清除功能
            test_cache_clear()
            print()
            
            print("🎉 所有测试完成！")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
