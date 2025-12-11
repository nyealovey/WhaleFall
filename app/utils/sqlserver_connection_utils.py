"""SQL Server 连接诊断工具.

分析 SQL Server 连接失败的具体原因,提供诊断信息和解决方案建议.
"""

import socket
from typing import Any

from app.utils.structlog_config import get_sync_logger


class SQLServerConnectionDiagnostics:
    """SQL Server 连接诊断工具.

    提供 SQL Server 连接错误的诊断功能,包括错误类型识别、网络检查、
    端口可达性测试和连接字符串建议.

    Attributes:
        diag_logger: 同步日志记录器.

    Example:
        >>> diag = SQLServerConnectionDiagnostics()
        >>> result = diag.diagnose_connection_error("Login failed", "localhost", 1433)
        >>> result['error_type']
        'authentication_failed'

    """

    def __init__(self) -> None:
        """初始化 SQL Server 连接诊断工具."""
        self.diag_logger = get_sync_logger()

    def diagnose_connection_error(self, error_message: str, host: str, port: int) -> dict[str, Any]:
        """诊断 SQL Server 连接错误.

        分析错误消息,识别错误类型,执行网络和端口检查,提供可能的原因和解决方案.

        Args:
            error_message: 连接错误消息.
            host: 数据库主机地址.
            port: 数据库端口号.

        Returns:
            诊断结果字典,包含以下字段:
            - host: 主机地址
            - port: 端口号
            - error_message: 错误消息
            - error_type: 错误类型(authentication_failed、connection_failed、timeout 等)
            - possible_causes: 可能的原因列表
            - solutions: 解决方案建议列表
            - network_check: 网络连通性检查结果
            - port_check: 端口可达性检查结果

        Example:
            >>> diag = SQLServerConnectionDiagnostics()
            >>> result = diag.diagnose_connection_error("Error 18456", "localhost", 1433)
            >>> result['error_type']
            'authentication_failed'

        """
        diagnosis = {
            "host": host,
            "port": port,
            "error_message": error_message,
            "error_type": "unknown",
            "possible_causes": [],
            "solutions": [],
            "network_check": False,
            "port_check": False,
        }

        # 分析错误类型
        if "18456" in error_message:
            diagnosis["error_type"] = "authentication_failed"
            diagnosis["possible_causes"] = [
                "用户名或密码不正确",
                "SQL Server认证模式设置问题",
                "用户账户被禁用或锁定",
                "数据库不存在或用户无访问权限",
            ]
            diagnosis["solutions"] = [
                "检查用户名和密码是否正确",
                "确认SQL Server使用混合认证模式",
                "检查用户账户状态",
                "验证用户是否有登录权限",
            ]
        elif "20018" in error_message:
            diagnosis["error_type"] = "general_sql_server_error"
            diagnosis["possible_causes"] = [
                "SQL Server服务未启动",
                "SQL Server配置错误",
                "数据库损坏或不可用",
                "权限不足",
            ]
            diagnosis["solutions"] = [
                "检查SQL Server服务状态",
                "查看SQL Server错误日志",
                "验证数据库完整性",
                "检查用户权限",
            ]
        elif "20002" in error_message:
            diagnosis["error_type"] = "connection_failed"
            diagnosis["possible_causes"] = [
                "网络连接问题",
                "防火墙阻止连接",
                "SQL Server未监听指定端口",
                "服务器不可达",
            ]
            diagnosis["solutions"] = [
                "检查网络连接",
                "验证防火墙设置",
                "确认SQL Server端口配置",
                "测试服务器可达性",
            ]
        elif "timeout" in error_message.lower():
            diagnosis["error_type"] = "timeout"
            diagnosis["possible_causes"] = [
                "网络延迟过高",
                "SQL Server响应慢",
                "连接超时设置过短",
                "服务器负载过高",
            ]
            diagnosis["solutions"] = [
                "增加连接超时时间",
                "检查网络质量",
                "优化SQL Server性能",
                "检查服务器资源使用",
            ]

        # 执行网络检查
        diagnosis["network_check"] = self._check_network_connectivity(host)
        diagnosis["port_check"] = self._check_port_accessibility(host, port)

        return diagnosis

    def _check_network_connectivity(self, host: str) -> bool:
        """检查网络连通性.

        通过 DNS 解析测试主机是否可达.

        Args:
            host: 主机地址.

        Returns:
            如果主机可达返回 True,否则返回 False.

        """
        try:
            socket.gethostbyname(host)
            return True
        except socket.gaierror:
            return False

    def _check_port_accessibility(self, host: str, port: int) -> bool:
        """检查端口可访问性.

        尝试建立 TCP 连接测试端口是否开放.

        Args:
            host: 主机地址.
            port: 端口号.

        Returns:
            如果端口可访问返回 True,否则返回 False.

        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except OSError:
            return False

    def get_connection_string_suggestions(
        self, host: str, port: int, username: str, database: str = "master"
    ) -> list[str]:
        """获取连接字符串建议.

        生成多种 SQL Server 连接字符串配置建议,包括基本连接、带超时、
        带加密和带重试的配置.

        Args:
            host: 主机地址.
            port: 端口号.
            username: 用户名.
            database: 数据库名称,默认为 'master'.

        Returns:
            连接字符串建议列表.

        Example:
            >>> diag = SQLServerConnectionDiagnostics()
            >>> suggestions = diag.get_connection_string_suggestions("localhost", 1433, "sa")
            >>> len(suggestions) > 0
            True

        """
        suggestions = []

        # 基本连接字符串
        suggestions.append(f"Server={host},{port};Database={database};User Id={username};Password=***;")

        # 带超时的连接字符串
        suggestions.append(
            f"Server={host},{port};Database={database};User Id={username};Password=***;Connection Timeout=60;"
        )

        # 带加密的连接字符串
        suggestions.append(
            f"Server={host},{port};Database={database};User Id={username};Password=***;Encrypt=True;TrustServerCertificate=True;"
        )

        # 带重试的连接字符串
        suggestions.append(
            f"Server={host},{port};Database={database};User Id={username};Password=***;Connection Timeout=60;Command Timeout=300;"
        )

        return suggestions

    def analyze_error_patterns(self, error_message: str) -> dict[str, Any]:
        """分析错误模式.

        通过关键词匹配识别错误消息中的错误类型模式.

        Args:
            error_message: 错误消息.

        Returns:
            错误模式字典,包含以下布尔字段:
            - has_network_error: 是否包含网络错误
            - has_auth_error: 是否包含认证错误
            - has_server_error: 是否包含服务器错误
            - has_permission_error: 是否包含权限错误

        Example:
            >>> diag = SQLServerConnectionDiagnostics()
            >>> patterns = diag.analyze_error_patterns("Login failed for user")
            >>> patterns['has_auth_error']
            True

        """
        return {
            "has_network_error": any(
                keyword in error_message.lower() for keyword in ["timeout", "connection", "network", "unreachable"]
            ),
            "has_auth_error": any(
                keyword in error_message.lower() for keyword in ["login", "authentication", "password", "user"]
            ),
            "has_server_error": any(
                keyword in error_message.lower() for keyword in ["server", "service", "database", "sql"]
            ),
            "has_permission_error": any(
                keyword in error_message.lower() for keyword in ["permission", "access", "denied", "unauthorized"]
            ),
        }


# 创建全局实例
sqlserver_connection_utils = SQLServerConnectionDiagnostics()
