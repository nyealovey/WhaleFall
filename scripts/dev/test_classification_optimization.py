#!/usr/bin/env python3
"""
鲸落 - 自动分类优化测试脚本
测试阶段1优化（方案B）的效果
"""

import os
import sys
import time
import json
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app import create_app
from app.services.optimized_account_classification_service import OptimizedAccountClassificationService
from app.services.cache_manager import cache_manager
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.account_classification import ClassificationRule
from app.models.instance import Instance
from app.utils.structlog_config import log_info, log_error


class ClassificationOptimizationTester:
    """自动分类优化测试器"""
    
    def __init__(self):
        self.app = create_app()
        self.service = OptimizedAccountClassificationService()
        self.results = {}
    
    def run_tests(self):
        """运行所有测试"""
        print("🚀 开始自动分类优化测试...")
        
        with self.app.app_context():
            try:
                # 1. 测试预分组优化
                self.test_pre_grouping_optimization()
                
                # 2. 测试规则过滤优化
                self.test_rule_filtering_optimization()
                
                # 3. 测试缓存优化
                self.test_cache_optimization()
                
                # 4. 测试整体性能
                self.test_overall_performance()
                
                # 5. 生成测试报告
                self.generate_test_report()
                
            except Exception as e:
                log_error(f"测试执行失败: {e}", module="classification_test")
                print(f"❌ 测试执行失败: {e}")
    
    def test_pre_grouping_optimization(self):
        """测试预分组优化"""
        print("\n📊 测试预分组优化...")
        
        try:
            # 获取测试数据
            accounts = CurrentAccountSyncData.query.join(Instance).limit(100).all()
            rules = ClassificationRule.query.filter_by(is_active=True).limit(20).all()
            
            if not accounts or not rules:
                print("⚠️  测试数据不足，跳过预分组测试")
                return
            
            # 测试预分组功能
            start_time = time.time()
            accounts_by_db_type = self.service._group_accounts_by_db_type(accounts)
            rules_by_db_type = self.service._group_rules_by_db_type(rules)
            grouping_time = time.time() - start_time
            
            # 统计结果
            db_types = list(accounts_by_db_type.keys())
            total_accounts = sum(len(accs) for accs in accounts_by_db_type.values())
            total_rules = sum(len(rules) for rules in rules_by_db_type.values())
            
            self.results["pre_grouping"] = {
                "success": True,
                "grouping_time": grouping_time,
                "db_types": db_types,
                "total_accounts": total_accounts,
                "total_rules": total_rules,
                "accounts_per_type": {db_type: len(accs) for db_type, accs in accounts_by_db_type.items()},
                "rules_per_type": {db_type: len(rules) for db_type, rules in rules_by_db_type.items()}
            }
            
            print(f"✅ 预分组优化测试完成")
            print(f"   - 分组时间: {grouping_time:.3f}s")
            print(f"   - 数据库类型: {', '.join(db_types)}")
            print(f"   - 账户总数: {total_accounts}")
            print(f"   - 规则总数: {total_rules}")
            
        except Exception as e:
            log_error(f"预分组优化测试失败: {e}", module="classification_test")
            self.results["pre_grouping"] = {"success": False, "error": str(e)}
            print(f"❌ 预分组优化测试失败: {e}")
    
    def test_rule_filtering_optimization(self):
        """测试规则过滤优化"""
        print("\n🔍 测试规则过滤优化...")
        
        try:
            # 获取测试数据
            accounts = CurrentAccountSyncData.query.join(Instance).limit(50).all()
            rules = ClassificationRule.query.filter_by(is_active=True).limit(10).all()
            
            if not accounts or not rules:
                print("⚠️  测试数据不足，跳过规则过滤测试")
                return
            
            # 测试规则过滤功能
            start_time = time.time()
            
            # 模拟按数据库类型过滤
            accounts_by_db_type = self.service._group_accounts_by_db_type(accounts)
            rules_by_db_type = self.service._group_rules_by_db_type(rules)
            
            filtered_operations = 0
            total_operations = 0
            
            for db_type, db_accounts in accounts_by_db_type.items():
                db_rules = rules_by_db_type.get(db_type, [])
                for rule in db_rules:
                    # 测试优化的规则匹配
                    matched_accounts = self.service._find_accounts_matching_rule_optimized(
                        rule, db_accounts, db_type
                    )
                    filtered_operations += 1
                    total_operations += len(db_accounts)
            
            filtering_time = time.time() - start_time
            
            # 计算优化效果
            original_operations = len(accounts) * len(rules)
            optimization_ratio = (original_operations - total_operations) / original_operations if original_operations > 0 else 0
            
            self.results["rule_filtering"] = {
                "success": True,
                "filtering_time": filtering_time,
                "original_operations": original_operations,
                "optimized_operations": total_operations,
                "filtered_operations": filtered_operations,
                "optimization_ratio": optimization_ratio,
                "time_saved": original_operations - total_operations
            }
            
            print(f"✅ 规则过滤优化测试完成")
            print(f"   - 过滤时间: {filtering_time:.3f}s")
            print(f"   - 原始操作数: {original_operations}")
            print(f"   - 优化后操作数: {total_operations}")
            print(f"   - 优化比例: {optimization_ratio:.2%}")
            print(f"   - 节省操作数: {original_operations - total_operations}")
            
        except Exception as e:
            log_error(f"规则过滤优化测试失败: {e}", module="classification_test")
            self.results["rule_filtering"] = {"success": False, "error": str(e)}
            print(f"❌ 规则过滤优化测试失败: {e}")
    
    def test_cache_optimization(self):
        """测试缓存优化"""
        print("\n💾 测试缓存优化...")
        
        try:
            if not cache_manager:
                print("⚠️  缓存管理器未初始化，跳过缓存测试")
                return
            
            # 测试按数据库类型的缓存
            db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
            cache_stats = {}
            
            for db_type in db_types:
                # 测试规则缓存
                rules_cache = cache_manager.get_classification_rules_by_db_type_cache(db_type)
                # 测试账户缓存
                accounts_cache = cache_manager.get_accounts_by_db_type_cache(db_type)
                
                cache_stats[db_type] = {
                    "rules_cached": rules_cache is not None,
                    "rules_count": len(rules_cache) if rules_cache else 0,
                    "accounts_cached": accounts_cache is not None,
                    "accounts_count": len(accounts_cache) if accounts_cache else 0
                }
            
            # 测试缓存性能
            start_time = time.time()
            
            # 模拟缓存操作
            test_data = [{"id": i, "name": f"test_{i}"} for i in range(10)]
            
            for db_type in db_types:
                cache_manager.set_classification_rules_by_db_type_cache(db_type, test_data)
                cached_data = cache_manager.get_classification_rules_by_db_type_cache(db_type)
                cache_manager.invalidate_db_type_cache(db_type)
            
            cache_time = time.time() - start_time
            
            self.results["cache_optimization"] = {
                "success": True,
                "cache_time": cache_time,
                "cache_stats": cache_stats,
                "db_types_tested": len(db_types)
            }
            
            print(f"✅ 缓存优化测试完成")
            print(f"   - 缓存操作时间: {cache_time:.3f}s")
            print(f"   - 测试数据库类型: {len(db_types)}")
            
            for db_type, stats in cache_stats.items():
                print(f"   - {db_type}: 规则缓存={stats['rules_cached']}, 账户缓存={stats['accounts_cached']}")
            
        except Exception as e:
            log_error(f"缓存优化测试失败: {e}", module="classification_test")
            self.results["cache_optimization"] = {"success": False, "error": str(e)}
            print(f"❌ 缓存优化测试失败: {e}")
    
    def test_overall_performance(self):
        """测试整体性能"""
        print("\n⚡ 测试整体性能...")
        
        try:
            # 获取测试数据
            accounts = CurrentAccountSyncData.query.join(Instance).limit(20).all()
            
            if not accounts:
                print("⚠️  测试数据不足，跳过整体性能测试")
                return
            
            # 测试优化后的分类性能
            start_time = time.time()
            
            result = self.service.auto_classify_accounts_optimized(
                instance_id=None,
                batch_type="test",
                created_by=1
            )
            
            classification_time = time.time() - start_time
            
            self.results["overall_performance"] = {
                "success": result.get("success", False),
                "classification_time": classification_time,
                "total_accounts": result.get("total_accounts", 0),
                "total_rules": result.get("total_rules", 0),
                "classified_accounts": result.get("classified_accounts", 0),
                "total_classifications_added": result.get("total_classifications_added", 0),
                "total_matches": result.get("total_matches", 0),
                "failed_count": result.get("failed_count", 0),
                "db_type_results": result.get("db_type_results", {})
            }
            
            print(f"✅ 整体性能测试完成")
            print(f"   - 分类时间: {classification_time:.3f}s")
            print(f"   - 处理账户: {result.get('total_accounts', 0)}")
            print(f"   - 应用规则: {result.get('total_rules', 0)}")
            print(f"   - 分类账户: {result.get('classified_accounts', 0)}")
            print(f"   - 添加分类: {result.get('total_classifications_added', 0)}")
            print(f"   - 匹配次数: {result.get('total_matches', 0)}")
            print(f"   - 失败次数: {result.get('failed_count', 0)}")
            
        except Exception as e:
            log_error(f"整体性能测试失败: {e}", module="classification_test")
            self.results["overall_performance"] = {"success": False, "error": str(e)}
            print(f"❌ 整体性能测试失败: {e}")
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n📋 生成测试报告...")
        
        try:
            report = {
                "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "optimization_version": "阶段1优化（方案B）",
                "test_results": self.results,
                "summary": self._generate_summary()
            }
            
            # 保存报告到文件
            report_file = os.path.join(project_root, "userdata", "logs", "classification_optimization_test_report.json")
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 测试报告已保存: {report_file}")
            print(f"\n📊 测试总结:")
            print(f"   - 预分组优化: {'✅ 通过' if self.results.get('pre_grouping', {}).get('success') else '❌ 失败'}")
            print(f"   - 规则过滤优化: {'✅ 通过' if self.results.get('rule_filtering', {}).get('success') else '❌ 失败'}")
            print(f"   - 缓存优化: {'✅ 通过' if self.results.get('cache_optimization', {}).get('success') else '❌ 失败'}")
            print(f"   - 整体性能: {'✅ 通过' if self.results.get('overall_performance', {}).get('success') else '❌ 失败'}")
            
        except Exception as e:
            log_error(f"生成测试报告失败: {e}", module="classification_test")
            print(f"❌ 生成测试报告失败: {e}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成测试总结"""
        summary = {
            "total_tests": len(self.results),
            "passed_tests": 0,
            "failed_tests": 0,
            "performance_metrics": {}
        }
        
        for test_name, result in self.results.items():
            if result.get("success"):
                summary["passed_tests"] += 1
            else:
                summary["failed_tests"] += 1
            
            # 收集性能指标
            if "time" in result:
                summary["performance_metrics"][f"{test_name}_time"] = result["time"]
        
        return summary


def main():
    """主函数"""
    print("🐋 鲸落 - 自动分类优化测试")
    print("=" * 50)
    
    tester = ClassificationOptimizationTester()
    tester.run_tests()
    
    print("\n🎉 测试完成！")


if __name__ == "__main__":
    main()
