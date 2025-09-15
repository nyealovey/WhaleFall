#!/usr/bin/env python3
"""
测试优化后的自动分类功能
"""

import json
import time
import requests
from typing import Dict, Any


class ClassificationTester:
    """分类功能测试器"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def login(self, username: str = "admin", password: str = "admin123") -> bool:
        """登录系统"""
        try:
            response = self.session.post(f"{self.base_url}/auth/login", json={
                "username": username,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ 登录成功: {username}")
                    return True
            
            print(f"❌ 登录失败: {response.text}")
            return False
            
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False
    
    def test_original_classification(self, instance_id: int = None) -> Dict[str, Any]:
        """测试原始分类功能"""
        print("\n🔄 测试原始分类功能...")
        
        try:
            start_time = time.time()
            
            response = self.session.post(f"{self.base_url}/account-classification/auto-classify", json={
                "instance_id": instance_id,
                "batch_type": "test_original",
                "use_optimized": False
            })
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 原始分类完成: {duration:.2f}秒")
                return {
                    "success": True,
                    "duration": duration,
                    "data": data
                }
            else:
                print(f"❌ 原始分类失败: {response.text}")
                return {
                    "success": False,
                    "duration": duration,
                    "error": response.text
                }
                
        except Exception as e:
            print(f"❌ 原始分类异常: {e}")
            return {
                "success": False,
                "duration": 0,
                "error": str(e)
            }
    
    def test_optimized_classification(self, instance_id: int = None) -> Dict[str, Any]:
        """测试优化后的分类功能"""
        print("\n🚀 测试优化后的分类功能...")
        
        try:
            start_time = time.time()
            
            response = self.session.post(f"{self.base_url}/account-classification/auto-classify-optimized", json={
                "instance_id": instance_id,
                "batch_type": "test_optimized"
            })
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 优化分类完成: {duration:.2f}秒")
                return {
                    "success": True,
                    "duration": duration,
                    "data": data
                }
            else:
                print(f"❌ 优化分类失败: {response.text}")
                return {
                    "success": False,
                    "duration": duration,
                    "error": response.text
                }
                
        except Exception as e:
            print(f"❌ 优化分类异常: {e}")
            return {
                "success": False,
                "duration": 0,
                "error": str(e)
            }
    
    def test_performance_comparison(self, instance_id: int = None) -> Dict[str, Any]:
        """测试性能比较"""
        print("\n📊 测试性能比较...")
        
        try:
            response = self.session.post(f"{self.base_url}/account-classification/auto-classify-comparison", json={
                "instance_id": instance_id,
                "batch_type": "performance_test"
            })
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 性能比较完成")
                return data
            else:
                print(f"❌ 性能比较失败: {response.text}")
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            print(f"❌ 性能比较异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_classifications(self) -> Dict[str, Any]:
        """获取分类列表"""
        try:
            response = self.session.get(f"{self.base_url}/account-classification/classifications")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ 获取到 {len(data.get('classifications', []))} 个分类")
                    return data
                else:
                    print(f"❌ 获取分类失败: {data.get('error')}")
                    return data
            else:
                print(f"❌ 获取分类失败: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ 获取分类异常: {e}")
            return {"success": False, "error": str(e)}
    
    def get_rules(self) -> Dict[str, Any]:
        """获取规则列表"""
        try:
            response = self.session.get(f"{self.base_url}/account-classification/rules")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    rules_by_db_type = data.get("rules_by_db_type", {})
                    total_rules = sum(len(rules) for rules in rules_by_db_type.values())
                    print(f"✅ 获取到 {total_rules} 个规则")
                    return data
                else:
                    print(f"❌ 获取规则失败: {data.get('error')}")
                    return data
            else:
                print(f"❌ 获取规则失败: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ 获取规则异常: {e}")
            return {"success": False, "error": str(e)}
    
    def run_full_test(self, instance_id: int = None) -> Dict[str, Any]:
        """运行完整测试"""
        print("🧪 开始完整测试...")
        
        # 1. 登录
        if not self.login():
            return {"success": False, "error": "登录失败"}
        
        # 2. 获取基础信息
        classifications = self.get_classifications()
        rules = self.get_rules()
        
        # 3. 测试原始分类
        original_result = self.test_original_classification(instance_id)
        
        # 4. 测试优化后的分类
        optimized_result = self.test_optimized_classification(instance_id)
        
        # 5. 性能比较
        comparison_result = self.test_performance_comparison(instance_id)
        
        # 6. 生成测试报告
        report = self.generate_test_report(
            original_result, 
            optimized_result, 
            comparison_result,
            classifications,
            rules
        )
        
        return report
    
    def generate_test_report(
        self, 
        original_result: Dict[str, Any], 
        optimized_result: Dict[str, Any], 
        comparison_result: Dict[str, Any],
        classifications: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成测试报告"""
        
        print("\n" + "="*60)
        print("📋 测试报告")
        print("="*60)
        
        # 基础信息
        print(f"📊 分类数量: {len(classifications.get('classifications', []))}")
        rules_by_db_type = rules.get("rules_by_db_type", {})
        total_rules = sum(len(rules) for rules in rules_by_db_type.values())
        print(f"📊 规则数量: {total_rules}")
        for db_type, rules_list in rules_by_db_type.items():
            print(f"   - {db_type}: {len(rules_list)} 个规则")
        
        # 原始分类结果
        print(f"\n🔄 原始分类:")
        if original_result["success"]:
            print(f"   ✅ 成功: {original_result['duration']:.2f}秒")
            data = original_result.get("data", {})
            print(f"   📊 分类账户: {data.get('classified_count', 0)}")
            print(f"   📊 失败数量: {data.get('failed_count', 0)}")
        else:
            print(f"   ❌ 失败: {original_result.get('error', '未知错误')}")
        
        # 优化分类结果
        print(f"\n🚀 优化分类:")
        if optimized_result["success"]:
            print(f"   ✅ 成功: {optimized_result['duration']:.2f}秒")
            data = optimized_result.get("data", {})
            print(f"   📊 总账户: {data.get('total_accounts', 0)}")
            print(f"   📊 分类分配: {data.get('total_classifications_added', 0)}")
            print(f"   📊 匹配次数: {data.get('total_matches', 0)}")
            print(f"   📊 失败数量: {data.get('failed_count', 0)}")
        else:
            print(f"   ❌ 失败: {optimized_result.get('error', '未知错误')}")
        
        # 性能比较
        if comparison_result.get("success"):
            comparison = comparison_result.get("comparison", {})
            print(f"\n📈 性能比较:")
            
            original = comparison.get("original", {})
            optimized = comparison.get("optimized", {})
            
            if original.get("success") and optimized.get("success"):
                original_duration = original.get("duration", 0)
                optimized_duration = optimized.get("duration", 0)
                
                if original_duration > 0 and optimized_duration > 0:
                    improvement = ((original_duration - optimized_duration) / original_duration) * 100
                    speed_ratio = original_duration / optimized_duration
                    
                    print(f"   ⏱️  原始耗时: {original_duration:.2f}秒")
                    print(f"   ⏱️  优化耗时: {optimized_duration:.2f}秒")
                    print(f"   🚀 性能提升: {improvement:.1f}%")
                    print(f"   🚀 速度倍数: {speed_ratio:.1f}x")
                    print(f"   ⏰ 节省时间: {original_duration - optimized_duration:.2f}秒")
                else:
                    print("   ⚠️  无法计算性能提升")
            else:
                print("   ⚠️  性能比较数据不完整")
        else:
            print(f"\n❌ 性能比较失败: {comparison_result.get('error', '未知错误')}")
        
        print("="*60)
        
        return {
            "success": True,
            "original_result": original_result,
            "optimized_result": optimized_result,
            "comparison_result": comparison_result,
            "classifications": classifications,
            "rules": rules,
        }


def main():
    """主函数"""
    print("🧪 泰摸鱼吧 - 优化后的自动分类功能测试")
    print("="*60)
    
    # 创建测试器
    tester = ClassificationTester()
    
    # 运行测试
    result = tester.run_full_test()
    
    if result["success"]:
        print("\n✅ 测试完成！")
    else:
        print(f"\n❌ 测试失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    main()
