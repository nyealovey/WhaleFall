"""
鲸落 - 常量管理器
统一管理常量的文档生成、监控和验证
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from app.utils.time_utils import time_utils

from app.utils.constants_doc_generator import ConstantsDocGenerator
from app.utils.constants_monitor import ConstantsMonitor
from app.utils.constants_validator import ConstantsValidator


class ConstantsManager:
    """常量管理器"""

    def __init__(self, project_root: str = None):
        """
        初始化常量管理器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root or str(Path(__file__).parent.parent.parent)
        self.doc_generator = ConstantsDocGenerator(self.project_root)
        self.monitor = ConstantsMonitor(self.project_root)
        self.validator = ConstantsValidator()

    def generate_documentation(self, output_file: str = None) -> str:
        """
        生成常量文档

        Args:
            output_file: 输出文件路径

        Returns:
            str: 生成的文档文件路径
        """
        return self.doc_generator.save_doc(output_file)

    def validate_constants(self) -> Dict[str, Any]:
        """
        验证常量

        Returns:
            Dict: 验证结果
        """
        return self.validator.get_validation_summary()

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        获取使用统计

        Returns:
            Dict: 使用统计信息
        """
        return self.monitor.generate_usage_report()

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取仪表板数据

        Returns:
            Dict: 仪表板数据
        """
        return self.monitor.create_usage_dashboard_data()

    def generate_comprehensive_report(self, output_dir: str = None) -> Dict[str, str]:
        """
        生成综合报告

        Args:
            output_dir: 输出目录路径

        Returns:
            Dict: 生成的文件路径
        """
        if not output_dir:
            output_dir = os.path.join(self.project_root, "docs", "constants")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        generated_files = {}
        
        # 生成文档
        doc_file = os.path.join(output_dir, "CONSTANTS_DOCUMENTATION.md")
        generated_files["documentation"] = self.generate_documentation(doc_file)
        
        # 生成验证报告
        validation_file = os.path.join(output_dir, "validation_report.json")
        generated_files["validation"] = self.validator.export_validation_report(validation_file)
        
        # 生成使用统计
        usage_file = os.path.join(output_dir, "usage_report.json")
        generated_files["usage"] = self.monitor.export_usage_data(usage_file)
        
        # 生成综合报告
        comprehensive_file = os.path.join(output_dir, "comprehensive_report.md")
        generated_files["comprehensive"] = self._generate_comprehensive_report(comprehensive_file)
        
        return generated_files

    def _generate_comprehensive_report(self, output_file: str) -> str:
        """
        生成综合报告

        Args:
            output_file: 输出文件路径

        Returns:
            str: 输出文件路径
        """
        # 获取各种数据
        validation_summary = self.validate_constants()
        usage_stats = self.get_usage_stats()
        dashboard_data = self.get_dashboard_data()
        
        # 生成报告内容
        report = f"""# 鲸落项目常量综合报告

## 📋 报告信息

- **生成时间**: {time_utils.now().strftime('%Y-%m-%d %H:%M:%S')}
- **项目路径**: {self.project_root}
- **报告类型**: 综合报告

## 🔍 验证结果

### 验证摘要
- **总常量数**: {validation_summary['total_constants']}
- **有效常量数**: {validation_summary['valid_constants']}
- **无效常量数**: {validation_summary['invalid_constants']}
- **验证通过率**: {validation_summary['validation_rate']:.2f}%

### 验证错误详情
"""
        
        if validation_summary['validation_errors']:
            for constant_name, errors in validation_summary['validation_errors'].items():
                report += f"\n#### {constant_name}\n"
                for error in errors:
                    report += f"- {error}\n"
        else:
            report += "\n✅ 所有常量验证通过！\n"
        
        report += f"""
## 📊 使用统计

### 使用摘要
- **总常量数**: {usage_stats['total_constants']}
- **已使用常量数**: {usage_stats['used_constants']}
- **未使用常量数**: {usage_stats['unused_constants']}
- **使用率**: {usage_stats['usage_rate']:.2f}%
- **变更次数**: {usage_stats['change_count']}

### 高频使用常量
"""
        
        if usage_stats['high_usage_constants']:
            for constant_name in usage_stats['high_usage_constants']:
                report += f"- `{constant_name}`\n"
        else:
            report += "- 无高频使用常量\n"
        
        report += f"""
### 未使用常量
"""
        
        if usage_stats['unused_constants_list']:
            for constant_name in usage_stats['unused_constants_list']:
                report += f"- `{constant_name}`\n"
        else:
            report += "- 所有常量都有被使用\n"
        
        report += f"""
## 📈 仪表板数据

### 使用分布
- **高频使用**: {dashboard_data['summary']['high_usage_count']} 个
- **中频使用**: {dashboard_data['summary']['medium_usage_count']} 个
- **低频使用**: {dashboard_data['summary']['low_usage_count']} 个
- **未使用**: {dashboard_data['summary']['unused_constants']} 个

### 使用频率排行榜
"""
        
        for constant_name, count in dashboard_data['top_used_constants']:
            report += f"- `{constant_name}`: {count} 次\n"
        
        report += f"""
## 🚀 优化建议

### 1. 验证问题修复
"""
        
        if validation_summary['validation_errors']:
            report += "需要修复以下验证错误：\n"
            for constant_name, errors in validation_summary['validation_errors'].items():
                report += f"- {constant_name}: {', '.join(errors)}\n"
        else:
            report += "✅ 所有常量验证通过，无需修复\n"
        
        report += f"""
### 2. 使用优化
"""
        
        if usage_stats['unused_constants'] > 0:
            report += f"发现 {usage_stats['unused_constants']} 个未使用常量，建议：\n"
            report += "- 检查是否真的不需要这些常量\n"
            report += "- 如果不需要，考虑删除以减少代码复杂度\n"
            report += "- 如果需要，检查为什么没有被使用\n"
        else:
            report += "✅ 所有常量都有被使用\n"
        
        report += f"""
### 3. 性能优化
"""
        
        if usage_stats['high_usage_constants']:
            report += "以下常量使用频率较高，建议优化：\n"
            for constant_name in usage_stats['high_usage_constants']:
                report += f"- `{constant_name}`: 考虑缓存或优化访问方式\n"
        else:
            report += "✅ 无高频使用常量需要优化\n"
        
        report += f"""
### 4. 文档完善
- 为每个常量添加详细注释
- 提供使用示例
- 定期更新文档

### 5. 监控建议
- 定期运行验证检查
- 监控常量使用情况
- 跟踪常量变更历史

## 📝 总结

本报告提供了鲸落项目常量的全面分析，包括验证结果、使用统计和优化建议。

**关键指标**:
- 验证通过率: {validation_summary['validation_rate']:.2f}%
- 使用率: {usage_stats['usage_rate']:.2f}%
- 高频使用常量: {len(usage_stats['high_usage_constants'])} 个
- 未使用常量: {usage_stats['unused_constants']} 个

**建议优先级**:
1. 修复验证错误（如果有）
2. 清理未使用常量
3. 优化高频使用常量
4. 完善文档和监控

---
*报告生成时间: {time_utils.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        # 保存报告
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        return output_file

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        运行完整分析

        Returns:
            Dict: 分析结果
        """
        print("🔍 开始常量分析...")
        
        # 验证常量
        print("📋 验证常量...")
        validation_results = self.validate_constants()
        
        # 分析使用情况
        print("📊 分析使用情况...")
        usage_results = self.get_usage_stats()
        
        # 生成文档
        print("📝 生成文档...")
        doc_file = self.generate_documentation()
        
        # 生成综合报告
        print("📈 生成综合报告...")
        comprehensive_files = self.generate_comprehensive_report()
        
        print("✅ 常量分析完成！")
        
        return {
            "validation": validation_results,
            "usage": usage_results,
            "documentation": doc_file,
            "comprehensive_files": comprehensive_files,
        }


def main():
    """主函数"""
    manager = ConstantsManager()
    
    # 运行完整分析
    results = manager.run_full_analysis()
    
    print("\n📊 分析结果摘要:")
    print(f"验证通过率: {results['validation']['validation_rate']:.2f}%")
    print(f"使用率: {results['usage']['usage_rate']:.2f}%")
    print(f"文档文件: {results['documentation']}")
    print(f"综合报告: {results['comprehensive_files']['comprehensive']}")


if __name__ == "__main__":
    main()
