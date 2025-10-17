#!/usr/bin/env python3
"""
清理 JavaScript 文件中的 console.log 调试日志
包括注释的和未注释的 console 语句
"""

import os
import re
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
JS_DIR = PROJECT_ROOT / "app" / "static" / "js"

# 需要保留的 console 语句（错误处理相关）
KEEP_PATTERNS = [
    r'console\.error\(',  # 保留错误日志
    r'console\.warn\(',   # 保留警告日志
]

# 需要删除的 console 语句模式
REMOVE_PATTERNS = [
    # 注释的 console 语句
    r'^\s*//\s*console\.log\(.*?\);?\s*$',
    r'^\s*//\s*console\.debug\(.*?\);?\s*$',
    r'^\s*//\s*console\.info\(.*?\);?\s*$',
    r'^\s*// // console\.log\(.*?\);?\s*$',  # 双注释
    
    # 未注释的 console.log 和 console.debug
    r'^\s*console\.log\(.*?\);?\s*$',
    r'^\s*console\.debug\(.*?\);?\s*$',
    r'^\s*console\.info\(.*?\);?\s*$',
]


def should_keep_line(line):
    """判断是否应该保留这一行"""
    # 检查是否包含需要保留的模式
    for pattern in KEEP_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def should_remove_line(line):
    """判断是否应该删除这一行"""
    # 如果应该保留，则不删除
    if should_keep_line(line):
        return False
    
    # 检查是否匹配需要删除的模式
    for pattern in REMOVE_PATTERNS:
        if re.match(pattern, line):
            return True
    return False


def clean_file(file_path):
    """清理单个文件中的 console 日志"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤掉需要删除的行
        cleaned_lines = []
        removed_count = 0
        
        for line in lines:
            if should_remove_line(line):
                removed_count += 1
            else:
                cleaned_lines.append(line)
        
        # 如果有修改，写回文件
        if removed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            return removed_count
        
        return 0
    
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return 0


def clean_all_js_files():
    """清理所有 JS 文件"""
    total_removed = 0
    files_modified = 0
    
    # 遍历所有 JS 文件
    for js_file in JS_DIR.rglob("*.js"):
        removed = clean_file(js_file)
        if removed > 0:
            files_modified += 1
            total_removed += removed
            print(f"✓ {js_file.relative_to(PROJECT_ROOT)}: 删除 {removed} 行")
    
    return files_modified, total_removed


def main():
    """主函数"""
    print("开始清理 JavaScript 文件中的 console 日志...")
    print(f"扫描目录: {JS_DIR.relative_to(PROJECT_ROOT)}")
    print()
    
    files_modified, total_removed = clean_all_js_files()
    
    print()
    print("=" * 60)
    print(f"清理完成！")
    print(f"修改文件数: {files_modified}")
    print(f"删除日志行数: {total_removed}")
    print("=" * 60)
    print()
    print("注意: 保留了 console.error() 和 console.warn() 用于错误处理")


if __name__ == "__main__":
    main()
