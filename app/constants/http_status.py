"""
HTTP状态码常量

参考: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
"""


class HttpStatus:
    """HTTP状态码常量
    
    提供标准的HTTP状态码，提高代码可读性和可维护性。
    """
    
    # ============================================================================
    # 成功响应 2xx
    # ============================================================================
    OK = 200                    # 请求成功
    CREATED = 201               # 资源创建成功
    ACCEPTED = 202              # 请求已接受，但未完成处理
    NO_CONTENT = 204            # 成功，但无返回内容
    
    # ============================================================================
    # 重定向 3xx
    # ============================================================================
    MOVED_PERMANENTLY = 301     # 资源已永久移动
    FOUND = 302                 # 资源临时移动
    NOT_MODIFIED = 304          # 资源未修改
    
    # ============================================================================
    # 客户端错误 4xx
    # ============================================================================
    BAD_REQUEST = 400           # 请求语法错误
    UNAUTHORIZED = 401          # 未授权，需要身份验证
    PAYMENT_REQUIRED = 402      # 保留，未来使用
    FORBIDDEN = 403             # 服务器拒绝请求
    NOT_FOUND = 404             # 资源不存在
    METHOD_NOT_ALLOWED = 405    # 请求方法不允许
    NOT_ACCEPTABLE = 406        # 无法根据Accept头生成响应
    CONFLICT = 409              # 请求冲突
    GONE = 410                  # 资源已永久删除
    UNPROCESSABLE_ENTITY = 422  # 语义错误
    TOO_MANY_REQUESTS = 429     # 请求过多
    
    # ============================================================================
    # 服务器错误 5xx
    # ============================================================================
    INTERNAL_SERVER_ERROR = 500 # 服务器内部错误
    NOT_IMPLEMENTED = 501       # 服务器不支持该功能
    BAD_GATEWAY = 502           # 网关错误
    SERVICE_UNAVAILABLE = 503   # 服务不可用
    GATEWAY_TIMEOUT = 504       # 网关超时
    
    # ============================================================================
    # 辅助方法
    # ============================================================================
    
    @classmethod
    def is_success(cls, status_code: int) -> bool:
        """判断是否为成功状态码 (2xx)
        
        Args:
            status_code: HTTP状态码
            
        Returns:
            bool: 是否为成功状态码
        """
        return 200 <= status_code < 300
    
    @classmethod
    def is_redirect(cls, status_code: int) -> bool:
        """判断是否为重定向状态码 (3xx)
        
        Args:
            status_code: HTTP状态码
            
        Returns:
            bool: 是否为重定向状态码
        """
        return 300 <= status_code < 400
    
    @classmethod
    def is_client_error(cls, status_code: int) -> bool:
        """判断是否为客户端错误 (4xx)
        
        Args:
            status_code: HTTP状态码
            
        Returns:
            bool: 是否为客户端错误
        """
        return 400 <= status_code < 500
    
    @classmethod
    def is_server_error(cls, status_code: int) -> bool:
        """判断是否为服务器错误 (5xx)
        
        Args:
            status_code: HTTP状态码
            
        Returns:
            bool: 是否为服务器错误
        """
        return 500 <= status_code < 600
    
    @classmethod
    def is_error(cls, status_code: int) -> bool:
        """判断是否为错误状态码 (4xx or 5xx)
        
        Args:
            status_code: HTTP状态码
            
        Returns:
            bool: 是否为错误状态码
        """
        return status_code >= 400
