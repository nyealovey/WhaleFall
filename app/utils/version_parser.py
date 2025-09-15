#!/usr/bin/env python3
"""
数据库版本解析工具
使用正则表达式提取简洁的版本信息
"""

import re
from typing import Dict, Optional, Tuple


class DatabaseVersionParser:
    """数据库版本解析器"""
    
    # 版本提取正则表达式
    VERSION_PATTERNS = {
        'mysql': [
            r'(\d+\.\d+\.\d+)',  # 8.0.32
            r'(\d+\.\d+)',       # 8.0
        ],
        'postgresql': [
            r'PostgreSQL\s+(\d+\.\d+)',  # PostgreSQL 13.4
            r'(\d+\.\d+)',               # 13.4
        ],
        'sqlserver': [
            r'Microsoft SQL Server \d+\s+\([^)]+\)\s+\([^)]+\)\s+-\s+(\d+\.\d+\.\d+\.\d+)',  # 14.0.3465.1
            r'(\d+\.\d+\.\d+\.\d+)',  # 14.0.3465.1
        ],
        'oracle': [
            r'Oracle Database \d+g Release (\d+\.\d+\.\d+\.\d+\.\d+)',  # Oracle Database 11g Release 11.2.0.1.0
            r'(\d+\.\d+\.\d+\.\d+\.\d+)',  # 11.2.0.1.0
        ],
    }
    
    @classmethod
    def parse_version(cls, db_type: str, version_string: str) -> Dict[str, str]:
        """
        解析数据库版本信息
        
        Args:
            db_type: 数据库类型 (mysql, postgresql, sqlserver, oracle)
            version_string: 原始版本字符串
            
        Returns:
            包含主版本和详细版本的字典
        """
        if not version_string or not db_type:
            return {
                'main_version': '未知',
                'detailed_version': '未知',
                'original': version_string or ''
            }
        
        db_type = db_type.lower()
        patterns = cls.VERSION_PATTERNS.get(db_type, [])
        
        # 尝试匹配版本号
        for pattern in patterns:
            match = re.search(pattern, version_string, re.IGNORECASE)
            if match:
                version = match.group(1)
                main_version = cls._extract_main_version(version, db_type)
                return {
                    'main_version': main_version,
                    'detailed_version': version,
                    'original': version_string
                }
        
        # 如果没有匹配到，返回原始字符串
        return {
            'main_version': '未知',
            'detailed_version': version_string[:50] + '...' if len(version_string) > 50 else version_string,
            'original': version_string
        }
    
    @classmethod
    def _extract_main_version(cls, version: str, db_type: str) -> str:
        """
        提取主版本号
        
        Args:
            version: 详细版本号
            db_type: 数据库类型
            
        Returns:
            主版本号
        """
        if not version:
            return '未知'
        
        # 按数据库类型提取主版本
        if db_type == 'mysql':
            # MySQL: 8.0.32 -> 8.0
            parts = version.split('.')
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version
            
        elif db_type == 'postgresql':
            # PostgreSQL: 13.4 -> 13.4
            parts = version.split('.')
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version
            
        elif db_type == 'sqlserver':
            # SQL Server: 14.0.3465.1 -> 14.0
            parts = version.split('.')
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version
            
        elif db_type == 'oracle':
            # Oracle: 11.2.0.1.0 -> 11.2
            parts = version.split('.')
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version
        
        # 默认情况：取前两个部分
        parts = version.split('.')
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return version
    
    @classmethod
    def format_version_display(cls, db_type: str, version_string: str) -> str:
        """
        格式化版本显示
        
        Args:
            db_type: 数据库类型
            version_string: 原始版本字符串
            
        Returns:
            格式化后的版本字符串
        """
        parsed = cls.parse_version(db_type, version_string)
        main_version = parsed['main_version']
        detailed_version = parsed['detailed_version']
        
        if main_version == '未知':
            return detailed_version
        
        if main_version == detailed_version:
            return main_version
        
        return f"{main_version} ({detailed_version})"


# 测试函数
def test_version_parser():
    """测试版本解析器"""
    test_cases = [
        ('mysql', '8.0.32', '8.0', '8.0.32'),
        ('postgresql', 'PostgreSQL 13.4 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 4.8.5 20150623 (Red Hat 4.8.5-44), 64-bit', '13.4', '13.4'),
        ('sqlserver', 'Microsoft SQL Server 2017 (RTM-CU31-GDR) (KB5029376) - 14.0.3465.1 (X64) Jul 30 2023 15:31:58 Copyright (C) 2017 Microsoft Corporation', '14.0', '14.0.3465.1'),
        ('oracle', 'Oracle Database 11g Release 11.2.0.1.0 - 64bit Production', '11.2', '11.2.0.1.0'),
    ]
    
    print("数据库版本解析测试:")
    print("=" * 80)
    
    for db_type, version_string, expected_main, expected_detailed in test_cases:
        result = DatabaseVersionParser.parse_version(db_type, version_string)
        display = DatabaseVersionParser.format_version_display(db_type, version_string)
        
        print(f"数据库类型: {db_type}")
        print(f"原始版本: {version_string[:60]}...")
        print(f"主版本: {result['main_version']} (期望: {expected_main})")
        print(f"详细版本: {result['detailed_version']} (期望: {expected_detailed})")
        print(f"显示格式: {display}")
        print("-" * 80)


if __name__ == "__main__":
    test_version_parser()
