"""数据库类型常量.

定义所有支持的数据库类型,避免魔法字符串.
"""

from __future__ import annotations

from typing import ClassVar


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

    ALL: ClassVar[tuple[str, ...]] = (MYSQL, POSTGRESQL, SQLSERVER, ORACLE, SQLITE)
    RELATIONAL: ClassVar[tuple[str, ...]] = (MYSQL, POSTGRESQL, SQLSERVER, ORACLE)

    DISPLAY_NAMES: ClassVar[dict[str, str]] = {
        MYSQL: "MySQL",
        POSTGRESQL: "PostgreSQL",
        SQLSERVER: "SQL Server",
        ORACLE: "Oracle Database",
        SQLITE: "SQLite",
    }

    ICONS: ClassVar[dict[str, str]] = {
        MYSQL: "fa-database",
        POSTGRESQL: "fa-database",
        SQLSERVER: "fa-server",
        ORACLE: "fa-database",
        SQLITE: "fa-database",
    }

    COLORS: ClassVar[dict[str, str]] = {
        MYSQL: "primary",
        POSTGRESQL: "info",
        SQLSERVER: "warning",
        ORACLE: "danger",
        SQLITE: "secondary",
    }

    DEFAULT_PORTS: ClassVar[dict[str, int | None]] = {
        MYSQL: 3306,
        POSTGRESQL: 5432,
        SQLSERVER: 1433,
        ORACLE: 1521,
        SQLITE: None,  # SQLite不需要端口
    }

    DEFAULT_SCHEMAS: ClassVar[dict[str, str]] = {
        MYSQL: "mysql",
        POSTGRESQL: "postgres",
        SQLSERVER: "master",
        ORACLE: "ORCL",
        SQLITE: "",
    }
