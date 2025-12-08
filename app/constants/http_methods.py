"""
HTTP方法常量

定义标准的HTTP请求方法，避免魔法字符串。
"""


class HttpMethod:
    """HTTP方法常量
    
    定义标准的HTTP请求方法（RFC 7231）。
    """

    # ============================================================================
    # 标准HTTP方法
    # ============================================================================
    GET = "GET"           # 获取资源
    POST = "POST"         # 创建资源
    PUT = "PUT"           # 更新资源（完整）
    PATCH = "PATCH"       # 更新资源（部分）
    DELETE = "DELETE"     # 删除资源
    HEAD = "HEAD"         # 获取资源头信息
    OPTIONS = "OPTIONS"   # 获取资源支持的方法
    TRACE = "TRACE"       # 回显请求
    CONNECT = "CONNECT"   # 建立隧道连接

    # 所有方法
    ALL = [GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, TRACE, CONNECT]

    # 安全方法（不修改资源）
    SAFE_METHODS = [GET, HEAD, OPTIONS]

    # 幂等方法（多次调用结果相同）
    IDEMPOTENT_METHODS = [GET, PUT, DELETE, HEAD, OPTIONS]

    # 写入方法（会修改资源）
    WRITE_METHODS = [POST, PUT, PATCH, DELETE]

    # 读取方法（不修改资源）
    READ_METHODS = [GET, HEAD, OPTIONS]

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @classmethod
    def is_safe(cls, method: str) -> bool:
        """判断HTTP方法是否为安全方法
        
        安全方法不会修改服务器资源。
        
        Args:
            method: HTTP方法字符串
            
        Returns:
            bool: 是否为安全方法

        """
        return method.upper() in cls.SAFE_METHODS

    @classmethod
    def is_idempotent(cls, method: str) -> bool:
        """判断HTTP方法是否为幂等方法
        
        幂等方法多次调用的结果与单次调用相同。
        
        Args:
            method: HTTP方法字符串
            
        Returns:
            bool: 是否为幂等方法

        """
        return method.upper() in cls.IDEMPOTENT_METHODS

    @classmethod
    def is_write(cls, method: str) -> bool:
        """判断HTTP方法是否为写入方法
        
        写入方法会修改服务器资源。
        
        Args:
            method: HTTP方法字符串
            
        Returns:
            bool: 是否为写入方法

        """
        return method.upper() in cls.WRITE_METHODS

    @classmethod
    def is_read(cls, method: str) -> bool:
        """判断HTTP方法是否为读取方法
        
        读取方法不会修改服务器资源。
        
        Args:
            method: HTTP方法字符串
            
        Returns:
            bool: 是否为读取方法

        """
        return method.upper() in cls.READ_METHODS

    @classmethod
    def is_valid(cls, method: str) -> bool:
        """判断HTTP方法是否有效
        
        Args:
            method: HTTP方法字符串
            
        Returns:
            bool: 是否为有效方法

        """
        return method.upper() in cls.ALL
