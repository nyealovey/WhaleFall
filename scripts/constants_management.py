#!/usr/bin/env python3
"""
鲸落 - 常量管理命令行工具
提供常量文档生成、监控和验证的命令行接口
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.constants_manager import ConstantsManager


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="鲸落常量管理工具")
    parser.add_argument(
        "command",
        choices=["generate-doc", "validate", "monitor", "full-analysis", "dashboard"],
        help="要执行的命令"
    )
    parser.add_argument(
        "--output-dir",
        default="docs/constants",
        help="输出目录路径"
    )
    parser.add_argument(
        "--project-root",
        default=str(project_root),
        help="项目根目录路径"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出"
    )
    
    args = parser.parse_args()
    
    # 创建常量管理器
    manager = ConstantsManager(args.project_root)
    
    try:
        if args.command == "generate-doc":
            print("📝 生成常量文档...")
            doc_file = manager.generate_documentation()
            print(f"✅ 文档已生成: {doc_file}")
            
        elif args.command == "validate":
            print("🔍 验证常量...")
            validation_results = manager.validate_constants()
            
            print(f"\n📊 验证结果:")
            print(f"总常量数: {validation_results['total_constants']}")
            print(f"有效常量数: {validation_results['valid_constants']}")
            print(f"无效常量数: {validation_results['invalid_constants']}")
            print(f"验证通过率: {validation_results['validation_rate']:.2f}%")
            
            if validation_results['validation_errors']:
                print(f"\n❌ 发现验证错误:")
                for constant_name, errors in validation_results['validation_errors'].items():
                    print(f"  {constant_name}:")
                    for error in errors:
                        print(f"    - {error}")
            else:
                print("\n✅ 所有常量验证通过！")
                
        elif args.command == "monitor":
            print("📊 分析常量使用情况...")
            usage_results = manager.get_usage_stats()
            
            print(f"\n📈 使用统计:")
            print(f"总常量数: {usage_results['total_constants']}")
            print(f"已使用常量数: {usage_results['used_constants']}")
            print(f"未使用常量数: {usage_results['unused_constants']}")
            print(f"使用率: {usage_results['usage_rate']:.2f}%")
            print(f"变更次数: {usage_results['change_count']}")
            
            if usage_results['high_usage_constants']:
                print(f"\n🔥 高频使用常量:")
                for constant_name in usage_results['high_usage_constants']:
                    print(f"  - {constant_name}")
            
            if usage_results['unused_constants_list']:
                print(f"\n⚠️  未使用常量:")
                for constant_name in usage_results['unused_constants_list']:
                    print(f"  - {constant_name}")
                    
        elif args.command == "dashboard":
            print("📈 生成仪表板数据...")
            dashboard_data = manager.get_dashboard_data()
            
            print(f"\n📊 仪表板数据:")
            print(f"总常量数: {dashboard_data['summary']['total_constants']}")
            print(f"已使用常量数: {dashboard_data['summary']['used_constants']}")
            print(f"未使用常量数: {dashboard_data['summary']['unused_constants']}")
            print(f"高频使用: {dashboard_data['summary']['high_usage_count']} 个")
            print(f"中频使用: {dashboard_data['summary']['medium_usage_count']} 个")
            print(f"低频使用: {dashboard_data['summary']['low_usage_count']} 个")
            
            print(f"\n🏆 使用频率排行榜:")
            for i, (constant_name, count) in enumerate(dashboard_data['top_used_constants'], 1):
                print(f"  {i}. {constant_name}: {count} 次")
                
        elif args.command == "full-analysis":
            print("🚀 运行完整分析...")
            results = manager.run_full_analysis()
            
            print(f"\n📊 分析结果摘要:")
            print(f"验证通过率: {results['validation']['validation_rate']:.2f}%")
            print(f"使用率: {results['usage']['usage_rate']:.2f}%")
            print(f"文档文件: {results['documentation']}")
            print(f"综合报告: {results['comprehensive_files']['comprehensive']}")
            
            if args.verbose:
                print(f"\n📁 生成的文件:")
                for file_type, file_path in results['comprehensive_files'].items():
                    print(f"  {file_type}: {file_path}")
        
        print("\n✅ 操作完成！")
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
