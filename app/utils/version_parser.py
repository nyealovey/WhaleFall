"""数据库版本解析工具
使用正则表达式提取简洁的版本信息.
"""

import re

from app.constants import DatabaseType


class DatabaseVersionParser:
    """数据库版本解析器.

    使用正则表达式从原始版本字符串中提取简洁的版本信息.
    支持 MySQL、PostgreSQL、SQL Server、Oracle 等主流数据库.

    Attributes:
        VERSION_PATTERNS: 各数据库类型的版本提取正则表达式字典.

    Example:
        >>> parser = DatabaseVersionParser()
        >>> result = parser.parse_version('mysql', 'MySQL 8.0.32-community')
        >>> print(result['main_version'])
        '8.0'

    """

    # 版本提取正则表达式
    VERSION_PATTERNS = {
        "mysql": [
            r"(\d+\.\d+\.\d+)",  # 8.0.32
            r"(\d+\.\d+)",  # 8.0
        ],
        "postgresql": [
            r"PostgreSQL\s+(\d+\.\d+)",  # PostgreSQL 13.4
            r"(\d+\.\d+)",  # 13.4
        ],
        "sqlserver": [
            r"Microsoft SQL Server \d+\s+\([^)]+\)\s+\([^)]+\)\s+-\s+(\d+\.\d+\.\d+\.\d+)",  # 14.0.3465.1
            r"(\d+\.\d+\.\d+\.\d+)",  # 14.0.3465.1
        ],
        "oracle": [
            r"Oracle Database \d+g Release (\d+\.\d+\.\d+\.\d+\.\d+)",  # Oracle Database 11g Release 11.2.0.1.0
            r"(\d+\.\d+\.\d+\.\d+\.\d+)",  # 11.2.0.1.0
        ],
    }

    @classmethod
    def parse_version(cls, db_type: str, version_string: str) -> dict[str, str]:
        """解析数据库版本信息.

        从原始版本字符串中提取主版本号和详细版本号.

        Args:
            db_type: 数据库类型,可选值:'mysql'、'postgresql'、'sqlserver'、'oracle'.
            version_string: 原始版本字符串,例如 'MySQL 8.0.32-community'.

        Returns:
            包含以下字段的字典:
            - main_version: 主版本号,例如 '8.0'
            - detailed_version: 详细版本号,例如 '8.0.32'
            - original: 原始版本字符串

        Example:
            >>> result = DatabaseVersionParser.parse_version('mysql', 'MySQL 8.0.32')
            >>> print(result)
            {'main_version': '8.0', 'detailed_version': '8.0.32', 'original': 'MySQL 8.0.32'}

        """
        if not version_string or not db_type:
            return {"main_version": "未知", "detailed_version": "未知", "original": version_string or ""}

        db_type = db_type.lower()
        patterns = cls.VERSION_PATTERNS.get(db_type, [])

        # 尝试匹配版本号
        for pattern in patterns:
            match = re.search(pattern, version_string, re.IGNORECASE)
            if match:
                version = match.group(1)
                main_version = cls._extract_main_version(version, db_type)
                return {"main_version": main_version, "detailed_version": version, "original": version_string}

        # 如果没有匹配到,返回原始字符串
        return {
            "main_version": "未知",
            "detailed_version": version_string[:50] + "..." if len(version_string) > 50 else version_string,
            "original": version_string,
        }

    @classmethod
    def _extract_main_version(cls, version: str, db_type: str) -> str:
        """提取主版本号.

        根据数据库类型从详细版本号中提取主版本号(通常是前两位).

        Args:
            version: 详细版本号,例如 '8.0.32' 或 '11.2.0.1.0'.
            db_type: 数据库类型.

        Returns:
            主版本号,例如 '8.0' 或 '11.2'.

        Example:
            >>> DatabaseVersionParser._extract_main_version('8.0.32', 'mysql')
            '8.0'

        """
        if not version:
            return "未知"

        # 按数据库类型提取主版本
        if db_type == DatabaseType.MYSQL:
            # MySQL: 8.0.32 -> 8.0
            parts = version.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version

        if db_type == DatabaseType.POSTGRESQL:
            # PostgreSQL: 13.4 -> 13.4
            parts = version.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version

        if db_type == DatabaseType.SQLSERVER:
            # SQL Server: 14.0.3465.1 -> 14.0
            parts = version.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version

        if db_type == DatabaseType.ORACLE:
            # Oracle: 11.2.0.1.0 -> 11.2
            parts = version.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            return version

        # 默认情况:取前两个部分
        parts = version.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return version

    @classmethod
    def format_version_display(cls, db_type: str, version_string: str) -> str:
        """格式化版本显示.

        生成适合在界面上显示的版本字符串.

        Args:
            db_type: 数据库类型.
            version_string: 原始版本字符串.

        Returns:
            格式化后的版本字符串.如果主版本和详细版本相同,只返回主版本;
            否则返回 '主版本 (详细版本)' 格式.

        Example:
            >>> DatabaseVersionParser.format_version_display('mysql', 'MySQL 8.0.32')
            '8.0 (8.0.32)'

        """
        parsed = cls.parse_version(db_type, version_string)
        main_version = parsed["main_version"]
        detailed_version = parsed["detailed_version"]

        if main_version == "未知":
            return detailed_version

        if main_version == detailed_version:
            return main_version

        return f"{main_version} ({detailed_version})"
