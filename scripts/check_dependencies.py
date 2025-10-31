#!/usr/bin/env python3
"""
依赖规则检查脚本
检查项目中的依赖是否符合分层架构规则

规则：
- utils 不应该依赖 services/routes/tasks
- common 不应该依赖 components（前端）
"""

import os
import re
from pathlib import Path
from typing import List, Dict

class DependencyChecker:
    def __init__(self, project_root: str = '.'):
        self.project_root = Path(project_root)
        self.violations = []
    
    def check_python_utils(self) -> List[Dict]:
        """检查 Python utils 目录的依赖"""
        utils_dir = self.project_root / 'app' / 'utils'
        if not utils_dir.exists():
            return []
        
        violations = []
        
        for py_file in utils_dir.glob('*.py'):
            if py_file.name == '__init__.py':
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
            except Exception as e:
                print(f"⚠️  无法读取文件 {py_file}: {e}")
                continue
            
            # 检查是否导入了 services/routes/tasks
            patterns = {
                'services': r'from app\.services',
                'routes': r'from app\.routes',
                'tasks': r'from app\.tasks',
            }
            
            for layer, pattern in patterns.items():
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    # 获取行号
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = content.split('\n')[line_num - 1].strip()
                    
                    violations.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'line': line_num,
                        'content': line_content,
                        'layer': layer,
                        'type': 'python_utils',
                        'message': f'utils 不应该依赖 {layer} 层'
                    })
        
        return violations
    
    def check_js_utils(self) -> List[Dict]:
        """检查 JavaScript utils 目录的依赖"""
        utils_dir = self.project_root / 'app' / 'static' / 'js' / 'utils'
        if not utils_dir.exists():
            return []
        
        violations = []
        
        for js_file in utils_dir.glob('*.js'):
            try:
                content = js_file.read_text(encoding='utf-8')
            except Exception as e:
                print(f"⚠️  无法读取文件 {js_file}: {e}")
                continue
            
            # 检查是否使用了 common 模块
            patterns = {
                'toast': r'window\.toast\.',
                'csrf': r'window\.csrf\.',
                'timeUtils': r'window\.timeUtils\.',
                'permission': r'window\.permission',
                'http': r'window\.http\.',
            }
            
            for module, pattern in patterns.items():
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = content.split('\n')[line_num - 1].strip()
                    
                    violations.append({
                        'file': str(js_file.relative_to(self.project_root)),
                        'line': line_num,
                        'content': line_content,
                        'module': module,
                        'type': 'js_utils',
                        'message': f'utils 不应该依赖 common 模块 ({module})'
                    })
        
        return violations
    
    def check_js_common(self) -> List[Dict]:
        """检查 JavaScript common 目录是否依赖 components"""
        common_dir = self.project_root / 'app' / 'static' / 'js' / 'common'
        if not common_dir.exists():
            return []
        
        violations = []
        
        for js_file in common_dir.rglob('*.js'):
            try:
                content = js_file.read_text(encoding='utf-8')
            except Exception as e:
                print(f"⚠️  无法读取文件 {js_file}: {e}")
                continue
            
            # 检查是否使用了 components
            patterns = {
                'TagSelector': r'new\s+TagSelector\(',
                'ConnectionManager': r'new\s+ConnectionManager\(',
                'PermissionButton': r'new\s+PermissionButton\(',
            }
            
            for component, pattern in patterns.items():
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = content.split('\n')[line_num - 1].strip()
                    
                    violations.append({
                        'file': str(js_file.relative_to(self.project_root)),
                        'line': line_num,
                        'content': line_content,
                        'component': component,
                        'type': 'js_common',
                        'message': f'common 不应该依赖 components ({component})'
                    })
        
        return violations
    
    def run_all_checks(self) -> bool:
        """运行所有检查"""
        print("🔍 开始检查依赖规则...")
        print()
        
        # 检查 Python utils
        print("📦 检查 Python utils 层...")
        py_utils_violations = self.check_python_utils()
        
        # 检查 JS utils
        print("📦 检查 JavaScript utils 层...")
        js_utils_violations = self.check_js_utils()
        
        # 检查 JS common
        print("📦 检查 JavaScript common 层...")
        js_common_violations = self.check_js_common()
        
        # 汇总所有违规
        all_violations = py_utils_violations + js_utils_violations + js_common_violations
        
        print()
        print("=" * 70)
        
        if not all_violations:
            print("✅ 所有依赖检查通过！")
            print()
            print("检查项：")
            print("  ✓ Python utils 不依赖 services/routes/tasks")
            print("  ✓ JavaScript utils 不依赖 common 模块")
            print("  ✓ JavaScript common 不依赖 components")
            return True
        
        # 输出违规信息
        print(f"❌ 发现 {len(all_violations)} 处依赖违规")
        print()
        
        # 按类型分组输出
        violations_by_type = {}
        for v in all_violations:
            vtype = v['type']
            if vtype not in violations_by_type:
                violations_by_type[vtype] = []
            violations_by_type[vtype].append(v)
        
        for vtype, violations in violations_by_type.items():
            if vtype == 'python_utils':
                print("🐍 Python Utils 违规：")
            elif vtype == 'js_utils':
                print("📜 JavaScript Utils 违规：")
            elif vtype == 'js_common':
                print("📜 JavaScript Common 违规：")
            
            for v in violations:
                print(f"  ❌ {v['file']}:{v['line']}")
                print(f"     {v['message']}")
                print(f"     代码: {v['content'][:80]}")
                print()
        
        print("=" * 70)
        print()
        print("💡 修复建议：")
        print("  1. 查看 docs/reports/dependency_violations_report.md 了解详情")
        print("  2. 重构违规代码，遵循分层架构原则")
        print("  3. 如果是 utils 依赖 service，考虑直接使用 service")
        print()
        
        return False

def main():
    """主函数"""
    checker = DependencyChecker()
    success = checker.run_all_checks()
    
    exit(0 if success else 1)

if __name__ == '__main__':
    main()
