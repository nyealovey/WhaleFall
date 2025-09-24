#!/usr/bin/env python3
"""
清理未使用的CSS样式脚本
分析HTML模板和CSS文件，删除未使用的CSS规则
"""

import os
import re
import glob
from pathlib import Path
from collections import defaultdict

def extract_css_selectors(css_content):
    """从CSS内容中提取选择器"""
    selectors = set()
    
    # 移除注释
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    
    # 匹配CSS规则
    css_rules = re.findall(r'([^{}]+)\s*\{[^{}]*\}', css_content)
    
    for rule in css_rules:
        # 分割多个选择器
        rule_selectors = [s.strip() for s in rule.split(',')]
        for selector in rule_selectors:
            if selector and not selector.startswith('@'):
                # 清理选择器
                selector = selector.strip()
                if selector:
                    selectors.add(selector)
    
    return selectors

def extract_html_classes_and_ids(html_content):
    """从HTML内容中提取class和id"""
    classes = set()
    ids = set()
    
    # 提取class属性
    class_matches = re.findall(r'class\s*=\s*["\']([^"\']*)["\']', html_content, re.IGNORECASE)
    for class_str in class_matches:
        for cls in class_str.split():
            if cls.strip():
                classes.add(cls.strip())
    
    # 提取id属性
    id_matches = re.findall(r'id\s*=\s*["\']([^"\']*)["\']', html_content, re.IGNORECASE)
    for id_str in id_matches:
        if id_str.strip():
            ids.add(id_str.strip())
    
    return classes, ids

def is_selector_used(selector, classes, ids):
    """检查CSS选择器是否被使用"""
    # 简单的选择器匹配逻辑
    selector = selector.strip()
    
    # 检查ID选择器
    if selector.startswith('#'):
        id_name = selector[1:].split()[0]  # 取第一个词
        return id_name in ids
    
    # 检查类选择器
    if selector.startswith('.'):
        class_name = selector[1:].split()[0]  # 取第一个词
        return class_name in classes
    
    # 检查标签选择器
    if re.match(r'^[a-zA-Z][a-zA-Z0-9-]*$', selector):
        return True  # 标签选择器通常都会被使用
    
    # 检查复合选择器
    if ' ' in selector or '>' in selector or '+' in selector or '~' in selector:
        # 对于复合选择器，检查是否包含已知的类或ID
        parts = re.split(r'[\s>+~]', selector)
        for part in parts:
            part = part.strip()
            if part.startswith('#'):
                if part[1:] in ids:
                    return True
            elif part.startswith('.'):
                if part[1:] in classes:
                    return True
            elif re.match(r'^[a-zA-Z][a-zA-Z0-9-]*$', part):
                return True  # 标签选择器
    
    # 检查伪类和伪元素
    if ':' in selector:
        base_selector = selector.split(':')[0]
        return is_selector_used(base_selector, classes, ids)
    
    # 检查属性选择器
    if '[' in selector:
        # 简化处理，检查是否包含已知的类或ID
        if '#' in selector:
            id_match = re.search(r'#([a-zA-Z0-9_-]+)', selector)
            if id_match and id_match.group(1) in ids:
                return True
        if '.' in selector:
            class_match = re.search(r'\.([a-zA-Z0-9_-]+)', selector)
            if class_match and class_match.group(1) in classes:
                return True
    
    return False

def analyze_css_usage():
    """分析CSS使用情况"""
    print("🔍 开始分析CSS使用情况...")
    
    # 收集所有HTML模板
    html_files = []
    for root, dirs, files in os.walk('app/templates'):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    print(f"📁 找到 {len(html_files)} 个HTML模板文件")
    
    # 收集所有CSS文件
    css_files = []
    for root, dirs, files in os.walk('app/static/css'):
        for file in files:
            if file.endswith('.css'):
                css_files.append(os.path.join(root, file))
    
    print(f"📁 找到 {len(css_files)} 个CSS文件")
    
    # 提取所有HTML中的类和ID
    all_classes = set()
    all_ids = set()
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
                classes, ids = extract_html_classes_and_ids(content)
                all_classes.update(classes)
                all_ids.update(ids)
        except Exception as e:
            print(f"❌ 读取HTML文件失败: {html_file} - {e}")
    
    print(f"📊 找到 {len(all_classes)} 个CSS类，{len(all_ids)} 个ID")
    
    # 分析每个CSS文件
    unused_rules = {}
    
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            selectors = extract_css_selectors(css_content)
            unused_selectors = []
            
            for selector in selectors:
                if not is_selector_used(selector, all_classes, all_ids):
                    unused_selectors.append(selector)
            
            if unused_selectors:
                unused_rules[css_file] = unused_selectors
                print(f"⚠️  {css_file}: {len(unused_selectors)} 个未使用的选择器")
            else:
                print(f"✅ {css_file}: 所有选择器都被使用")
                
        except Exception as e:
            print(f"❌ 分析CSS文件失败: {css_file} - {e}")
    
    return unused_rules, all_classes, all_ids

def generate_cleanup_report(unused_rules, all_classes, all_ids):
    """生成清理报告"""
    report_file = "unused_css_cleanup_report.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 未使用CSS清理报告\n\n")
        f.write(f"**分析时间**: {os.popen('date').read().strip()}\n\n")
        f.write(f"**发现**: {len(all_classes)} 个CSS类，{len(all_ids)} 个ID\n\n")
        
        if unused_rules:
            f.write(f"**未使用的CSS文件**: {len(unused_rules)} 个\n\n")
            
            for css_file, selectors in unused_rules.items():
                f.write(f"## {css_file}\n\n")
                f.write(f"**未使用选择器数量**: {len(selectors)}\n\n")
                f.write("### 未使用的选择器列表\n\n")
                for selector in sorted(selectors):
                    f.write(f"- `{selector}`\n")
                f.write("\n")
        else:
            f.write("**结果**: 所有CSS选择器都被使用，无需清理！\n")
    
    print(f"📄 清理报告已生成: {report_file}")

def main():
    """主函数"""
    print("🧹 CSS清理工具")
    print("=" * 50)
    
    # 检查是否在项目根目录
    if not os.path.exists('app'):
        print("❌ 请在项目根目录运行此脚本")
        return
    
    # 分析CSS使用情况
    unused_rules, all_classes, all_ids = analyze_css_usage()
    
    # 生成报告
    generate_cleanup_report(unused_rules, all_classes, all_ids)
    
    if unused_rules:
        print(f"\n📊 分析完成！发现 {len(unused_rules)} 个文件包含未使用的CSS")
        print("📄 详细报告请查看: unused_css_cleanup_report.md")
        
        # 询问是否要清理
        response = input("\n❓ 是否要清理未使用的CSS？(y/N): ").strip().lower()
        if response == 'y':
            cleanup_unused_css(unused_rules)
        else:
            print("ℹ️  跳过清理，仅生成报告")
    else:
        print("\n🎉 太棒了！所有CSS选择器都被使用，无需清理！")

def cleanup_unused_css(unused_rules):
    """清理未使用的CSS"""
    print("\n🧹 开始清理未使用的CSS...")
    
    for css_file, unused_selectors in unused_rules.items():
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 创建备份
            backup_file = css_file + '.backup'
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # 移除未使用的规则
            cleaned_content = original_content
            for selector in unused_selectors:
                # 简单的规则移除（可能需要更复杂的逻辑）
                pattern = rf'{re.escape(selector)}\s*\{{[^{{}}]*\}}'
                cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE)
            
            # 清理多余的空行
            cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)
            
            # 写回文件
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            print(f"✅ 已清理: {css_file}")
            print(f"   📁 备份文件: {backup_file}")
            
        except Exception as e:
            print(f"❌ 清理失败: {css_file} - {e}")

if __name__ == "__main__":
    main()
