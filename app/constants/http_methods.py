"""HTTP方法常量.

定义标准的HTTP请求方法,避免魔法字符串.
"""

from typing import ClassVar


class HttpMethod:
    """HTTP方法常量.

    定义标准的HTTP请求方法(RFC 7231).
    """

    # 标准HTTP方法
    GET: ClassVar[str] = "GET"           # 获取资源
    POST: ClassVar[str] = "POST"         # 创建资源
    PUT: ClassVar[str] = "PUT"           # 更新资源(完整)
    PATCH: ClassVar[str] = "PATCH"       # 更新资源(部分)
    DELETE: ClassVar[str] = "DELETE"     # 删除资源
    HEAD: ClassVar[str] = "HEAD"         # 获取资源头信息
    OPTIONS: ClassVar[str] = "OPTIONS"   # 获取资源支持的方法
    TRACE: ClassVar[str] = "TRACE"       # 回显请求
    CONNECT: ClassVar[str] = "CONNECT"   # 建立隧道连接

    ALL: ClassVar[tuple[str, ...]] = (
        GET,
        POST,
        PUT,
        PATCH,
        DELETE,
        HEAD,
        OPTIONS,
        TRACE,
        CONNECT,
    )

    SAFE_METHODS: ClassVar[tuple[str, ...]] = (GET, HEAD, OPTIONS)

    IDEMPOTENT_METHODS: ClassVar[tuple[str, ...]] = (GET, PUT, DELETE, HEAD, OPTIONS)

    WRITE_METHODS: ClassVar[tuple[str, ...]] = (POST, PUT, PATCH, DELETE)

    READ_METHODS: ClassVar[tuple[str, ...]] = (GET, HEAD, OPTIONS)

    # 辅助方法

    @classmethod
    def is_safe(cls, method: str) -> bool:
        """判断HTTP方法是否为安全方法.

        安全方法不会修改服务器资源.

        Args:
            method: HTTP方法字符串

        Returns:
            bool: 是否为安全方法

        """
        return method.upper() in cls.SAFE_METHODS

    @classmethod
    def is_idempotent(cls, method: str) -> bool:
        """判断HTTP方法是否为幂等方法.

        幂等方法多次调用的结果与单次调用相同.

        Args:
            method: HTTP方法字符串

        Returns:
            bool: 是否为幂等方法

        """
        return method.upper() in cls.IDEMPOTENT_METHODS

    @classmethod
    def is_write(cls, method: str) -> bool:
        """判断HTTP方法是否为写入方法.

        写入方法会修改服务器资源.

        Args:
            method: HTTP方法字符串

        Returns:
            bool: 是否为写入方法

        """
        return method.upper() in cls.WRITE_METHODS

    @classmethod
    def is_read(cls, method: str) -> bool:
        """判断HTTP方法是否为读取方法.

        读取方法不会修改服务器资源.

        Args:
            method: HTTP方法字符串

        Returns:
            bool: 是否为读取方法

        """
        return method.upper() in cls.READ_METHODS

    @classmethod
    def is_valid(cls, method: str) -> bool:
        """判断HTTP方法是否有效.

        Args:
            method: HTTP方法字符串

        Returns:
            bool: 是否为有效方法

        """
        return method.upper() in cls.ALL
