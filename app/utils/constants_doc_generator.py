"""
鲸落 - 常量文档生成器
自动生成常量文档，包括使用统计和依赖分析
"""

import ast
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from app.utils.time_utils import time_utils

from app.constants import (
    CacheKeys,
    DangerousPatterns,
    DefaultConfig,
    ErrorMessages,
    FieldLengths,
    LogLevel,
    LogType,
    Pagination,
    RegexPatterns,
    SuccessMessages,
    SyncType,
    SystemConstants,
    TaskStatus,
    TimeFormats,
    UserRole,
)


class ConstantsDocGenerator:
    """常量文档生成器"""

    def __init__(self, project_root: str = None):
        """
        初始化常量文档生成器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root or str(Path(__file__).parent.parent.parent)
        self.app_dir = os.path.join(self.project_root, "app")
        self.docs_dir = os.path.join(self.project_root, "docs")
        self.constants_usage = defaultdict(list)
        self.constants_dependencies = defaultdict(set)
        self.constants_definitions = {}

    def generate_doc(self) -> str:
        """
        生成常量文档

        Returns:
            str: 生成的文档内容
        """
        # 分析常量使用情况
        self._analyze_constants_usage()
        
        # 分析常量依赖关系
        self._analyze_constants_dependencies()
        
        # 收集常量定义
        self._collect_constants_definitions()
        
        # 生成文档
        doc = self._build_documentation()
        
        return doc

    def _analyze_constants_usage(self) -> None:
        """分析常量使用情况"""
        for root, dirs, files in os.walk(self.app_dir):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    self._analyze_file_constants_usage(file_path)

    def _analyze_file_constants_usage(self, file_path: str) -> None:
        """分析单个文件的常量使用情况"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 查找常量使用
            for constant_class in self._get_constant_classes():
                for constant_name in self._get_class_constants(constant_class):
                    if self._is_constant_used(content, constant_class, constant_name):
                        self.constants_usage[constant_name].append(file_path)
        
        except Exception as e:
            print(f"分析文件 {file_path} 时出错: {e}")

    def _analyze_constants_dependencies(self) -> None:
        """分析常量依赖关系"""
        for root, dirs, files in os.walk(self.app_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    self._analyze_file_constants_dependencies(file_path)

    def _analyze_file_constants_dependencies(self, file_path: str) -> None:
        """分析单个文件的常量依赖关系"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 查找导入语句
            import_pattern = r"from\s+app\.constants\s+import\s+([^\n]+)"
            matches = re.findall(import_pattern, content)
            
            for match in matches:
                imported_constants = [c.strip() for c in match.split(",")]
                for constant in imported_constants:
                    self.constants_dependencies[constant].add(file_path)
        
        except Exception as e:
            print(f"分析文件 {file_path} 依赖关系时出错: {e}")

    def _collect_constants_definitions(self) -> None:
        """收集常量定义"""
        constants_file = os.path.join(self.app_dir, "constants.py")
        
        try:
            with open(constants_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 解析常量定义
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.constants_definitions[node.name] = self._extract_class_constants(node)
        
        except Exception as e:
            print(f"解析常量定义时出错: {e}")

    def _extract_class_constants(self, class_node: ast.ClassDef) -> Dict[str, Any]:
        """提取类中的常量定义"""
        constants = {}
        
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = self._get_constant_value(node.value)
        
        return constants

    def _get_constant_value(self, value_node: ast.AST) -> Any:
        """获取常量值"""
        if isinstance(value_node, ast.Constant):
            return value_node.value
        elif isinstance(value_node, ast.Str):  # Python < 3.8
            return value_node.s
        elif isinstance(value_node, ast.Num):  # Python < 3.8
            return value_node.n
        elif isinstance(value_node, ast.List):
            return [self._get_constant_value(item) for item in value_node.elts]
        elif isinstance(value_node, ast.Dict):
            return {
                self._get_constant_value(k): self._get_constant_value(v)
                for k, v in zip(value_node.keys, value_node.values)
            }
        else:
            return str(value_node)

    def _get_constant_classes(self) -> List[type]:
        """获取所有常量类"""
        return [
            SystemConstants,
            DefaultConfig,
            ErrorMessages,
            SuccessMessages,
            RegexPatterns,
            DangerousPatterns,
            FieldLengths,
            CacheKeys,
            TimeFormats,
            Pagination,
            LogLevel,
            LogType,
            UserRole,
            TaskStatus,
            SyncType,
        ]

    def _get_class_constants(self, constant_class: type) -> List[str]:
        """获取类中的所有常量"""
        constants = []
        
        for attr_name in dir(constant_class):
            if not attr_name.startswith("_"):
                constants.append(attr_name)
        
        return constants

    def _is_constant_used(self, content: str, constant_class: type, constant_name: str) -> bool:
        """检查常量是否被使用"""
        # 检查直接使用
        patterns = [
            f"{constant_class.__name__}.{constant_name}",
            f"SystemConstants.{constant_name}",
            f"DefaultConfig.{constant_name}",
            f"ErrorMessages.{constant_name}",
            f"SuccessMessages.{constant_name}",
        ]
        
        for pattern in patterns:
            if pattern in content:
                return True
        
        return False

    def _build_documentation(self) -> str:
        """构建文档内容"""
        doc = f"""# 鲸落项目常量文档

## 📋 文档信息

- **生成时间**: {time_utils.format_china_time(time_utils.now())}
- **项目路径**: {self.project_root}
- **常量总数**: {len(self.constants_usage)}
- **使用文件数**: {len(set(file for files in self.constants_usage.values() for file in files))}

## 🔍 常量使用统计

### 使用频率统计

"""
        
        # 按使用频率排序
        usage_stats = sorted(
            self.constants_usage.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        doc += "| 常量名 | 使用次数 | 使用文件 |\n"
        doc += "|--------|----------|----------|\n"
        
        for constant_name, files in usage_stats:
            doc += f"| {constant_name} | {len(files)} | {len(set(files))} |\n"
        
        doc += "\n### 常量定义详情\n\n"
        
        # 生成每个常量类的文档
        for constant_class in self._get_constant_classes():
            doc += self._build_class_documentation(constant_class)
        
        doc += "\n## 📊 依赖关系分析\n\n"
        
        # 生成依赖关系图
        doc += self._build_dependency_graph()
        
        doc += "\n## 🚀 使用建议\n\n"
        
        # 生成使用建议
        doc += self._build_usage_recommendations()
        
        return doc

    def _build_class_documentation(self, constant_class: type) -> str:
        """构建单个常量类的文档"""
        class_name = constant_class.__name__
        doc = f"### {class_name}\n\n"
        
        if hasattr(constant_class, "__doc__") and constant_class.__doc__:
            doc += f"**描述**: {constant_class.__doc__}\n\n"
        
        doc += "| 常量名 | 值 | 类型 | 使用次数 | 描述 |\n"
        doc += "|--------|----|----|----------|------|\n"
        
        constants = self.constants_definitions.get(class_name, {})
        
        for constant_name in dir(constant_class):
            if not constant_name.startswith("_"):
                value = getattr(constant_class, constant_name)
                value_type = type(value).__name__
                usage_count = len(self.constants_usage.get(constant_name, []))
                
                # 获取常量描述（如果有的话）
                description = self._get_constant_description(constant_class, constant_name)
                
                doc += f"| {constant_name} | {value} | {value_type} | {usage_count} | {description} |\n"
        
        doc += "\n"
        return doc

    def _get_constant_description(self, constant_class: type, constant_name: str) -> str:
        """获取常量描述"""
        # 这里可以根据常量名称或值提供描述
        descriptions = {
            "DEFAULT_PAGE_SIZE": "默认分页大小",
            "MAX_PAGE_SIZE": "最大分页大小",
            "MIN_PASSWORD_LENGTH": "最小密码长度",
            "MAX_PASSWORD_LENGTH": "最大密码长度",
            "PASSWORD_HASH_ROUNDS": "密码哈希轮数",
            "DEFAULT_CACHE_TIMEOUT": "默认缓存超时时间",
            "CONNECTION_TIMEOUT": "数据库连接超时时间",
            "MAX_RETRY_ATTEMPTS": "最大重试次数",
            "JWT_ACCESS_TOKEN_EXPIRES": "JWT访问令牌过期时间",
            "SESSION_LIFETIME": "会话生命周期",
        }
        
        return descriptions.get(constant_name, "无描述")

    def _build_dependency_graph(self) -> str:
        """构建依赖关系图"""
        doc = "```mermaid\ngraph TD\n"
        
        # 添加节点
        for constant_name in self.constants_dependencies:
            doc += f'    {constant_name}["{constant_name}"]\n'
        
        # 添加依赖关系
        for constant_name, files in self.constants_dependencies.items():
            for file in files:
                file_name = os.path.basename(file)
                doc += f'    {constant_name} --> {file_name}\n'
        
        doc += "```\n\n"
        return doc

    def _build_usage_recommendations(self) -> str:
        """构建使用建议"""
        doc = "### 高频使用常量\n\n"
        
        # 获取使用频率最高的常量
        high_usage = [name for name, files in self.constants_usage.items() if len(files) >= 5]
        
        if high_usage:
            doc += "以下常量使用频率较高，建议优先优化：\n\n"
            for constant_name in high_usage:
                doc += f"- `{constant_name}`: 使用 {len(self.constants_usage[constant_name])} 次\n"
        else:
            doc += "暂无高频使用常量\n"
        
        doc += "\n### 未使用常量\n\n"
        
        # 获取未使用的常量
        all_constants = set()
        for constant_class in self._get_constant_classes():
            for constant_name in self._get_class_constants(constant_class):
                all_constants.add(constant_name)
        
        unused_constants = all_constants - set(self.constants_usage.keys())
        
        if unused_constants:
            doc += "以下常量未被使用，建议考虑删除：\n\n"
            for constant_name in sorted(unused_constants):
                doc += f"- `{constant_name}`\n"
        else:
            doc += "所有常量都有被使用\n"
        
        doc += "\n### 优化建议\n\n"
        doc += "1. **统一常量命名**: 确保常量命名规范一致\n"
        doc += "2. **添加常量注释**: 为每个常量添加详细注释\n"
        doc += "3. **优化常量组织**: 按功能模块重新组织常量\n"
        doc += "4. **清理未使用常量**: 删除未使用的常量定义\n"
        doc += "5. **添加常量验证**: 为常量值添加验证机制\n"
        
        return doc

    def save_doc(self, output_file: str = None) -> str:
        """
        保存文档到文件

        Args:
            output_file: 输出文件路径

        Returns:
            str: 保存的文件路径
        """
        if not output_file:
            output_file = os.path.join(self.docs_dir, "constants", "CONSTANTS_DOCUMENTATION.md")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 生成文档
        doc = self.generate_doc()
        
        # 保存文档
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(doc)
        
        return output_file

    def generate_usage_report(self) -> Dict[str, Any]:
        """
        生成使用报告

        Returns:
            Dict: 使用报告数据
        """
        return {
            "total_constants": len(self.constants_usage),
            "total_files": len(set(file for files in self.constants_usage.values() for file in files)),
            "usage_stats": dict(self.constants_usage),
            "dependencies": dict(self.constants_dependencies),
            "definitions": self.constants_definitions,
            "high_usage_constants": [name for name, files in self.constants_usage.items() if len(files) >= 5],
            "unused_constants": self._get_unused_constants(),
        }

    def _get_unused_constants(self) -> List[str]:
        """获取未使用的常量"""
        all_constants = set()
        for constant_class in self._get_constant_classes():
            for constant_name in self._get_class_constants(constant_class):
                all_constants.add(constant_name)
        
        return list(all_constants - set(self.constants_usage.keys()))


def main():
    """主函数"""
    generator = ConstantsDocGenerator()
    
    # 生成文档
    output_file = generator.save_doc()
    print(f"常量文档已生成: {output_file}")
    
    # 生成使用报告
    report = generator.generate_usage_report()
    print(f"常量使用报告已生成: {len(report['total_constants'])} 个常量")
    print(f"使用文件数: {report['total_files']}")
    print(f"高频使用常量: {len(report['high_usage_constants'])} 个")
    print(f"未使用常量: {len(report['unused_constants'])} 个")


if __name__ == "__main__":
    main()
