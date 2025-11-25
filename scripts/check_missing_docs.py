#!/usr/bin/env python3
"""
检查缺少文档注释的文件

扫描 app 目录下的所有 Python 和 JavaScript 文件，
检查哪些类、函数缺少完整的文档字符串/JSDoc 注释。
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

# 排除的目录
EXCLUDE_DIRS = {
    '__pycache__',
    '.venv',
    'migrations',
    'vendor',
    'node_modules',
    '.git',
}

# 排除的文件模式
EXCLUDE_FILES = {
    '__init__.py',  # 可选：如果想检查 __init__.py，移除这行
}


class DocChecker:
    """文档检查器。"""
    
    def __init__(self, root_dir: str):
        """初始化检查器。
        
        Args:
            root_dir: 根目录路径。
        """
        self.root_dir = Path(root_dir)
        self.issues: List[Dict] = []
        
    def check_all(self):
        """检查所有文件。"""
        print(f"🔍 开始扫描目录: {self.root_dir}")
        print(f"📁 排除目录: {', '.join(EXCLUDE_DIRS)}\n")
        
        # 检查 Python 文件
        py_files = self._find_files('**/*.py')
        print(f"📄 找到 {len(py_files)} 个 Python 文件")
        for file_path in py_files:
            self._check_python_file(file_path)
        
        # 检查 JavaScript 文件
        js_files = self._find_files('**/*.js')
        print(f"📄 找到 {len(js_files)} 个 JavaScript 文件\n")
        for file_path in js_files:
            self._check_javascript_file(file_path)
        
        self._print_report()
    
    def _find_files(self, pattern: str) -> List[Path]:
        """查找文件。
        
        Args:
            pattern: 文件模式。
            
        Returns:
            文件路径列表。
        """
        files = []
        for file_path in self.root_dir.glob(pattern):
            # 检查是否在排除目录中
            if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
                continue
            # 检查是否是排除的文件
            if file_path.name in EXCLUDE_FILES:
                continue
            if file_path.is_file():
                files.append(file_path)
        return sorted(files)
    
    def _check_python_file(self, file_path: Path):
        """检查 Python 文件。
        
        Args:
            file_path: 文件路径。
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"⚠️  无法读取文件 {file_path}: {e}")
            return
        
        lines = content.split('\n')
        
        # 检查类定义
        for i, line in enumerate(lines):
            # 匹配类定义
            class_match = re.match(r'^class\s+(\w+)', line)
            if class_match:
                class_name = class_match.group(1)
                # 检查下一行是否有文档字符串
                if not self._has_python_docstring(lines, i + 1):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'line': i + 1,
                        'type': 'class',
                        'name': class_name,
                        'language': 'python',
                        'issue': '缺少类文档字符串'
                    })
            
            # 匹配函数/方法定义
            func_match = re.match(r'^(\s*)def\s+(\w+)\s*\(', line)
            if func_match:
                indent = func_match.group(1)
                func_name = func_match.group(2)
                # 跳过私有方法（以 _ 开头但不是 __ 开头和结尾）
                if func_name.startswith('_') and not (func_name.startswith('__') and func_name.endswith('__')):
                    continue
                # 检查下一行是否有文档字符串
                if not self._has_python_docstring(lines, i + 1):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'line': i + 1,
                        'type': 'function',
                        'name': func_name,
                        'language': 'python',
                        'issue': '缺少函数文档字符串'
                    })
    
    def _has_python_docstring(self, lines: List[str], start_line: int) -> bool:
        """检查是否有 Python 文档字符串。
        
        Args:
            lines: 文件行列表。
            start_line: 开始行号。
            
        Returns:
            如果有文档字符串返回 True。
        """
        if start_line >= len(lines):
            return False
        
        # 跳过空行和注释
        i = start_line
        while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith('#')):
            i += 1
        
        if i >= len(lines):
            return False
        
        # 检查是否是文档字符串
        line = lines[i].strip()
        return line.startswith('"""') or line.startswith("'''")
    
    def _check_javascript_file(self, file_path: Path):
        """检查 JavaScript 文件。
        
        Args:
            file_path: 文件路径。
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"⚠️  无法读取文件 {file_path}: {e}")
            return
        
        lines = content.split('\n')
        
        # 检查类定义
        for i, line in enumerate(lines):
            # 匹配类定义
            class_match = re.match(r'^\s*class\s+(\w+)', line)
            if class_match:
                class_name = class_match.group(1)
                # 检查前面是否有 JSDoc
                if not self._has_jsdoc(lines, i):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'line': i + 1,
                        'type': 'class',
                        'name': class_name,
                        'language': 'javascript',
                        'issue': '缺少 JSDoc 注释'
                    })
            
            # 匹配函数定义（function 关键字）
            func_match = re.match(r'^\s*function\s+(\w+)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                # 检查前面是否有 JSDoc
                if not self._has_jsdoc(lines, i):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'line': i + 1,
                        'type': 'function',
                        'name': func_name,
                        'language': 'javascript',
                        'issue': '缺少 JSDoc 注释'
                    })
            
            # 匹配箭头函数赋值
            arrow_match = re.match(r'^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>', line)
            if arrow_match:
                func_name = arrow_match.group(1)
                # 检查前面是否有 JSDoc
                if not self._has_jsdoc(lines, i):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'line': i + 1,
                        'type': 'function',
                        'name': func_name,
                        'language': 'javascript',
                        'issue': '缺少 JSDoc 注释'
                    })
    
    def _has_jsdoc(self, lines: List[str], line_num: int) -> bool:
        """检查是否有 JSDoc 注释。
        
        Args:
            lines: 文件行列表。
            line_num: 当前行号。
            
        Returns:
            如果有 JSDoc 注释返回 True。
        """
        # 向上查找 JSDoc 注释
        i = line_num - 1
        # 跳过空行
        while i >= 0 and not lines[i].strip():
            i -= 1
        
        if i < 0:
            return False
        
        # 检查是否是 JSDoc 结束标记
        if lines[i].strip() == '*/':
            # 继续向上查找开始标记
            while i >= 0:
                if '/**' in lines[i]:
                    return True
                i -= 1
        
        return False
    
    def _print_report(self):
        """打印报告。"""
        print("\n" + "="*80)
        print("📊 检查报告")
        print("="*80 + "\n")
        
        if not self.issues:
            print("✅ 太棒了！所有文件都有完整的文档注释！\n")
            return
        
        # 按文件分组
        issues_by_file: Dict[str, List[Dict]] = {}
        for issue in self.issues:
            file_path = issue['file']
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        # 统计
        total_files = len(issues_by_file)
        total_issues = len(self.issues)
        python_issues = sum(1 for i in self.issues if i['language'] == 'python')
        js_issues = sum(1 for i in self.issues if i['language'] == 'javascript')
        
        print(f"⚠️  发现 {total_issues} 个问题，涉及 {total_files} 个文件")
        print(f"   - Python: {python_issues} 个问题")
        print(f"   - JavaScript: {js_issues} 个问题\n")
        
        # 打印详细信息
        for file_path in sorted(issues_by_file.keys()):
            issues = issues_by_file[file_path]
            print(f"\n📄 {file_path} ({len(issues)} 个问题)")
            print("-" * 80)
            for issue in issues:
                icon = "🐍" if issue['language'] == 'python' else "📜"
                print(f"  {icon} 行 {issue['line']:4d}: {issue['type']:8s} {issue['name']:30s} - {issue['issue']}")
        
        print("\n" + "="*80)
        print(f"总计: {total_issues} 个问题需要修复")
        print("="*80 + "\n")


def main():
    """主函数。"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent / 'app'
    
    if not root_dir.exists():
        print(f"❌ 错误: 目录不存在 {root_dir}")
        return
    
    checker = DocChecker(str(root_dir))
    checker.check_all()


if __name__ == '__main__':
    main()
