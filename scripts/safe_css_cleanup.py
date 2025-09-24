#!/usr/bin/env python3
"""
安全的CSS清理脚本
只清理明确未使用的装饰性样式：动画效果、阴影效果、渐变效果
"""

import os
import re
import glob
from pathlib import Path

def is_decorative_selector(selector):
    """判断是否为装饰性选择器"""
    decorative_patterns = [
        # 动画效果类
        r'\.fade-in',
        r'\.slide-in-',
        r'\.slide-out-',
        r'\.pulse',
        r'\.loading-animation',
        
        # 阴影效果类
        r'\.shadow-soft',
        r'\.shadow-medium', 
        r'\.shadow-strong',
        r'\.text-shadow',
        r'\.text-shadow-strong',
        
        # 渐变效果类
        r'\.gradient-text',
        r'\.gradient-border',
        r'\.border-gradient',
        
        # 其他装饰性样式
        r'\.glass-effect',
        r'\.pattern-dots',
        r'\.pattern-grid',
        r'\.btn-glow',
    ]
    
    for pattern in decorative_patterns:
        if re.search(pattern, selector):
            return True
    return False

def clean_css_file(css_file):
    """清理单个CSS文件"""
    print(f"🧹 清理文件: {css_file}")
    
    try:
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建备份
        backup_file = css_file + '.backup'
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   📁 备份文件: {backup_file}")
        
        # 统计清理前的规则数
        original_rules = len(re.findall(r'[^{}]+{[^{}]*}', content))
        
        # 清理装饰性样式
        cleaned_content = content
        removed_count = 0
        
        # 匹配CSS规则
        css_rules = re.findall(r'([^{}]+)\s*\{[^{}]*\}', content)
        
        for rule in css_rules:
            # 分割多个选择器
            selectors = [s.strip() for s in rule.split(',')]
            
            # 检查是否包含装饰性选择器
            has_decorative = any(is_decorative_selector(sel) for sel in selectors)
            
            if has_decorative:
                # 构建完整的规则模式
                full_rule_pattern = re.escape(rule) + r'\s*\{[^{}]*\}'
                # 移除规则
                cleaned_content = re.sub(full_rule_pattern, '', cleaned_content, flags=re.MULTILINE)
                removed_count += 1
                print(f"   ❌ 移除装饰性规则: {rule.strip()}")
        
        # 清理多余的空行
        cleaned_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_content)
        
        # 统计清理后的规则数
        final_rules = len(re.findall(r'[^{}]+{[^{}]*}', cleaned_content))
        
        # 写回文件
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"   ✅ 清理完成: 移除了 {removed_count} 个装饰性规则")
        print(f"   📊 规则数量: {original_rules} → {final_rules}")
        
        return removed_count, original_rules, final_rules
        
    except Exception as e:
        print(f"   ❌ 清理失败: {e}")
        return 0, 0, 0

def main():
    """主函数"""
    print("🎨 安全CSS清理工具")
    print("=" * 50)
    print("只清理装饰性样式：动画效果、阴影效果、渐变效果")
    print()
    
    # 检查是否在项目根目录
    if not os.path.exists('app'):
        print("❌ 请在项目根目录运行此脚本")
        return
    
    # 收集所有CSS文件
    css_files = []
    for root, dirs, files in os.walk('app/static/css'):
        for file in files:
            if file.endswith('.css'):
                css_files.append(os.path.join(root, file))
    
    print(f"📁 找到 {len(css_files)} 个CSS文件")
    print()
    
    total_removed = 0
    total_original = 0
    total_final = 0
    
    # 清理每个文件
    for css_file in css_files:
        removed, original, final = clean_css_file(css_file)
        total_removed += removed
        total_original += original
        total_final += final
        print()
    
    # 生成清理报告
    report_file = "safe_css_cleanup_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 安全CSS清理报告\n\n")
        f.write(f"**清理时间**: {os.popen('date').read().strip()}\n\n")
        f.write("## 清理策略\n\n")
        f.write("只清理明确未使用的装饰性样式：\n\n")
        f.write("- 动画效果类（`.fade-in`, `.slide-*`）\n")
        f.write("- 阴影效果类（`.shadow-*`）\n")
        f.write("- 渐变效果类（`.gradient-*`）\n")
        f.write("- 其他装饰性样式（`.glass-effect`, `.pattern-*`等）\n\n")
        f.write("## 清理结果\n\n")
        f.write(f"- **处理文件数**: {len(css_files)}\n")
        f.write(f"- **移除规则数**: {total_removed}\n")
        f.write(f"- **原始规则数**: {total_original}\n")
        f.write(f"- **最终规则数**: {total_final}\n")
        f.write(f"- **清理率**: {(total_removed/total_original*100):.1f}%\n\n")
        f.write("## 备份文件\n\n")
        f.write("所有原始文件都已备份为 `.backup` 文件，如需恢复可重命名备份文件。\n")
    
    print("🎉 清理完成！")
    print(f"📊 总计移除: {total_removed} 个装饰性规则")
    print(f"📄 详细报告: {report_file}")
    print()
    print("💡 提示: 所有原始文件都已备份，如需恢复可重命名 .backup 文件")

if __name__ == "__main__":
    main()
