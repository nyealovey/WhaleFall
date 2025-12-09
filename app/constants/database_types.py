"""数据库类型常量.

定义所有支持的数据库类型,避免魔法字符串.
"""


class DatabaseType:
    """数据库类型常量.

    提供标准的数据库类型字符串,提高代码可读性和类型安全.
    """

    # 支持的数据库类型
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"
    SQLITE = "sqlite"

    # 所有支持的类型
    ALL = [MYSQL, POSTGRESQL, SQLSERVER, ORACLE, SQLITE]

    # 主流关系型数据库
    RELATIONAL = [MYSQL, POSTGRESQL, SQLSERVER, ORACLE]

    # 显示名称映射
    DISPLAY_NAMES = {
        MYSQL: "MySQL",
        POSTGRESQL: "PostgreSQL",
        SQLSERVER: "SQL Server",
        ORACLE: "Oracle Database",
        SQLITE: "SQLite",
    }

    # 默认端口映射
    DEFAULT_PORTS = {
        MYSQL: 3306,
        POSTGRESQL: 5432,
        SQLSERVER: 1433,
        ORACLE: 1521,
        SQLITE: None,  # SQLite不需要端口
    }

    # 辅助方法

    @classmethod
    def is_valid(cls, db_type: str) -> bool:
        """验证数据库类型是否有效.

        Args:
            db_type: 数据库类型字符串

        Returns:
            bool: 是否为支持的数据库类型

        """
        return db_type in cls.ALL

    @classmethod
    def get_display_name(cls, db_type: str) -> str:
        """获取数据库类型的显示名称.

        Args:
            db_type: 数据库类型字符串

        Returns:
            str: 显示名称(如果未知则返回原始类型)

        """
        return cls.DISPLAY_NAMES.get(db_type, db_type)

    @classmethod
    def get_default_port(cls, db_type: str) -> int | None:
        """获取数据库类型的默认端口.

        Args:
            db_type: 数据库类型字符串

        Returns:
            int | None: 默认端口号,如果没有则返回None

        """
        return cls.DEFAULT_PORTS.get(db_type)

    @classmethod
    def normalize(cls, db_type: str) -> str:
        """规范化数据库类型字符串(转小写).

        Args:
            db_type: 数据库类型字符串

        Returns:
            str: 规范化后的数据库类型

        """
        normalized = db_type.lower().strip()

        # 处理常见的别名
        aliases = {
            "mssql": cls.SQLSERVER,
            "sql server": cls.SQLSERVER,
            "postgres": cls.POSTGRESQL,
            "pg": cls.POSTGRESQL,
        }

        return aliases.get(normalized, normalized)

    @classmethod
    def requires_port(cls, db_type: str) -> bool:
        """判断数据库类型是否需要端口配置.

        Args:
            db_type: 数据库类型字符串

        Returns:
            bool: 是否需要端口

        """
        return cls.get_default_port(db_type) is not None
